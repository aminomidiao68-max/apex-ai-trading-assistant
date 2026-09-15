"""Indicator Pack v2 — deterministic professional oscillator/indicator grid.

Adds the indicators that were missing from the v1 grid (advanced_indicators):
TRIX, KST, ROC, Force Index, Elder Ray, Chaikin, Ultimate Osc, Aroon,
Donchian, Keltner, TTM Squeeze, PVT, A/D line, VWAP ±σ bands, Awesome &
Accelerator Oscillator, Hull MA, Williams Fractals, Choppiness, classic
Pivot Points, Z-Score and linear-regression momentum.

Pure python, no look-ahead: every value uses only data up to the last candle.
"""

from __future__ import annotations

import math
from typing import Any

# --------------------------------------------------------------- primitives


def _sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def _sma_series(values: list[float], period: int) -> list[float]:
    out: list[float] = []
    roll = 0.0
    for i, v in enumerate(values):
        roll += v
        if i >= period:
            roll -= values[i - period]
        if i >= period - 1:
            out.append(roll / period)
    return out


def _ema_series(values: list[float], period: int) -> list[float]:
    if len(values) < period:
        return []
    k = 2.0 / (period + 1)
    out = [sum(values[:period]) / period]
    for v in values[period:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def _ema(values: list[float], period: int) -> float | None:
    s = _ema_series(values, period)
    return s[-1] if s else None


def _wma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    w = list(range(1, period + 1))
    chunk = values[-period:]
    return sum(x * wi for x, wi in zip(chunk, w)) / sum(w)


def _rma(values: list[float], period: int) -> list[float]:
    """Wilder smoothing series."""
    if len(values) < period:
        return []
    out = [sum(values[:period]) / period]
    for v in values[period:]:
        out.append((out[-1] * (period - 1) + v) / period)
    return out


def _true_ranges(highs: list[float], lows: list[float], closes: list[float]) -> list[float]:
    trs = [highs[0] - lows[0]]
    for i in range(1, len(highs)):
        trs.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))
    return trs


