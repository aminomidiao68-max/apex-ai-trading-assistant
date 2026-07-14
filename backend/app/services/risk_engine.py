from __future__ import annotations

import math
import re

from app.models import MarketType, PortfolioPosition, RiskPlan, RiskPlanRequest, SignalDirection


_CORRELATION_THRESHOLD = 0.60
_INDEX_SYMBOLS = {"US30", "DJI", "NAS100", "NDX", "SPX", "SP500", "US500"}
_METAL_SYMBOLS = {"XAUUSD", "XAGUSD", "GOLD", "SILVER"}


def _direction_sign(direction: SignalDirection) -> int:
    if direction == SignalDirection.buy:
        return 1
    if direction == SignalDirection.sell:
        return -1
    return 0


def _clean_symbol(symbol: str) -> str:
    return re.sub(r"[^A-Z]", "", (symbol or "").upper())


def _forex_exposure(symbol: str, direction: SignalDirection) -> dict[str, float]:
    """Return structural currency exposure, not a claimed historical correlation."""
    clean = _clean_symbol(symbol)
    if len(clean) != 6:
        return {}
    sign = _direction_sign(direction)
    if not sign:
        return {}
    return {clean[:3]: float(sign), clean[3:]: float(-sign)}


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    keys = set(left) | set(right)
    dot = sum(left.get(key, 0.0) * right.get(key, 0.0) for key in keys)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm <= 0 or right_norm <= 0:
        return 0.0
    return max(-1.0, min(1.0, dot / (left_norm * right_norm)))


def _structural_alignment(
    candidate_symbol: str,
    candidate_market: MarketType | None,
    candidate_direction: SignalDirection,
    position: PortfolioPosition,
) -> float:
    """Conservative exposure proxy used only when no explicit correlation is supplied.

    The value is labelled structural_proxy in every response. It is never described
    as a measured or calibrated market correlation.
    """
    candidate = _clean_symbol(candidate_symbol)
    existing = _clean_symbol(position.symbol)
    if not candidate or candidate == "UNKNOWN":
        return 0.0

    if candidate_market == MarketType.forex and position.market == MarketType.forex:
        fx_alignment = _cosine(
            _forex_exposure(candidate, candidate_direction),
            _forex_exposure(existing, position.direction),
        )
        if fx_alignment:
            return fx_alignment

    direction_alignment = _direction_sign(candidate_direction) * _direction_sign(position.direction)
    if not direction_alignment:
        return 0.0
    if candidate == existing:
        return float(direction_alignment)
    if candidate_market == MarketType.crypto and position.market == MarketType.crypto:
        return 0.75 * direction_alignment
    if candidate in _INDEX_SYMBOLS and existing in _INDEX_SYMBOLS:
        return 0.80 * direction_alignment
    if candidate in _METAL_SYMBOLS and existing in _METAL_SYMBOLS:
        return 0.70 * direction_alignment
    return 0.0


def _drawdown_multiplier(request: RiskPlanRequest) -> float:
    settings = request.risk_settings
    drawdown = request.trade_stats.current_drawdown_pct
    if drawdown >= settings.max_drawdown_pct:
        return 0.0
    if drawdown <= settings.drawdown_reduction_start_pct:
        return 1.0
    span = settings.max_drawdown_pct - settings.drawdown_reduction_start_pct
    progress = (drawdown - settings.drawdown_reduction_start_pct) / max(span, 1e-9)
    multiplier = 1.0 - progress * (1.0 - settings.min_drawdown_risk_multiplier)
    return max(settings.min_drawdown_risk_multiplier, min(1.0, multiplier))


def _volatility_multiplier(request: RiskPlanRequest) -> float:
    atr_pct = request.atr_pct
    if atr_pct is None:
        return 1.0
    if request.market == MarketType.forex:
        if atr_pct >= 2.0:
            return 0.50
        if atr_pct >= 1.20:
            return 0.70
        if atr_pct >= 0.80:
            return 0.85
        if atr_pct <= 0.03:
            return 0.75
        return 1.0
    if request.market == MarketType.crypto:
        if atr_pct >= 8.0:
            return 0.50
        if atr_pct >= 5.0:
            return 0.70
        if atr_pct >= 3.0:
            return 0.85
        if atr_pct <= 0.08:
            return 0.75
        return 1.0
    if atr_pct >= 5.0:
        return 0.70
    return 1.0


