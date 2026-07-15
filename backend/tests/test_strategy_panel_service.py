from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models import (
    MarketType,
    QuantDatasetManifest,
    StrategyPanelValidationRequest,
    StrategyReturnSeries,
)
from app.services.strategy_panel_service import StrategyPanelValidationService


def _manifest(n: int) -> QuantDatasetManifest:
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    return QuantDatasetManifest(
        dataset_id="strategy-panel-dataset",
        version="v1",
        source="versioned_oos_panel",
        symbol="BTCUSDT",
        market=MarketType.crypto,
        timeframe="1h",
        start_time=start,
        end_time=start + timedelta(hours=n),
        sample_count=n,
        source_sha256="e" * 64,
        is_point_in_time=True,
        is_survivorship_bias_controlled=True,
        is_independent_holdout=False,
        data_quality_score=100,
    )


def _timestamps(n: int):
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    return [start + timedelta(hours=index) for index in range(n)]


def test_consistently_dominant_strategy_is_robustness_candidate():
    n = 800
    levels = [0.50, 0.30, 0.10, -0.10, -0.30]
    strategies = [
        StrategyReturnSeries(
            strategy_id=f"stable-{index}",
            strategy_version="v1",
            returns_rr=[level + (0.05 if i % 2 == 0 else -0.05) for i in range(n)],
        )
        for index, level in enumerate(levels)
    ]
    request = StrategyPanelValidationRequest(
        panel_id="stable-panel",
        panel_version="v1",
        dataset=_manifest(n),
        strategies=strategies,
        timestamps=_timestamps(n),
        block_count=8,
    )
    first = StrategyPanelValidationService().validate(request)
    second = StrategyPanelValidationService().validate(request)

    assert first.status == "ROBUSTNESS_CANDIDATE"
    assert first.cscv_combinations == 70
    assert first.probability_of_backtest_overfitting == 0.0
    assert first.median_selected_oos_rank_percentile == 1.0
    assert first.most_selected_strategy_id == "stable-0"
    assert first.most_selected_strategy_mean_oos_metric > 0
    assert first.actionable_for_live is False
    assert all(first.hard_gates.values())
    assert first.model_dump() == second.model_dump()


def test_block_mined_strategies_are_flagged_high_overfit_risk():
    block_count = 8
    block_size = 100
    n = block_count * block_size
    strategies = []
    for strategy_index in range(block_count):
        returns = []
        for observation in range(n):
            block = observation // block_size
            returns.append(2.0 if block == strategy_index else -0.2)
        strategies.append(
            StrategyReturnSeries(
                strategy_id=f"mined-{strategy_index}",
                strategy_version="v1",
                returns_rr=returns,
            )
        )
    request = StrategyPanelValidationRequest(
        panel_id="mined-panel",
        panel_version="v1",
        dataset=_manifest(n),
        strategies=strategies,
        timestamps=_timestamps(n),
        block_count=block_count,
        selection_metric="expectancy",
    )
    result = StrategyPanelValidationService().validate(request)

    assert result.status == "HIGH_OVERFIT_RISK"
    assert result.probability_of_backtest_overfitting >= 0.80
    assert result.median_selected_oos_rank_percentile <= 0.50
    assert result.actionable_for_live is False
    assert "pbo_at_most_0_20" in result.failed_gates


def test_strategy_panel_rejects_untraceable_dataset():
    n = 400
    manifest = _manifest(n)
    manifest.source_sha256 = None
    manifest.is_point_in_time = False
    strategies = [
        StrategyReturnSeries(
            strategy_id=f"s-{index}",
            strategy_version="v1",
            returns_rr=[0.1 + index * 0.01] * n,
        )
        for index in range(5)
    ]
    result = StrategyPanelValidationService().validate(
        StrategyPanelValidationRequest(
            panel_id="bad-data-panel",
            panel_version="v1",
            dataset=manifest,
            strategies=strategies,
            timestamps=_timestamps(n),
        )
    )
    assert result.status == "REJECT"
    assert "source_fingerprint" in result.failed_gates
    assert "point_in_time_dataset" in result.failed_gates


def test_strategy_panel_contract_rejects_mismatch_odd_blocks_and_duplicate_ids():
    n = 200
    base = StrategyReturnSeries(
        strategy_id="duplicate",
        strategy_version="v1",
        returns_rr=[0.1] * n,
    )
    with pytest.raises(ValueError, match="even"):
        StrategyPanelValidationRequest(
            panel_id="odd-panel",
            panel_version="v1",
            dataset=_manifest(n),
            strategies=[
                base,
                base.model_copy(update={"strategy_id": "b"}),
                base.model_copy(update={"strategy_id": "c"}),
            ],
            block_count=5,
        )
    with pytest.raises(ValueError, match="unique"):
        StrategyPanelValidationRequest(
            panel_id="duplicate-panel",
            panel_version="v1",
            dataset=_manifest(n),
            strategies=[base, base, base],
            block_count=4,
        )
    with pytest.raises(ValueError, match="match dataset"):
        StrategyPanelValidationRequest(
            panel_id="length-panel",
            panel_version="v1",
            dataset=_manifest(n),
            strategies=[
                base,
                base.model_copy(update={"strategy_id": "b", "returns_rr": [0.1] * 199}),
                base.model_copy(update={"strategy_id": "c"}),
            ],
            block_count=4,
        )
