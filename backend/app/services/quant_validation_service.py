from __future__ import annotations

import hashlib
import json
import math
import random
from statistics import mean, median, stdev

from app.models import (
    PurgedSplitPlanRequest,
    PurgedSplitPlanResponse,
    QuantCalibrationDiagnostics,
    QuantInterval,
    QuantValidationRequest,
    QuantValidationResponse,
    QuantWalkForwardDiagnostics,
)


_METHOD_VERSION = "quant_evidence_v1"
_SIMULATION_SAMPLE_CAP = 5_000


def _round(value: float, digits: int = 6) -> float:
    return round(float(value), digits)


def _percentile(sorted_values: list[float], probability: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = max(0.0, min(1.0, probability)) * (len(sorted_values) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def _max_drawdown(values: list[float]) -> float:
    equity = 0.0
    peak = 0.0
    drawdown = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return drawdown


def _profit_factor(values: list[float]) -> float:
    positive = sum(value for value in values if value > 0)
    negative = abs(sum(value for value in values if value < 0))
    if negative <= 0:
        return positive
    return positive / negative


def _analysis_fingerprint(request: QuantValidationRequest) -> str:
    payload = {
        "method": _METHOD_VERSION,
        "strategy_id": request.strategy_id,
        "strategy_version": request.strategy_version,
        "dataset": request.dataset.model_dump(mode="json"),
        "returns_rr": request.returns_rr,
        "timestamps": [item.isoformat() for item in request.timestamps],
        "return_source_indices": request.return_source_indices,
        "benchmark_returns_rr": request.benchmark_returns_rr,
        "predicted_probabilities": request.predicted_probabilities,
        "binary_outcomes": request.binary_outcomes,
        "walk_forward_folds": [item.model_dump(mode="json") for item in request.walk_forward_folds],
        "strategies_tried": request.strategies_tried,
        "seed": request.random_seed,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _simulation_values(values: list[float]) -> tuple[list[float], bool]:
    if len(values) <= _SIMULATION_SAMPLE_CAP:
        return list(values), False
    step = len(values) / _SIMULATION_SAMPLE_CAP
    sampled = [values[min(len(values) - 1, int(index * step))] for index in range(_SIMULATION_SAMPLE_CAP)]
    return sampled, True


def _block_bootstrap_path(values: list[float], rng: random.Random, size: int) -> list[float]:
    n = len(values)
    block_size = max(2, min(n, int(math.sqrt(n))))
    result: list[float] = []
    while len(result) < size:
        start = rng.randrange(n)
        for offset in range(block_size):
            result.append(values[(start + offset) % n])
            if len(result) >= size:
                break
    return result


def _bootstrap_mean_interval(
    values: list[float],
    samples: int,
    confidence: float,
    rng: random.Random,
) -> QuantInterval:
    distribution = []
    for _ in range(samples):
        path = _block_bootstrap_path(values, rng, len(values))
        distribution.append(mean(path))
    distribution.sort()
    alpha = (1.0 - confidence) / 2.0
    return QuantInterval(
        estimate=_round(mean(values)),
        lower=_round(_percentile(distribution, alpha)),
        upper=_round(_percentile(distribution, 1.0 - alpha)),
        confidence_level=confidence,
        method="circular_block_bootstrap",
    )


def _sign_flip_p_value(values: list[float], samples: int, rng: random.Random) -> float:
    observed = mean(values)
    if observed <= 0:
        return 1.0
    exceed = 1
    for _ in range(samples):
        permuted = sum(value if rng.getrandbits(1) else -value for value in values) / len(values)
        if permuted >= observed:
            exceed += 1
    return exceed / (samples + 1)


def _monte_carlo_diagnostics(
    values: list[float],
    paths: int,
    risk_fraction: float,
    ruin_threshold: float,
    rng: random.Random,
) -> tuple[float, float, float, float]:
    drawdowns: list[float] = []
    ruined = 0
    n = len(values)
    for _ in range(paths):
        shuffled = list(values)
        rng.shuffle(shuffled)
        drawdowns.append(_max_drawdown(shuffled))

        equity = 1.0
        peak = 1.0
        path_ruined = False
        for _step in range(n):
            rr = values[rng.randrange(n)]
            equity *= max(0.0, 1.0 + risk_fraction * rr)
            peak = max(peak, equity)
            if equity <= 0.0 or (peak - equity) / peak >= ruin_threshold:
                path_ruined = True
                break
        ruined += int(path_ruined)
    drawdowns.sort()
    return (
        _percentile(drawdowns, 0.50),
        _percentile(drawdowns, 0.95),
        _percentile(drawdowns, 0.99),
        ruined / paths,
    )


def _calibration(
    request: QuantValidationRequest,
    fingerprint: str,
) -> QuantCalibrationDiagnostics:
    if not request.predicted_probabilities:
        return QuantCalibrationDiagnostics(
            available=False,
            failed_requirements=["probability_predictions_not_supplied"],
        )

    probabilities = request.predicted_probabilities
    outcomes = request.binary_outcomes
    n = len(probabilities)
    base_rate = mean(outcomes)
    brier = mean((probability - outcome) ** 2 for probability, outcome in zip(probabilities, outcomes))
    base_brier = mean((base_rate - outcome) ** 2 for outcome in outcomes)
    skill = 1.0 - brier / base_brier if base_brier > 0 else 0.0
    epsilon = 1e-12
    log_loss = -mean(
        outcome * math.log(max(epsilon, min(1.0 - epsilon, probability)))
        + (1 - outcome) * math.log(max(epsilon, min(1.0 - epsilon, 1.0 - probability)))
        for probability, outcome in zip(probabilities, outcomes)
    )

    bins = []
    weighted_gap = 0.0
    max_gap = 0.0
    for index in range(10):
        lower = index / 10.0
        upper = (index + 1) / 10.0
        members = [
            (probability, outcome)
            for probability, outcome in zip(probabilities, outcomes)
            if lower <= probability < upper or (index == 9 and probability == 1.0)
        ]
        if not members:
            continue
        avg_probability = mean(item[0] for item in members)
        observed_rate = mean(item[1] for item in members)
        gap = abs(avg_probability - observed_rate)
        weighted_gap += gap * len(members) / n
        max_gap = max(max_gap, gap)
        bins.append(
            {
                "lower": _round(lower, 3),
                "upper": _round(upper, 3),
                "count": len(members),
                "mean_prediction": _round(avg_probability),
                "observed_rate": _round(observed_rate),
                "absolute_gap": _round(gap),
            }
        )

    requirements = {
        "minimum_500_out_of_sample_predictions": n >= 500,
        "independent_holdout": request.dataset.is_independent_holdout,
        "point_in_time_dataset": request.dataset.is_point_in_time,
        "data_quality_at_least_90": request.dataset.data_quality_score >= 90.0,
        "positive_brier_skill": skill > 0.0,
        "ece_at_most_0_05": weighted_gap <= 0.05,
        "mce_at_most_0_15": max_gap <= 0.15,
    }
    failed = [name for name, passed in requirements.items() if not passed]
    eligible = not failed
    calibration_id = None
    if eligible:
        payload = (
            f"{_METHOD_VERSION}:{fingerprint}:{_round(brier,8)}:"
            f"{_round(weighted_gap,8)}:{n}"
        )
        calibration_id = "cal-" + hashlib.sha256(payload.encode()).hexdigest()[:24]

    return QuantCalibrationDiagnostics(
        available=True,
        sample_count=n,
        brier_score=_round(brier),
        base_rate_brier_score=_round(base_brier),
        brier_skill_score=_round(skill),
        expected_calibration_error=_round(weighted_gap),
        maximum_calibration_error=_round(max_gap),
        log_loss=_round(log_loss),
        reliability_bins=bins,
        eligible_for_calibration=eligible,
        probability_is_calibrated=eligible,
        calibration_id=calibration_id,
        scope="dataset_specific_independent_holdout" if eligible else "diagnostic_only",
        failed_requirements=failed,
    )


def _walk_forward(request: QuantValidationRequest) -> tuple[QuantWalkForwardDiagnostics, bool]:
    folds = sorted(request.walk_forward_folds, key=lambda item: item.test_start_index)
    if not folds:
        return QuantWalkForwardDiagnostics(available=False), False

    overlap = any(
        current.test_start_index <= previous.test_end_index
        for previous, current in zip(folds, folds[1:])
    )
    returns_match = True
    fold_nets = []
    fold_expectancies = []
    source_return_map = (
        dict(zip(request.return_source_indices, request.returns_rr))
        if request.return_source_indices
        else {}
    )
    for fold in folds:
        if fold.test_return_indices:
            if not source_return_map:
                returns_match = False
                expected = []
            else:
                expected = [
                    source_return_map[index]
                    for index in fold.test_return_indices
                    if index in source_return_map
                ]
        else:
            expected = request.returns_rr[fold.test_start_index : fold.test_end_index + 1]
        if len(expected) != len(fold.test_returns_rr) or any(
            abs(left - right) > 1e-12 for left, right in zip(expected, fold.test_returns_rr)
        ):
            returns_match = False
        fold_nets.append(sum(fold.test_returns_rr))
        fold_expectancies.append(mean(fold.test_returns_rr))
    positive_ratio = sum(value > 0 for value in fold_nets) / len(fold_nets)
    stable = (
        len(folds) >= 3
        and not overlap
        and returns_match
        and positive_ratio >= 0.60
        and sum(fold_nets) > 0
    )
    diagnostics = QuantWalkForwardDiagnostics(
        available=True,
        fold_count=len(folds),
        all_boundaries_purged=True,
        positive_fold_ratio=_round(positive_ratio),
        aggregate_test_net_rr=_round(sum(fold_nets)),
        mean_fold_expectancy_rr=_round(mean(fold_expectancies)),
        worst_fold_net_rr=_round(min(fold_nets)),
        selected_config_count=len({fold.selected_config_id for fold in folds}),
        stable=stable,
    )
    return diagnostics, returns_match and not overlap


class QuantValidationService:
    def validate(self, request: QuantValidationRequest) -> QuantValidationResponse:
        fingerprint = _analysis_fingerprint(request)
        values = [float(value) for value in request.returns_rr]
        simulation_values, simulation_capped = _simulation_values(values)
        rng = random.Random(request.random_seed)

        expectancy_interval = _bootstrap_mean_interval(
            simulation_values,
            request.bootstrap_samples,
            request.confidence_level,
            rng,
        )
        benchmark_interval = None
        if request.benchmark_returns_rr:
            differences = [
                strategy - benchmark
                for strategy, benchmark in zip(values, request.benchmark_returns_rr)
            ]
            simulation_differences, _ = _simulation_values(differences)
            benchmark_interval = _bootstrap_mean_interval(
                simulation_differences,
                request.bootstrap_samples,
                request.confidence_level,
                rng,
            )

        sign_flip = _sign_flip_p_value(
            simulation_values,
            request.bootstrap_samples,
            rng,
        )
        adjusted_alpha = 0.05 / request.strategies_tried
        mc_p50, mc_p95, mc_p99, risk_of_ruin = _monte_carlo_diagnostics(
            simulation_values,
            request.monte_carlo_paths,
            request.risk_fraction_per_trade,
            request.ruin_drawdown_threshold,
            rng,
        )
        walk_forward, fold_contract_valid = _walk_forward(request)
        calibration = _calibration(request, fingerprint)

        closed = [value for value in values if value != 0]
        empirical_win_rate = (
            sum(value > 0 for value in closed) / len(closed) * 100.0 if closed else 0.0
        )
        core_gates = {
            "source_fingerprint": request.dataset.source_sha256 is not None,
            "point_in_time_dataset": request.dataset.is_point_in_time,
            "survivorship_bias_controlled": request.dataset.is_survivorship_bias_controlled,
            "independent_holdout": request.dataset.is_independent_holdout,
            "data_quality": request.dataset.data_quality_score >= 90.0,
            "strict_timestamps": bool(request.timestamps),
            "minimum_sample_size": len(values) >= 200,
            "positive_expectancy_interval": expectancy_interval.lower > 0.0,
            "benchmark_available": bool(request.benchmark_returns_rr),
            "benchmark_outperformance": bool(
                benchmark_interval and benchmark_interval.lower > 0.0
            ),
            "multiple_testing_control": sign_flip <= adjusted_alpha,
            "purged_walk_forward_contract": fold_contract_valid,
            "walk_forward_stability": walk_forward.stable,
            "drawdown_budget": _max_drawdown(values) <= request.max_allowed_drawdown_rr,
            "risk_of_ruin_budget": risk_of_ruin <= request.max_allowed_ruin_probability,
        }
        hard_gates = dict(core_gates)
        if calibration.available:
            hard_gates["probability_calibration"] = calibration.probability_is_calibrated

        failed = [name for name, passed in hard_gates.items() if not passed]
        integrity_gates = (
            "source_fingerprint",
            "point_in_time_dataset",
            "data_quality",
            "strict_timestamps",
        )
        if any(not core_gates[name] for name in integrity_gates):
            status = "REJECT"
        elif len(values) < 200 or not request.benchmark_returns_rr or not request.walk_forward_folds:
            status = "INSUFFICIENT_EVIDENCE"
        elif all(core_gates.values()):
            status = "RESEARCH_CANDIDATE"
        else:
            status = "WATCH"

        limitations = [
            "Historical diagnostics do not prove future profitability.",
            "Risk-of-ruin is a simulation estimate, not a calibrated live probability.",
            "Sign-flip testing assumes exchangeability around zero under the null.",
            "PBO/CSCV requires a panel of competing strategy returns and is not inferred from one series.",
            "Live execution remains unauthorized regardless of validation status.",
        ]
        if simulation_capped:
            limitations.append(
                f"Simulation paths used a deterministic {_SIMULATION_SAMPLE_CAP}-observation cap; full-series descriptive metrics remain unchanged."
            )
        if not calibration.available:
            limitations.append("No probability calibration claim is available without predictions and outcomes.")

        return QuantValidationResponse(
            strategy_id=request.strategy_id,
            strategy_version=request.strategy_version,
            dataset_id=request.dataset.dataset_id,
            dataset_version=request.dataset.version,
            analysis_fingerprint=fingerprint,
            status=status,
            sample_count=len(values),
            empirical_win_rate=_round(empirical_win_rate, 4),
            net_rr=_round(sum(values)),
            expectancy_rr=_round(mean(values)),
            median_rr=_round(median(values)),
            standard_deviation_rr=_round(stdev(values) if len(values) > 1 else 0.0),
            profit_factor=_round(_profit_factor(values)),
            max_drawdown_rr=_round(_max_drawdown(values)),
            expectancy_interval=expectancy_interval,
            benchmark_difference_interval=benchmark_interval,
            sign_flip_p_value=_round(sign_flip, 8),
            multiple_testing_alpha=_round(adjusted_alpha, 8),
            multiple_testing_adjusted_significant=sign_flip <= adjusted_alpha,
            monte_carlo_drawdown_p50_rr=_round(mc_p50),
            monte_carlo_drawdown_p95_rr=_round(mc_p95),
            monte_carlo_drawdown_p99_rr=_round(mc_p99),
            simulated_risk_of_ruin=_round(risk_of_ruin, 8),
            walk_forward=walk_forward,
            calibration=calibration,
            hard_gates=hard_gates,
            failed_gates=failed,
            limitations=limitations,
            actionable_for_live=False,
            deterministic_reproducible=True,
            random_seed=request.random_seed,
        )

    def build_split_plan(self, request: PurgedSplitPlanRequest) -> PurgedSplitPlanResponse:
        folds = []
        cursor = 0
        previous_test_end = -1
        overlap = False
        while len(folds) < request.max_folds:
            train_start = cursor
            train_end = train_start + request.train_size - 1
            test_start = train_end + request.embargo_bars + 1
            test_end = test_start + request.test_size - 1
            if test_end >= request.sample_count:
                break
            if test_start <= previous_test_end:
                overlap = True
            folds.append(
                {
                    "fold_id": f"fold-{len(folds) + 1:02d}",
                    "train_start_index": train_start,
                    "train_end_index": train_end,
                    "test_start_index": test_start,
                    "test_end_index": test_end,
                    "embargo_bars": request.embargo_bars,
                }
            )
            previous_test_end = test_end
            cursor += request.step_size

        raw = json.dumps(
            {
                "method": "purged_walk_forward_v1",
                "request": request.model_dump(),
                "folds": folds,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return PurgedSplitPlanResponse(
            sample_count=request.sample_count,
            fold_count=len(folds),
            folds=folds,
            overlap_detected=overlap,
            all_boundaries_purged=all(
                fold["train_end_index"] + fold["embargo_bars"] < fold["test_start_index"]
                for fold in folds
            ),
            plan_fingerprint=hashlib.sha256(raw.encode()).hexdigest(),
        )


quant_validation_service = QuantValidationService()
