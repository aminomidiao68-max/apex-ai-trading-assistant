from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.models import (
    AutomatedPanelResearchRequest,
    BacktestExecutionSettings,
    Candle,
    MarketType,
    QuantDatasetManifest,
    SignalDirection,
)
from app.services.automated_panel_service import AutomatedPanelError, AutomatedPanelResearchService
from app.services.backtest_service import BacktestService
from app.services.database_service import DatabaseManager, LATEST_SCHEMA_VERSION
from app.services.deflated_performance_service import DeflatedPerformanceService
from app.services.historical_data_service import HistoricalDatasetStore
from app.services.quant_validation_service import QuantValidationService
from app.services.strategy_panel_service import StrategyPanelValidationService


class _ScoreGradientWinningEngine:
    def analyze(self, request):
        index = int(request.candles[-1].volume)
        score = 50.0 + float(index % 45)
        return SimpleNamespace(
            direction=SignalDirection.buy,
            score=score,
            entry_low=100.0,
            entry_high=100.0,
            stop_loss=98.0,
            take_profits=[101.0, 102.0, 103.0],
        )


def _service(tmp_path):
    database = DatabaseManager(db_path=str(tmp_path / "automated.db"))
    store = HistoricalDatasetStore(database)
    start = datetime(2019, 1, 1, tzinfo=timezone.utc)
    candles = [
        Candle(
            timestamp=start + timedelta(hours=index),
            open=100.0,
            high=101.5,
            low=99.0,
            close=100.5,
            volume=float(index),
        )
        for index in range(380)
    ]
    manifest = QuantDatasetManifest(
        dataset_id="automated-panel-data",
        version="v1",
        source="versioned_fixture",
        symbol="BTCUSDT",
        market=MarketType.crypto,
        timeframe="1h",
        start_time=candles[0].timestamp,
        end_time=candles[-1].timestamp,
        sample_count=len(candles),
        source_sha256="1" * 64,
        is_point_in_time=True,
        is_survivorship_bias_controlled=True,
        is_independent_holdout=False,
        data_quality_score=100,
    )
    store.save(1, manifest, "2" * 64, candles)
    service = AutomatedPanelResearchService(
        database,
        store,
        BacktestService(_ScoreGradientWinningEngine()),
        StrategyPanelValidationService(),
        QuantValidationService(),
        DeflatedPerformanceService(),
    )
    return service, database


def _request(**overrides):
    values = {
        "experiment_id": "locked-panel-experiment",
        "experiment_version": "v1",
        "dataset_id": "automated-panel-data",
        "dataset_version": "v1",
        "holdout_fraction": 0.40,
        "holdout_embargo_bars": 3,
        "window_sizes": [20],
        "lookahead_options": [3],
        "score_thresholds": [50, 60, 70, 80, 90],
        "take_profit_indices": [0],
        "pbo_block_count": 8,
        "selection_metric": "expectancy",
        "minimum_development_trades": 20,
        "minimum_holdout_trades": 50,
        "bootstrap_samples": 500,
        "monte_carlo_paths": 500,
        "random_seed": 77,
        "execution": BacktestExecutionSettings(
            fee_bps_per_side=0,
            spread_bps=0,
            slippage_bps=0,
            entry_expiry_bars=1,
            prevent_overlapping_trades=True,
        ),
    }
    values.update(overrides)
    return AutomatedPanelResearchRequest(**values)


def test_automated_panel_locks_holdout_selects_on_development_and_reuses_result(tmp_path):
    service, database = _service(tmp_path)
    request = _request()
    first = service.run(1, request)
    repeated = service.run(1, request)

    assert first.parameter_combinations == 5
    assert first.eligible_panel_strategies == 5
    assert first.panel_validation is not None
    assert first.panel_validation.status == "ROBUSTNESS_CANDIDATE"
    assert first.selected_configuration is not None
    assert first.holdout_backtest is not None
    assert first.holdout_backtest.activated_signals >= 100
    assert first.deflated_performance is not None
    assert first.deflated_performance.active_return_count >= 100
    assert first.holdout_quant_validation is not None
    assert first.status == "FINAL_HOLDOUT_CANDIDATE"
    assert first.deflated_performance.eligible is True
    assert all(first.hard_gates.values())
    assert first.actionable_for_live is False
    assert first.holdout_start_index > first.development_end_index + first.holdout_embargo_bars
    assert repeated.experiment_reused is True
    assert repeated.experiment_fingerprint == first.experiment_fingerprint
    assert repeated.holdout_backtest.model_dump() == first.holdout_backtest.model_dump()
    assert database.schema_version() == LATEST_SCHEMA_VERSION == 12

    with database.connection() as conn:
        row = conn.execute(
            "SELECT status, result_json FROM research_experiments WHERE user_id = ?",
            (1,),
        ).fetchone()
    assert row["status"] == "complete"
    assert row["result_json"]


def test_immutable_experiment_version_blocks_holdout_redefinition(tmp_path):
    service, _ = _service(tmp_path)
    service.run(1, _request())
    with pytest.raises(AutomatedPanelError, match="immutable_experiment_version_conflict"):
        service.run(1, _request(holdout_fraction=0.30))


def test_automated_experiment_is_user_scoped(tmp_path):
    service, _ = _service(tmp_path)
    with pytest.raises(AutomatedPanelError, match="historical_dataset_not_found"):
        service.run(2, _request())


def test_automated_panel_contract_caps_grid_and_requires_embargo():
    with pytest.raises(ValueError, match="embargo"):
        _request(holdout_embargo_bars=2)
    with pytest.raises(ValueError, match="100 parameter"):
        _request(
            window_sizes=list(range(20, 30)),
            lookahead_options=list(range(2, 12)),
            score_thresholds=[50, 60],
            take_profit_indices=[0],
            holdout_embargo_bars=12,
        )
