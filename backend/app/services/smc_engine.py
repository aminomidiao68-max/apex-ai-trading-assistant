from __future__ import annotations

from typing import List

from app.models import Candle, SignalDirection


def detect_smc_features(candles: List[Candle], lookback: int = 10) -> dict:
    recent = candles[-(lookback + 1):]
    last = recent[-1]
    prev = recent[:-1]

    recent_high = max(c.high for c in prev)
    recent_low = min(c.low for c in prev)

    bos = None
    sweep = None
    if last.close > recent_high:
        bos = "bullish"
    elif last.close < recent_low:
        bos = "bearish"

    if last.high > recent_high and last.close < recent_high:
        sweep = "sell_side_liquidity_swept"
    elif last.low < recent_low and last.close > recent_low:
        sweep = "buy_side_liquidity_swept"

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

    direction = SignalDirection.neutral
    score = 8.0
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
        reasons.append("Sell-side liquidity sweep and reclaim")
    elif sweep == "sell_side_liquidity_swept":
        direction = SignalDirection.sell
        score += 6
        reasons.append("Buy-side liquidity sweep and rejection")

    if fvg:
        score += 5
        reasons.append(f"{fvg['type'].title()} FVG present")

    return {
        "direction": direction,
        "score": min(score, 25.0),
        "bos": bos,
        "sweep": sweep,
        "fvg": fvg,
        "bullish_ob": bullish_ob,
        "bearish_ob": bearish_ob,
        "recent_high": recent_high,
        "recent_low": recent_low,
        "reasons": reasons,
    }
