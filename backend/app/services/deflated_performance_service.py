from __future__ import annotations

import math
from statistics import NormalDist, mean, stdev

from app.models import DeflatedPerformanceDiagnostics


_EULER_MASCHERONI = 0.5772156649015329


def _sharpe_like(values: list[float]) -> float:
    if not values:
        return 0.0
    avg = mean(values)
    dispersion = stdev(values) if len(values) > 1 else 0.0
    if dispersion <= 1e-12:
        return avg * 1_000_000.0
    return avg / dispersion


def _moments(values: list[float]) -> tuple[float, float]:
    avg = mean(values)
    centered = [value - avg for value in values]
    m2 = mean(value**2 for value in centered)
    if m2 <= 1e-18:
        return 0.0, 3.0
    m3 = mean(value**3 for value in centered)
    m4 = mean(value**4 for value in centered)
    return m3 / (m2 ** 1.5), m4 / (m2**2)


def _probabilistic_sharpe(
    observed_sharpe: float,
    reference_sharpe: float,
    sample_count: int,
    skewness: float,
    kurtosis: float,
) -> float:
    if sample_count < 2:
        return 0.0
    denominator_squared = (
        1.0
        - skewness * observed_sharpe
        + ((kurtosis - 1.0) / 4.0) * observed_sharpe**2
    )
    if denominator_squared <= 1e-18:
        return 1.0 if observed_sharpe > reference_sharpe else 0.0
    statistic = (
        (observed_sharpe - reference_sharpe)
        * math.sqrt(sample_count - 1)
        / math.sqrt(denominator_squared)
    )
    return NormalDist().cdf(statistic)


def _expected_max_sharpe(panel_sharpes: list[float]) -> float:
    trials = len(panel_sharpes)
    if not panel_sharpes:
        return 0.0
    panel_mean = mean(panel_sharpes)
    if trials <= 1:
        return panel_mean
    panel_std = stdev(panel_sharpes)
    if panel_std <= 1e-12:
        return panel_mean
    normal = NormalDist()
    first_probability = max(1e-12, min(1 - 1e-12, 1.0 - 1.0 / trials))
    second_probability = max(
        1e-12,
        min(1 - 1e-12, 1.0 - 1.0 / (trials * math.e)),
    )
    expected_standard_max = (
        (1.0 - _EULER_MASCHERONI) * normal.inv_cdf(first_probability)
        + _EULER_MASCHERONI * normal.inv_cdf(second_probability)
    )
    return panel_mean + panel_std * expected_standard_max


class DeflatedPerformanceService:
    def evaluate(
        self,
        holdout_returns: list[float],
        development_panel_returns: list[list[float]],
        active_return_count: int,
    ) -> DeflatedPerformanceDiagnostics:
        if not holdout_returns or not development_panel_returns:
            return DeflatedPerformanceDiagnostics(
                available=False,
                failed_requirements=["holdout_or_strategy_panel_missing"],
            )
        sample_count = len(holdout_returns)
        avg = mean(holdout_returns)
        dispersion = stdev(holdout_returns) if sample_count > 1 else 0.0
        observed_sharpe = _sharpe_like(holdout_returns)
        skewness, kurtosis = _moments(holdout_returns)
        panel_sharpes = [_sharpe_like(values) for values in development_panel_returns]
        threshold = _expected_max_sharpe(panel_sharpes)
        psr_zero = _probabilistic_sharpe(
            observed_sharpe,
            0.0,
            sample_count,
            skewness,
            kurtosis,
        )
        dsr = _probabilistic_sharpe(
            observed_sharpe,
            threshold,
            sample_count,
            skewness,
            kurtosis,
        )
        requirements = {
            "minimum_30_holdout_trades": active_return_count >= 30,
            "positive_holdout_expectancy": avg > 0.0,
            "probabilistic_sharpe_at_least_0_95": psr_zero >= 0.95,
            "deflated_sharpe_at_least_0_95": dsr >= 0.95,
            "minimum_three_strategy_trials": len(panel_sharpes) >= 3,
        }
        failed = [name for name, passed in requirements.items() if not passed]
        return DeflatedPerformanceDiagnostics(
            available=True,
            sample_count=sample_count,
            active_return_count=active_return_count,
            mean_rr=round(avg, 8),
            standard_deviation_rr=round(dispersion, 8),
            sharpe_like_per_observation=round(observed_sharpe, 8),
            skewness=round(skewness, 8),
            kurtosis=round(kurtosis, 8),
            probabilistic_sharpe_vs_zero=round(psr_zero, 8),
            expected_max_sharpe_threshold=round(threshold, 8),
            deflated_sharpe_probability=round(dsr, 8),
            strategy_trials=len(panel_sharpes),
            eligible=not failed,
            failed_requirements=failed,
            scope="per_observation_non_annualized",
        )


deflated_performance_service = DeflatedPerformanceService()