def _correlated_existing_risk(request: RiskPlanRequest) -> tuple[float, str]:
    if not request.open_positions:
        return 0.0, "none"

    correlated = 0.0
    sources: set[str] = set()
    candidate_sign = _direction_sign(request.direction)
    for position in request.open_positions:
        if position.direction == SignalDirection.neutral or position.risk_amount <= 0:
            continue
        if position.correlation_to_candidate is not None:
            alignment = (
                position.correlation_to_candidate
                * candidate_sign
                * _direction_sign(position.direction)
            )
            sources.add("explicit")
        else:
            alignment = _structural_alignment(
                request.symbol,
                request.market,
                request.direction,
                position,
            )
            sources.add("structural_proxy")
        if alignment >= _CORRELATION_THRESHOLD:
            correlated += position.risk_amount

    if not sources:
        source = "none"
    elif len(sources) == 1:
        source = next(iter(sources))
    else:
        source = "mixed_explicit_and_structural_proxy"
    return correlated, source


def build_risk_plan(request: RiskPlanRequest) -> RiskPlan:
    settings = request.risk_settings
    stats = request.trade_stats
    balance = settings.account_balance
    warnings: list[str] = []

    stop_distance = abs(request.entry_price - request.stop_loss)
    spread_known = request.spread_bps is not None
    spread_bps = float(request.spread_bps or 0.0)
    slippage_bps = float(
        settings.default_slippage_bps
        if request.estimated_slippage_bps is None
        else request.estimated_slippage_bps
    )

    drawdown_multiplier = _drawdown_multiplier(request)
    volatility_multiplier = _volatility_multiplier(request)
    execution_multiplier = 1.0
    if spread_bps >= settings.max_spread_bps * 0.75:
        execution_multiplier *= 0.80
    if slippage_bps >= settings.max_slippage_bps * 0.75:
        execution_multiplier *= 0.80
    risk_multiplier = drawdown_multiplier * volatility_multiplier * execution_multiplier

    base_risk_amount = balance * (settings.risk_per_trade_pct / 100.0)
    risk_amount = base_risk_amount * risk_multiplier
    execution_cost_per_unit = request.entry_price * ((spread_bps + 2.0 * slippage_bps) / 10_000.0)
    effective_stop_distance = stop_distance + execution_cost_per_unit

    listed_open_risk = sum(position.risk_amount for position in request.open_positions)
    reported_open_risk = max(
        stats.open_risk_amount,
        balance * (stats.portfolio_heat_pct / 100.0),
    )
    existing_open_risk = max(listed_open_risk, reported_open_risk)
    projected_open_risk = existing_open_risk + risk_amount
    open_risk_pct = (projected_open_risk / balance) * 100.0
    portfolio_heat_pct = open_risk_pct

    correlated_existing, correlation_source = _correlated_existing_risk(request)
    correlated_risk_pct = ((correlated_existing + risk_amount) / balance) * 100.0
    open_position_count = max(stats.open_positions, len(request.open_positions))

    stop_geometry = (
        request.direction == SignalDirection.buy and request.stop_loss < request.entry_price
    ) or (
        request.direction == SignalDirection.sell and request.stop_loss > request.entry_price
    )

    hard_gates: dict[str, bool] = {
        "direction": request.direction != SignalDirection.neutral,
        "stop_geometry": stop_geometry and stop_distance > 0,
        "daily_loss": stats.daily_loss_pct < settings.max_daily_loss_pct,
        "trade_frequency": stats.trades_today < settings.max_trades_per_day,
        "loss_streak": stats.consecutive_losses < settings.max_consecutive_losses,
        "position_count": open_position_count < settings.max_open_positions,
        "drawdown": stats.current_drawdown_pct < settings.max_drawdown_pct,
        "execution_spread_known": spread_known,
        "execution_spread": spread_known and spread_bps <= settings.max_spread_bps,
        "execution_slippage": slippage_bps <= settings.max_slippage_bps,
        "open_risk_budget": open_risk_pct <= settings.max_open_risk_pct,
        "portfolio_heat": portfolio_heat_pct <= settings.max_portfolio_heat_pct,
        "correlation_exposure": correlated_risk_pct <= settings.max_correlated_risk_pct,
        "effective_stop": effective_stop_distance > 0,
    }

    warning_by_gate = {
        "direction": "Neutral direction cannot produce a trade plan",
        "stop_geometry": "Stop-loss geometry is invalid for the trade direction",
        "daily_loss": "Daily loss limit reached",
        "trade_frequency": "Maximum trades per day reached",
        "loss_streak": "Maximum consecutive losses reached",
        "position_count": "Maximum open positions reached",
        "drawdown": "Maximum account drawdown reached",
        "execution_spread_known": "Execution spread is unknown; strict risk approval requires a measured spread",
        "execution_spread": "Expected spread exceeds the execution policy",
        "execution_slippage": "Estimated slippage exceeds the execution policy",
        "open_risk_budget": "Open-risk budget would be exceeded",
        "portfolio_heat": "Portfolio heat limit would be exceeded",
        "correlation_exposure": "Correlated exposure limit would be exceeded",
        "effective_stop": "Effective stop distance is invalid",
    }
    failed_gates = [name for name, passed in hard_gates.items() if not passed]
    warnings.extend(warning_by_gate[name] for name in failed_gates)

    if drawdown_multiplier < 1.0 and hard_gates["drawdown"]:
        warnings.append(
            f"Risk reduced by drawdown policy to {drawdown_multiplier:.2f}x"
        )
    if volatility_multiplier < 1.0:
        warnings.append(
            f"Risk reduced by volatility policy to {volatility_multiplier:.2f}x"
        )
    if correlation_source == "structural_proxy":
        warnings.append(
            "Correlation exposure uses a transparent structural proxy, not measured historical correlation"
        )
    elif correlation_source == "mixed_explicit_and_structural_proxy":
        warnings.append(
            "Correlation exposure mixes explicit values with a transparent structural proxy"
        )
    if request.estimated_slippage_bps is None:
        warnings.append("Slippage uses the configured conservative policy default")
    if request.atr_pct is None:
        warnings.append("ATR percentage was not supplied; no volatility size adjustment was applied")

    is_allowed = all(hard_gates.values())
    if is_allowed:
        position_size_units = risk_amount / (
            effective_stop_distance * settings.value_per_point
        )
    else:
        position_size_units = 0.0

    capacity_pct = min(settings.max_open_risk_pct, settings.max_portfolio_heat_pct)
    capacity_amount = balance * capacity_pct / 100.0
    risk_budget_remaining = max(0.0, capacity_amount - projected_open_risk)

    return RiskPlan(
        is_trade_allowed=is_allowed,
        risk_amount=round(risk_amount, 2),
        position_size_units=round(position_size_units, 6),
        stop_distance=round(stop_distance, 8),
        max_loss_amount=round(risk_amount, 2),
        breakeven_rr=settings.breakeven_rr,
        partial_take_profit_rr=settings.partial_tp_rr,
        base_risk_amount=round(base_risk_amount, 2),
        adjusted_risk_pct=round((risk_amount / balance) * 100.0, 4),
        risk_multiplier=round(risk_multiplier, 4),
        effective_stop_distance=round(effective_stop_distance, 8),
        execution_cost_per_unit=round(execution_cost_per_unit, 8),
        portfolio_heat_pct=round(portfolio_heat_pct, 4),
        open_risk_pct=round(open_risk_pct, 4),
        correlated_risk_pct=round(correlated_risk_pct, 4),
        risk_budget_remaining=round(risk_budget_remaining, 2),
        drawdown_risk_multiplier=round(drawdown_multiplier, 4),
        volatility_risk_multiplier=round(volatility_multiplier, 4),
        correlation_source=correlation_source,
        hard_gates=hard_gates,
        failed_gates=failed_gates,
        warnings=warnings,
    )
