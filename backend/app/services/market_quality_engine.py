from __future__ import annotations

import math
from datetime import datetime, timezone
from statistics import median
from typing import Any


def timeframe_seconds(timeframe: str) -> int:
    value = (timeframe or "15m").lower().replace("min", "m")
    return {
        "1m": 60,
        "3m": 180,
        "5m": 300,
        "15m": 900,
        "30m": 1800,
        "1h": 3600,
        "2h": 7200,
        "4h": 14400,
        "1d": 86400,
    }.get(value, 900)


def _finite_positive(value: Any) -> bool:
    try:
        number = float(value)
        return math.isfinite(number) and number > 0
    except (TypeError, ValueError):
        return False


def _weekend_gap(start: float, end: float, market: str) -> bool:
    if market != "forex":
        return False
    try:
        first = datetime.fromtimestamp(start, tz=timezone.utc)
        second = datetime.fromtimestamp(end, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return False
    return first.weekday() >= 4 and second.weekday() in (0, 6)


def assess_data_quality(candles: list[dict], timeframe: str, market: str) -> dict:
    issues: list[str] = []
    warnings: list[str] = []
    score = 100.0
    count = len(candles)

    if count < 50:
        score -= 40
        issues.append("fewer_than_50_candles")
    elif count < 120:
        score -= 12
        warnings.append("limited_history")

    timestamps: list[float] = []
    ranges: list[float] = []
    invalid_ohlc = 0
    invalid_price = 0
    volume_present = 0
    for candle in candles:
        try:
            timestamp = float(candle.get("t", 0))
            open_price = float(candle.get("o", 0))
            high = float(candle.get("h", 0))
            low = float(candle.get("l", 0))
            close = float(candle.get("c", 0))
            volume = float(candle.get("v", 0) or 0)
        except (TypeError, ValueError):
            invalid_price += 1
            continue
        if timestamp > 0:
            timestamps.append(timestamp)
        if not all(_finite_positive(value) for value in (open_price, high, low, close)):
            invalid_price += 1
            continue
        if high < max(open_price, close) or low > min(open_price, close) or high <= low:
            invalid_ohlc += 1
            continue
        ranges.append(high - low)
        if volume > 0:
            volume_present += 1

    if invalid_price:
        penalty = min(35, invalid_price * 3)
        score -= penalty
        issues.append(f"invalid_prices:{invalid_price}")
    if invalid_ohlc:
        penalty = min(35, invalid_ohlc * 4)
        score -= penalty
        issues.append(f"invalid_ohlc:{invalid_ohlc}")

    chronological = all(timestamps[index] < timestamps[index + 1] for index in range(len(timestamps) - 1))
    if not chronological:
        score -= 30
        issues.append("timestamps_not_strictly_increasing")

    duplicates = len(timestamps) - len(set(timestamps))
    if duplicates:
        score -= min(25, duplicates * 3)
        issues.append(f"duplicate_timestamps:{duplicates}")

    expected = timeframe_seconds(timeframe)
    gaps = 0
    if expected > 0:
        for previous, current in zip(timestamps, timestamps[1:]):
            if current - previous > expected * 2.2 and not _weekend_gap(previous, current, market):
                gaps += 1
    gap_ratio = gaps / max(len(timestamps) - 1, 1)
    if gap_ratio > 0.08:
        score -= min(25, gap_ratio * 100)
        issues.append(f"excessive_gaps:{gaps}")
    elif gaps:
        score -= min(8, gaps * 0.5)
        warnings.append(f"minor_gaps:{gaps}")

    outliers = 0
    median_range = median(ranges) if ranges else 0.0
    if median_range > 0:
        outliers = sum(1 for item in ranges if item > median_range * 12)
        if outliers:
            score -= min(18, outliers * 2)
            warnings.append(f"range_outliers:{outliers}")

    volume_coverage = volume_present / max(count, 1)
    volume_mode = "real_or_tick" if volume_coverage >= 0.7 else "sparse_or_unavailable"
    if market == "crypto" and volume_coverage < 0.7:
        score -= 15
        issues.append("crypto_volume_missing")
    elif market == "forex" and volume_coverage < 0.3:
        warnings.append("forex_volume_proxy_unavailable")

    score = round(max(0.0, min(score, 100.0)), 1)
    return {
        "score": score,
        "tradable": score >= 72 and not invalid_ohlc and chronological,
        "sample_size": count,
        "expected_interval_seconds": expected,
        "gap_count": gaps,
        "gap_ratio": round(gap_ratio, 4),
        "duplicate_timestamps": duplicates,
        "invalid_ohlc": invalid_ohlc,
        "invalid_prices": invalid_price,
        "range_outliers": outliers,
        "volume_coverage": round(volume_coverage, 3),
        "volume_mode": volume_mode,
        "issues": issues,
        "warnings": warnings,
    }


def classify_market_regime(candles: list[dict]) -> dict:
    if len(candles) < 30:
        return {
            "name": "insufficient_data",
            "direction": "neutral",
            "efficiency_ratio": 0.0,
            "volatility_ratio": 0.0,
            "risk_multiplier": 0.0,
        }

    closes = [float(item["c"]) for item in candles[-120:]]
    highs = [float(item["h"]) for item in candles[-120:]]
    lows = [float(item["l"]) for item in candles[-120:]]
    total_path = sum(abs(closes[index] - closes[index - 1]) for index in range(1, len(closes)))
    displacement = abs(closes[-1] - closes[0])
    efficiency = displacement / total_path if total_path else 0.0

    true_ranges = []
    for index in range(1, len(closes)):
        true_ranges.append(
            max(
                highs[index] - lows[index],
                abs(highs[index] - closes[index - 1]),
                abs(lows[index] - closes[index - 1]),
            )
        )
    base_atr = median(true_ranges) if true_ranges else 0.0
    recent_atr = median(true_ranges[-20:]) if true_ranges[-20:] else base_atr
    volatility_ratio = recent_atr / base_atr if base_atr else 1.0
    move_in_atr = displacement / base_atr if base_atr else 0.0
    direction = "bullish" if closes[-1] > closes[0] else "bearish" if closes[-1] < closes[0] else "neutral"

    if volatility_ratio >= 1.65:
        name = "volatile"
        risk_multiplier = 0.55
    elif volatility_ratio <= 0.62:
        name = "compressed"
        risk_multiplier = 0.72
    elif efficiency >= 0.32 and move_in_atr >= 3.0:
        name = "trending"
        risk_multiplier = 1.0
    elif efficiency <= 0.14:
        name = "choppy"
        risk_multiplier = 0.6
    else:
        name = "balanced"
        risk_multiplier = 0.82

    return {
        "name": name,
        "direction": direction,
        "efficiency_ratio": round(efficiency, 4),
        "volatility_ratio": round(volatility_ratio, 3),
        "move_in_atr": round(move_in_atr, 2),
        "atr": round(base_atr, 8),
        "atr_pct": round((base_atr / closes[-1] * 100), 5) if closes[-1] else 0.0,
        "risk_multiplier": risk_multiplier,
    }
