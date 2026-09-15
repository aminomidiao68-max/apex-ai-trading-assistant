"""Strategy Pack v2 — deterministic classic/professional strategy detectors.

22 validated strategies scanned on real candles (no repainting, no look-ahead):
Wyckoff (Spring / Upthrust / SOS), Turtle-Donchian breakout, ORB, Inside-Bar,
Double Top/Bottom, Head & Shoulders (+inverse), Rising/Falling Wedge,
Flag/Pennant, EMA 9/21 pullback, Golden/Death cross, TTM Squeeze breakout,
VWAP reversion & bounce, Judas Swing, Power-of-3 (AMD), RSI/MACD divergence
reversal, Supertrend flip, Ichimoku system, SAR flip, Engulfing-at-level.

Every detector returns status=active|forming|none with a strict quality score.
"""

from __future__ import annotations

import math
from typing import Any

# ---------------------------------------------------------------- helpers


def _r(value: Any, digits: int = 6) -> Any:
    try:
        if value is None:
            return None
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        return round(float(value), digits)
    except Exception:
        return None


def _atr(items: list[dict], n: int = 14) -> float:
    if len(items) < n + 1:
        rng = [it["h"] - it["l"] for it in items]
        return sum(rng) / len(rng) if rng else 0.0
    trs = []
    for i in range(1, len(items)):
        h, l, pc = items[i]["h"], items[i]["l"], items[i - 1]["c"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    seed = sum(trs[:n]) / n
    val = seed
    for tr in trs[n:]:
        val = (val * (n - 1) + tr) / n
    return val or 1e-9


def _sma(values: list[float], n: int) -> float | None:
    return sum(values[-n:]) / n if len(values) >= n else None


def _ema_series(values: list[float], n: int) -> list[float]:
    if len(values) < n:
        return []
    k = 2 / (n + 1)
    out = [sum(values[:n]) / n]
    for v in values[n:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def _swings(items: list[dict], k: int = 2) -> tuple[list[int], list[int]]:
    highs: list[int] = []
    lows: list[int] = []
    for i in range(k, len(items) - k):
        win_h = [items[j]["h"] for j in range(i - k, i + k + 1)]
        win_l = [items[j]["l"] for j in range(i - k, i + k + 1)]
        if items[i]["h"] == max(win_h) and win_h.count(items[i]["h"]) == 1:
            highs.append(i)
        if items[i]["l"] == min(win_l) and win_l.count(items[i]["l"]) == 1:
            lows.append(i)
    return highs, lows


def _rsi_series(closes: list[float], n: int = 14) -> list[float]:
    if len(closes) < n + 2:
        return []
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    ag = sum(gains[:n]) / n
    al = sum(losses[:n]) / n
    out = []
    for i in range(n, len(gains)):
        ag = (ag * (n - 1) + gains[i]) / n
        al = (al * (n - 1) + losses[i]) / n
        rs = ag / al if al > 0 else 999
        out.append(100 - 100 / (1 + rs))
    return out


def _macd(closes: list[float]) -> tuple[list[float], list[float], list[float]]:
    if len(closes) < 35:
        return [], [], []
    f = _ema_series(closes, 12)
    s = _ema_series(closes, 26)
    diff = len(f) - len(s)
    macd = [f[diff + i] - s[i] for i in range(len(s))]
    sig = _ema_series(macd, 9)
    d2 = len(macd) - len(sig)
    hist = [macd[d2 + i] - sig[i] for i in range(len(sig))]
    return macd, sig, hist


def _result(id_: str, name_fa: str, family: str, direction: str, status: str,
            quality: int, reason_fa: str, entry=None, stop=None, target=None,
            extra: dict | None = None) -> dict:
    out = {
        "id": id_, "name_fa": name_fa, "family": family,
        "direction": direction if status != "none" else "none",
        "status": status, "quality": int(max(0, min(100, quality))),
        "reason_fa": reason_fa,
        "entry": _r(entry), "stop": _r(stop), "target": _r(target),
    }
    if extra:
        out.update(extra)
    return out


# ---------------------------------------------------------------- detectors


def _wyckoff(items: list[dict], atr: float) -> list[dict]:
    out = []
    n = len(items)
    if n < 60:
        return out
    box = items[-60:-3]
    hi = max(it["h"] for it in box)
    lo = min(it["l"] for it in box)
    width = (hi - lo) / ((hi + lo) / 2) if hi + lo else 0
    avg_v = _sma([it["v"] for it in items[-60:-3]], 57) or 0
    recent = items[-3:]
    # Spring: wick below range low, close back inside
    for it in recent:
        if it["l"] < lo - 0.05 * atr and it["c"] > lo and it["c"] > it["o"]:
            recovery = (it["c"] - lo) / (it["h"] - it["l"]) if it["h"] > it["l"] else 0
            q = int(45 + 35 * min(recovery, 1.0) + (15 if avg_v and it["v"] > 1.2 * avg_v else 0) + (5 if width < 0.06 else 0))
            out.append(_result(
                "wyckoff_spring", "اسپرینگ وایکاف (Spring)", "Wyckoff", "long", "active", q,
                f"قیمت کف رنج {lo:.6g} را جارو کرد و با قدرت به داخل رنج برگشت — نشانه جذب فروشندگان (فاز C وایکاف).",
                entry=it["c"], stop=it["l"] - 0.5 * atr, target=max(hi, it["c"] + 1.2 * atr),
                extra={"range_high": _r(hi), "range_low": _r(lo)}))
            break
        if it["h"] > hi + 0.05 * atr and it["c"] < hi and it["c"] < it["o"]:
            rejection = (hi - it["c"]) / (it["h"] - it["l"]) if it["h"] > it["l"] else 0
            q = int(45 + 35 * min(rejection, 1.0) + (15 if avg_v and it["v"] > 1.2 * avg_v else 0) + (5 if width < 0.06 else 0))
            out.append(_result(
                "wyckoff_upthrust", "آپ‌تراست وایکاف (UTAD)", "Wyckoff", "short", "active", q,
                f"قیمت سقف رنج {hi:.6g} را شکست اما نتوانست نگه دارد — تله گاوها (فاز C وایکاف).",
                entry=it["c"], stop=it["h"] + 0.5 * atr, target=min(lo, it["c"] - 1.2 * atr),
                extra={"range_high": _r(hi), "range_low": _r(lo)}))
            break
    # SOS: strong spread + volume breakout above range
    last = items[-1]
    avg_spread = _sma([it["h"] - it["l"] for it in items[-40:-1]], 39) or atr
    if last["c"] > hi and (last["h"] - last["l"]) > 1.5 * avg_spread and avg_v and last["v"] > 1.4 * avg_v:
        out.append(_result(
            "wyckoff_sos", "نشانه قدرت (SOS)", "Wyckoff", "long", "active", 70,
            f"شکست رنج با اسپرید و حجم قوی — SOS؛ انتظار LPS (پولبک کم‌حجم) برای ورود.",
            entry=hi, stop=hi - 1.2 * atr, target=hi + 2.5 * atr))
    return out


def _turtle(items: list[dict]) -> list[dict]:
    n = len(items)
    if n < 56:
        return []
    up20 = max(it["h"] for it in items[-21:-1])
    dn20 = min(it["l"] for it in items[-21:-1])
    up55 = max(it["h"] for it in items[-56:-1])
    dn55 = min(it["l"] for it in items[-56:-1])
    last = items[-1]
    res = []
    if last["c"] > up20:
        trend = "با تأیید روند ۵۵ کندلی" if last["c"] > up55 else ""
        res.append(_result("turtle_breakout", "شکست لاک‌پشتی (Donchian 20)", "Breakout", "long", "active",
                           72 if trend else 58, f"بسته‌شدن بالای بالاترین سقف ۲۰ کندل {up20:.6g} {trend} — ورود کلاسیک Turtle.",
                           entry=up20, stop=dn20 if not trend else max(dn20, last["c"] * 0.98), target=None))
    if last["c"] < dn20:
        trend = "با تأیید روند ۵۵ کندلی" if last["c"] < dn55 else ""
        res.append(_result("turtle_breakout", "شکست لاک‌پشتی (Donchian 20)", "Breakout", "short", "active",
                           72 if trend else 58, f"بسته‌شدن زیر پایین‌ترین کف ۲۰ کندل {dn20:.6g} {trend} — ورود کلاسیک Turtle.",
                           entry=dn20, stop=up20 if not trend else min(up20, last["c"] * 1.02), target=None))
    return res


def _orb(items: list[dict], timeframe: str) -> list[dict]:
    """Opening Range Breakout — first 60 minutes of the current UTC day."""
    tf_min = {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30, "60m": 60, "1h": 60, "2h": 120, "4h": 240}.get(timeframe, 15)
    if tf_min > 30:
        return []
    day = int(items[-1]["t"] // 86400)
    day_items = [it for it in items if int(it["t"] // 86400) == day]
    bars_per_hour = max(int(60 / tf_min), 1)
    if len(day_items) < bars_per_hour + 1:
        return []
    or_bars = day_items[:bars_per_hour]
    rest = day_items[bars_per_hour:]
    hi = max(it["h"] for it in or_bars)
    lo = min(it["l"] for it in or_bars)
    if not rest:
        return []
    last = rest[-1]
    if last["c"] > hi:
        return [_result("orb", "شکست محدوده بازگشایی (ORB)", "Breakout", "long", "active", 62,
                        f"شکست سقف ORB ساعت اول {hi:.6g} — ادامه حرکت روزانه محتمل.", entry=hi, stop=(hi + lo) / 2, target=hi + (hi - lo))]
    if last["c"] < lo:
        return [_result("orb", "شکست محدوده بازگشایی (ORB)", "Breakout", "short", "active", 62,
                        f"شکست کف ORB ساعت اول {lo:.6g} — ادامه حرکت روزانه محتمل.", entry=lo, stop=(hi + lo) / 2, target=lo - (hi - lo))]
    return [_result("orb", "شکست محدوده بازگشایی (ORB)", "Breakout", "none", "forming", 30,
                    f"قیمت داخل محدوده ORB ({lo:.6g}–{hi:.6g}) — منتظر شکست یکی از دو لبه.")]


def _inside_bar(items: list[dict], atr: float) -> list[dict]:
    if len(items) < 4:
        return []
    mother, inside, last = items[-3], items[-2], items[-1]
    is_inside = inside["h"] <= mother["h"] and inside["l"] >= mother["l"]
    if not is_inside:
        return []
    if last["c"] > mother["h"]:
        return [_result("inside_bar", "شکست اینساید بار", "Price Action", "long", "active", 60,
                        f"شکست سقف مادر {mother['h']:.6g} بعد از فشردگی — مومنتوم صعودی.", entry=mother["h"], stop=inside["l"], target=mother["h"] + 2 * (mother["h"] - inside["l"]))]
    if last["c"] < mother["l"]:
        return [_result("inside_bar", "شکست اینساید بار", "Price Action", "short", "active", 60,
                        f"شکست کف مادر {mother['l']:.6g} بعد از فشردگی — مومنتوم نزولی.", entry=mother["l"], stop=inside["h"], target=mother["l"] - 2 * (inside["h"] - mother["l"]))]
    return [_result("inside_bar", "اینساید بار (فشردگی)", "Price Action", "none", "forming", 40,
                    f"اینساید بار شکل گرفته ({inside['l']:.6g}–{inside['h']:.6g}) — منتظر شکست مادر.")]


def _double_tb(items: list[dict], atr: float) -> list[dict]:
    sh, sl = _swings(items[-80:] if len(items) >= 80 else items, k=3)
    off = max(0, len(items) - 80)
    out = []
    tol = 0.25 * atr
    # Double bottom
    if len(sl) >= 2:
        i1, i2 = sl[-2], sl[-1]
        p1, p2 = items[off + i1]["l"], items[off + i2]["l"]
        if abs(p1 - p2) <= tol and i2 - i1 >= 6:
            neck = max(items[off + j]["h"] for j in range(i1, i2 + 1))
            price = items[-1]["c"]
            if price < neck:
                out.append(_result("double_bottom", "کف دوقلو", "Classic Pattern", "long", "active", 68,
                                   f"دو کف هم‌سطح ~{p1:.6g} و شکست نک‌لاین {neck:.6g} — هدف به اندازه ارتفاع الگو.",
                                   entry=neck, stop=min(p1, p2) - 0.5 * atr, target=neck + (neck - min(p1, p2))))
            elif len(items) - (off + i2) <= 15:
                out.append(_result("double_bottom", "کف دوقلو", "Classic Pattern", "long", "forming", 45,
                                   f"کف دوقلو در ~{p1:.6g} شکل گرفته — منتظر شکست نک‌لاین {neck:.6g}."))
    # Double top
    if len(sh) >= 2:
        i1, i2 = sh[-2], sh[-1]
        p1, p2 = items[off + i1]["h"], items[off + i2]["h"]
        if abs(p1 - p2) <= tol and i2 - i1 >= 6:
            neck = min(items[off + j]["l"] for j in range(i1, i2 + 1))
            price = items[-1]["c"]
            if price < neck:
                out.append(_result("double_top", "سقف دوقلو", "Classic Pattern", "short", "active", 68,
                                   f"دو سقف هم‌سطح ~{p1:.6g} و شکست نک‌لاین {neck:.6g} — هدف به اندازه ارتفاع الگو.",
                                   entry=neck, stop=max(p1, p2) + 0.5 * atr, target=neck - (max(p1, p2) - neck)))
            elif len(items) - (off + i2) <= 15:
                out.append(_result("double_top", "سقف دوقلو", "Classic Pattern", "short", "forming", 45,
                                   f"سقف دوقلو در ~{p1:.6g} شکل گرفته — منتظر شکست نک‌لاین {neck:.6g}."))
    return out


def _head_shoulders(items: list[dict], atr: float) -> list[dict]:
    win = items[-90:] if len(items) >= 90 else items
    off = len(items) - len(win)
    sh, sl = _swings(win, k=3)
    out = []
    if len(sh) >= 3:
        s1, s2, s3 = sh[-3], sh[-2], sh[-1]
        h1, h2, h3 = win[s1]["h"], win[s2]["h"], win[s3]["h"]
        tol = 0.4 * atr
        if h2 > h1 + tol and h2 > h3 + tol and abs(h1 - h3) <= 0.8 * atr and s3 - s1 >= 12:
            lows_between = [win[j]["l"] for j in range(s1, s3 + 1)]
            t1 = min(lows_between[: max(len(lows_between) // 2, 1)])
            t2 = min(lows_between[max(len(lows_between) // 2, 1):])
            neck = (t1 + t2) / 2
            if items[-1]["c"] < neck:
                out.append(_result("head_shoulders", "سر و شانه", "Classic Pattern", "short", "active", 72,
                                   f"سر و شانه کامل با سر {h2:.6g} و شکست نک‌لاین ~{neck:.6g}.",
                                   entry=neck, stop=h2 + 0.5 * atr, target=neck - (h2 - neck)))
            elif len(items) - (off + s3) <= 12:
                out.append(_result("head_shoulders", "سر و شانه", "Classic Pattern", "short", "forming", 50,
                                   f"سر و شانه در حال شکل‌گیری (سر {h2:.6g}) — منتظر شکست نک‌لاین ~{neck:.6g}."))
    if len(sl) >= 3:
        s1, s2, s3 = sl[-3], sl[-2], sl[-1]
        l1, l2, l3 = win[s1]["l"], win[s2]["l"], win[s3]["l"]
        tol = 0.4 * atr
        if l2 < l1 - tol and l2 < l3 - tol and abs(l1 - l3) <= 0.8 * atr and s3 - s1 >= 12:
            highs_between = [win[j]["h"] for j in range(s1, s3 + 1)]
            t1 = max(highs_between[: max(len(highs_between) // 2, 1)])
            t2 = max(highs_between[max(len(highs_between) // 2, 1):])
            neck = (t1 + t2) / 2
            if items[-1]["c"] > neck:
                out.append(_result("inverse_hs", "سر و شانه معکوس", "Classic Pattern", "long", "active", 72,
                                   f"سر و شانه معکوس با سر {l2:.6g} و شکست نک‌لاین ~{neck:.6g}.",
                                   entry=neck, stop=l2 - 0.5 * atr, target=neck + (neck - l2)))
            elif len(items) - (off + s3) <= 12:
                out.append(_result("inverse_hs", "سر و شانه معکوس", "Classic Pattern", "long", "forming", 50,
                                   f"سر و شانه معکوس در حال شکل‌گیری (سر {l2:.6g}) — منتظر شکست نک‌لاین ~{neck:.6g}."))
    return out


def _wedge(items: list[dict], atr: float) -> list[dict]:
    win = items[-60:] if len(items) >= 60 else items
    if len(win) < 30:
        return []
    sh, sl = _swings(win, k=2)
    if len(sh) < 3 or len(sl) < 3:
        return []
    def slope(idx: list[int], key: str) -> float:
        pts = [(i, win[i][key]) for i in idx[-3:]]
        n = len(pts)
        mx = sum(p[0] for p in pts) / n
        my = sum(p[1] for p in pts) / n
        den = sum((p[0] - mx) ** 2 for p in pts)
        return sum((p[0] - mx) * (p[1] - my) for p in pts) / den if den else 0.0
    hs, ls = slope(sh, "h"), slope(sl, "l")
    last_h, last_l = win[sh[-1]]["h"], win[sl[-1]]["l"]
    conv = (last_h - last_l) < 3.0 * atr
    out = []
    if hs > 0 and ls > 0 and ls > hs and conv and len(items) - sh[-1] < 20:
        out.append(_result("rising_wedge", "کنج صعودی (Rising Wedge)", "Classic Pattern", "short", "forming", 55,
                           "کنج صعودی همگرا — الگوی بازگشتی نزولی؛ منتظر شکست لبه پایین."))
    if hs < 0 and ls < 0 and abs(hs) > abs(ls) and conv and len(items) - sl[-1] < 20:
        out.append(_result("falling_wedge", "کنج نزولی (Falling Wedge)", "Classic Pattern", "long", "forming", 55,
                           "کنج نزولی همگرا — الگوی بازگشتی صعودی؛ منتظر شکست لبه بالا."))
    return out


def _flag(items: list[dict], atr: float) -> list[dict]:
    n = len(items)
    if n < 40:
        return []
    # impulse: max |move| over any 10-bar window in last 30 bars
    best = None
    for start in range(max(0, n - 30), n - 10):
        move = items[start + 10]["c"] - items[start]["c"]
        if best is None or abs(move) > abs(best[1]):
            best = (start, move)
    if best is None or abs(best[1]) < 3 * atr:
        return []
    start, move = best
    consol = items[start + 10:]
    if len(consol) < 5:
        return []
    hi = max(it["h"] for it in consol)
    lo = min(it["l"] for it in consol)
    if (hi - lo) > 0.5 * abs(move):
        return []
    direction = "long" if move > 0 else "short"
    drift = consol[-1]["c"] - consol[0]["c"]
    counter = (drift < 0) if direction == "long" else (drift > 0)
    status = "forming"
    q = 52
    if counter:
        q += 8
    return [_result("flag_pennant", "پرچم/پنانگ ادامه‌دهنده", "Continuation", direction, status, q,
                    f"ایمپالس {abs(move) / atr:.1f}×ATR سپس فشردگی خلاف‌جهت ({lo:.6g}–{hi:.6g}) — پرچم؛ منتظر شکست در جهت ایمپالس.",
                    entry=hi if direction == "long" else lo,
                    stop=(hi + lo) / 2,
                    target=(hi if direction == "long" else lo) + (abs(move) if direction == "long" else -abs(move)) * 0.6)]


def _ema_pullback(items: list[dict], atr: float) -> list[dict]:
    closes = [it["c"] for it in items]
    if len(closes) < 60:
        return []
    e9 = _ema_series(closes, 9)
    e21 = _ema_series(closes, 21)
    if len(e9) < 8 or len(e21) < 8:
        return []
    d = len(e9) - len(e21)
    e9a = e9[d:]
    trend_up = e9a[-1] > e21[-1] and e21[-1] > e21[-6]
    trend_dn = e9a[-1] < e21[-1] and e21[-1] < e21[-6]
    zone = 0.4 * atr
    for it in items[-4:]:
        if trend_up and it["l"] <= e9a[-1] + zone and it["l"] >= e21[-1] - zone and it["c"] > it["o"] and it["c"] > e9a[-1]:
            return [_result("ema_pullback", "پولبک EMA 9/21", "Trend Following", "long", "active", 64,
                            "پولبک به ناحیه EMA9/21 در روند صعودی با کندل رد (بازگشت بالای EMA9).",
                            entry=it["c"], stop=it["l"] - 0.6 * atr, target=it["c"] + 2 * atr)]
        if trend_dn and it["h"] >= e9a[-1] - zone and it["h"] <= e21[-1] + zone and it["c"] < it["o"] and it["c"] < e9a[-1]:
            return [_result("ema_pullback", "پولبک EMA 9/21", "Trend Following", "short", "active", 64,
                            "پولبک به ناحیه EMA9/21 در روند نزولی با کندل رد (بازگشت زیر EMA9).",
                            entry=it["c"], stop=it["h"] + 0.6 * atr, target=it["c"] - 2 * atr)]
    return []


def _cross_50_200(items: list[dict]) -> list[dict]:
    closes = [it["c"] for it in items]
    if len(closes) < 210:
        return []
    now50, now200 = _sma(closes, 50), _sma(closes, 200)
    prev50, prev200 = _sma(closes[:-10], 50), _sma(closes[:-10], 200)
    if None in (now50, now200, prev50, prev200):
        return []
    if prev50 <= prev200 and now50 > now200:
        return [_result("golden_cross", "گلدن کراس 50/200", "Trend Following", "long", "active", 66,
                        "تقاطع طلایی: SMA50 بالای SMA200 در ۱۰ کندل اخیر.")]
    if prev50 >= prev200 and now50 < now200:
        return [_result("death_cross", "دث کراس 50/200", "Trend Following", "short", "active", 66,
                        "تقاطع مرگ: SMA50 زیر SMA200 در ۱۰ کندل اخیر.")]
    return []


def _squeeze_breakout(items: list[dict]) -> list[dict]:
    from app.services.indicator_pack_v2 import ttm_squeeze
    closes = [it["c"] for it in items]
    highs = [it["h"] for it in items]
    lows = [it["l"] for it in items]
    if len(closes) < 40:
        return []
    sq = ttm_squeeze(highs, lows, closes)
    if sq.get("squeeze_fired") and sq.get("momentum") is not None:
        d = "long" if sq["momentum"] > 0 else "short"
        return [_result("squeeze_breakout", "انفجار فشردگی TTM", "Momentum", d, "active", 67,
                        f"اسکوییز آزاد شد با مومنتوم {sq['momentum']} — جهت {d}.")]
    if sq.get("squeeze_on"):
        return [_result("squeeze_breakout", "فشردگی TTM (در انتظار)", "Momentum", "none", "forming", 42,
                        "باندهای بولینگر داخل کلتنر — فشردگی فعال؛ حرکت انفجاری در راه است.")]
    return []


def _vwap_strategies(items: list[dict], atr: float) -> list[dict]:
    from app.services.indicator_pack_v2 import vwap_bands
    vw = vwap_bands(items)
    if not vw.get("vwap") or not vw.get("sd"):
        return []
    vwap, sd = vw["vwap"], vw["sd"]
    z = (items[-1]["c"] - vwap) / sd if sd else 0
    last = items[-1]
    out = []
    if z >= 2.2 and last["c"] < last["o"] and last["c"] < items[-2]["c"]:
        out.append(_result("vwap_reversion", "بازگشت به میانگین VWAP", "Mean Reversion", "short", "active", 63,
                           f"قیمت {z:.1f}σ بالای VWAP با کندل برگشتی — کشسانی به سمت {vwap:.6g}.",
                           entry=last["c"], stop=last["h"] + 0.4 * atr, target=vwap))
    if z <= -2.2 and last["c"] > last["o"] and last["c"] > items[-2]["c"]:
        out.append(_result("vwap_reversion", "بازگشت به میانگین VWAP", "Mean Reversion", "long", "active", 63,
                           f"قیمت {abs(z):.1f}σ زیر VWAP با کندل برگشتی — کشسانی به سمت {vwap:.6g}.",
                           entry=last["c"], stop=last["l"] - 0.4 * atr, target=vwap))
    # VWAP bounce: trend day, price retests vwap and holds
    if abs(z) <= 0.5 and len(items) >= 30:
        day_move = items[-1]["c"] - items[max(0, len(items) - 30)]["c"]
        touched = any(abs((it["l"] + it["h"]) / 2 - vwap) < 0.35 * sd for it in items[-5:])
        if touched and day_move > 1.2 * atr and last["c"] > vwap:
            out.append(_result("vwap_bounce", "بازگشت از VWAP (روند روز)", "Trend Following", "long", "active", 65,
                               f"لمس VWAP {vwap:.6g} و حفظ آن در روز صعودی — ادامه روند محتمل.",
                               entry=last["c"], stop=vwap - 0.6 * sd, target=last["c"] + 2 * atr))
        if touched and day_move < -1.2 * atr and last["c"] < vwap:
            out.append(_result("vwap_bounce", "رد شدن از VWAP (روند روز)", "Trend Following", "short", "active", 65,
                               f"لمس VWAP {vwap:.6g} و ناتوانی در عبور در روز نزولی — ادامه روند محتمل.",
                               entry=last["c"], stop=vwap + 0.6 * sd, target=last["c"] - 2 * atr))
    return out


def _judas_swing(items: list[dict], timeframe: str) -> list[dict]:
    """London open false move against the Asian range (07:00–10:00 UTC window)."""
    tf_min = {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30, "60m": 60, "1h": 60}.get(timeframe, 15)
    if tf_min > 60 or len(items) < 60:
        return []
    now = items[-1]["t"]
    hour_now = (now % 86400) / 3600
    if not (7.0 <= hour_now <= 11.0):
        return []
    day = int(now // 86400)
    asia = [it for it in items if int(it["t"] // 86400) == day and 0 <= (it["t"] % 86400) / 3600 < 7]
    london = [it for it in items if int(it["t"] // 86400) == day and 7 <= (it["t"] % 86400) / 3600 <= hour_now]
    if len(asia) < 20 or len(london) < 2:
        return []
    ahi = max(it["h"] for it in asia)
    alo = min(it["l"] for it in asia)
    lhi = max(it["h"] for it in london)
    llo = min(it["l"] for it in london)
    last = items[-1]
    if llo < alo and last["c"] > alo:
        return [_result("judas_swing", "جوداس سوئینگ (تله لندن)", "Session", "long", "active", 70,
                        f"حرکت جعلی زیر رنج آسیا {alo:.6g} در بازگشایی لندن و بازگشت به داخل — تله فروشندگان.",
                        entry=last["c"], stop=llo - 0.2 * (ahi - alo), target=ahi)]
    if lhi > ahi and last["c"] < ahi:
        return [_result("judas_swing", "جوداس سوئینگ (تله لندن)", "Session", "short", "active", 70,
                        f"حرکت جعلی بالای رنج آسیا {ahi:.6g} در بازگشایی لندن و بازگشت به داخل — تله خریداران.",
                        entry=last["c"], stop=lhi + 0.2 * (ahi - alo), target=alo)]
    return []


def _power_of_3(items: list[dict], timeframe: str) -> list[dict]:
    """AMD: Accumulation → Manipulation → Distribution on today's daily bar."""
    if timeframe in ("4h", "1d"):
        return []
    day = int(items[-1]["t"] // 86400)
    today = [it for it in items if int(it["t"] // 86400) == day]
    if len(today) < 8:
        return []
    o = today[0]["o"]
    hi = max(it["h"] for it in today)
    lo = min(it["l"] for it in today)
    c = today[-1]["c"]
    hour_now = (today[-1]["t"] % 86400) / 3600
    body = abs(c - o)
    rng = max(hi - lo, 1e-12)
    manip_down = (o - lo) / rng
    manip_up = (hi - o) / rng
    phase = "accumulation" if hour_now < 7 else "manipulation" if hour_now < 13 else "distribution"
    direction = "none"
    q = 40
    reason = f"AMD امروز: باز={o:.6g} بالا={hi:.6g} پایین={lo:.6g} فعلی={c:.6g} — فاز {phase}."
    if phase != "accumulation" and manip_down > 0.45 and c > o and body / rng > 0.2:
        direction, q = "long", 60
        reason = f"مانیپولاسیون نزولی (ویک {manip_down * 100:.0f}٪ زیر باز) و شروع توزیع صعودی — Power of 3 صعودی."
    elif phase != "accumulation" and manip_up > 0.45 and c < o and body / rng > 0.2:
        direction, q = "short", 60
        reason = f"مانیپولاسیون صعودی (ویک {manip_up * 100:.0f}٪ بالای باز) و شروع توزیع نزولی — Power of 3 نزولی."
    status = "active" if direction != "none" else "forming"
    return [_result("power_of_3", "Power of 3 (AMD)", "Session", direction, status, q, reason,
                    extra={"phase": phase, "day_open": _r(o), "day_high": _r(hi), "day_low": _r(lo)})]


def _divergences(items: list[dict]) -> list[dict]:
    closes = [it["c"] for it in items]
    if len(closes) < 60:
        return []
    rsi = _rsi_series(closes)
    if len(rsi) < 30:
        return []
    win = items[-40:]
    _, sl = _swings(win, k=3)
    sh, _ = _swings(win, k=3)
    off = len(items) - 40
    rsi_off = len(rsi) - len(items)  # rsi[i+rsi_off] aligns with items[i]
    out = []
    if len(sl) >= 2:
        i1, i2 = off + sl[-2], off + sl[-1]
        if i1 >= -rsi_off and win[sl[-1]]["l"] < win[sl[-2]]["l"] and rsi[i2 + rsi_off] > rsi[i1 + rsi_off]:
            out.append(_result("rsi_div", "واگرایی صعودی RSI", "Divergence", "long", "active", 64,
                               f"کف پایین‌تر قیمت ولی RSI بالاتر ({rsi[i1 + rsi_off]:.0f}→{rsi[i2 + rsi_off]:.0f}) — تضعیف فروشندگان."))
    if len(sh) >= 2:
        i1, i2 = off + sh[-2], off + sh[-1]
        if i1 >= -rsi_off and win[sh[-1]]["h"] > win[sh[-2]]["h"] and rsi[i2 + rsi_off] < rsi[i1 + rsi_off]:
            out.append(_result("rsi_div", "واگرایی نزولی RSI", "Divergence", "short", "active", 64,
                               f"سقف بالاتر قیمت ولی RSI پایین‌تر ({rsi[i1 + rsi_off]:.0f}→{rsi[i2 + rsi_off]:.0f}) — تضعیف خریداران."))
    macd, sig, hist = _macd(closes)
    if len(hist) >= 3:
        if hist[-2] < 0 <= hist[-1]:
            out.append(_result("macd_flip", "چرخش هیستوگرام MACD", "Momentum", "long", "active", 55,
                               "هیستوگرام MACD از منفی به مثبت چرخید — مومنتوم در حال تغییر به صعودی."))
        elif hist[-2] > 0 >= hist[-1]:
            out.append(_result("macd_flip", "چرخش هیستوگرام MACD", "Momentum", "short", "active", 55,
                               "هیستوگرام MACD از مثبت به منفی چرخید — مومنتوم در حال تغییر به نزولی."))
    return out


def _supertrend_flip(items: list[dict]) -> list[dict]:
    from app.services.advanced_indicators import supertrend
    highs = [it["h"] for it in items]
    lows = [it["l"] for it in items]
    closes = [it["c"] for it in items]
    if len(closes) < 30:
        return []
    now = supertrend(highs, lows, closes)
    prev = supertrend(highs[:-1], lows[:-1], closes[:-1])
    d_now = str(now.get("direction") or "").lower()
    d_prev = str(prev.get("direction") or "").lower()
    if d_now in ("up", "down") and d_now != d_prev:
        d = "long" if d_now == "up" else "short"
        return [_result("supertrend_flip", "چرخش سوپرتِرِند", "Trend Following", d, "active", 58,
                        f"سوپرتِرِند روی کندل آخر چرخید ({d_prev}→{d_now}) — سیگنال کلاسیک دنبال‌کردن روند.",
                        stop=now.get("level"), extra={"supertrend_level": now.get("level")})]
    return []


def _ichimoku_system(items: list[dict]) -> list[dict]:
    from app.services.advanced_indicators import ichimoku
    highs = [it["h"] for it in items]
    lows = [it["l"] for it in items]
    closes = [it["c"] for it in items]
    if len(closes) < 60:
        return []
    ich = ichimoku(highs, lows, closes)
    score = 0
    parts = []
    price = closes[-1]
    tenkan = ich.get("tenkan") or 0
    kijun = ich.get("kijun") or 0
    span_a = ich.get("span_a") or 0
    span_b = ich.get("span_b") or 0
    cloud_top, cloud_bot = max(span_a, span_b), min(span_a, span_b)
    if price > cloud_top:
        score += 1
        parts.append("قیمت بالای کومو")
    elif price < cloud_bot:
        score -= 1
        parts.append("قیمت زیر کومو")
    if tenkan > kijun:
        score += 1
        parts.append("TK صعودی")
    elif tenkan < kijun:
        score -= 1
        parts.append("TK نزولی")
    if span_a > span_b:
        score += 1
        parts.append("کوموی آینده صعودی")
    elif span_b > span_a:
        score -= 1
        parts.append("کوموی آینده نزولی")
    if abs(score) >= 3:
        d = "long" if score > 0 else "short"
        return [_result("ichimoku_system", "سیستم کامل ایچیموکو", "Trend Following", d, "active", 55 + abs(score) * 5,
                        "؛ ".join(parts) + " — هم‌راستایی کامل سه‌گانه ایچیموکو.",
                        entry=price, stop=kijun, target=None)]
    return []


def _sar_flip(items: list[dict]) -> list[dict]:
    from app.services.smc_engine import _psar
    highs = [it["h"] for it in items]
    lows = [it["l"] for it in items]
    closes = [it["c"] for it in items]
    if len(closes) < 30:
        return []
    val, up = _psar(highs, lows, closes)
    prev_val, prev_up = _psar(highs[:-1], lows[:-1], closes[:-1])
    if up != prev_up:
        d = "long" if up else "short"
        return [_result("sar_flip", "چرخش Parabolic SAR", "Trend Following", d, "active", 52,
                        f"SAR چرخید — اکنون {'زیر' if up else 'بالای'} قیمت در {val:.6g}.", stop=val)]
    return []


def _engulfing_at_level(items: list[dict], atr: float) -> list[dict]:
    if len(items) < 25:
        return []
    last, prev = items[-1], items[-2]
    body_l = abs(last["c"] - last["o"])
    body_p = abs(prev["c"] - prev["o"])
    up20 = max(it["h"] for it in items[-21:-1])
    dn20 = min(it["l"] for it in items[-21:-1])
    zone = 0.5 * atr
    bullish = last["c"] > last["o"] and prev["c"] < prev["o"] and last["c"] >= prev["o"] and last["o"] <= prev["c"] and body_l > body_p
    bearish = last["c"] < last["o"] and prev["c"] > prev["o"] and last["o"] >= prev["c"] and last["c"] <= prev["o"] and body_l > body_p
    if bullish and (prev["l"] <= dn20 + zone or prev["l"] <= last["c"] - 2 * atr):
        return [_result("engulfing_level", "انگالفینگ صعودی در سطح", "Price Action", "long", "active", 62,
                        f"انگالفینگ صعودی قوی نزدیک حمایت/کف ۲۰ کندلی {dn20:.6g}.",
                        entry=last["c"], stop=last["l"] - 0.3 * atr, target=last["c"] + 2 * atr)]
    if bearish and (prev["h"] >= up20 - zone or prev["h"] >= last["c"] + 2 * atr):
        return [_result("engulfing_level", "انگالفینگ نزولی در سطح", "Price Action", "short", "active", 62,
                        f"انگالفینگ نزولی قوی نزدیک مقاومت/سقف ۲۰ کندلی {up20:.6g}.",
                        entry=last["c"], stop=last["h"] + 0.3 * atr, target=last["c"] - 2 * atr)]
    return []


# ---------------------------------------------------------------- scan


def scan_all(items: list[dict], timeframe: str = "15m") -> dict:
    """Run every detector; strict data requirements, no fabricated signals."""
    if len(items) < 40:
        return {"available": False, "reason": "insufficient_data", "active": [], "forming": [], "counts": {}}
    atr = _atr(items)
    tf = str(timeframe or "15m").replace("min", "m").lower()
    results: list[dict] = []
    for fn in (
        lambda: _wyckoff(items, atr),
        lambda: _turtle(items),
        lambda: _orb(items, tf),
        lambda: _inside_bar(items, atr),
        lambda: _double_tb(items, atr),
        lambda: _head_shoulders(items, atr),
        lambda: _wedge(items, atr),
        lambda: _flag(items, atr),
        lambda: _ema_pullback(items, atr),
        lambda: _cross_50_200(items),
        lambda: _squeeze_breakout(items),
        lambda: _vwap_strategies(items, atr),
        lambda: _judas_swing(items, tf),
        lambda: _power_of_3(items, tf),
        lambda: _divergences(items),
        lambda: _supertrend_flip(items),
        lambda: _ichimoku_system(items),
        lambda: _sar_flip(items),
        lambda: _engulfing_at_level(items, atr),
    ):
        try:
            results.extend(fn() or [])
        except Exception:
            continue
    # dedupe by (id, direction) keeping highest quality
    best: dict[tuple, dict] = {}
    for r in results:
        key = (r["id"], r["direction"])
        if key not in best or r["quality"] > best[key]["quality"]:
            best[key] = r
    results = sorted(best.values(), key=lambda r: (r["status"] != "active", -r["quality"]))
    active = [r for r in results if r["status"] == "active"]
    forming = [r for r in results if r["status"] == "forming"]
    longs = sum(1 for r in active if r["direction"] == "long")
    shorts = sum(1 for r in active if r["direction"] == "short")
    if longs and not shorts:
        net = "long"
    elif shorts and not longs:
        net = "short"
    elif longs and shorts:
        net = "conflict"
    else:
        net = "none"
    total = max(longs + shorts, 1)
    return {
        "available": True,
        "timeframe": tf,
        "active": active,
        "forming": forming[:6],
        "counts": {"active": len(active), "forming": len(forming), "long": longs, "short": shorts},
        "net_direction": net,
        "agreement_pct": int(max(longs, shorts) / total * 100) if (longs or shorts) else 0,
        "top": [
            {"id": r["id"], "name_fa": r["name_fa"], "direction": r["direction"], "quality": r["quality"]}
            for r in active[:5]
        ],
    }


def build_context_text(scan: dict) -> str:
    if not scan.get("available"):
        return ""
    c = scan.get("counts") or {}
    lines = [f"استراتژی‌های کلاسیک (پک v2): {c.get('active', 0)} سیگنال فعال ({c.get('long', 0)} خرید / {c.get('short', 0)} فروش)، {c.get('forming', 0)} در حال شکل‌گیری — جهت خالص: {scan.get('net_direction')}"]
    for r in scan.get("active", [])[:8]:
        lines.append(f"  • {r['name_fa']} [{r['direction']}] کیفیت={r['quality']} — {r['reason_fa']}")
    for r in scan.get("forming", [])[:3]:
        lines.append(f"  ◌ (forming) {r['name_fa']} — {r['reason_fa']}")
    return "\n".join(lines)
