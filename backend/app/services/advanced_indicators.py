"""Advanced professional indicators & oscillators (pure deterministic math).

No external deps, no guessing: every value is computed from real candles.
`confluence_snapshot` returns per-indicator values + bull/bear/neutral votes
and a signed convergence score in [-100, +100].
"""
from __future__ import annotations

import math
from typing import Any


def _sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def _wilder(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    result = sum(values[:period]) / period
    alpha = 1.0 / period
    for value in values[period:]:
        result = result * (1 - alpha) + value * alpha
    return result


def _r(value: float | None, digits: int = 4) -> Any:
    return round(value, digits) if value is not None and math.isfinite(value) else None


def rsi_series(closes: list[float], period: int = 14) -> list[float]:
    out: list[float] = []
    gains = losses = 0.0
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gain, loss = max(change, 0.0), max(-change, 0.0)
        if i <= period:
            gains += gain
            losses += loss
            if i == period:
                avg_gain, avg_loss = gains / period, losses / period
                out.append(100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss))
        else:
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period
            out.append(100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss))
    return out


def rsi(closes: list[float], period: int = 14) -> float | None:
    series = rsi_series(closes, period)
    return series[-1] if series else None


def stochastic(highs: list[float], lows: list[float], closes: list[float], period: int = 14, smoothing: int = 3) -> tuple[float | None, float | None]:
    if len(closes) < period + smoothing:
        return None, None
    k_values: list[float] = []
    for i in range(period - 1, len(closes)):
        window_high = max(highs[i - period + 1:i + 1])
        window_low = min(lows[i - period + 1:i + 1])
        span = window_high - window_low
        k_values.append(50.0 if span == 0 else (closes[i] - window_low) / span * 100)
    k = k_values[-1]
    d = sum(k_values[-smoothing:]) / smoothing
    return _r(k, 2), _r(d, 2)


def stoch_rsi(closes: list[float], period: int = 14) -> tuple[float | None, float | None]:
    series = rsi_series(closes, period)
    if len(series) < period:
        return None, None
    window = series[-period:]
    low, high = min(window), max(window)
    span = high - low
    k = 50.0 if span == 0 else (series[-1] - low) / span * 100
    return _r(k, 2), None


def cci(highs: list[float], lows: list[float], closes: list[float], period: int = 20) -> float | None:
    if len(closes) < period:
        return None
    tp = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)][-period:]
    mean = sum(tp) / period
    mean_dev = sum(abs(x - mean) for x in tp) / period
    if mean_dev == 0:
        return 0.0
    return _r((tp[-1] - mean) / (0.015 * mean_dev), 2)


