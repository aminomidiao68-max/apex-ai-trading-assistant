from __future__ import annotations

from app.models import (
    Candle,
    RiskPlanRequest,
    ScoreBreakdown,
    SignalDirection,
    SignalRequest,
    SignalResponse,
    TradeStats,
)
from app.services.indicators import atr, ema, momentum_histogram, rsi
from app.services.news_engine import evaluate_news_risk
from app.services.risk_engine import build_risk_plan
from app.services.session_engine import evaluate_session
from app.services.smc_engine import detect_smc_features


def _timeframe_minutes(timeframe: str) -> int:
    mapping = {
        "1m": 1,
        "3m": 3,
        "5m": 5,
        "15m": 15,
        "30m": 30,
        "1h": 60,
        "4h": 240,
        "1d": 1440,
    }
    return mapping.get(timeframe.lower(), 15)


def _atr_pct(last_price: float, current_atr: float) -> float:
    if last_price <= 0 or current_atr <= 0:
        return 0.0
    return (current_atr / last_price) * 100.0


def _recent_candle_pressure(candles: list[Candle]) -> tuple[float, float]:
    bull_pressure = 0.0
    bear_pressure = 0.0
    for candle in candles[-5:]:
        candle_range = max(candle.high - candle.low, 1e-9)
        body_ratio = abs(candle.close - candle.open) / candle_range
        if candle.close > candle.open:
            bull_pressure += body_ratio
        elif candle.close < candle.open:
            bear_pressure += body_ratio
    return bull_pressure, bear_pressure


def _ema_stack_alignment(closes: list[float]) -> tuple[bool, bool, float]:
    last_price = closes[-1]
    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    ema55 = ema(closes, 55)
    bullish_stack = ema9 > ema21 > ema55 and last_price > ema9
    bearish_stack = ema9 < ema21 < ema55 and last_price < ema9
    normalization = max(abs(last_price) * 0.001, 1e-9)
    stack_strength = abs(ema9 - ema55) / normalization
    return bullish_stack, bearish_stack, stack_strength


def _context_summary(candles: list[Candle]) -> dict:
    if len(candles) < 20:
        return {
            "direction": SignalDirection.neutral,
            "trend_strength": 0.0,
            "bull_pressure": 0.0,
            "bear_pressure": 0.0,
            "volatility_pct": 0.0,
            "bullish_stack": False,
            "bearish_stack": False,
        }

    closes = [c.close for c in candles]
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]
    last_price = closes[-1]
    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)
    current_atr = atr(highs, lows, closes, 14)
    bullish_stack, bearish_stack, _ = _ema_stack_alignment(closes)
    bull_pressure, bear_pressure = _recent_candle_pressure(candles)
    trend_strength = abs(ema20 - ema50) / current_atr if current_atr > 0 else 0.0

    direction = SignalDirection.neutral
    if ema20 > ema50 and last_price > ema20 and bullish_stack:
        direction = SignalDirection.buy
    elif ema20 < ema50 and last_price < ema20 and bearish_stack:
        direction = SignalDirection.sell

    return {
        "direction": direction,
        "trend_strength": trend_strength,
        "bull_pressure": bull_pressure,
        "bear_pressure": bear_pressure,
        "volatility_pct": _atr_pct(last_price, current_atr),
        "bullish_stack": bullish_stack,
        "bearish_stack": bearish_stack,
    }


