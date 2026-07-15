from __future__ import annotations

import hashlib
import itertools
import json
import math
from collections import Counter, defaultdict
from statistics import mean, stdev

from app.models import StrategyPanelValidationRequest, StrategyPanelValidationResponse


_METHOD_VERSION = "cscv_pbo_v1"


def _metric(values: list[float], method: str) -> float:
    if not values:
        return -1e12
    expectancy = mean(values)
    if method == "expectancy":
        return expectancy
    dispersion = stdev(values) if len(values) > 1 else 0.0
    if dispersion <= 1e-12:
        return expectancy * 1_000_000.0
    return expectancy / dispersion


def _rank_percentile(value: float, population: list[float]) -> float:
    if len(population) <= 1:
        return 0.5
    lower = sum(item < value for item in population)
    equal = sum(abs(item - value) <= 1e-12 for item in population)
    average_zero_based_rank = lower + (equal - 1) / 2.0
    return average_zero_based_rank / (len(population) - 1)


def _fingerprint(request: StrategyPanelValidationRequest) -> str:
    payload = {
        "method": _METHOD_VERSION,
        "panel_id": request.panel_id,
        "panel_version": request.panel_version,
        "dataset": request.dataset.model_dump(mode="json"),
        "strategies": [item.model_dump(mode="json") for item in request.strategies],
        "timestamps": [item.isoformat() for item in request.timestamps],
        "block_count": request.block_count,
        "selection_metric": request.selection_metric,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class StrategyPanelValidationService:
    def validate(self, request: StrategyPanelValidationRequest) -> StrategyPanelValidationResponse:
        n = request.dataset.sample_count
        block_size, remainder = divmod(n, request.block_count)
        blocks: list[list[int]] = []
        cursor = 0
        for index in range(request.block_count):
            size = block_size + (1 if index < remainder else 0)
            blocks.append(list(range(cursor, cursor + size)))
            cursor += size

        half = request.block_count // 2
        combinations = list(itertools.combinations(range(request.block_count), half))
        selected_counts: Counter[str] = Counter()
        selected_oos_metrics: dict[str, list[float]] = defaultdict(list)
        rank_percentiles: list[float] = []
        degradations: list[float] = []

        strategy_map = {item.strategy_id: item for item in request.strategies}
        strategy_ids = sorted(strategy_map)
        all_blocks = set(range(request.block_count))
        for train_block_ids in combinations:
            train_blocks = set(train_block_ids)
            test_blocks = all_blocks - train_blocks
            train_indices = [item for block in sorted(train_blocks) for item in blocks[block]]
            test_indices = [item for block in sorted(test_blocks) for item in blocks[block]]
            is_metrics = {}
            oos_metrics = {}
            for strategy_id in strategy_ids:
                returns = strategy_map[strategy_id].returns_rr
                is_metrics[strategy_id] = _metric(
                    [returns[index] for index in train_indices], request.selection_metric
                )
                oos_metrics[strategy_id] = _metric(
                    [returns[index] for index in test_indices], request.selection_metric
                )
            selected = max(strategy_ids, key=lambda key: (is_metrics[key], key))
            selected_counts[selected] += 1
            selected_oos_metrics[selected].append(oos_metrics[selected])
            rank_percentiles.append(
                _rank_percentile(oos_metrics[selected], list(oos_metrics.values()))
            )
            degradations.append(is_metrics[selected] - oos_metrics[selected])

        pbo = sum(percentile <= 0.5 for percentile in rank_percentiles) / len(rank_percentiles)
        sorted_ranks = sorted(rank_percentiles)
        midpoint = len(sorted_ranks) // 2
        if len(sorted_ranks) % 2:
            median_rank = sorted_ranks[midpoint]
        else:
            median_rank = (sorted_ranks[midpoint - 1] + sorted_ranks[midpoint]) / 2.0
        most_selected = None
        most_selected_oos = None
        if selected_counts:
            most_selected = max(sorted(selected_counts), key=lambda key: selected_counts[key])
            values = selected_oos_metrics[most_selected]
            most_selected_oos = mean(values) if values else None

        gates = {
            "source_fingerprint": request.dataset.source_sha256 is not None,
            "point_in_time_dataset": request.dataset.is_point_in_time,
            "survivorship_bias_controlled": request.dataset.is_survivorship_bias_controlled,
            "data_quality": request.dataset.data_quality_score >= 90.0,
            "strict_timestamps": bool(request.timestamps),
            "minimum_observations": n >= 200,
            "minimum_strategy_panel": len(request.strategies) >= 5,
            "sufficient_cscv_combinations": len(combinations) >= 20,
            "pbo_at_most_0_20": pbo <= 0.20,
            "median_oos_rank_at_least_0_60": median_rank >= 0.60,
            "selected_strategy_oos_metric_positive": bool(
                most_selected_oos is not None and most_selected_oos > 0.0
            ),
        }
        failed = [name for name, passed in gates.items() if not passed]
        integrity = (
            "source_fingerprint",
            "point_in_time_dataset",
            "data_quality",
            "strict_timestamps",
        )
        if any(not gates[name] for name in integrity):
            status = "REJECT"
        elif not gates["minimum_strategy_panel"] or not gates["sufficient_cscv_combinations"]:
            status = "INCONCLUSIVE"
        elif all(gates.values()):
            status = "ROBUSTNESS_CANDIDATE"
        elif pbo > 0.20 or not gates["selected_strategy_oos_metric_positive"]:
            status = "HIGH_OVERFIT_RISK"
        else:
            status = "INCONCLUSIVE"

        limitations = [
            "PBO is conditional on the submitted strategy panel and observation period.",
            "CSCV reuses the panel for robustness diagnostics; a final untouched holdout is still required.",
            "A low PBO estimate does not prove future profitability.",
            "Correlated strategy variants reduce the effective diversity of the panel.",
            "No result authorizes live execution.",
        ]
        if request.dataset.is_independent_holdout:
            limitations.append(
                "The dataset is marked independent holdout, but running panel selection on it consumes that holdout for model-selection analysis."
            )

        return StrategyPanelValidationResponse(
            panel_id=request.panel_id,
            panel_version=request.panel_version,
            dataset_id=request.dataset.dataset_id,
            analysis_fingerprint=_fingerprint(request),
            status=status,
            strategy_count=len(request.strategies),
            observation_count=n,
            block_count=request.block_count,
            cscv_combinations=len(combinations),
            selection_metric=request.selection_metric,
            probability_of_backtest_overfitting=round(pbo, 8),
            median_selected_oos_rank_percentile=round(median_rank, 8),
            mean_is_oos_degradation=round(mean(degradations), 8),
            selected_strategy_frequency=dict(sorted(selected_counts.items())),
            most_selected_strategy_id=most_selected,
            most_selected_strategy_mean_oos_metric=(
                round(most_selected_oos, 8) if most_selected_oos is not None else None
            ),
            hard_gates=gates,
            failed_gates=failed,
            limitations=limitations,
            actionable_for_live=False,
            deterministic_reproducible=True,
        )


strategy_panel_validation_service = StrategyPanelValidationService()
