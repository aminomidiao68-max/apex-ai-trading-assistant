from __future__ import annotations

from typing import Iterable, List


def sma(values: Iterable[float], period: int) -> float:
    vals = list(values)
    if len(vals) < period:
        return sum(vals) / max(len(vals), 1)
    window = vals[-period:]
    return sum(window) / period


def ema(values: List[float], period: int) -> float:
    if not values:
        return 0.0
    k = 2 / (period + 1)
    ema_value = values[0]
    for price in values[1:]:
        ema_value = price * k + ema_value * (1 - k)
    return ema_value


def rsi(values: List[float], period: int = 14) -> float:
    if len(values) <= period:
        return 50.0
    gains = []
    losses = []
    for i in range(1, len(values)):
        diff = values[i] - values[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(abs(min(diff, 0.0)))
    avg_gain = sma(gains, period)
    avg_loss = sma(losses, period)
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    if len(closes) < 2:
        return 0.0
    true_ranges = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        true_ranges.append(tr)
    return sma(true_ranges, min(period, len(true_ranges)))


def momentum_histogram(values: List[float], fast: int = 12, slow: int = 26) -> float:
    if len(values) < 5:
        return 0.0
    return ema(values, fast) - ema(values, slow)