def williams_r(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period:
        return None
    hh = max(highs[-period:])
    ll = min(lows[-period:])
    span = hh - ll
    return _r(-50.0 if span == 0 else (hh - closes[-1]) / span * -100, 2)


def mfi(highs: list[float], lows: list[float], closes: list[float], volumes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 1 or not volumes:
        return None
    positive = negative = 0.0
    for i in range(len(closes) - period, len(closes)):
        tp_prev = (highs[i - 1] + lows[i - 1] + closes[i - 1]) / 3
        tp = (highs[i] + lows[i] + closes[i]) / 3
        flow = tp * volumes[i]
        if tp > tp_prev:
            positive += flow
        elif tp < tp_prev:
            negative += flow
    if negative == 0:
        return 100.0
    if positive == 0:
        return 0.0
    return _r(100 - 100 / (1 + positive / negative), 2)


def obv_trend(closes: list[float], volumes: list[float]) -> dict:
    if not volumes or len(closes) < 10:
        return {"obv": None, "slope": "unknown"}
    obv = 0.0
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            obv += volumes[i]
        elif closes[i] < closes[i - 1]:
            obv -= volumes[i]
    recent = 0.0
    for i in range(len(closes) - 5, len(closes)):
        if closes[i] > closes[i - 1]:
            recent += volumes[i]
        elif closes[i] < closes[i - 1]:
            recent -= volumes[i]
    slope = "up" if recent > 0 else "down" if recent < 0 else "flat"
    return {"obv": _r(obv, 2), "slope": slope}


def adx_dmi(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> dict:
    n = len(closes)
    if n < period * 2 + 1:
        return {"adx": None, "plus_di": None, "minus_di": None}
    trs: list[float] = []
    plus_dms: list[float] = []
    minus_dms: list[float] = []
    for i in range(1, n):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]
        plus_dms.append(up_move if up_move > down_move and up_move > 0 else 0.0)
        minus_dms.append(down_move if down_move > up_move and down_move > 0 else 0.0)
        trs.append(tr)
    atr = _wilder(trs, period)
    plus_di = (_wilder(plus_dms, period) or 0) / atr * 100 if atr else None
    minus_di = (_wilder(minus_dms, period) or 0) / atr * 100 if atr else None
    dx_values: list[float] = []
    for i in range(period - 1, len(trs)):
        a = _wilder(trs[: i + 1], period) or 1e-12
        pdi = (_wilder(plus_dms[: i + 1], period) or 0) / a * 100
        mdi = (_wilder(minus_dms[: i + 1], period) or 0) / a * 100
        total = pdi + mdi
        dx_values.append(0.0 if total == 0 else abs(pdi - mdi) / total * 100)
    adx_value = _wilder(dx_values, period) if len(dx_values) >= period else None
    return {"adx": _r(adx_value, 2), "plus_di": _r(plus_di, 2), "minus_di": _r(minus_di, 2)}


def vwap_session(items: list[dict]) -> dict:
    if not items:
        return {"vwap": None, "distance_pct": None}
    last_day = int(items[-1]["t"]) // 86400
    pv = vv = 0.0
    for item in items:
        if int(item["t"]) // 86400 != last_day:
            continue
        tp = (item["h"] + item["l"] + item["c"]) / 3
        pv += tp * item.get("v", 0.0)
        vv += item.get("v", 0.0)
    if vv == 0:
        return {"vwap": None, "distance_pct": None}
    vwap = pv / vv
    price = items[-1]["c"]
    return {"vwap": _r(vwap, 6), "distance_pct": _r((price - vwap) / vwap * 100, 3) if vwap else None}


def supertrend(highs: list[float], lows: list[float], closes: list[float], period: int = 10, multiplier: float = 3.0) -> dict:
    n = len(closes)
    if n < period + 2:
        return {"direction": "unknown", "level": None}
    trs = [max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])) for i in range(1, n)]
    atr_series: list[float] = []
    atr = sum(trs[:period]) / period
    atr_series.append(atr)
    alpha = 1.0 / period
    for tr in trs[period:]:
        atr = atr * (1 - alpha) + tr * alpha
        atr_series.append(atr)
    upper = lower = 0.0
    direction = 1
    level = 0.0
    for i in range(period, n):
        idx = i - period
        mid = (highs[i] + lows[i]) / 2
        basic_upper = mid + multiplier * atr_series[idx]
        basic_lower = mid - multiplier * atr_series[idx]
        upper = min(basic_upper, upper) if upper and closes[i - 1] <= upper else basic_upper
        lower = max(basic_lower, lower) if lower and closes[i - 1] >= lower else basic_lower
        if closes[i] > upper:
            direction = 1
            level = lower
        elif closes[i] < lower:
            direction = -1
            level = upper
    return {"direction": "up" if direction == 1 else "down", "level": _r(level, 6)}


def ichimoku(highs: list[float], lows: list[float], closes: list[float]) -> dict:
    if len(closes) < 52:
        return {"tenkan": None, "kijun": None, "span_a": None, "span_b": None, "position": "unknown"}
    hh = lambda p: max(highs[-p:])
    ll = lambda p: min(lows[-p:])
    tenkan = (hh(9) + ll(9)) / 2
    kijun = (hh(26) + ll(26)) / 2
    span_a = (tenkan + kijun) / 2
    span_b = (hh(52) + ll(52)) / 2
    price = closes[-1]
    top = max(span_a, span_b)
    bottom = min(span_a, span_b)
    position = "above_cloud" if price > top else "below_cloud" if price < bottom else "inside_cloud"
    return {
        "tenkan": _r(tenkan, 6), "kijun": _r(kijun, 6),
        "span_a": _r(span_a, 6), "span_b": _r(span_b, 6), "position": position,
    }


def bollinger_percent_b(closes: list[float], period: int = 20, deviations: float = 2.0) -> dict:
    if len(closes) < period:
        return {"percent_b": None, "band_width_pct": None}
    window = closes[-period:]
    mean = sum(window) / period
    sd = (sum((x - mean) ** 2 for x in window) / period) ** 0.5
    upper = mean + deviations * sd
    lower = mean - deviations * sd
    span = upper - lower
    percent_b = 50.0 if span == 0 else (closes[-1] - lower) / span * 100
    band_width = span / mean * 100 if mean else None
    return {"percent_b": _r(percent_b, 2), "band_width_pct": _r(band_width, 3)}


