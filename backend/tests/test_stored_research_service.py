from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.models import (
    BacktestExecutionSettings,
    Candle,
    MarketType,
    QuantDatasetManifest,
    SignalDirection,
    StoredBacktestResearchRequest,
    StoredWalkForwardResearchRequest,
)
from app.services.backtest_service import BacktestService
from app.services.database_service import DatabaseManager
from app.services.historical_data_service import HistoricalDatasetStore
from app.services.quant_validation_service import QuantValidationService
from app.services.stored_research_service import StoredResearchError, StoredResearchService


class _AlwaysWinningEngine:
    def analyze(self, request):
        return SimpleNamespace(
            direction=SignalDirection.buy,
            score=90.0,
            entry_low=100.0,
            entry_high=100.0,
            stop_loss=98.0,
            take_profits=[101.0, 102.0, 103.0],
        )


def _service(tmp_path):
    database = DatabaseManager(db_path=str(tmp_path / "stored-research.db"))
    store = HistoricalDatasetStore(database)
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    candles = [
        Candle(
            timestamp=start + timedelta(hours=index),
            open=100.0,
            high=101.5,
            low=99.0,
            close=100.5,
            volume=1000,
        )
        for index in range(1000)
    ]
    manifest = QuantDatasetManifest(
        dataset_id="stored-btc-history",
        version="v1",
        source="versioned_fixture",
        symbol="BTCUSDT",
        market=MarketType.crypto,
        timeframe="1h",
        start_time=candles[0].timestamp,
        end_time=candles[-1].timestamp,
        sample_count=len(candles),
        source_sha256="a" * 64,
        is_point_in_time=True,
        is_survivorship_bias_controlled=True,
        is_independent_holdout=True,
        data_quality_score=100,
    )
    store.save(1, manifest, "b" * 64, candles)
    service = StoredResearchService(
        store,
        BacktestService(_AlwaysWinningEngine()),
        QuantValidationService(),
    )
    return service, manifest


def test_fixed_stored_backtest_is_holdout_only_when_config_was_pre_frozen(tmp_path):
    service, manifest = _service(tmp_path)
    frozen = service.run_fixed_backtest(
        1,
        StoredBacktestResearchRequest(
            dataset_id=manifest.dataset_id,
            dataset_version=manifest.version,
            configuration_id="frozen-config-v1",
            configuration_frozen_at=manifest.start_time - timedelta(days=1),
            window_size=20,
            lookahead_candles=3,
            score_threshold=65,
            max_signals=50,
            execution=BacktestExecutionSettings(
                fee_bps_per_side=0,
                spread_bps=0,
                slippage_bps=0,
                entry_expiry_bars=1,
            ),
        ),
    )
    retrospective = service.run_fixed_backtest(
        1,
        StoredBacktestResearchRequest(
            dataset_id=manifest.dataset_id,
            dataset_version=manifest.version,
            configuration_id="retrospective-config",
            window_size=20,
            lookahead_candles=3,
            max_signals=50,
        ),
    )

    assert frozen.evaluation_scope == "fixed_config_holdout"
    assert frozen.configuration_frozen_before_dataset is True
    assert frozen.backtest.activated_signals == 50
    assert frozen.actionable_for_live is False
    assert retrospective.evaluation_scope == "retrospective_not_holdout"
    assert retrospective.configuration_frozen_before_dataset is False
    assert any("retrospective" in item for item in retrospective.limitations)


def test_purged_stored_walk_forward_promotes_only_oos_returns_to_quant(tmp_path):
    service, manifest = _service(tmp_path)
    request = StoredWalkForwardResearchRequest(
        dataset_id=manifest.dataset_id,
        dataset_version=manifest.version,
        train_size=300,
        test_size=200,
        step_size=200,
        embargo_bars=5,
        max_folds=3,
        window_sizes=[20],
        lookahead_options=[3],
        score_thresholds=[65],
        take_profit_indices=[0],
        max_signals_per_fold=200,
        minimum_activated_trades=3,
        bootstrap_samples=500,
        monte_carlo_paths=500,
        execution=BacktestExecutionSettings(
            fee_bps_per_side=0,
            spread_bps=0,
            slippage_bps=0,
            entry_expiry_bars=1,
            prevent_overlapping_trades=True,
        ),
        random_seed=42,
    )
    first = service.run_purged_walk_forward(1, request)
    second = service.run_purged_walk_forward(1, request)

    assert first.fold_count == 3
    assert first.combinations_per_fold == 1
    assert first.total_oos_activated_trades >= 500
    assert first.aggregate_oos_net_rr > 0
    assert first.quant_validation is not None
    assert first.quant_validation.status == "RESEARCH_CANDIDATE"
    assert first.quant_validation.walk_forward.stable is True
    assert first.quant_validation.actionable_for_live is False
    assert first.actionable_for_live is False
    assert all(
        fold.train_end_index + fold.embargo_bars < fold.test_start_index
        for fold in first.folds
    )
    assert all(
        current.test_start_index > previous.test_end_index
        for previous, current in zip(first.folds, first.folds[1:])
    )
    assert first.model_dump() == second.model_dump()


def test_stored_research_is_user_scoped_and_missing_dataset_is_sanitized(tmp_path):
    service, manifest = _service(tmp_path)
    with pytest.raises(StoredResearchError, match="historical_dataset_not_found"):
        service.run_fixed_backtest(
            2,
            StoredBacktestResearchRequest(
                dataset_id=manifest.dataset_id,
                dataset_version=manifest.version,
                configuration_id="other-user",
            ),
        )


def test_walk_forward_contract_rejects_overlap_and_insufficient_embargo():
    with pytest.raises(ValueError, match="step_size"):
        StoredWalkForwardResearchRequest(
            dataset_id="dataset",
            dataset_version="v1",
            train_size=300,
            test_size=100,
            step_size=50,
            embargo_bars=10,
        )
    with pytest.raises(ValueError, match="embargo"):
        StoredWalkForwardResearchRequest(
            dataset_id="dataset",
            dataset_version="v1",
            train_size=300,
            test_size=100,
            step_size=100,
            embargo_bars=2,
            lookahead_options=[6],
        )
