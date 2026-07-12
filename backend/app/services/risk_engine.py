from __future__ import annotations

from app.models import RiskPlan, RiskPlanRequest, SignalDirection


def build_risk_plan(request: RiskPlanRequest) -> RiskPlan:
    settings = request.risk_settings
    stats = request.trade_stats

    warnings: list[str] = []
    is_allowed = True

    if request.direction == SignalDirection.neutral:
        is_allowed = False
        warnings.append("Neutral direction cannot produce a trade plan")
    elif request.direction == SignalDirection.buy and request.stop_loss >= request.entry_price:
        is_allowed = False
        warnings.append("Buy stop-loss must be below entry price")
    elif request.direction == SignalDirection.sell and request.stop_loss <= request.entry_price:
        is_allowed = False
        warnings.append("Sell stop-loss must be above entry price")

    if stats.daily_loss_pct >= settings.max_daily_loss_pct:
        is_allowed = False
        warnings.append("Daily loss limit reached")
    if stats.trades_today >= settings.max_trades_per_day:
        is_allowed = False
        warnings.append("Maximum trades per day reached")
    if stats.consecutive_losses >= settings.max_consecutive_losses:
        is_allowed = False
        warnings.append("Maximum consecutive losses reached")
    if stats.open_positions >= settings.max_open_positions:
        is_allowed = False
        warnings.append("Maximum open positions reached")

    stop_distance = abs(request.entry_price - request.stop_loss)
    risk_amount = settings.account_balance * (settings.risk_per_trade_pct / 100)

    if stop_distance <= 0:
        is_allowed = False
        warnings.append("Invalid stop distance")

    if not is_allowed or stop_distance <= 0:
        position_size_units = 0.0
    else:
        position_size_units = risk_amount / (stop_distance * settings.value_per_point)

    return RiskPlan(
        is_trade_allowed=is_allowed,
        risk_amount=round(risk_amount, 2),
        position_size_units=round(position_size_units, 4),
        stop_distance=round(stop_distance, 6),
        max_loss_amount=round(risk_amount, 2),
        breakeven_rr=settings.breakeven_rr,
        partial_take_profit_rr=settings.partial_tp_rr,
        warnings=warnings,
    )