class SignalEngine:
    def analyze(self, request: SignalRequest) -> SignalResponse:
        closes = [c.close for c in request.candles]
        highs = [c.high for c in request.candles]
        lows = [c.low for c in request.candles]
        last_price = closes[-1]

        ema20 = ema(closes, 20)
        ema50 = ema(closes, 50)
        current_rsi = rsi(closes, 14)
        current_atr = atr(highs, lows, closes, 14)
        momentum = momentum_histogram(closes)
        bull_pressure, bear_pressure = _recent_candle_pressure(request.candles)
        bullish_stack, bearish_stack, _ = _ema_stack_alignment(closes)
        timeframe_minutes = _timeframe_minutes(request.timeframe)
        volatility_pct = _atr_pct(last_price, current_atr)
        trend_strength = abs(ema20 - ema50) / current_atr if current_atr > 0 else 0.0
        higher_tf_ctx = _context_summary(request.higher_timeframe_candles)
        lower_tf_ctx = _context_summary(request.lower_timeframe_candles)

        structure_score = 0.0
        indicator_score = 0.0
        bull_bias = 0.0
        bear_bias = 0.0
        reasons: list[str] = []
        quality_gate_penalty = 0.0

        if ema20 > ema50 and last_price > ema20:
            structure_score += 16
            indicator_score += 5
            bull_bias += 1.5
            reasons.append("Price above EMA20/EMA50 with bullish structure")
        elif ema20 < ema50 and last_price < ema20:
            structure_score += 16
            indicator_score += 5
            bear_bias += 1.5
            reasons.append("Price below EMA20/EMA50 with bearish structure")
        else:
            structure_score += 8
            reasons.append("Mixed structure, no clear trend dominance")

        if bullish_stack:
            structure_score += 3
            bull_bias += 0.8
            reasons.append("Fast EMA stack confirms bullish continuation")
        elif bearish_stack:
            structure_score += 3
            bear_bias += 0.8
            reasons.append("Fast EMA stack confirms bearish continuation")

        if trend_strength > 0.35:
            structure_score += 2
            reasons.append("EMA spread shows strong directional separation")

        if 45 <= current_rsi <= 65:
            indicator_score += 3
        elif current_rsi > 65:
            bull_bias += 0.8
            indicator_score += 4
            reasons.append("RSI supports bullish momentum")
        elif current_rsi < 35:
            bear_bias += 0.8
            indicator_score += 4
            reasons.append("RSI supports bearish momentum")

        if momentum > 0:
            bull_bias += 0.6
            indicator_score += 2
        elif momentum < 0:
            bear_bias += 0.6
            indicator_score += 2

        if bull_pressure > bear_pressure + 0.6:
            bull_bias += 0.7
            indicator_score += 1.5
            reasons.append("Recent candle pressure favors buyers")
        elif bear_pressure > bull_pressure + 0.6:
            bear_bias += 0.7
            indicator_score += 1.5
            reasons.append("Recent candle pressure favors sellers")

        structure_score = min(structure_score, 25.0)
        indicator_score = min(indicator_score, 10.0)

        smc = detect_smc_features(request.candles)
        smc_score = smc["score"]
        reasons.extend(smc["reasons"])
        if smc["direction"] == SignalDirection.buy:
            bull_bias += 1.6
        elif smc["direction"] == SignalDirection.sell:
            bear_bias += 1.6

        order_flow_score = 8.0
        if request.order_flow:
            of = request.order_flow
            if (of.delta_volume or 0) > 0:
                bull_bias += 0.6
                order_flow_score += 3
            elif (of.delta_volume or 0) < 0:
                bear_bias += 0.6
                order_flow_score += 3

            if request.market.value == "crypto":
                if (of.open_interest_change_pct or 0) > 0:
                    order_flow_score += 2
                if (of.funding_rate or 0) > 0.02:
                    bear_bias += 0.3
                elif (of.funding_rate or 0) < -0.02:
                    bull_bias += 0.3
                if (of.aggressive_buy_ratio or 0) > 0.55:
                    bull_bias += 0.6
                    order_flow_score += 3
                if (of.aggressive_sell_ratio or 0) > 0.55:
                    bear_bias += 0.6
                    order_flow_score += 3
        order_flow_score = min(order_flow_score, 20.0)

        session = evaluate_session(request.now_utc)
        session_score = session["score"]
        if session["quality"] == "high":
            reasons.append(f"Active trading session: {session['session_name']}")
            if "Overlap" in session["session_name"]:
                session_score = min(session_score + 1.0, 10.0)
                reasons.append("Session overlap boosts liquidity and execution quality")
        else:
            reasons.append("Off-session conditions reduce setup quality")

        news = evaluate_news_risk(request.news, request.now_utc)
        news_score = news["score"]
        reasons.extend(news["warnings"])

        if news["blocked"]:
            direction = SignalDirection.neutral
        else:
            if bull_bias > bear_bias + 0.4:
                direction = SignalDirection.buy
            elif bear_bias > bull_bias + 0.4:
                direction = SignalDirection.sell
            else:
                direction = SignalDirection.neutral

        higher_direction = higher_tf_ctx["direction"]
        if higher_direction != SignalDirection.neutral:
            if higher_direction == direction and direction != SignalDirection.neutral:
                structure_score = min(structure_score + 3.0, 25.0)
                indicator_score = min(indicator_score + 1.0, 10.0)
                reasons.append(f"Higher timeframe bias confirms {direction.value} continuation")
            elif direction != SignalDirection.neutral and higher_direction != direction:
                quality_gate_penalty += 6.0
                reasons.append("Higher timeframe trend disagrees with local setup")

        if direction == SignalDirection.buy:
            if lower_tf_ctx["bull_pressure"] > lower_tf_ctx["bear_pressure"] + 0.35:
                indicator_score = min(indicator_score + 1.5, 10.0)
                reasons.append("Lower timeframe execution momentum supports buy continuation")
            elif lower_tf_ctx["bear_pressure"] > lower_tf_ctx["bull_pressure"] + 0.5:
                quality_gate_penalty += 2.5
                reasons.append("Lower timeframe sellers are still pressing against entry")
        elif direction == SignalDirection.sell:
            if lower_tf_ctx["bear_pressure"] > lower_tf_ctx["bull_pressure"] + 0.35:
                indicator_score = min(indicator_score + 1.5, 10.0)
                reasons.append("Lower timeframe execution momentum supports sell continuation")
            elif lower_tf_ctx["bull_pressure"] > lower_tf_ctx["bear_pressure"] + 0.5:
                quality_gate_penalty += 2.5
                reasons.append("Lower timeframe buyers are still pressing against entry")

        if direction != SignalDirection.neutral and higher_direction == direction and lower_tf_ctx["direction"] in (direction, SignalDirection.neutral):
            structure_score = min(structure_score + 2.0, 25.0)
            reasons.append("Multi-timeframe confluence boosts conviction")

        if direction == SignalDirection.buy:
            fvg = smc.get("fvg") or {}
            if smc.get("sweep") == "buy_side_liquidity_swept" and fvg.get("type") == "bullish":
                smc_score = min(smc_score + 4, 25.0)
                reasons.append("Liquidity sweep and bullish imbalance align")
            if smc.get("bullish_ob"):
                smc_score = min(smc_score + 2, 25.0)
                reasons.append("Bullish order block supports entry zone")
        elif direction == SignalDirection.sell:
            fvg = smc.get("fvg") or {}
            if smc.get("sweep") == "sell_side_liquidity_swept" and fvg.get("type") == "bearish":
                smc_score = min(smc_score + 4, 25.0)
                reasons.append("Liquidity sweep and bearish imbalance align")
            if smc.get("bearish_ob"):
                smc_score = min(smc_score + 2, 25.0)
                reasons.append("Bearish order block supports entry zone")

        if direction == SignalDirection.buy and ema20 > ema50 and smc["direction"] == SignalDirection.buy:
            structure_score = min(structure_score + 4, 25.0)
            indicator_score = min(indicator_score + 1.5, 10.0)
            reasons.append("Bullish multi-layer confluence confirmed")
        elif direction == SignalDirection.sell and ema20 < ema50 and smc["direction"] == SignalDirection.sell:
            structure_score = min(structure_score + 4, 25.0)
            indicator_score = min(indicator_score + 1.5, 10.0)
            reasons.append("Bearish multi-layer confluence confirmed")

        if current_atr > 0 and session["quality"] == "high" and not news["blocked"]:
            indicator_score = min(indicator_score + 1.0, 10.0)
            reasons.append("Volatility and session conditions support execution")

        if timeframe_minutes <= 1:
            if session["quality"] != "high":
                session_score = max(session_score - 4.0, 0.0)
                reasons.append("1m scalping outside prime session reduces quality")
            if trend_strength < 0.18:
                quality_gate_penalty += 3.5
                reasons.append("1m trend strength is too weak for high-quality execution")
            if higher_direction == SignalDirection.neutral:
                quality_gate_penalty += 2.5
                reasons.append("1m setup has no higher timeframe directional sponsor")
            if max(bull_pressure, bear_pressure) < 2.0:
                quality_gate_penalty += 1.5
                reasons.append("1m candle pressure is not decisive")
        elif timeframe_minutes <= 5:
            if session["quality"] != "high":
                session_score = max(session_score - 2.0, 0.0)
                reasons.append("Lower timeframe outside prime session reduces quality")
            if trend_strength < 0.12:
                quality_gate_penalty += 1.5
                reasons.append("Lower timeframe trend spread is modest")

        if timeframe_minutes <= 5:
            vol_floor = 0.004 if request.market.value == "forex" else 0.02
            if volatility_pct < vol_floor:
                quality_gate_penalty += 1.0
                reasons.append("Short timeframe volatility is compressed")

        entry_low = None
        entry_high = None
        stop_loss = None
        take_profits: list[float] = []
        rr = None

        if direction == SignalDirection.buy:
            zone = smc.get("bullish_ob") or smc.get("fvg")
            entry_low = (zone or {}).get("low", last_price - current_atr * 0.2)
            entry_high = (zone or {}).get("high", last_price)
            stop_loss = min(smc.get("recent_low", last_price - current_atr), entry_low - current_atr * 0.2)
            risk = max(((entry_low + entry_high) / 2) - stop_loss, current_atr * 0.5)
            mid_entry = (entry_low + entry_high) / 2
            take_profits = [round(mid_entry + risk * n, 6) for n in (1, 2, 3)]
            rr = 3.0
        elif direction == SignalDirection.sell:
            zone = smc.get("bearish_ob") or smc.get("fvg")
            entry_low = (zone or {}).get("low", last_price)
            entry_high = (zone or {}).get("high", last_price + current_atr * 0.2)
            stop_loss = max(smc.get("recent_high", last_price + current_atr), entry_high + current_atr * 0.2)
            risk = max(stop_loss - ((entry_low + entry_high) / 2), current_atr * 0.5)
            mid_entry = (entry_low + entry_high) / 2
            take_profits = [round(mid_entry - risk * n, 6) for n in (1, 2, 3)]
            rr = 3.0

        total_score = round(structure_score + smc_score + order_flow_score + session_score + news_score + indicator_score - quality_gate_penalty, 2)
        total_score = max(0.0, min(total_score, 100.0))

        confidence = "low"
        if total_score >= 84:
            confidence = "high"
        elif total_score >= 70:
            confidence = "medium"

        if timeframe_minutes <= 1 and total_score < 68:
            direction = SignalDirection.neutral
            reasons.append("1m quality gate blocked execution")
        elif timeframe_minutes <= 5 and total_score < 62:
            direction = SignalDirection.neutral
            reasons.append("Lower timeframe quality gate blocked execution")

        risk_plan = None
        if request.risk_settings and direction != SignalDirection.neutral and stop_loss is not None:
            risk_plan = build_risk_plan(
                RiskPlanRequest(
                    entry_price=round((entry_low + entry_high) / 2, 6),
                    stop_loss=round(stop_loss, 6),
                    direction=direction,
                    risk_settings=request.risk_settings,
                    trade_stats=request.trade_stats or TradeStats(),
                )
            )
            if not risk_plan.is_trade_allowed:
                reasons.extend(risk_plan.warnings)

        breakdown = ScoreBreakdown(
            structure=round(structure_score, 2),
            smc=round(smc_score, 2),
            order_flow=round(order_flow_score, 2),
            session=round(session_score, 2),
            news=round(news_score, 2),
            indicators=round(indicator_score, 2),
            total=total_score,
        )

        return SignalResponse(
            symbol=request.symbol,
            market=request.market,
            timeframe=request.timeframe,
            direction=direction,
            score=total_score,
            confidence=confidence,
            session_name=session["session_name"],
            session_quality=session["quality"],
            news_blocked=news["blocked"],
            entry_low=round(entry_low, 6) if entry_low is not None else None,
            entry_high=round(entry_high, 6) if entry_high is not None else None,
            stop_loss=round(stop_loss, 6) if stop_loss is not None else None,
            take_profits=take_profits,
            risk_to_reward=rr,
            score_breakdown=breakdown,
            reasons=reasons,
            risk_plan=risk_plan,
        )
