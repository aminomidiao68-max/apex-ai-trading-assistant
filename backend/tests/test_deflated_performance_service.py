from app.services.deflated_performance_service import DeflatedPerformanceService


def test_deflated_performance_rewards_holdout_beyond_panel_selection_threshold():
    panel = []
    for strategy in range(5):
        level = 0.05 + strategy * 0.02
        panel.append([level + (0.02 if index % 2 else -0.02) for index in range(200)])
    holdout = [1.0 + (0.05 if index % 2 else -0.05) for index in range(200)]
    result = DeflatedPerformanceService().evaluate(
        holdout,
        panel,
        active_return_count=120,
    )
    assert result.available is True
    assert result.probabilistic_sharpe_vs_zero >= 0.95
    assert result.deflated_sharpe_probability >= 0.95
    assert result.eligible is True
    assert result.strategy_trials == 5
    assert result.scope == "per_observation_non_annualized"


def test_deflated_performance_rejects_weak_or_small_holdout():
    panel = [[0.2 if index % 2 else -0.1 for index in range(100)] for _ in range(5)]
    holdout = [-0.05 if index % 2 else 0.01 for index in range(100)]
    result = DeflatedPerformanceService().evaluate(
        holdout,
        panel,
        active_return_count=10,
    )
    assert result.eligible is False
    assert "minimum_30_holdout_trades" in result.failed_requirements
    assert "positive_holdout_expectancy" in result.failed_requirements


def test_deflated_performance_missing_panel_fails_closed():
    result = DeflatedPerformanceService().evaluate([0.1] * 50, [], active_return_count=50)
    assert result.available is False
    assert result.eligible is False