def confluence_snapshot(items: list[dict]) -> dict:
    """Full professional oscillator/indicator grid + signed convergence score."""
    if len(items) < 35:
        return {"available": False, "reason": "insufficient_candles"}
    closes = [float(c["c"]) for c in items]
    highs = [float(c["h"]) for c in items]
    lows = [float(c["l"]) for c in items]
    volumes = [float(c.get("v") or 0) for c in items]
    price = closes[-1]

    ema = lambda period: _ema_last(closes, period)
    ema50 = ema(50)
    ema200 = ema(200) if len(closes) >= 200 else None

    rsi_v = rsi(closes)
    stoch_k, stoch_d = stochastic(highs, lows, closes)
    srsi_k, _ = stoch_rsi(closes)
    cci_v = cci(highs, lows, closes)
    willr_v = williams_r(highs, lows, closes)
    mfi_v = mfi(highs, lows, closes, volumes)
    obv = obv_trend(closes, volumes)
    dmi = adx_dmi(highs, lows, closes)
    vwap = vwap_session(items)
    st = supertrend(highs, lows, closes)
    ichi = ichimoku(highs, lows, closes)
    bb = bollinger_percent_b(closes)

    votes: dict[str, int] = {}

    def vote(name: str, direction: int) -> None:
        votes[name] = max(-1, min(1, direction))

    if rsi_v is not None:
        vote("rsi", 1 if rsi_v > 55 else -1 if rsi_v < 45 else 0)
    if stoch_k is not None and stoch_d is not None:
        vote("stoch", 1 if stoch_k > stoch_d and stoch_k < 80 else -1 if stoch_k < stoch_d and stoch_k > 20 else 0)
    if srsi_k is not None:
        vote("stoch_rsi", 1 if srsi_k > 50 else -1 if srsi_k < 50 else 0)
    if cci_v is not None:
        vote("cci", 1 if cci_v > 0 else -1 if cci_v < 0 else 0)
    if willr_v is not None:
        vote("williams_r", 1 if willr_v > -50 else -1 if willr_v < -50 else 0)
    if mfi_v is not None:
        vote("mfi", 1 if mfi_v > 50 else -1 if mfi_v < 50 else 0)
    vote("obv", 1 if obv["slope"] == "up" else -1 if obv["slope"] == "down" else 0)
    if dmi.get("adx") is not None and dmi["adx"] >= 20 and dmi.get("plus_di") is not None:
        vote("dmi", 1 if dmi["plus_di"] > (dmi.get("minus_di") or 0) else -1)
    else:
        vote("dmi", 0)
    if vwap.get("vwap"):
        vote("vwap", 1 if price > vwap["vwap"] else -1)
    vote("supertrend", 1 if st["direction"] == "up" else -1 if st["direction"] == "down" else 0)
    vote("ichimoku", {"above_cloud": 1, "below_cloud": -1}.get(ichi["position"], 0))
    if ema50:
        vote("ema50", 1 if price > ema50 else -1)
    if ema200:
        vote("ema200", 1 if price > ema200 else -1)

    bull = sum(1 for v in votes.values() if v == 1)
    bear = sum(1 for v in votes.values() if v == -1)
    neutral = sum(1 for v in votes.values() if v == 0)
    total = max(1, bull + bear + neutral)
    score = round(100 * (bull - bear) / max(1, bull + bear), 1) if (bull + bear) else 0.0
    stance = "bullish" if score >= 35 else "bearish" if score <= -35 else "mixed"

    return {
        "available": True,
        "price": _r(price, 6),
        "values": {
            "rsi14": _r(rsi_v, 2), "stoch_k": stoch_k, "stoch_d": stoch_d,
            "stoch_rsi_k": srsi_k, "cci20": cci_v, "williams_r": willr_v,
            "mfi14": mfi_v, "obv": obv, "adx": dmi, "vwap": vwap,
            "supertrend": st, "ichimoku": ichi, "bollinger": bb,
            "ema50": _r(ema50, 6), "ema200": _r(ema200, 6),
        },
        "votes": votes,
        "bull_count": bull, "bear_count": bear, "neutral_count": neutral,
        "score": score, "stance": stance,
    }


def _ema_last(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    result = sum(values[:period]) / period
    alpha = 2.0 / (period + 1)
    for value in values[period:]:
        result = value * alpha + result * (1 - alpha)
    return result
