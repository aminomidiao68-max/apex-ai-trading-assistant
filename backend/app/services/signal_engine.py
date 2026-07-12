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


def _direction_from_bias(bull_bias: float, bear_bias: float, gap: float = 0.4) -> SignalDirection:
    if bull_bias > bear_bias + gap:
        return SignalDirection.buy
    if bear_bias > bull_bias + gap:
        return SignalDirection.sell
    return SignalDirection.neutral


def _zone_for_direction(smc: dict, direction: SignalDirection) -> dict | None:
    fvg = smc.get("fvg") if isinstance(smc.get("fvg"), dict) else None
    if direction == SignalDirection.buy:
        if isinstance(smc.get("bullish_ob"), dict):
            return smc["bullish_ob"]
        if fvg and fvg.get("type") == "bullish":
            return fvg
    elif direction == SignalDirection.sell:
        if isinstance(smc.get("bearish_ob"), dict):
            return smc["bearish_ob"]
        if fvg and fvg.get("type") == "bearish":
            return fvg
    return None


def _dedupe_reasons(reasons: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in reasons:
        clean = item.strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        ordered.append(clean)
    return ordered


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        clean = item.strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        ordered.append(clean)
    return ordered


def _grade_from_score(score: float) -> str:
    if score >= 88:
        return "A+"
    if score >= 78:
        return "A"
    if score >= 68:
        return "B"
    return "C"


def _execution_label(
    direction: SignalDirection,
    score: float,
    session_quality: str,
    news_blocked: bool,
    timeframe_minutes: int,
    quality_gate_penalty: float,
) -> str:
    if news_blocked:
        return "blocked"
    if direction == SignalDirection.neutral:
        return "blocked" if score < 62 or quality_gate_penalty >= 4 else "observe"
    if timeframe_minutes <= 5 and score >= 76 and session_quality == "high":
        return "scalp_ready"
    if score >= 82 and session_quality == "high":
        return "execution_ready"
    if score >= 68:
        return "watchlist"
    return "observe"


def _entry_model(smc: dict, direction: SignalDirection) -> str:
    if direction == SignalDirection.buy:
        if smc.get("bullish_ob"):
            return "Bullish Order Block"
        if (smc.get("fvg") or {}).get("type") == "bullish":
            return "Bullish Imbalance"
        return "Momentum Continuation"
    if direction == SignalDirection.sell:
        if smc.get("bearish_ob"):
            return "Bearish Order Block"
        if (smc.get("fvg") or {}).get("type") == "bearish":
            return "Bearish Imbalance"
        return "Momentum Continuation"
    return "No Trade"


def _build_tags(
    direction: SignalDirection,
    higher_direction: SignalDirection,
    lower_tf_ctx: dict,
    smc: dict,
    session: dict,
) -> list[str]:
    tags: list[str] = []
    if direction != SignalDirection.neutral and higher_direction == direction:
        tags.append("HTF aligned")
    if direction == SignalDirection.buy and lower_tf_ctx.get("bull_pressure", 0.0) > lower_tf_ctx.get("bear_pressure", 0.0):
        tags.append("LTF trigger")
    if direction == SignalDirection.sell and lower_tf_ctx.get("bear_pressure", 0.0) > lower_tf_ctx.get("bull_pressure", 0.0):
        tags.append("LTF trigger")
    if smc.get("sweep"):
        tags.append("Liquidity sweep")
    if smc.get("choch"):
        tags.append("CHoCH")
    if smc.get("displacement"):
        tags.append("Displacement")
    if smc.get("bullish_ob") or smc.get("bearish_ob"):
        tags.append("Order block")
    if smc.get("fvg"):
        tags.append("FVG imbalance")
    if direction == SignalDirection.buy and smc.get("premium_discount") == "discount":
        tags.append("Discount buy")
    if direction == SignalDirection.sell and smc.get("premium_discount") == "premium":
        tags.append("Premium sell")
    if session.get("quality") == "high":
        tags.append("Prime session")
    return _unique(tags)[:6]


def _build_risk_flags(
    session: dict,
    news: dict,
    higher_direction: SignalDirection,
    direction: SignalDirection,
    liquidity_score: float,
    timeframe_minutes: int,
    volatility_pct: float,
    market: str,
    quality_gate_penalty: float,
) -> list[str]:
    flags: list[str] = []
    if news.get("blocked"):
        flags.append("High impact news")
    if session.get("quality") != "high":
        flags.append("Off session")
    if direction != SignalDirection.neutral and higher_direction not in (SignalDirection.neutral, direction):
        flags.append("HTF conflict")
    if liquidity_score < 4.0 and timeframe_minutes <= 5:
        flags.append("Shallow liquidity")
    vol_floor = 0.004 if market == "forex" else 0.02
    if timeframe_minutes <= 5 and volatility_pct < vol_floor:
        flags.append("Compressed volatility")
    if timeframe_minutes <= 1 and higher_direction == SignalDirection.neutral:
        flags.append("No HTF sponsor")
    if quality_gate_penalty >= 5:
        flags.append("Execution blocked")
    return _unique(flags)[:4]


def _build_ai_summary(
    symbol: str,
    timeframe: str,
    direction: SignalDirection,
    grade: str,
    entry_model: str,
    session_name: str,
    tags: list[str],
    risk_flags: list[str],
) -> str:
    if direction == SignalDirection.neutral:
        if risk_flags:
            return f"{symbol} {timeframe} remains neutral because {risk_flags[0].lower()} is reducing execution quality."
        return f"{symbol} {timeframe} is neutral because the current confluence is still incomplete."

    side = "buy" if direction == SignalDirection.buy else "sell"
    summary = f"{symbol} {timeframe} shows a {grade} {side} setup with {entry_model.lower()} context during {session_name}."
    if tags:
        summary += f" Key confluence: {', '.join(tags[:3])}."
    if risk_flags:
        summary += f" Main caution: {risk_flags[0].lower()}."
    return summary


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
            bull_bias += 1.6
            reasons.append("Price above EMA20/EMA50 with bullish structure")
        elif ema20 < ema50 and last_price < ema20:
            structure_score += 16
            indicator_score += 5
            bear_bias += 1.6
            reasons.append("Price below EMA20/EMA50 with bearish structure")
        else:
            structure_score += 8
            reasons.append("Mixed structure, no clear trend dominance")

        if bullish_stack:
            structure_score += 3
            bull_bias += 0.9
            reasons.append("Fast EMA stack confirms bullish continuation")
        elif bearish_stack:
            structure_score += 3
            bear_bias += 0.9
            reasons.append("Fast EMA stack confirms bearish continuation")

        if trend_strength > 0.55:
            structure_score += 2.5
            reasons.append("EMA spread shows strong directional separation")
        elif trend_strength > 0.35:
            structure_score += 1.5
            reasons.append("EMA spread shows directional commitment")

        if 45 <= current_rsi <= 65:
            indicator_score += 3
        elif current_rsi > 65:
            bull_bias += 0.9
            indicator_score += 4
            reasons.append("RSI supports bullish momentum")
        elif current_rsi < 35:
            bear_bias += 0.9
            indicator_score += 4
            reasons.append("RSI supports bearish momentum")

        if momentum > 0:
            bull_bias += 0.6
            indicator_score += 2
        elif momentum < 0:
            bear_bias += 0.6
            indicator_score += 2

        if bull_pressure > bear_pressure + 0.6:
            bull_bias += 0.8
            indicator_score += 1.5
            reasons.append("Recent candle pressure favors buyers")
        elif bear_pressure > bull_pressure + 0.6:
            bear_bias += 0.8
            indicator_score += 1.5
            reasons.append("Recent candle pressure favors sellers")

        structure_score = min(structure_score, 25.0)
        indicator_score = min(indicator_score, 10.0)

        smc = detect_smc_features(request.candles)
        smc_score = smc["score"]
        liquidity_score = smc.get("liquidity_score", 0.0)
        reasons.extend(smc["reasons"])

        if smc["direction"] == SignalDirection.buy:
            bull_bias += 1.6
        elif smc["direction"] == SignalDirection.sell:
            bear_bias += 1.6

        if smc.get("equal_highs") and smc.get("sweep") == "sell_side_liquidity_swept":
            smc_score = min(smc_score + 2.0, 25.0)
            bear_bias += 0.5
            reasons.append("Equal-high liquidity was engineered before bearish rejection")
        if smc.get("equal_lows") and smc.get("sweep") == "buy_side_liquidity_swept":
            smc_score = min(smc_score + 2.0, 25.0)
            bull_bias += 0.5
            reasons.append("Equal-low liquidity was engineered before bullish reclaim")

        if smc.get("displacement") == "bullish":
            smc_score = min(smc_score + 2.0, 25.0)
            bull_bias += 0.5
            reasons.append("Displacement confirms institutional intent")
        elif smc.get("displacement") == "bearish":
            smc_score = min(smc_score + 2.0, 25.0)
            bear_bias += 0.5
            reasons.append("Displacement confirms institutional intent")

        if smc.get("choch") == "bullish":
            smc_score = min(smc_score + 2.5, 25.0)
            bull_bias += 0.5
            reasons.append("Market structure shift improves reversal credibility")
        elif smc.get("choch") == "bearish":
            smc_score = min(smc_score + 2.5, 25.0)
            bear_bias += 0.5
            reasons.append("Market structure shift improves reversal credibility")

        directional_candidate = _direction_from_bias(bull_bias, bear_bias)
        if smc.get("premium_discount") == "discount" and directional_candidate == SignalDirection.buy:
            smc_score = min(smc_score + 1.5, 25.0)
            bull_bias += 0.3
            reasons.append("Buy setup sits in discount zone")
        elif smc.get("premium_discount") == "premium" and directional_candidate == SignalDirection.sell:
            smc_score = min(smc_score + 1.5, 25.0)
            bear_bias += 0.3
            reasons.append("Sell setup sits in premium zone")
        elif smc.get("premium_discount") == "premium" and directional_candidate == SignalDirection.buy:
            quality_gate_penalty += 1.5
            reasons.append("Buy setup is entering from premium zone")
        elif smc.get("premium_discount") == "discount" and directional_candidate == SignalDirection.sell:
            quality_gate_penalty += 1.5
            reasons.append("Sell setup is entering from discount zone")

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

        higher_direction = higher_tf_ctx["direction"]
        base_direction = _direction_from_bias(bull_bias, bear_bias)
        if higher_direction != SignalDirection.neutral:
            if base_direction == SignalDirection.neutral:
                if higher_direction == SignalDirection.buy:
                    bull_bias += 0.45
                else:
                    bear_bias += 0.45
                reasons.append(f"Higher timeframe bias is sponsoring {higher_direction.value} continuation")
            elif higher_direction == base_direction:
                structure_score = min(structure_score + 3.0, 25.0)
                indicator_score = min(indicator_score + 1.0, 10.0)
                if higher_direction == SignalDirection.buy:
                    bull_bias += 0.45
                else:
                    bear_bias += 0.45
                reasons.append(f"Higher timeframe bias confirms {base_direction.value} continuation")
            else:
                quality_gate_penalty += 6.0
                reasons.append("Higher timeframe trend disagrees with local setup")

        direction = _direction_from_bias(bull_bias, bear_bias)
        if direction == SignalDirection.buy:
            if lower_tf_ctx["bull_pressure"] > lower_tf_ctx["bear_pressure"] + 0.35:
                bull_bias += 0.35
                indicator_score = min(indicator_score + 1.5, 10.0)
                reasons.append("Lower timeframe execution momentum supports buy continuation")
            elif lower_tf_ctx["bear_pressure"] > lower_tf_ctx["bull_pressure"] + 0.5:
                quality_gate_penalty += 2.5
                reasons.append("Lower timeframe sellers are still pressing against entry")
        elif direction == SignalDirection.sell:
            if lower_tf_ctx["bear_pressure"] > lower_tf_ctx["bull_pressure"] + 0.35:
                bear_bias += 0.35
                indicator_score = min(indicator_score + 1.5, 10.0)
                reasons.append("Lower timeframe execution momentum supports sell continuation")
            elif lower_tf_ctx["bull_pressure"] > lower_tf_ctx["bear_pressure"] + 0.5:
                quality_gate_penalty += 2.5
                reasons.append("Lower timeframe buyers are still pressing against entry")

        direction = _direction_from_bias(bull_bias, bear_bias)
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

        if liquidity_score < 4.0 and timeframe_minutes <= 5:
            quality_gate_penalty += 1.0
            reasons.append("Liquidity map is still shallow for lower timeframe execution")

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

        if news["blocked"]:
            direction = SignalDirection.neutral
        else:
            direction = _direction_from_bias(bull_bias, bear_bias)

        entry_low = None
        entry_high = None
        stop_loss = None
        take_profits: list[float] = []
        rr = None

        if direction == SignalDirection.buy:
            zone = _zone_for_direction(smc, direction) or {}
            entry_low = zone.get("low", last_price - current_atr * 0.2)
            entry_high = zone.get("high", last_price)
            stop_anchor = smc.get("recent_low", last_price - current_atr)
            stop_loss = min(stop_anchor, entry_low - current_atr * 0.2)
            risk = max(((entry_low + entry_high) / 2) - stop_loss, current_atr * 0.5)
            mid_entry = (entry_low + entry_high) / 2
            take_profits = [round(mid_entry + risk * n, 6) for n in (1, 2, 3)]
            rr = 3.0
        elif direction == SignalDirection.sell:
            zone = _zone_for_direction(smc, direction) or {}
            entry_low = zone.get("low", last_price)
            entry_high = zone.get("high", last_price + current_atr * 0.2)
            stop_anchor = smc.get("recent_high", last_price + current_atr)
            stop_loss = max(stop_anchor, entry_high + current_atr * 0.2)
            risk = max(stop_loss - ((entry_low + entry_high) / 2), current_atr * 0.5)
            mid_entry = (entry_low + entry_high) / 2
            take_profits = [round(mid_entry - risk * n, 6) for n in (1, 2, 3)]
            rr = 3.0

        total_score = round(
            structure_score + smc_score + order_flow_score + session_score + news_score + indicator_score - quality_gate_penalty,
            2,
        )
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

        if direction == SignalDirection.neutral:
            # A neutral/blocked setup must never leak stale actionable levels
            # calculated before the final quality gate.
            entry_low = None
            entry_high = None
            stop_loss = None
            take_profits = []
            rr = None

        reasons = _dedupe_reasons(reasons)
        grade = _grade_from_score(total_score)
        entry_model = _entry_model(smc, direction)
        risk_flags = _build_risk_flags(
            session=session,
            news=news,
            higher_direction=higher_direction,
            direction=direction,
            liquidity_score=liquidity_score,
            timeframe_minutes=timeframe_minutes,
            volatility_pct=volatility_pct,
            market=request.market.value,
            quality_gate_penalty=quality_gate_penalty,
        )
        confluence_tags = _build_tags(direction, higher_direction, lower_tf_ctx, smc, session)
        execution_label = _execution_label(direction, total_score, session["quality"], news["blocked"], timeframe_minutes, quality_gate_penalty)
        ai_summary = _build_ai_summary(
            symbol=request.symbol,
            timeframe=request.timeframe,
            direction=direction,
            grade=grade,
            entry_model=entry_model,
            session_name=session["session_name"],
            tags=confluence_tags,
            risk_flags=risk_flags,
        )

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
                risk_flags = _unique(risk_flags + risk_plan.warnings[:2])
                if execution_label == "execution_ready":
                    execution_label = "watchlist"

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
            setup_grade=grade,
            execution_label=execution_label,
            entry_model=entry_model,
            ai_summary=ai_summary,
            confluence_tags=confluence_tags,
            risk_flags=risk_flags,
            reasons=reasons,
            risk_plan=risk_plan,
        )