def _atr_value(highs, lows, closes, period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    s = _rma(_true_ranges(highs, lows, closes), period)
    return s[-1] if s else None


def _linreg(values: list[float], period: int) -> dict | None:
    """Least-squares line over the last `period` values; returns last value and slope."""
    if len(values) < period:
        return None
    ys = values[-period:]
    n = period
    xs = list(range(n))
    mx = (n - 1) / 2
    my = sum(ys) / n
    denom = sum((x - mx) ** 2 for x in xs)
    slope = sum((xs[i] - mx) * (ys[i] - my) for i in range(n)) / denom if denom else 0.0
    intercept = my - slope * mx
    last = intercept + slope * (n - 1)
    return {"value": last, "slope": slope}


def _r(value: Any, digits: int = 4) -> Any:
    try:
        if value is None:
            return None
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        return round(float(value), digits)
    except Exception:
        return None


def _sig(value: float | None, bull_if: float, bear_if: float, digits: int = 4) -> dict:
    """Generic three-way signal helper: value >= bull_if -> bullish etc."""
    if value is None:
        return {"value": None, "signal": "neutral", "strength": 0}
    if bull_if >= bear_if:
        if value >= bull_if:
            sig = "bullish"
        elif value <= bear_if:
            sig = "bearish"
        else:
            sig = "neutral"
    else:
        sig = "neutral"
    span = max(abs(bull_if - bear_if), 1e-9)
    strength = int(min(100, abs(value) / span * 50)) if sig != "neutral" else 0
    return {"value": _r(value, digits), "signal": sig, "strength": strength}


def _dir_sig(value: float | None, ref: float | None, digits: int = 4) -> dict:
    if value is None or ref is None:
        return {"value": _r(value, digits), "signal": "neutral", "strength": 0}
    if value > ref:
        return {"value": _r(value, digits), "signal": "bullish", "strength": 50}
    if value < ref:
        return {"value": _r(value, digits), "signal": "bearish", "strength": 50}
    return {"value": _r(value, digits), "signal": "neutral", "strength": 0}


# --------------------------------------------------------------- indicators


def roc(closes: list[float], period: int = 12) -> dict:
    if len(closes) <= period:
        return _sig(None, 1, -1)
    v = (closes[-1] - closes[-1 - period]) / closes[-1 - period] * 100 if closes[-1 - period] else None
    out = _sig(v, 0.5, -0.5, 3)
    return out


def momentum(closes: list[float], period: int = 10) -> dict:
    if len(closes) <= period:
        return _sig(None, 0, 0)
    v = closes[-1] - closes[-1 - period]
    ref = max(abs(closes[-1]) * 0.001, 1e-9)
    out = _sig(v / ref, 1.0, -1.0, 4)
    return out


def trix(closes: list[float], period: int = 15, signal: int = 9) -> dict:
    if len(closes) < period * 3 + signal:
        return {"value": None, "signal_line": None, "signal": "neutral", "cross": None}
    e1 = _ema_series(closes, period)
    e2 = _ema_series(e1, period)
    e3 = _ema_series(e2, period)
    if len(e3) < 2:
        return {"value": None, "signal_line": None, "signal": "neutral", "cross": None}
    trix_series = [(e3[i] - e3[i - 1]) / e3[i - 1] * 100 for i in range(1, len(e3)) if e3[i - 1]]
    if len(trix_series) < signal:
        return {"value": None, "signal_line": None, "signal": "neutral", "cross": None}
    sig_line = _ema(trix_series, signal)
    val = trix_series[-1]
    cross = None
    if sig_line is not None and len(trix_series) >= signal + 1:
        prev_sig = _ema(trix_series[:-1], signal)
        if prev_sig is not None:
            if trix_series[-2] <= prev_sig and val > sig_line:
                cross = "bullish"
            elif trix_series[-2] >= prev_sig and val < sig_line:
                cross = "bearish"
    sig_name = "bullish" if (sig_line is not None and val > sig_line) else "bearish" if (sig_line is not None and val < sig_line) else "neutral"
    return {"value": _r(val, 5), "signal_line": _r(sig_line, 5), "signal": sig_name, "cross": cross}


def kst(closes: list[float]) -> dict:
    """Know Sure Thing: smoothed ROC(10,15,20,30) with SMA(10,10,10,15)."""
    if len(closes) < 65:
        return {"value": None, "signal_line": None, "signal": "neutral"}
    def roc_sma(roc_n: int, sma_n: int) -> float | None:
        series = []
        for i in range(roc_n, len(closes) + 1):
            base = closes[i - 1 - roc_n]
            if base:
                series.append((closes[i - 1] - base) / base * 100)
        return _sma(series, sma_n)
    r1, r2, r3, r4 = roc_sma(10, 10), roc_sma(15, 10), roc_sma(20, 10), roc_sma(30, 15)
    if None in (r1, r2, r3, r4):
        return {"value": None, "signal_line": None, "signal": "neutral"}
    val = r1 + 2 * r2 + 3 * r3 + 4 * r4
    # signal = SMA9 of KST — approximate with last 9 KST values recomputed on shifted windows
    kst_series = []
    for shift in range(8, -1, -1):
        c = closes[: len(closes) - shift] if shift else closes
        def rs(roc_n: int, sma_n: int) -> float | None:
            series = []
            for i in range(roc_n, len(c) + 1):
                base = c[i - 1 - roc_n]
                if base:
                    series.append((c[i - 1] - base) / base * 100)
            return _sma(series, sma_n)
        a, b, cc, d = rs(10, 10), rs(15, 10), rs(20, 10), rs(30, 15)
        if None not in (a, b, cc, d):
            kst_series.append(a + 2 * b + 3 * cc + 4 * d)
    sig_line = _sma(kst_series, 9) if len(kst_series) >= 9 else None
    sig_name = "neutral"
    if sig_line is not None:
        sig_name = "bullish" if val > sig_line else "bearish" if val < sig_line else "neutral"
    return {"value": _r(val, 3), "signal_line": _r(sig_line, 3), "signal": sig_name}


def force_index(closes: list[float], vols: list[float], period: int = 13) -> dict:
    if len(closes) < period + 2:
        return _sig(None, 1, -1)
    fi = [(closes[i] - closes[i - 1]) * vols[i] for i in range(1, len(closes))]
    smoothed = _ema_series(fi, period)
    if not smoothed:
        return _sig(None, 1, -1)
    val = smoothed[-1]
    scale = max(_sma([abs(x) for x in fi[-50:]], 50) or 1.0, 1e-9)
    return _sig(val / scale, 0.15, -0.15, 4)


def elder_ray(highs: list[float], lows: list[float], closes: list[float], period: int = 13) -> dict:
    e = _ema(closes, period)
    if e is None:
        return {"bull_power": None, "bear_power": None, "signal": "neutral"}
    atr = _atr_value(highs, lows, closes) or max(e * 0.01, 1e-9)
    bull = (highs[-1] - e) / atr
    bear = (lows[-1] - e) / atr
    if bull > 0.1 and bear > -1.2:
        sig = "bullish"
    elif bear < -0.1 and bull < 1.2:
        sig = "bearish"
    else:
        sig = "neutral"
    return {"bull_power": _r(bull, 3), "bear_power": _r(bear, 3), "signal": sig}


def chaikin_oscillator(highs: list[float], lows: list[float], closes: list[float], vols: list[float]) -> dict:
    if len(closes) < 15:
        return _sig(None, 1, -1)
    adl: list[float] = []
    acc = 0.0
    for i in range(len(closes)):
        rng = highs[i] - lows[i]
        mfm = ((closes[i] - lows[i]) - (highs[i] - closes[i])) / rng if rng > 0 else 0.0
        acc += mfm * vols[i]
        adl.append(acc)
    e3 = _ema_series(adl, 3)
    e10 = _ema_series(adl, 10)
    if not e3 or not e10:
        return _sig(None, 1, -1)
    # align tails
    val = e3[-1] - e10[-1]
    vol_scale = max(_sma(vols, 20) or 1.0, 1e-9)
    return _sig(val / vol_scale, 0.1, -0.1, 4)


def ultimate_oscillator(highs: list[float], lows: list[float], closes: list[float]) -> dict:
    if len(closes) < 29:
        return _sig(None, 70, 30)
    trs = _true_ranges(highs, lows, closes)
    bps = []
    for i in range(1, len(closes)):
        tr = trs[i]
        bp = closes[i] - min(lows[i], closes[i - 1])
        bps.append(bp / tr if tr > 0 else 0.0)
    def avg(n: int) -> float | None:
        if len(bps) < n:
            return None
        return sum(bps[-n:]) / n  # simplified average of BP/TR ratio
    a7, a14, a28 = avg(7), avg(14), avg(28)
    if None in (a7, a14, a28):
        return _sig(None, 70, 30)
    val = (4 * a7 + 2 * a14 + a28) / 7 * 100
    sig = "bullish" if val > 55 else "bearish" if val < 45 else "neutral"
    if val > 70:
        sig = "bearish"  # overbought
    elif val < 30:
        sig = "bullish"  # oversold
    return {"value": _r(val, 2), "signal": sig, "overbought": val > 70, "oversold": val < 30}


def aroon(highs: list[float], lows: list[float], period: int = 25) -> dict:
    if len(highs) < period + 1:
        return {"up": None, "down": None, "osc": None, "signal": "neutral"}
    win_h = highs[-(period + 1):]
    win_l = lows[-(period + 1):]
    hi_idx = win_h.index(max(win_h))
    lo_idx = win_l.index(min(win_l))
    up = hi_idx / period * 100
    down = lo_idx / period * 100
    osc = up - down
    sig = "bullish" if up > 70 and down < 30 else "bearish" if down > 70 and up < 30 else "neutral"
    return {"up": _r(up, 1), "down": _r(down, 1), "osc": _r(osc, 1), "signal": sig}


def donchian(highs: list[float], lows: list[float], closes: list[float], period: int = 20) -> dict:
    if len(highs) < period + 1:
        return {"upper": None, "lower": None, "mid": None, "signal": "neutral"}
    upper = max(highs[-period - 1:-1])
    lower = min(lows[-period - 1:-1])
    mid = (upper + lower) / 2
    c = closes[-1]
    if c > upper:
        sig = "bullish"
    elif c < lower:
        sig = "bearish"
    else:
        sig = "neutral"
    return {"upper": _r(upper, 6), "lower": _r(lower, 6), "mid": _r(mid, 6), "signal": sig,
            "position_pct": _r((c - lower) / (upper - lower) * 100 if upper > lower else 50, 1)}


def keltner(highs: list[float], lows: list[float], closes: list[float], period: int = 20, mult: float = 2.0) -> dict:
    e = _ema_series(closes, period)
    atr = _atr_value(highs, lows, closes, period)
    if not e or atr is None:
        return {"upper": None, "lower": None, "mid": None, "signal": "neutral"}
    mid = e[-1]
    return {
        "upper": _r(mid + mult * atr, 6),
        "lower": _r(mid - mult * atr, 6),
        "mid": _r(mid, 6),
        "signal": "bullish" if closes[-1] > mid + mult * atr else "bearish" if closes[-1] < mid - mult * atr else "neutral",
    }


def ttm_squeeze(highs: list[float], lows: list[float], closes: list[float], period: int = 20) -> dict:
    """TTM Squeeze: Bollinger(20,2) inside Keltner(20,1.5) + linreg momentum."""
    if len(closes) < period + 12:
        return {"squeeze_on": None, "momentum": None, "signal": "neutral"}
    def bb_inside(offset: int) -> bool | None:
        c = closes[: len(closes) - offset] if offset else closes
        h = highs[: len(highs) - offset] if offset else highs
        l = lows[: len(lows) - offset] if offset else lows
        if len(c) < period:
            return None
        mean = sum(c[-period:]) / period
        sd = math.sqrt(sum((x - mean) ** 2 for x in c[-period:]) / period)
        atr = _atr_value(h, l, c, period)
        if atr is None:
            return None
        bb_up, bb_lo = mean + 2 * sd, mean - 2 * sd
        kc_up, kc_lo = mean + 1.5 * atr, mean - 1.5 * atr
        return bb_lo > kc_lo and bb_up < kc_up
    current = bb_inside(0)
    history = [bb_inside(k) for k in range(0, 10)]
    history = [h for h in history if h is not None]
    on_count = sum(1 for h in history if h)
    lr = _linreg(closes, period)
    mom = lr["slope"] if lr else None
    price_ref = closes[-1] or 1.0
    mom_pct = (mom / price_ref * 100) if mom is not None else None
    fired = bool(current is False and on_count >= 5)
    sig = "neutral"
    if fired and mom_pct is not None:
        sig = "bullish" if mom_pct > 0 else "bearish"
    elif current:
        sig = "coiling"
    return {
        "squeeze_on": bool(current) if current is not None else None,
        "recent_on_count": on_count,
        "squeeze_fired": fired,
        "momentum": _r(mom_pct, 4),
        "signal": sig,
    }


def pvt(closes: list[float], vols: list[float], period: int = 20) -> dict:
    if len(closes) < period + 2:
        return {"slope_pct": None, "signal": "neutral"}
    series = [0.0]
    for i in range(1, len(closes)):
        if closes[i - 1]:
            series.append(series[-1] + (closes[i] - closes[i - 1]) / closes[i - 1] * vols[i])
    lr = _linreg(series, period)
    if lr is None:
        return {"slope_pct": None, "signal": "neutral"}
    scale = max(_sma(vols, 20) or 1.0, 1e-9)
    norm = lr["slope"] / scale
    return {"slope_pct": _r(norm, 4), "signal": "bullish" if norm > 0.02 else "bearish" if norm < -0.02 else "neutral"}


def accumulation_distribution(highs: list[float], lows: list[float], closes: list[float], vols: list[float], period: int = 20) -> dict:
    if len(closes) < period + 2:
        return {"slope_pct": None, "signal": "neutral"}
    series = [0.0]
    for i in range(len(closes)):
        rng = highs[i] - lows[i]
        mfm = ((closes[i] - lows[i]) - (highs[i] - closes[i])) / rng if rng > 0 else 0.0
        series.append(series[-1] + mfm * vols[i])
    lr = _linreg(series, period)
    if lr is None:
        return {"slope_pct": None, "signal": "neutral"}
    scale = max(_sma(vols, 20) or 1.0, 1e-9)
    norm = lr["slope"] / scale
    return {"slope_pct": _r(norm, 4), "signal": "bullish" if norm > 0.02 else "bearish" if norm < -0.02 else "neutral"}


def vwap_bands(items: list[dict]) -> dict:
    """Session-anchored VWAP (UTC day) with ±1σ/±2σ bands; rolling fallback."""
    if not items:
        return {"vwap": None, "signal": "neutral"}
    day = int(items[-1]["t"] // 86400)
    todays = [it for it in items if int(it["t"] // 86400) == day]
    src = todays if len(todays) >= 5 else items[-96:]
    cum_pv = cum_v = 0.0
    cum_pvv = 0.0
    for it in src:
        tp = (it["h"] + it["l"] + it["c"]) / 3
        v = max(it["v"], 0.0)
        cum_pv += tp * v
        cum_v += v
        cum_pvv += (tp * tp) * v
    if cum_v <= 0:
        return {"vwap": None, "signal": "neutral"}
    vwap = cum_pv / cum_v
    var = max(cum_pvv / cum_v - vwap * vwap, 0.0)
    sd = math.sqrt(var)
    price = items[-1]["c"]
    sig = "neutral"
    if sd > 0:
        z = (price - vwap) / sd
        if z > 2:
            sig = "extended_up"
        elif z < -2:
            sig = "extended_down"
        elif z > 0.3:
            sig = "above"
        elif z < -0.3:
            sig = "below"
    return {
        "vwap": _r(vwap, 6), "sd": _r(sd, 6),
        "band_up1": _r(vwap + sd, 6), "band_up2": _r(vwap + 2 * sd, 6),
        "band_dn1": _r(vwap - sd, 6), "band_dn2": _r(vwap - 2 * sd, 6),
        "z_score": _r((price - vwap) / sd if sd > 0 else 0, 2),
        "anchored_today": len(todays) >= 5,
        "signal": sig,
    }


def awesome_oscillator(highs: list[float], lows: list[float]) -> dict:
    mids = [(h + l) / 2 for h, l in zip(highs, lows)]
    if len(mids) < 35:
        return {"value": None, "signal": "neutral"}
    fast = _sma_series(mids, 5)
    slow = _sma_series(mids, 34)
    if not fast or not slow:
        return {"value": None, "signal": "neutral"}
    align = min(len(fast), len(slow))
    ao = [fast[-align + i] - slow[-align + i] for i in range(align)]
    val = ao[-1]
    ref = mids[-1] * 0.001 if mids[-1] else 1.0
    norm = val / max(ref, 1e-12)
    cross = None
    if len(ao) >= 2:
        if ao[-2] <= 0 < ao[-1]:
            cross = "bullish"
        elif ao[-2] >= 0 > ao[-1]:
            cross = "bearish"
    sig = "bullish" if norm > 0.15 else "bearish" if norm < -0.15 else "neutral"
    accel = None
    if len(ao) >= 6:
        acc = ao[-1] - _sma(ao[-5:], 5)
        accel = _r(acc / max(ref, 1e-12), 4)
    return {"value": _r(norm, 4), "signal": sig, "cross": cross, "accelerator": accel}


def hull_ma(closes: list[float], period: int = 20) -> dict:
    if len(closes) < period + 4:
        return {"value": None, "direction": None, "signal": "neutral"}
    half = max(int(period / 2), 1)
    root = max(int(math.sqrt(period)), 1)
    w_half = _wma(closes[:-1], half)
    w_full = _wma(closes[:-1], period)
    # series for direction
    raw = []
    for i in range(period, len(closes) + 1):
        c = closes[:i]
        a = _wma(c, half)
        b = _wma(c, period)
        if a is not None and b is not None:
            raw.append(2 * a - b)
    hull = _wma(raw, root) if len(raw) >= root else None
    if hull is None:
        return {"value": None, "direction": None, "signal": "neutral"}
    prev = _wma(raw[:-1], root) if len(raw) >= root + 1 else None
    direction = None
    if prev is not None:
        direction = "up" if hull > prev else "down" if hull < prev else "flat"
    sig = "neutral"
    if direction == "up" and closes[-1] > hull:
        sig = "bullish"
    elif direction == "down" and closes[-1] < hull:
        sig = "bearish"
    return {"value": _r(hull, 6), "direction": direction, "signal": sig}


def williams_fractals(highs: list[float], lows: list[float], lookback: int = 40) -> dict:
    n = len(highs)
    if n < 7:
        return {"last_up": None, "last_down": None}
    up = down = None
    start = max(2, n - lookback)
    for i in range(start, n - 2):
        if highs[i] == max(highs[i - 2:i + 3]):
            up = highs[i]
        if lows[i] == min(lows[i - 2:i + 3]):
            down = lows[i]
    return {"last_up": _r(up, 6), "last_down": _r(down, 6)}


def choppiness(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> dict:
    if len(closes) < period + 1:
        return {"value": None, "regime": None}
    trs = _true_ranges(highs, lows, closes)[-period:]
    atr_sum = sum(trs)
    hh = max(highs[-period:])
    ll = min(lows[-period:])
    if hh <= ll or atr_sum <= 0:
        return {"value": None, "regime": None}
    val = 100 * math.log10(atr_sum / (hh - ll)) / math.log10(period)
    regime = "range" if val > 61.8 else "trend" if val < 38.2 else "transition"
    return {"value": _r(val, 1), "regime": regime, "signal": "neutral"}


def pivot_points(items: list[dict]) -> dict:
    """Classic floor pivots from the last completed UTC day."""
    if len(items) < 10:
        return {"pivot": None}
    day = int(items[-1]["t"] // 86400)
    prev = [it for it in items if int(it["t"] // 86400) == day - 1]
    if len(prev) < 4:
        days = sorted({int(it["t"] // 86400) for it in items})
        completed = [d for d in days if d < day]
        if not completed:
            return {"pivot": None}
        prev = [it for it in items if int(it["t"] // 86400) == completed[-1]]
    if not prev:
        return {"pivot": None}
    h = max(it["h"] for it in prev)
    l = min(it["l"] for it in prev)
    c = prev[-1]["c"]
    p = (h + l + c) / 3
    return {
        "pivot": _r(p, 6),
        "r1": _r(2 * p - l, 6), "s1": _r(2 * p - h, 6),
        "r2": _r(p + (h - l), 6), "s2": _r(p - (h - l), 6),
        "r3": _r(h + 2 * (p - l), 6), "s3": _r(l - 2 * (h - p), 6),
        "price_vs_p": "above" if items[-1]["c"] > p else "below",
    }


def zscore(closes: list[float], period: int = 20) -> dict:
    if len(closes) < period:
        return {"value": None, "signal": "neutral"}
    mean = sum(closes[-period:]) / period
    sd = math.sqrt(sum((x - mean) ** 2 for x in closes[-period:]) / period)
    if sd <= 0:
        return {"value": None, "signal": "neutral"}
    z = (closes[-1] - mean) / sd
    sig = "extreme_up" if z > 2 else "extreme_down" if z < -2 else "neutral"
    return {"value": _r(z, 2), "signal": sig}


def linreg_momentum(closes: list[float], period: int = 20) -> dict:
    lr = _linreg(closes, period)
    if lr is None:
        return {"slope_pct": None, "signal": "neutral"}
    ref = closes[-1] or 1.0
    slope_pct = lr["slope"] / ref * 100
    return {"slope_pct": _r(slope_pct, 4), "signal": "bullish" if slope_pct > 0.02 else "bearish" if slope_pct < -0.02 else "neutral"}


# --------------------------------------------------------------- aggregate


def compute_all(items: list[dict]) -> dict:
    if len(items) < 30:
        return {"available": False, "reason": "insufficient_data"}
    closes = [it["c"] for it in items]
    highs = [it["h"] for it in items]
    lows = [it["l"] for it in items]
    vols = [it["v"] for it in items]
    return {
        "available": True,
        "roc": roc(closes),
        "momentum": momentum(closes),
        "trix": trix(closes),
        "kst": kst(closes),
        "force_index": force_index(closes, vols),
        "elder_ray": elder_ray(highs, lows, closes),
        "chaikin": chaikin_oscillator(highs, lows, closes, vols),
        "ultimate_osc": ultimate_oscillator(highs, lows, closes),
        "aroon": aroon(highs, lows),
        "donchian": donchian(highs, lows, closes),
        "keltner": keltner(highs, lows, closes),
        "ttm_squeeze": ttm_squeeze(highs, lows, closes),
        "pvt": pvt(closes, vols),
        "ad_line": accumulation_distribution(highs, lows, closes, vols),
        "vwap": vwap_bands(items),
        "awesome": awesome_oscillator(highs, lows),
        "hull": hull_ma(closes),
        "fractals": williams_fractals(highs, lows),
        "choppiness": choppiness(highs, lows, closes),
        "pivots": pivot_points(items),
        "zscore": zscore(closes),
        "linreg_momentum": linreg_momentum(closes),
    }


_VOTERS = (
    "roc", "momentum", "trix", "kst", "force_index", "elder_ray", "chaikin",
    "ultimate_osc", "aroon", "donchian", "keltner", "pvt", "ad_line",
    "awesome", "hull", "linreg_momentum",
)


def summarize(pack: dict) -> dict:
    """Vote summary + regime + key levels for UI/AI context."""
    if not pack.get("available"):
        return {"available": False, "votes": {"bullish": 0, "bearish": 0, "neutral": 0}, "net": 0, "verdict": "no_data"}
    bull = bear = neutral = 0
    bullish_names: list[str] = []
    bearish_names: list[str] = []
    for name in _VOTERS:
        sig = str((pack.get(name) or {}).get("signal") or "neutral")
        if sig == "bullish":
            bull += 1
            bullish_names.append(name)
        elif sig == "bearish":
            bear += 1
            bearish_names.append(name)
        else:
            neutral += 1
    total = bull + bear + neutral
    net = round((bull - bear) / total * 100) if total else 0
    squeeze = pack.get("ttm_squeeze") or {}
    chop = pack.get("choppiness") or {}
    vwap = pack.get("vwap") or {}
    verdict = "bullish" if net >= 25 else "bearish" if net <= -25 else "mixed"
    if chop.get("regime") == "range" and abs(net) < 40:
        verdict = "range"
    levels = {
        "donchian_upper": (pack.get("donchian") or {}).get("upper"),
        "donchian_lower": (pack.get("donchian") or {}).get("lower"),
        "keltner_upper": (pack.get("keltner") or {}).get("upper"),
        "keltner_lower": (pack.get("keltner") or {}).get("lower"),
        "vwap": vwap.get("vwap"),
        "vwap_up2": vwap.get("band_up2"),
        "vwap_dn2": vwap.get("band_dn2"),
        "pivot": (pack.get("pivots") or {}).get("pivot"),
        "pivot_r1": (pack.get("pivots") or {}).get("r1"),
        "pivot_s1": (pack.get("pivots") or {}).get("s1"),
    }
    return {
        "available": True,
        "votes": {"bullish": bull, "bearish": bear, "neutral": neutral, "total": total},
        "net": net,
        "verdict": verdict,
        "bullish_indicators": bullish_names,
        "bearish_indicators": bearish_names,
        "squeeze_on": squeeze.get("squeeze_on"),
        "squeeze_fired": squeeze.get("squeeze_fired"),
        "regime_choppiness": chop.get("regime"),
        "choppiness_value": chop.get("value"),
        "vwap_z": vwap.get("z_score"),
        "levels": levels,
    }


def build_context_text(pack: dict, summary: dict) -> str:
    """Persian one-block context for AI prompts (empty string if unavailable)."""
    if not summary.get("available"):
        return ""
    v = summary["votes"]
    lines = [
        f"رأی اندیکاتورهای پیشرفته (پک v2): {v['bullish']} صعودی / {v['bearish']} نزولی / {v['neutral']} خنثی → خالص {summary['net']}٪ ({summary['verdict']})",
    ]
    sq = pack.get("ttm_squeeze") or {}
    if sq.get("squeeze_on"):
        lines.append("TTM Squeeze فعال (فشردگی) — منتظر انفجار حرکت؛ مومنتوم رگرسیون: " + str(sq.get("momentum")))
    elif sq.get("squeeze_fired"):
        lines.append("TTM Squeeze آزاد شد — جهت مومنتوم: " + str(sq.get("momentum")))
    chop = pack.get("choppiness") or {}
    if chop.get("value") is not None:
        lines.append(f"Choppiness={chop['value']} → رژیم: {chop.get('regime')}")
    vw = pack.get("vwap") or {}
    if vw.get("vwap") is not None:
        lines.append(f"VWAP جلسه={vw['vwap']} (z={vw.get('z_score')}) باندها: +2σ={vw.get('band_up2')} / -2σ={vw.get('band_dn2')}")
    piv = pack.get("pivots") or {}
    if piv.get("pivot") is not None:
        lines.append(f"پیوت کلاسیک روز قبل: P={piv['pivot']} R1={piv['r1']} S1={piv['s1']} R2={piv['r2']} S2={piv['s2']} — قیمت {piv.get('price_vs_p')} پیوت")
    if summary.get("bullish_indicators"):
        lines.append("صعودی: " + ", ".join(summary["bullish_indicators"]))
    if summary.get("bearish_indicators"):
        lines.append("نزولی: " + ", ".join(summary["bearish_indicators"]))
    return "\n".join(lines)
