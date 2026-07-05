from __future__ import annotations

from typing import List

from app.models import Candle, SignalDirection


def _near(a: float, b: float, tolerance_pct: float = 0.03) -> bool:
    if a == 0 or b == 0:
        return False
    return abs(a - b) / max(abs(a), abs(b)) * 100 <= tolerance_pct


def _candle_body_ratio(candle: Candle) -> float:
    candle_range = max(candle.high - candle.low, 1e-9)
    return abs(candle.close - candle.open) / candle_range


def detect_smc_features(candles: List[Candle], lookback: int = 10) -> dict:
    recent = candles[-(lookback + 1):]
    last = recent[-1]
    prev = recent[:-1]

    recent_high = max(c.high for c in prev)
    recent_low = min(c.low for c in prev)

    bos = None
    sweep = None
    choch = None
    displacement = None
    equal_highs = False
    equal_lows = False
    premium_discount = None

    if last.close > recent_high:
        bos = "bullish"
    elif last.close < recent_low:
        bos = "bearish"

    if last.high > recent_high and last.close < recent_high:
        sweep = "sell_side_liquidity_swept"
    elif last.low < recent_low and last.close > recent_low:
        sweep = "buy_side_liquidity_swept"

    prev_last = candles[-2] if len(candles) >= 2 else last
    if sweep == "buy_side_liquidity_swept" and last.close > prev_last.high:
        choch = "bullish"
    elif sweep == "sell_side_liquidity_swept" and last.close < prev_last.low:
        choch = "bearish"

    if len(candles) >= 4:
        c1 = candles[-4]
        c2 = candles[-3]
        c3 = candles[-2]
        recent_range = max(last.high - last.low, 1e-9)
        avg_recent_range = max((c1.high - c1.low + c2.high - c2.low + c3.high - c3.low) / 3, 1e-9)
        if recent_range > avg_recent_range * 1.35 and _candle_body_ratio(last) > 0.6:
            displacement = "bullish" if last.close > last.open else "bearish"

    swing_highs = [c.high for c in candles[-8:-1]]
    swing_lows = [c.low for c in candles[-8:-1]]
    if len(swing_highs) >= 2:
        equal_highs = _near(max(swing_highs), sorted(swing_highs)[-2])
    if len(swing_lows) >= 2:
        equal_lows = _near(min(swing_lows), sorted(swing_lows)[1])

    fvg = None
    if len(candles) >= 3:
        c1 = candles[-3]
        c3 = candles[-1]
        if c1.high < c3.low:
            fvg = {"type": "bullish", "low": c1.high, "high": c3.low}
        elif c1.low > c3.high:
            fvg = {"type": "bearish", "low": c3.high, "high": c1.low}

    bullish_ob = None
    bearish_ob = None
    for candle in reversed(candles[-12:-1]):
        if candle.close < candle.open and bullish_ob is None:
            bullish_ob = {"low": candle.low, "high": candle.high}
        if candle.close > candle.open and bearish_ob is None:
            bearish_ob = {"low": candle.low, "high": candle.high}
        if bullish_ob and bearish_ob:
            break

    dealing_range = recent_high - recent_low
    if dealing_range > 0:
        midpoint = recent_low + dealing_range / 2
        if last.close < midpoint:
            premium_discount = "discount"
        else:
            premium_discount = "premium"

    direction = SignalDirection.neutral
    score = 8.0
    liquidity_score = 0.0
    reasons: list[str] = []

    if bos == "bullish":
        direction = SignalDirection.buy
        score += 8
        reasons.append("Bullish BOS detected")
    elif bos == "bearish":
        direction = SignalDirection.sell
        score += 8
        reasons.append("Bearish BOS detected")

    if sweep == "buy_side_liquidity_swept":
        direction = SignalDirection.buy
        score += 6
        liquidity_score += 6
        reasons.append("Sell-side liquidity sweep and reclaim")
    elif sweep == "sell_side_liquidity_swept":
        direction = SignalDirection.sell
        score += 6
        liquidity_score += 6
        reasons.append("Buy-side liquidity sweep and rejection")

    if choch == "bullish":
        direction = SignalDirection.buy
        score += 3
        liquidity_score += 3
        reasons.append("Bullish CHoCH confirmed after liquidity event")
    elif choch == "bearish":
        direction = SignalDirection.sell
        score += 3
        liquidity_score += 3
        reasons.append("Bearish CHoCH confirmed after liquidity event")

    if displacement == "bullish":
        score += 2
        liquidity_score += 2
        reasons.append("Bullish displacement candle detected")
    elif displacement == "bearish":
        score += 2
        liquidity_score += 2
        reasons.append("Bearish displacement candle detected")

    if equal_highs:
        liquidity_score += 1.5
        reasons.append("Equal highs liquidity pool detected")
    if equal_lows:
        liquidity_score += 1.5
        reasons.append("Equal lows liquidity pool detected")

    if premium_discount == "discount":
        reasons.append("Price positioned in discount zone of current range")
    elif premium_discount == "premium":
        reasons.append("Price positioned in premium zone of current range")

    if fvg:
        score += 5
        reasons.append(f"{fvg['type'].title()} FVG present")

    return {
        "direction": direction,
        "score": min(score, 25.0),
        "liquidity_score": min(liquidity_score, 10.0),
        "bos": bos,
        "sweep": sweep,
        "choch": choch,
        "displacement": displacement,
        "equal_highs": equal_highs,
        "equal_lows": equal_lows,
        "premium_discount": premium_discount,
        "fvg": fvg,
        "bullish_ob": bullish_ob,
        "bearish_ob": bearish_ob,
        "recent_high": recent_high,
        "recent_low": recent_low,
        "reasons": reasons,
    }
