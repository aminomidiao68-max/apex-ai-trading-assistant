"""Strategy Pack v2 — deterministic classic/professional strategy detectors.

34 validated strategies scanned on real candles (no repainting, no look-ahead):
Wyckoff (Spring / Upthrust / SOS), Turtle-Donchian breakout, ORB, Inside-Bar,
Double Top/Bottom, Head & Shoulders (+inverse), Rising/Falling Wedge,
Flag/Pennant, EMA 9/21 pullback, Golden/Death cross, TTM Squeeze breakout,
VWAP reversion & bounce, Judas Swing, Power-of-3 (AMD), RSI/MACD divergence
reversal, Supertrend flip, Ichimoku system, SAR flip, Engulfing-at-level,
plus the v3.16 professional batch: liquidity sweep (stop-hunt), FVG tap,
order-block retest, EQH/EQL raid, Connors RSI(2) reversion, NR7/NR4 breakout,
Hikkake trap, ascending/descending triangle measured-move, three-drive
divergence, Asian-range killzone sweep, floor-pivot rejection, ICT Silver Bullet.

Every detector returns status=active|forming|none with a strict quality score.

v3.17: measured-edge calibration — every detector's plan was walk-forward
replayed on real OKX candles with the in-app honest fill engine (limit-touch
entry, no same-bar TP, stop-first, taker fees). Quality scores now carry the
measured prior; detectors with a proven negative edge after fees are demoted
to watch-only. Raw detector behavior stays available via calibrated=False.
"""

from __future__ import annotations

import math
from typing import Any

GATE_VOTE_THRESHOLD = 15
GATE_EMA_SPAN = 50
GATE_PERF_MIN_TRADES = 3

# ------------------------------------------- measured-edge calibration (v3.17)
# Provenance: walk-forward replay on REAL OKX candles — 6 symbols
# (BTC/ETH/SOL/XRP/DOGE/BNB-USDT) × 3 timeframes (15m/1h/4h) × 1800 bars,
# run 2026-09-16, using the SAME engine as the in-app backtest
# (strategy_backtest_service._simulate_plan): entry fills only when a later
# bar touches the plan price, entry bar checks stop only, ambiguous bars
# assume stop first, 96-bar horizon, taker fee 0.05%/side. An earlier
# optimistic-fill pass (instant fill at plan price) was discarded after an
# honesty audit exposed massive entry bias (e.g. ORB +1.73R → -0.55R honest).
# Table holds raw measured stats only; the adjustment RULES below were
# pre-registered before reading the results. Recalibrate periodically.
EDGE_CALIBRATION_SOURCE = (
    "OKX walk-forward 2026-09-16 — 6 symbols × 15m/1h/4h × 1800 real candles, "
    "in-app honest engine (limit-touch entry, no same-bar TP, stop-first, fee 0.05%/side)"
)
EDGE_CALIBRATION_MIN_N = 25
_EDGE_CALIBRATION: dict[str, dict] = {
    "triangle_break": {"n": 28, "wr": 0.6429, "avgR": 0.1316, "pf": 1.34},
    "eqh_eql_raid": {"n": 83, "wr": 0.3735, "avgR": 0.0782, "pf": 1.107},
    "inverse_hs": {"n": 56, "wr": 0.5714, "avgR": 0.0517, "pf": 1.134},
    "wyckoff_sos": {"n": 120, "wr": 0.375, "avgR": 0.0055, "pf": 1.008},
    "liquidity_sweep": {"n": 232, "wr": 0.2931, "avgR": -0.0033, "pf": 0.996},
    "hikkake": {"n": 404, "wr": 0.3837, "avgR": -0.019, "pf": 0.972},
    "three_drives": {"n": 440, "wr": 0.3909, "avgR": -0.0374, "pf": 0.94},
    "head_shoulders": {"n": 52, "wr": 0.5, "avgR": -0.0494, "pf": 0.883},
    "engulfing_level": {"n": 347, "wr": 0.4294, "avgR": -0.055, "pf": 0.919},
    "turtle_breakout": {"n": 313, "wr": 0.3898, "avgR": -0.0797, "pf": 0.873},
    "asian_sweep": {"n": 163, "wr": 0.3926, "avgR": -0.1059, "pf": 0.859},
    "pivot_reject": {"n": 192, "wr": 0.375, "avgR": -0.1131, "pf": 0.856},
    "fvg_tap": {"n": 843, "wr": 0.3203, "avgR": -0.145, "pf": 0.814},
    "double_top": {"n": 87, "wr": 0.5057, "avgR": -0.1453, "pf": 0.712},
    "rsi2_reversion": {"n": 401, "wr": 0.5636, "avgR": -0.1697, "pf": 0.655},
    "silver_bullet": {"n": 46, "wr": 0.3913, "avgR": -0.181, "pf": 0.771},
    "ob_retest": {"n": 121, "wr": 0.314, "avgR": -0.211, "pf": 0.716},
    "ichimoku_system": {"n": 1201, "wr": 0.3164, "avgR": -0.2452, "pf": 0.696},
    "wyckoff_upthrust": {"n": 244, "wr": 0.209, "avgR": -0.2873, "pf": 0.679},
    "vwap_bounce": {"n": 422, "wr": 0.3009, "avgR": -0.2933, "pf": 0.696},
    "double_bottom": {"n": 75, "wr": 0.4267, "avgR": -0.3075, "pf": 0.488},
    "ema_pullback": {"n": 1808, "wr": 0.3507, "avgR": -0.3094, "pf": 0.583},
    "inside_bar": {"n": 335, "wr": 0.3104, "avgR": -0.3558, "pf": 0.597},
    "vwap_reversion": {"n": 42, "wr": 0.2143, "avgR": -0.4705, "pf": 0.484},
    "wyckoff_spring": {"n": 220, "wr": 0.1818, "avgR": -0.5106, "pf": 0.43},
    "orb": {"n": 264, "wr": 0.3068, "avgR": -0.5647, "pf": 0.454},
    "nr7_breakout": {"n": 512, "wr": 0.3457, "avgR": -0.608, "pf": 0.371},
    "judas_swing": {"n": 78, "wr": 0.2436, "avgR": -0.6232, "pf": 0.312},
}


def _calib_adj(n: int, avg_r: float, pf: float | None) -> int:
    """Pre-registered quality adjustment from measured edge. Deterministic."""
    if n < EDGE_CALIBRATION_MIN_N:
        return 0
    pfv = 99.0 if pf is None else float(pf)
    if avg_r >= 0.30 or (avg_r >= 0.15 and pfv >= 1.15):
        return 6
    if avg_r >= 0.08 and pfv >= 1.05:
        return 3
    if avg_r <= -0.10 or pfv <= 0.85:
        return -10
    if avg_r <= -0.04 or pfv <= 0.95:
        return -5
    return 0


def _apply_calibration(results: list[dict]) -> int:
    """Attach measured edge per detector, adjust quality, demote proven losers.

    perf_ok semantics in live scans: True = measured positive edge on real data,
    False = measured negative edge, None = insufficient sample (n<25). The
    backtest service fills its own perf_ok from per-run replay; this is the
    large-sample prior for live signals.
    """
    adjusted = 0
    for r in results:
        cal = _EDGE_CALIBRATION.get(str(r.get("id")))
        if not cal or int(cal.get("n") or 0) < EDGE_CALIBRATION_MIN_N:
            r["measured_edge"] = None
            r["perf_ok"] = None
            continue
        n = int(cal["n"])
        avg_r = float(cal["avgR"])
        pf = cal.get("pf")
        adj = _calib_adj(n, avg_r, pf)
        r["measured_edge"] = {"n": n, "avgR": avg_r, "wr": cal.get("wr"), "pf": pf, "adj": adj}
        r["perf_ok"] = True if adj > 0 else (False if adj < 0 else None)
        if adj:
            r["quality"] = int(max(0, min(100, int(r.get("quality") or 0) + adj)))
            adjusted += 1
        # v3.31: ANY measured non-positive edge (pf<=1 or avgR<=0) is watch-only.
        # Previously only the worst bucket (adj<=-10) was demoted, so mildly
        # losing detectors could still emit live "active" entries.
        negative_edge = (pf is not None and float(pf) <= 1.0) or avg_r <= 0
        if negative_edge:
            r["watch_only"] = True
            r["perf_ok"] = False
            if r.get("status") == "active":
                r["status"] = "forming"
                r["calibration_demoted"] = True
            r["reason_fa"] = (str(r.get("reason_fa") or "") +
                              " — ⚠ edge اندازه‌گیری‌شده روی داده واقعی (پس از کارمزد) منفی است: فقط رصد، نه ورود")
    return adjusted

# ---------------------------------------------------------------- helpers


def _ema_last(values: list[float], span: int) -> float | None:
    """SMA-seeded EMA, last value only. Deterministic, no deps."""
    if len(values) < span:
        return None
    alpha = 2.0 / (span + 1)
    ema = sum(values[:span]) / span
    for v in values[span:]:
        ema = alpha * v + (1 - alpha) * ema
    return ema


def _signal_gates(items: list[dict], results: list[dict]) -> dict:
    """Tag each result with walk-forward-safe alignment gates (context bar = items[-1]).

    trend_ok : close vs EMA50 agrees with the signal direction
    votes_ok : indicator_pack_v2 net vote beyond +/-GATE_VOTE_THRESHOLD agrees
    perf_ok  : measured-edge prior from v3.17 calibration (set earlier by
               _apply_calibration; kept as-is here — None when sample is thin).
               The backtest service overwrites it with per-run replay results.
    gate_ok  : trend_ok AND votes_ok (both must be known)
    """
    closes = [float(b.get("c") or 0.0) for b in items]
    ema = _ema_last(closes, GATE_EMA_SPAN)
    last = closes[-1] if closes else None
    net_votes: int | None = None
    try:
        from app.services import indicator_pack_v2
        net_votes = int(indicator_pack_v2.summarize(indicator_pack_v2.compute_all(items)).get("net") or 0)
    except Exception:
        net_votes = None
    counts = {"trend_ok": 0, "votes_ok": 0, "gate_ok": 0, "tagged": 0}
    for r in results:
        d = str(r.get("direction"))
        if d not in ("long", "short"):
            r["trend_ok"] = r["votes_ok"] = r["gate_ok"] = None
            r.setdefault("perf_ok", None)  # keep calibration prior if set
            continue
        t_ok = None if (ema is None or last is None) else (last > ema if d == "long" else last < ema)
        v_ok = None if net_votes is None else (
            net_votes >= GATE_VOTE_THRESHOLD if d == "long" else net_votes <= -GATE_VOTE_THRESHOLD
        )
        r["trend_ok"] = t_ok
        r["votes_ok"] = v_ok
        r.setdefault("perf_ok", None)  # keep calibration prior if set
        r["gate_ok"] = None if (t_ok is None or v_ok is None) else bool(t_ok and v_ok)
        counts["tagged"] += 1
        counts["trend_ok"] += 1 if t_ok else 0
        counts["votes_ok"] += 1 if v_ok else 0
        counts["gate_ok"] += 1 if r["gate_ok"] else 0
    return {
        "ema_span": GATE_EMA_SPAN,
        "vote_threshold": GATE_VOTE_THRESHOLD,
        "ema50": round(ema, 8) if ema is not None else None,
        "net_votes": net_votes,
        "counts": counts,
    }


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
            # v3.17 fix: a double bottom is CONFIRMED only on a close ABOVE the
            # neckline (mirror of double_top). The old `price < neck` branch was
            # a sign error — it "bought" unconfirmed patterns inside the dip and
            # measured -0.59R / 22% WR on real data.
            if price > neck:
                out.append(_result("double_bottom", "کف دوقلو", "Classic Pattern", "long", "active", 68,
                                   f"دو کف هم‌سطح ~{p1:.6g} و شکست تأییدی نک‌لاین {neck:.6g} — هدف به اندازه ارتفاع الگو.",
                                   entry=neck, stop=min(p1, p2) - 0.5 * atr, target=neck + (neck - min(p1, p2))))
            elif len(items) - (off + i2) <= 15:
                out.append(_result("double_bottom", "کف دوقلو", "Classic Pattern", "long", "forming", 45,
                                   f"کف دوقلو در ~{p1:.6g} شکل گرفته — منتظر شکست تأییدی نک‌لاین {neck:.6g}."))
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


# ---------------------------------------------------------------- v3.16 batch
# 12 additional professional detectors (liquidity/ICT/SMC/quant/session/levels).
# Same contract as the rest: strict geometry + confirmation, no repainting
# (only closed bars decide active/forming), honest quality scoring, and a real
# entry/stop/target plan or nothing at all.


def _vol_avg(items: list[dict], n: int = 20) -> float:
    vs = [float(it.get("v") or 0.0) for it in items[-n:]]
    return sum(vs) / len(vs) if vs else 0.0


def _hour_utc(ts: float) -> int:
    return int(ts // 3600) % 24


_TF_MIN = {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30, "60m": 60, "1h": 60,
         "2h": 120, "4h": 240, "6h": 360, "12h": 720, "1d": 1440}


def _tf_minutes(timeframe: str) -> int:
    return _TF_MIN.get(str(timeframe or "").replace("min", "m").lower(), 0)


def _bar_pos(bar: dict) -> float:
    """Close position inside the bar range: 1=at high, 0=at low."""
    rng = float(bar["h"]) - float(bar["l"])
    if rng <= 0:
        return 0.5
    return (float(bar["c"]) - float(bar["l"])) / rng


def _confirmed_swings(items: list[dict], k: int = 2) -> tuple[list[int], list[int]]:
    """Swings already confirmed by k later closed bars (no repainting)."""
    hi, lo = _swings(items, k)
    limit = len(items) - 1 - k
    return [i for i in hi if i <= limit], [i for i in lo if i <= limit]


def _fvg_zones(items: list[dict], lookback: int = 40) -> list[dict]:
    """Unmitigated 3-candle fair value gaps, newest last.

    Bullish FVG at (a, b, c): low[c] > high[a] -> zone [high[a], low[c]].
    Mitigated when any later bar trades through the far side of the zone.
    """
    n = len(items)
    out: list[dict] = []
    start = max(1, n - lookback)
    for c in range(start + 1, n):
        a, b = c - 2, c - 1
        ha, la = float(items[a]["h"]), float(items[a]["l"])
        hc, lc = float(items[c]["h"]), float(items[c]["l"])
        disp = float(items[b]["h"]) - float(items[b]["l"])
        if lc > ha:
            zone = {"dir": "bull", "top": lc, "bottom": ha, "c": c, "disp": disp}
        elif hc < la:
            zone = {"dir": "bear", "top": la, "bottom": hc, "c": c, "disp": disp}
        else:
            continue
        mitigated = False
        for j in range(c + 1, n):
            if zone["dir"] == "bull" and float(items[j]["l"]) <= zone["bottom"]:
                mitigated = True
                break
            if zone["dir"] == "bear" and float(items[j]["h"]) >= zone["top"]:
                mitigated = True
                break
        if not mitigated:
            out.append(zone)
    return out


def _liquidity_sweep(items: list[dict], atr: float) -> list[dict]:
    """Stop-hunt / liquidity sweep reversal: wick beyond a confirmed swing pool,
    close back inside, close at the rejecting end of the bar."""
    n = len(items)
    if n < 25 or atr <= 0:
        return []
    hi_idx, lo_idx = _confirmed_swings(items, 2)
    last = items[-1]
    vol_hit = float(last.get("v") or 0) >= 1.3 * _vol_avg(items)
    recent_h = [i for i in hi_idx if n - 1 - i <= 40]
    recent_l = [i for i in lo_idx if n - 1 - i <= 40]
    if not recent_h and not recent_l:
        return []
    out: list[dict] = []
    if recent_h:
        level = max(float(items[i]["h"]) for i in recent_h)
        touches = sum(1 for j in range(max(0, n - 41), n - 1) if float(items[j]["h"]) >= level - 0.05 * atr)
        beyond = float(last["h"]) - level
        if beyond > 0.10 * atr and beyond < 1.5 * atr and float(last["c"]) < level and _bar_pos(last) <= 0.45:
            q = 58 + (6 if vol_hit else 0) + (4 if beyond >= 0.25 * atr else 0) + (6 if touches >= 3 else 0)
            risk = float(last["h"]) + 0.25 * atr - float(last["c"])
            struct = min((float(items[i]["l"]) for i in recent_l), default=None)
            target = float(last["c"]) - 2 * risk
            if struct is not None and struct < float(last["c"]) - 1.2 * risk:
                target = struct
            out.append(_result("liquidity_sweep", "جاروی نقدینگی سقف (Stop-Hunt)", "Liquidity", "short", "active", q,
                               f"ویک تا {beyond / atr:.2f}×ATR بالای استخر نقدینگی {level:.6g} ({touches} برخورد) رفت و زیر سطح با بدنه پایین بسته شد — شکار استاپ‌ها و بازگشت.",
                               entry=last["c"], stop=float(last["h"]) + 0.25 * atr, target=target))
        elif abs(float(last["c"]) - level) <= 0.15 * atr and float(last["h"]) <= level:
            out.append(_result("liquidity_sweep", "استخر نقدینگی سقف", "Liquidity", "none", "forming", 46,
                               f"قیمت {abs(float(last['c']) - level) / atr:.2f}×ATR زیر استخر نقدینگی {level:.6g} ({touches} برخورد) — جاروی بالقوه در کمین."))
    if recent_l:
        level = min(float(items[i]["l"]) for i in recent_l)
        touches = sum(1 for j in range(max(0, n - 41), n - 1) if float(items[j]["l"]) <= level + 0.05 * atr)
        beyond = level - float(last["l"])
        if beyond > 0.10 * atr and beyond < 1.5 * atr and float(last["c"]) > level and _bar_pos(last) >= 0.55:
            q = 58 + (6 if vol_hit else 0) + (4 if beyond >= 0.25 * atr else 0) + (6 if touches >= 3 else 0)
            risk = float(last["c"]) - (float(last["l"]) - 0.25 * atr)
            struct = max((float(items[i]["h"]) for i in recent_h), default=None)
            target = float(last["c"]) + 2 * risk
            if struct is not None and struct > float(last["c"]) + 1.2 * risk:
                target = struct
            out.append(_result("liquidity_sweep", "جاروی نقدینگی کف (Stop-Hunt)", "Liquidity", "long", "active", q,
                               f"ویک تا {beyond / atr:.2f}×ATR زیر استخر نقدینگی {level:.6g} ({touches} برخورد) رفت و بالای سطح با بدنه بالا بسته شد — شکار استاپ‌ها و بازگشت.",
                               entry=last["c"], stop=float(last["l"]) - 0.25 * atr, target=target))
        elif abs(float(last["c"]) - level) <= 0.15 * atr and float(last["l"]) >= level:
            out.append(_result("liquidity_sweep", "استخر نقدینگی کف", "Liquidity", "none", "forming", 46,
                               f"قیمت {abs(float(last['c']) - level) / atr:.2f}×ATR بالای استخر نقدینگی {level:.6g} ({touches} برخورد) — جاروی بالقوه در کمین."))
    return out


def _fvg_tap(items: list[dict], atr: float) -> list[dict]:
    """Tap-and-reject of an unmitigated Fair Value Gap (ICT)."""
    n = len(items)
    if n < 20 or atr <= 0:
        return []
    last = items[-1]
    vol_hit = float(last.get("v") or 0) >= 1.3 * _vol_avg(items)
    out: list[dict] = []
    hi_idx, lo_idx = _confirmed_swings(items, 2)
    for z in _fvg_zones(items, 40)[-4:]:
        fresh = n - 1 - z["c"] <= 20
        strong_disp = z["disp"] >= 1.2 * atr
        tall = (z["top"] - z["bottom"]) >= 0.3 * atr
        q = 56 + (6 if strong_disp else 0) + (4 if tall else 0) + (4 if fresh else 0) + (4 if vol_hit else 0)
        if z["dir"] == "bull":
            tapped = float(last["l"]) <= z["top"] and float(last["l"]) > z["bottom"] - 0.3 * atr
            rejected = float(last["c"]) >= z["top"] and _bar_pos(last) >= 0.55
            if tapped and rejected:
                risk = float(last["c"]) - (z["bottom"] - 0.2 * atr)
                if risk <= 0:
                    continue
                target = float(last["c"]) + 2 * risk
                struct = max((float(items[i]["h"]) for i in hi_idx if n - 1 - i <= 40), default=None)
                if struct is not None and struct >= float(last["c"]) + 1.2 * risk:
                    target = struct
                out.append(_result("fvg_tap", "واکنش به FVG صعودی (ICT)", "ICT", "long", "active", q,
                                   f"قیمت داخل FVG بی‌مصرف [{z['bottom']:.6g}–{z['top']:.6g}] نشست و با بدنه بالا رد شد — جابه‌جایی {z['disp'] / atr:.1f}×ATR.",
                                   entry=last["c"], stop=z["bottom"] - 0.2 * atr, target=target))
            elif float(last["c"]) > z["top"] and float(last["l"]) - z["top"] <= 0.5 * atr:
                out.append(_result("fvg_tap", "FVG صعودی در انتظار لمس", "ICT", "none", "forming", 46,
                                   f"FVG بی‌مصرف [{z['bottom']:.6g}–{z['top']:.6g}] زیر قیمت — {max(float(last['l']) - z['top'], 0) / atr:.2f}×ATR فاصله تا ناحیه."))
        else:
            tapped = float(last["h"]) >= z["bottom"] and float(last["h"]) < z["top"] + 0.3 * atr
            rejected = float(last["c"]) <= z["bottom"] and _bar_pos(last) <= 0.45
            if tapped and rejected:
                risk = (z["top"] + 0.2 * atr) - float(last["c"])
                if risk <= 0:
                    continue
                target = float(last["c"]) - 2 * risk
                struct = min((float(items[i]["l"]) for i in lo_idx if n - 1 - i <= 40), default=None)
                if struct is not None and struct <= float(last["c"]) - 1.2 * risk:
                    target = struct
                out.append(_result("fvg_tap", "واکنش به FVG نزولی (ICT)", "ICT", "short", "active", q,
                                   f"قیمت داخل FVG بی‌مصرف [{z['bottom']:.6g}–{z['top']:.6g}] نشست و با بدنه پایین رد شد — جابه‌جایی {z['disp'] / atr:.1f}×ATR.",
                                   entry=last["c"], stop=z["top"] + 0.2 * atr, target=target))
            elif float(last["c"]) < z["bottom"] and z["bottom"] - float(last["h"]) <= 0.5 * atr:
                out.append(_result("fvg_tap", "FVG نزولی در انتظار لمس", "ICT", "none", "forming", 46,
                                   f"FVG بی‌مصرف [{z['bottom']:.6g}–{z['top']:.6g}] بالای قیمت — {max(z['bottom'] - float(last['h']), 0) / atr:.2f}×ATR فاصله تا ناحیه."))
    return out[:4]


def _ob_retest(items: list[dict], atr: float) -> list[dict]:
    """Order block created by a displacement impulse that broke structure,
    retested and defended."""
    n = len(items)
    if n < 25 or atr <= 0:
        return []
    last = items[-1]
    vol_hit = float(last.get("v") or 0) >= 1.3 * _vol_avg(items)
    out: list[dict] = []
    for j in range(max(12, n - 40), n - 2):
        rng = float(items[j]["h"]) - float(items[j]["l"])
        body = abs(float(items[j]["c"]) - float(items[j]["o"]))
        if rng < 1.3 * atr or body < 0.7 * rng:
            continue
        bull = float(items[j]["c"]) > float(items[j]["o"])
        prior = [float(items[k]["h"] if bull else items[k]["l"]) for k in range(j - 10, j)]
        bos = float(items[j]["c"]) > max(prior) if bull else float(items[j]["c"]) < min(prior)
        if not bos:
            continue
        k = None
        for m in range(j - 1, max(j - 8, -1), -1):
            bear_bar = float(items[m]["c"]) < float(items[m]["o"])
            if bear_bar == bull:
                k = m
                break
        if k is None:
            continue
        top, bottom = float(items[k]["h"]), float(items[k]["l"])
        mitigated = any(
            (float(items[q]["l"]) <= bottom) if bull else (float(items[q]["h"]) >= top)
            for q in range(k + 1, n - 1)
        )
        if mitigated:
            continue
        age = n - 1 - k
        q_score = 56 + 6 + (4 if rng >= 1.8 * atr else 0) + (4 if vol_hit else 0) + (2 if age >= 5 else 0)
        if bull:
            tapped = float(last["l"]) <= top and float(last["l"]) > bottom - 0.3 * atr
            if tapped and float(last["c"]) > top and _bar_pos(last) >= 0.55:
                risk = float(last["c"]) - (bottom - 0.2 * atr)
                if risk <= 0:
                    continue
                struct = max(float(items[m]["h"]) for m in range(j, n - 1))
                target = struct if struct >= float(last["c"]) + 1.2 * risk else float(last["c"]) + 2 * risk
                out.append(_result("ob_retest", "واکنش به اوردر بلاک صعودی (SMC)", "SMC", "long", "active", q_score,
                                   f"اوردر بلاک [{bottom:.6g}–{top:.6g}] از جابه‌جایی {rng / atr:.1f}×ATR با شکست ساختار — لمس شد و با بدنه بالا دفاع شد.",
                                   entry=last["c"], stop=bottom - 0.2 * atr, target=target))
            elif float(last["c"]) > top and float(last["l"]) - top <= 0.5 * atr:
                out.append(_result("ob_retest", "اوردر بلاک صعودی در انتظار", "SMC", "none", "forming", 46,
                                   f"اوردر بلاک بی‌مصرف [{bottom:.6g}–{top:.6g}] زیر قیمت — منتظر بازگشت و واکنش."))
        else:
            tapped = float(last["h"]) >= bottom and float(last["h"]) < top + 0.3 * atr
            if tapped and float(last["c"]) < bottom and _bar_pos(last) <= 0.45:
                risk = (top + 0.2 * atr) - float(last["c"])
                if risk <= 0:
                    continue
                struct = min(float(items[m]["l"]) for m in range(j, n - 1))
                target = struct if struct <= float(last["c"]) - 1.2 * risk else float(last["c"]) - 2 * risk
                out.append(_result("ob_retest", "واکنش به اوردر بلاک نزولی (SMC)", "SMC", "short", "active", q_score,
                                   f"اوردر بلاک [{bottom:.6g}–{top:.6g}] از جابه‌جایی {rng / atr:.1f}×ATR با شکست ساختار — لمس شد و با بدنه پایین دفاع شد.",
                                   entry=last["c"], stop=top + 0.2 * atr, target=target))
            elif float(last["c"]) < bottom and bottom - float(last["h"]) <= 0.5 * atr:
                out.append(_result("ob_retest", "اوردر بلاک نزولی در انتظار", "SMC", "none", "forming", 46,
                                   f"اوردر بلاک بی‌مصرف [{bottom:.6g}–{top:.6g}] بالای قیمت — منتظر بازگشت و واکنش."))
    return out[:3]


def _eqh_eql_raid(items: list[dict], atr: float) -> list[dict]:
    """Equal highs/lows (retail double top/bottom stop cluster) raided and reversed."""
    n = len(items)
    if n < 25 or atr <= 0:
        return []
    hi_idx, lo_idx = _confirmed_swings(items, 2)
    last = items[-1]
    vol_hit = float(last.get("v") or 0) >= 1.3 * _vol_avg(items)
    out: list[dict] = []
    hs = [i for i in hi_idx if n - 1 - i <= 45]
    ls = [i for i in lo_idx if n - 1 - i <= 45]
    pools_h: list[tuple[int, float]] = []
    for a in range(len(hs)):
        anchor = float(items[hs[a]]["h"])
        grp = [hs[a]]
        for b in range(a + 1, len(hs)):
            if abs(anchor - float(items[hs[b]]["h"])) <= 0.10 * atr:
                grp.append(hs[b])
            else:
                break
        if len(grp) >= 2 and (grp[-1] - grp[0]) >= 6:
            level = max(float(items[i]["h"]) for i in grp)
            if not any(abs(level - lv) <= 0.10 * atr for _, lv in pools_h):
                pools_h.append((len(grp), level))
    best_h = None
    for touches, level in pools_h:
        beyond = float(last["h"]) - level
        raided = 0.05 * atr < beyond < 1.2 * atr and float(last["c"]) < level
        if raided and (best_h is None or touches > best_h[0]):
            best_h = (touches, level)
    if best_h is None:
        # forming: nearest pool the price is approaching from below
        near = [(t_, lv) for t_, lv in pools_h
                if abs(float(last["c"]) - lv) <= 0.3 * atr and float(last["h"]) <= lv]
        if near:
            best_h = min(near, key=lambda x: abs(float(last["c"]) - x[1]))
    if best_h:
        touches, level = best_h
        beyond = float(last["h"]) - level
        if beyond > 0.05 * atr and beyond < 1.2 * atr and float(last["c"]) < level and _bar_pos(last) <= 0.45:
            q = 60 + (4 if touches >= 3 else 0) + (6 if vol_hit else 0) + (4 if beyond >= 0.20 * atr else 0)
            risk = float(last["h"]) + 0.25 * atr - float(last["c"])
            struct = min((float(items[i]["l"]) for i in ls), default=None)
            target = float(last["c"]) - 2 * risk
            if struct is not None and struct < float(last["c"]) - 1.2 * risk:
                target = struct
            out.append(_result("eqh_eql_raid", "شکار سقف‌های برابر (EQH Raid)", "Liquidity", "short", "active", q,
                               f"{touches} سقف برابر روی {level:.6g} جارو شد (ویک {beyond / atr:.2f}×ATR) و قیمت زیر استخر بسته شد — نقدینگی خرده‌فروش جمع شد.",
                               entry=last["c"], stop=float(last["h"]) + 0.25 * atr, target=target))
        elif abs(float(last["c"]) - level) <= 0.3 * atr and float(last["h"]) <= level:
            out.append(_result("eqh_eql_raid", "استخر EQH بالای قیمت", "Liquidity", "none", "forming", 48,
                               f"{touches} سقف برابر روی {level:.6g} — استخر نقدینگی بالای قیمت؛ شکست یا جارو هر دو محتمل."))
    pools_l: list[tuple[int, float]] = []
    for a in range(len(ls)):
        anchor = float(items[ls[a]]["l"])
        grp = [ls[a]]
        for b in range(a + 1, len(ls)):
            if abs(anchor - float(items[ls[b]]["l"])) <= 0.10 * atr:
                grp.append(ls[b])
            else:
                break
        if len(grp) >= 2 and (grp[-1] - grp[0]) >= 6:
            level = min(float(items[i]["l"]) for i in grp)
            if not any(abs(level - lv) <= 0.10 * atr for _, lv in pools_l):
                pools_l.append((len(grp), level))
    best_l = None
    for touches, level in pools_l:
        beyond = level - float(last["l"])
        raided = 0.05 * atr < beyond < 1.2 * atr and float(last["c"]) > level
        if raided and (best_l is None or touches > best_l[0]):
            best_l = (touches, level)
    if best_l is None:
        near = [(t_, lv) for t_, lv in pools_l
                if abs(float(last["c"]) - lv) <= 0.3 * atr and float(last["l"]) >= lv]
        if near:
            best_l = min(near, key=lambda x: abs(float(last["c"]) - x[1]))
    if best_l:
        touches, level = best_l
        beyond = level - float(last["l"])
        if beyond > 0.05 * atr and beyond < 1.2 * atr and float(last["c"]) > level and _bar_pos(last) >= 0.55:
            q = 60 + (4 if touches >= 3 else 0) + (6 if vol_hit else 0) + (4 if beyond >= 0.20 * atr else 0)
            risk = float(last["c"]) - (float(last["l"]) - 0.25 * atr)
            struct = max((float(items[i]["h"]) for i in hs), default=None)
            target = float(last["c"]) + 2 * risk
            if struct is not None and struct > float(last["c"]) + 1.2 * risk:
                target = struct
            out.append(_result("eqh_eql_raid", "شکار کف‌های برابر (EQL Raid)", "Liquidity", "long", "active", q,
                               f"{touches} کف برابر زیر {level:.6g} جارو شد (ویک {beyond / atr:.2f}×ATR) و قیمت بالای استخر بسته شد — نقدینگی خرده‌فروش جمع شد.",
                               entry=last["c"], stop=float(last["l"]) - 0.25 * atr, target=target))
        elif abs(float(last["c"]) - level) <= 0.3 * atr and float(last["l"]) >= level:
            out.append(_result("eqh_eql_raid", "استخر EQL زیر قیمت", "Liquidity", "none", "forming", 48,
                               f"{touches} کف برابر روی {level:.6g} — استخر نقدینگی زیر قیمت؛ شکست یا جارو هر دو محتمل."))
    return out


def _rsi2_reversion(items: list[dict], atr: float) -> list[dict]:
    """Connors RSI(2) mean reversion with EMA200 trend filter (quant classic)."""
    n = len(items)
    if n < 210 or atr <= 0:
        return []
    closes = [float(it["c"]) for it in items]
    ema200 = _ema_series(closes, 200)
    if len(ema200) < 6:
        return []
    rsi2 = _rsi_series(closes, 2)
    if len(rsi2) < 3:
        return []
    r_now, r_prev = rsi2[-1], rsi2[-2]
    last = items[-1]
    ma5 = _sma(closes, 5)
    slope_up = ema200[-1] > ema200[-5]
    slope_dn = ema200[-1] < ema200[-5]
    out: list[dict] = []
    if closes[-1] > ema200[-1] and slope_up and r_prev > 10 and r_now <= 10:
        q = 58 + (8 if r_now <= 5 else 0) + (4 if ma5 is not None and closes[-1] < ma5 else 0)
        stop = closes[-1] - 1.5 * atr
        target = ma5 if (ma5 is not None and ma5 >= closes[-1] + 0.9 * atr) else closes[-1] + 1.0 * atr
        out.append(_result("rsi2_reversion", "بازگشت RSI(2) کانرز (هم‌روند)", "Quant", "long", "active", q,
                           f"RSI(2)={r_now:.1f} (زیر ۱۰) در حالی که قیمت بالای EMA200 صعودی است — کشش کوتاه‌مدت در جهت روند اصلی. خروج کلاسیک: میانگین ۵ کندلی.",
                           entry=closes[-1], stop=stop, target=target))
    if closes[-1] < ema200[-1] and slope_dn and r_prev < 90 and r_now >= 90:
        q = 58 + (8 if r_now >= 95 else 0) + (4 if ma5 is not None and closes[-1] > ma5 else 0)
        stop = closes[-1] + 1.5 * atr
        target = ma5 if (ma5 is not None and ma5 <= closes[-1] - 0.9 * atr) else closes[-1] - 1.0 * atr
        out.append(_result("rsi2_reversion", "بازگشت RSI(2) کانرز (هم‌روند)", "Quant", "short", "active", q,
                           f"RSI(2)={r_now:.1f} (بالای ۹۰) در حالی که قیمت زیر EMA200 نزولی است — کشش کوتاه‌مدت در جهت روند اصلی. خروج کلاسیک: میانگین ۵ کندلی.",
                           entry=closes[-1], stop=stop, target=target))
    return out


def _nr7_breakout(items: list[dict], atr: float) -> list[dict]:
    """NR7/NR4 (Crabel): narrowest range of the last 7 bars, trade the break."""
    n = len(items)
    if n < 12 or atr <= 0:
        return []
    if n < 13:
        return []
    last = items[-1]          # trigger bar (closed)
    nr = items[-2]            # narrow-range bar
    nr_rng = float(nr["h"]) - float(nr["l"])
    if nr_rng <= 0:
        return []
    prev7 = [float(items[j]["h"]) - float(items[j]["l"]) for j in range(n - 9, n - 2)]
    if not prev7 or nr_rng >= min(prev7):
        return []
    prev4 = [float(items[j]["h"]) - float(items[j]["l"]) for j in range(n - 6, n - 2)]
    is_nr4 = bool(prev4) and nr_rng < min(prev4)
    inside = float(nr["h"]) <= float(items[-3]["h"]) and float(nr["l"]) >= float(items[-3]["l"])
    vol_hit = float(last.get("v") or 0) >= 1.3 * _vol_avg(items)
    q = 58 + (6 if is_nr4 else 0) + (6 if inside else 0) + (4 if vol_hit else 0)
    tag = "NR7" + ("/NR4" if is_nr4 else "") + (" + اینساید" if inside else "")
    plan_stop_long = float(nr["l"])
    plan_stop_short = float(nr["h"])
    if float(last["h"]) <= float(nr["h"]) and float(last["l"]) >= float(nr["l"]):
        return [_result("nr7_breakout", f"{tag} شکل گرفت", "Volatility", "none", "forming", 50,
                        f"انقباض نوسان {tag} (دامنه {nr_rng / atr:.2f}×ATR) — منتظر شکست سقف {float(nr['h']):.6g} یا کف {float(nr['l']):.6g}.")]
    if float(last["c"]) > float(nr["h"]):
        risk = float(nr["h"]) - plan_stop_long
        if risk <= 0:
            return []
        return [_result("nr7_breakout", f"شکست {tag} (انقباض نوسان)", "Volatility", "long", "active", q,
                        f"کندل {tag} با دامنه {nr_rng / atr:.2f}×ATR (کمینه ۷ کندل) — شکست سقف آن با بسته‌شدن بیرون، نشانه شروع موج جدید.",
                        entry=float(nr["h"]), stop=plan_stop_long, target=float(nr["h"]) + 1.5 * risk)]
    if float(last["c"]) < float(nr["l"]):
        risk = plan_stop_short - float(nr["l"])
        if risk <= 0:
            return []
        return [_result("nr7_breakout", f"شکست {tag} (انقباض نوسان)", "Volatility", "short", "active", q,
                        f"کندل {tag} با دامنه {nr_rng / atr:.2f}×ATR (کمینه ۷ کندل) — شکست کف آن با بسته‌شدن بیرون، نشانه شروع موج جدید.",
                        entry=float(nr["l"]), stop=plan_stop_short, target=float(nr["l"]) - 1.5 * risk)]
    return [_result("nr7_breakout", f"{tag} شکل گرفت", "Volatility", "none", "forming", 50,
                    f"انقباض نوسان {tag} (دامنه {nr_rng / atr:.2f}×ATR) — منتظر شکست سقف {float(nr['h']):.6g} یا کف {float(nr['l']):.6g}.")]


def _hikkake(items: list[dict], atr: float) -> list[dict]:
    """Hikkake: inside-bar trap — false break of an inside bar reversed within 3 bars."""
    n = len(items)
    if n < 8 or atr <= 0:
        return []
    mother, inside = items[-5], items[-4]
    if not (float(inside["h"]) <= float(mother["h"]) and float(inside["l"]) >= float(mother["l"])):
        return []
    trap_hi = max(float(items[j]["h"]) for j in range(n - 3, n))
    trap_lo = min(float(items[j]["l"]) for j in range(n - 3, n))
    up_trap = trap_hi > float(inside["h"])
    dn_trap = trap_lo < float(inside["l"])
    last = items[-1]
    vol_hit = float(last.get("v") or 0) >= 1.3 * _vol_avg(items)
    out: list[dict] = []
    if up_trap and float(last["c"]) < float(inside["l"]):
        depth = trap_hi - float(inside["h"])
        q = 58 + (6 if vol_hit else 0) + (4 if depth >= 0.3 * atr else 0)
        stop = trap_hi + 0.25 * atr
        risk = stop - float(last["c"])
        target = float(mother["l"]) if float(mother["l"]) <= float(last["c"]) - 1.2 * risk else float(last["c"]) - 2 * risk
        out.append(_result("hikkake", "هیکاکی نزولی (تله اینساید بار)", "Price Action", "short", "active", q,
                           f"شکست ناموفق سقف اینساید بار (تله تا {trap_hi:.6g}) و حالا بسته‌شدن زیر کف آن {float(inside['l']):.6g} — گیرافتادن خریداران.",
                           entry=last["c"], stop=stop, target=target))
    if dn_trap and float(last["c"]) > float(inside["h"]):
        depth = float(inside["l"]) - trap_lo
        q = 58 + (6 if vol_hit else 0) + (4 if depth >= 0.3 * atr else 0)
        stop = trap_lo - 0.25 * atr
        risk = float(last["c"]) - stop
        target = float(mother["h"]) if float(mother["h"]) >= float(last["c"]) + 1.2 * risk else float(last["c"]) + 2 * risk
        out.append(_result("hikkake", "هیکاکی صعودی (تله اینساید بار)", "Price Action", "long", "active", q,
                           f"شکست ناموفق کف اینساید بار (تله تا {trap_lo:.6g}) و حالا بسته‌شدن بالای سقف آن {float(inside['h']):.6g} — گیرافتادن فروشندگان.",
                           entry=last["c"], stop=stop, target=target))
    if not out and (up_trap or dn_trap):
        out.append(_result("hikkake", "هیکاکی (تله شکل گرفت)", "Price Action", "none", "forming", 46,
                           f"اینساید بار و شکست {'سقف' if up_trap else 'کف'} آن (تله بالقوه) — منتظر بسته‌شدن پشت سمت مخالف برای تأیید."))
    return out


def _triangle_break(items: list[dict], atr: float) -> list[dict]:
    """Ascending/descending triangle (flat side + sloped side) measured-move break."""
    n = len(items)
    if n < 30 or atr <= 0:
        return []
    hi_idx, lo_idx = _confirmed_swings(items, 2)
    win_h = [i for i in hi_idx if n - 1 - i <= 60]
    win_l = [i for i in lo_idx if n - 1 - i <= 60]
    if len(win_h) < 2 or len(win_l) < 2:
        return []
    last = items[-1]
    vol_hit = float(last.get("v") or 0) >= 1.3 * _vol_avg(items)
    out: list[dict] = []
    best_asc = 0
    best_desc = 0
    # ---- ascending: flat highs + rising lows
    for a in range(len(win_h)):
        top = float(items[win_h[a]]["h"])
        grp = [win_h[a]]
        for b in range(a + 1, len(win_h)):
            if abs(top - float(items[win_h[b]]["h"])) <= 0.15 * atr:
                grp.append(win_h[b])
            else:
                break
        if len(grp) < 2 or (grp[-1] - grp[0]) < 10:
            continue
        top = max(float(items[i]["h"]) for i in grp)
        lows_after = [i for i in win_l if i >= grp[0]]
        if len(lows_after) < 2:
            continue
        lv = [float(items[i]["l"]) for i in lows_after]
        rising = all(lv[b] > lv[b - 1] for b in range(1, len(lv))) and lv[-1] < top
        if not rising:
            best_asc = max(best_asc, len(grp)) if best_asc else len(grp)
            continue
        height = top - min(lv)
        touches = len(grp)
        broke = float(last["c"]) > top + 0.05 * atr and float(items[grp[-1]]["h"]) <= top + 1e-9
        if broke:
            q = 60 + min(6, 3 * (touches - 2)) + (6 if vol_hit else 0) + (4 if height <= 6 * atr else 0)
            stop = lv[-1] - 0.1 * atr
            if float(last["c"]) - stop <= 0:
                continue
            out.append(_result("triangle_break", "شکست مثلث صعودی", "Classic Pattern", "long", "active", q,
                               f"سقف صاف {top:.6g} با {touches} برخورد + کف‌های بالا‌رونده — شکست با بدنه بیرون؛ هدف اندازه حرکت (ارتفاع {height / atr:.1f}×ATR).",
                               entry=float(last["c"]), stop=stop, target=top + height))
            break
        if top - float(last["c"]) <= 0.3 * atr and float(last["c"]) > lv[-1]:
            out.append(_result("triangle_break", "مثلث صعودی (فشردگی)", "Classic Pattern", "none", "forming", 48,
                               f"{touches} برخورد با سقف صاف {top:.6g} و کف‌های بالا‌رونده — فنر فشرده؛ منتظر شکست سقف."))
            break
    # ---- descending: flat lows + falling highs
    for a in range(len(win_l)):
        bot = float(items[win_l[a]]["l"])
        grp = [win_l[a]]
        for b in range(a + 1, len(win_l)):
            if abs(bot - float(items[win_l[b]]["l"])) <= 0.15 * atr:
                grp.append(win_l[b])
            else:
                break
        if len(grp) < 2 or (grp[-1] - grp[0]) < 10:
            continue
        bot = min(float(items[i]["l"]) for i in grp)
        highs_after = [i for i in win_h if i >= grp[0]]
        if len(highs_after) < 2:
            continue
        hv = [float(items[i]["h"]) for i in highs_after]
        falling = all(hv[b] < hv[b - 1] for b in range(1, len(hv))) and hv[-1] > bot
        if not falling:
            continue
        height = max(hv) - bot
        touches = len(grp)
        broke = float(last["c"]) < bot - 0.05 * atr and float(items[grp[-1]]["l"]) >= bot - 1e-9
        if broke:
            q = 60 + min(6, 3 * (touches - 2)) + (6 if vol_hit else 0) + (4 if height <= 6 * atr else 0)
            stop = hv[-1] + 0.1 * atr
            if stop - float(last["c"]) <= 0:
                continue
            out.append(_result("triangle_break", "شکست مثلث نزولی", "Classic Pattern", "short", "active", q,
                               f"کف صاف {bot:.6g} با {touches} برخورد + سقف‌های پایین‌رونده — شکست با بدنه بیرون؛ هدف اندازه حرکت (ارتفاع {height / atr:.1f}×ATR).",
                               entry=float(last["c"]), stop=stop, target=bot - height))
            break
        if float(last["c"]) - bot <= 0.3 * atr and float(last["c"]) < hv[-1]:
            out.append(_result("triangle_break", "مثلث نزولی (فشردگی)", "Classic Pattern", "none", "forming", 48,
                               f"{touches} برخورد با کف صاف {bot:.6g} و سقف‌های پایین‌رونده — فنر فشرده؛ منتظر شکست کف."))
            break
    return out


def _three_drives(items: list[dict], atr: float) -> list[dict]:
    """Three-drive pattern: 3 successive pushes with momentum divergence."""
    n = len(items)
    if n < 35 or atr <= 0:
        return []
    closes = [float(it["c"]) for it in items]
    rsi = _rsi_series(closes, 14)
    rsi_off = n - len(rsi) if rsi else 0   # rsi[k] corresponds to items[k + rsi_off]
    hi_idx, lo_idx = _confirmed_swings(items, 2)
    last = items[-1]
    vol_hit = float(last.get("v") or 0) >= 1.3 * _vol_avg(items)
    out: list[dict] = []
    # ---- 3-drive bottom (bullish reversal): lower lows, higher RSI at each low
    lows = [i for i in lo_idx if n - 1 - i <= 50][-3:]
    if len(lows) == 3 and lows[0] < lows[1] < lows[2]:
        l1, l2, l3 = (float(items[i]["l"]) for i in lows)
        idx_ok = rsi and all(0 <= i - rsi_off < len(rsi) for i in lows)
        r1 = r2 = r3 = None
        if idx_ok:
            r1, r2, r3 = (rsi[i - rsi_off] for i in lows)
        drives_down = l1 > l2 > l3
        div = idx_ok and r1 < r2 < r3
        gaps = (l1 - l2, l2 - l3)
        symmetric = gaps[1] > 0 and 0.3 <= gaps[0] / gaps[1] <= 3.0
        reacted = float(last["c"]) > float(items[lows[2]]["c"]) + 0.5 * atr and _bar_pos(last) >= 0.55
        if drives_down and reacted:
            q = 56 + (8 if div else 0) + (4 if symmetric else 0) + (4 if vol_hit else 0)
            stop = l3 - 0.25 * atr
            risk = float(last["c"]) - stop
            struct = max(float(items[i]["h"]) for i in range(lows[0], n - 1))
            target = struct if struct >= float(last["c"]) + 1.2 * risk else float(last["c"]) + 2 * risk
            div_fa = f" با واگرایی RSI ({r1:.0f}→{r2:.0f}→{r3:.0f})" if div else " بدون واگرایی تأییدشده RSI"
            if risk > 0:
                out.append(_result("three_drives", "سه پرس نزولی (3-Drive)", "Harmonic", "long", "active", q,
                                   f"سه کف پیاپی ({l1:.6g} → {l2:.6g} → {l3:.6g}){div_fa} — فرسایش فروشندگان و واکنش تأییدشده.",
                                   entry=last["c"], stop=stop, target=target))
    # ---- 3-drive top (bearish reversal)
    highs = [i for i in hi_idx if n - 1 - i <= 50][-3:]
    if len(highs) == 3 and highs[0] < highs[1] < highs[2]:
        h1, h2, h3 = (float(items[i]["h"]) for i in highs)
        idx_ok = rsi and all(0 <= i - rsi_off < len(rsi) for i in highs)
        r1 = r2 = r3 = None
        if idx_ok:
            r1, r2, r3 = (rsi[i - rsi_off] for i in highs)
        drives_up = h1 < h2 < h3
        div = idx_ok and r1 > r2 > r3
        gaps = (h2 - h1, h3 - h2)
        symmetric = gaps[1] > 0 and 0.3 <= gaps[0] / gaps[1] <= 3.0
        reacted = float(last["c"]) < float(items[highs[2]]["c"]) - 0.5 * atr and _bar_pos(last) <= 0.45
        if drives_up and reacted:
            q = 56 + (8 if div else 0) + (4 if symmetric else 0) + (4 if vol_hit else 0)
            stop = h3 + 0.25 * atr
            risk = stop - float(last["c"])
            struct = min(float(items[i]["l"]) for i in range(highs[0], n - 1))
            target = struct if struct <= float(last["c"]) - 1.2 * risk else float(last["c"]) - 2 * risk
            div_fa = f" با واگرایی RSI ({r1:.0f}→{r2:.0f}→{r3:.0f})" if div else " بدون واگرایی تأییدشده RSI"
            if risk > 0:
                out.append(_result("three_drives", "سه پرس صعودی (3-Drive)", "Harmonic", "short", "active", q,
                                   f"سه سقف پیاپی ({h1:.6g} → {h2:.6g} → {h3:.6g}){div_fa} — فرسایش خریداران و واکنش تأییدشده.",
                                   entry=last["c"], stop=stop, target=target))
    return out


def _asian_sweep(items: list[dict], atr: float, timeframe: str) -> list[dict]:
    """Asian-range liquidity raid during London/NY killzones (ICT)."""
    n = len(items)
    tf_min = _tf_minutes(timeframe)
    if atr <= 0 or tf_min == 0 or tf_min > 60:
        return []
    last = items[-1]
    day = int(float(last["t"]) // 86400)
    # bar OPEN hour in UTC — a 1h bar opened at 05:00 belongs to the Asian range
    asian = [it for it in items
             if int(float(it["t"]) // 86400) == day and 0 <= _hour_utc(float(it["t"])) < 6]
    if len(asian) < 3:
        return []
    hour = _hour_utc(float(last["t"]))
    in_london = 7 <= hour < 10
    in_ny = 12 <= hour < 15
    if not (in_london or in_ny):
        return []
    a_hi = max(float(it["h"]) for it in asian)
    a_lo = min(float(it["l"]) for it in asian)
    a_mid = (a_hi + a_lo) / 2
    vol_hit = float(last.get("v") or 0) >= 1.3 * _vol_avg(items)
    kz_name = "لندن" if in_london else "نیویورک"
    q_base = 60 + (6 if in_london else 4) + (6 if vol_hit else 0)
    out: list[dict] = []
    beyond = float(last["h"]) - a_hi
    if beyond > 0.05 * atr and beyond < 1.5 * atr and float(last["c"]) < a_hi and _bar_pos(last) <= 0.45:
        q = q_base + (4 if beyond >= 0.2 * atr else 0)
        stop = float(last["h"]) + 0.25 * atr
        risk = stop - float(last["c"])
        target = a_mid if (float(last["c"]) - a_mid) >= 1.0 * risk else float(last["c"]) - 2 * risk
        if risk > 0:
            out.append(_result("asian_sweep", f"جاروی سقف آسیا در کیلزون {kz_name}", "Killzone", "short", "active", q,
                               f"ویک {beyond / atr:.2f}×ATR بالای سقف رنج آسیا ({a_hi:.6g}) در کیلزون {kz_name} و بسته‌شدن زیر آن — تله صعودی کلاسیک ICT.",
                               entry=last["c"], stop=stop, target=target))
    beyond = a_lo - float(last["l"])
    if beyond > 0.05 * atr and beyond < 1.5 * atr and float(last["c"]) > a_lo and _bar_pos(last) >= 0.55:
        q = q_base + (4 if beyond >= 0.2 * atr else 0)
        stop = float(last["l"]) - 0.25 * atr
        risk = float(last["c"]) - stop
        target = a_mid if (a_mid - float(last["c"])) >= 1.0 * risk else float(last["c"]) + 2 * risk
        if risk > 0:
            out.append(_result("asian_sweep", f"جاروی کف آسیا در کیلزون {kz_name}", "Killzone", "long", "active", q,
                               f"ویک {beyond / atr:.2f}×ATR زیر کف رنج آسیا ({a_lo:.6g}) در کیلزون {kz_name} و بسته‌شدن بالای آن — تله نزولی کلاسیک ICT.",
                               entry=last["c"], stop=stop, target=target))
    if not out:
        if abs(float(last["c"]) - a_hi) <= 0.2 * atr:
            out.append(_result("asian_sweep", "قیمت لب سقف رنج آسیا", "Killzone", "none", "forming", 48,
                               f"کیلزون {kz_name} فعال؛ قیمت {abs(float(last['c']) - a_hi) / atr:.2f}×ATR از سقف آسیا ({a_hi:.6g}) — نقدینگی بالا در کمین."))
        elif abs(float(last["c"]) - a_lo) <= 0.2 * atr:
            out.append(_result("asian_sweep", "قیمت لب کف رنج آسیا", "Killzone", "none", "forming", 48,
                               f"کیلزون {kz_name} فعال؛ قیمت {abs(float(last['c']) - a_lo) / atr:.2f}×ATR از کف آسیا ({a_lo:.6g}) — نقدینگی پایین در کمین."))
    return out


def _pivot_reject(items: list[dict], atr: float, timeframe: str) -> list[dict]:
    """Classic floor-pivot (P/R1/S1 from the previous UTC day) rejection."""
    n = len(items)
    tf_min = _tf_minutes(timeframe)
    if atr <= 0 or tf_min == 0 or tf_min > 60:
        return []
    last = items[-1]
    day = int(float(last["t"]) // 86400)
    prev = [it for it in items if int(float(it["t"]) // 86400) == day - 1]
    today = [it for it in items if int(float(it["t"]) // 86400) == day]
    if len(prev) < 3 or len(today) < 1:
        return []
    ph = max(float(it["h"]) for it in prev)
    pl = min(float(it["l"]) for it in prev)
    pc = float(prev[-1]["c"])
    p = (ph + pl + pc) / 3
    r1, s1 = 2 * p - pl, 2 * p - ph
    vol_hit = float(last.get("v") or 0) >= 1.3 * _vol_avg(items)
    out: list[dict] = []
    for lvl, name, side in ((r1, "R1", "short"), (s1, "S1", "long")):
        if side == "short":
            wicked = float(last["h"]) > lvl and float(last["c"]) < lvl
            deep = (float(last["h"]) - lvl) >= 0.25 * atr
            pos_ok = _bar_pos(last) <= 0.45
        else:
            wicked = float(last["l"]) < lvl and float(last["c"]) > lvl
            deep = (lvl - float(last["l"])) >= 0.25 * atr
            pos_ok = _bar_pos(last) >= 0.55
        near = abs(float(last["c"]) - lvl) <= 0.15 * atr
        if wicked and pos_ok:
            q = 59 + (4 if deep else 0) + (6 if vol_hit else 0)
            if side == "short":
                stop = float(last["h"]) + 0.2 * atr
                risk = stop - float(last["c"])
                target = p if (float(last["c"]) - p) >= 0.8 * risk else float(last["c"]) - 2 * risk
                if risk > 0:
                    out.append(_result("pivot_reject", f"رد شدن از پیوت {name} (کلاسیک)", "Levels", "short", "active", q,
                                       f"ویک بالای {name} روز قبل ({lvl:.6g}) و بسته‌شدن زیر آن — هدف طبیعی، پیوت {p:.6g}.",
                                       entry=last["c"], stop=stop, target=target))
            else:
                stop = float(last["l"]) - 0.2 * atr
                risk = float(last["c"]) - stop
                target = p if (p - float(last["c"])) >= 0.8 * risk else float(last["c"]) + 2 * risk
                if risk > 0:
                    out.append(_result("pivot_reject", f"رد شدن از پیوت {name} (کلاسیک)", "Levels", "long", "active", q,
                                       f"ویک زیر {name} روز قبل ({lvl:.6g}) و بسته‌شدن بالای آن — هدف طبیعی، پیوت {p:.6g}.",
                                       entry=last["c"], stop=stop, target=target))
        elif near and not out:
            out.append(_result("pivot_reject", f"قیمت روی پیوت {name}", "Levels", "none", "forming", 45,
                               f"قیمت {abs(float(last['c']) - lvl) / atr:.2f}×ATR از {name} روز قبل ({lvl:.6g}) — منتظر واکنش معتبر."))
    return out


def _silver_bullet(items: list[dict], atr: float, timeframe: str) -> list[dict]:
    """ICT Silver Bullet: an FVG formed inside the 14:00-16:00 UTC window
    (NY AM 10-11 across DST) with price trading into it during the window."""
    n = len(items)
    tf_min = _tf_minutes(timeframe)
    if atr <= 0 or tf_min == 0 or tf_min > 30:
        return []
    last = items[-1]
    hour = _hour_utc(float(last["t"]))
    if not (14 <= hour < 16):
        return []
    day = int(float(last["t"]) // 86400)
    vol_hit = float(last.get("v") or 0) >= 1.3 * _vol_avg(items)
    out: list[dict] = []
    for z in _fvg_zones(items, 24)[-3:]:
        b_idx = z["c"] - 1
        if int(float(items[b_idx]["t"]) // 86400) != day or not (14 <= _hour_utc(float(items[b_idx]["t"])) < 16):
            continue
        q = 58 + (6 if z["disp"] >= 1.5 * atr else 0) + (4 if vol_hit else 0)
        if z["dir"] == "bull":
            in_zone = float(last["l"]) <= z["top"] and float(last["h"]) >= z["bottom"] and float(last["c"]) > z["bottom"]
            if in_zone:
                stop = z["bottom"] - 0.2 * atr
                risk = float(last["c"]) - stop
                if risk > 0:
                    out.append(_result("silver_bullet", "سیلور بولت صعودی (ICT)", "Killzone", "long", "active", q,
                                       f"FVG [{z['bottom']:.6g}–{z['top']:.6g}] داخل پنجره سیلور بولت (۱۴-۱۶ UTC) ساخته شد و قیمت داخل آن معامله می‌شود — ورود در جهت جابه‌جایی {z['disp'] / atr:.1f}×ATR.",
                                       entry=last["c"], stop=stop, target=float(last["c"]) + 2 * risk))
            elif float(last["c"]) > z["top"]:
                out.append(_result("silver_bullet", "سیلور بولت در انتظار (صعودی)", "Killzone", "none", "forming", 47,
                                   f"FVG سیلور بولت [{z['bottom']:.6g}–{z['top']:.6g}] زیر قیمت — منتظر بازگشت قیمت داخل ناحیه تا پایان پنجره."))
        else:
            in_zone = float(last["h"]) >= z["bottom"] and float(last["l"]) <= z["top"] and float(last["c"]) < z["top"]
            if in_zone:
                stop = z["top"] + 0.2 * atr
                risk = stop - float(last["c"])
                if risk > 0:
                    out.append(_result("silver_bullet", "سیلور بولت نزولی (ICT)", "Killzone", "short", "active", q,
                                       f"FVG [{z['bottom']:.6g}–{z['top']:.6g}] داخل پنجره سیلور بولت (۱۴-۱۶ UTC) ساخته شد و قیمت داخل آن معامله می‌شود — ورود در جهت جابه‌جایی {z['disp'] / atr:.1f}×ATR.",
                                       entry=last["c"], stop=stop, target=float(last["c"]) - 2 * risk))
            elif float(last["c"]) < z["bottom"]:
                out.append(_result("silver_bullet", "سیلور بولت در انتظار (نزولی)", "Killzone", "none", "forming", 47,
                                   f"FVG سیلور بولت [{z['bottom']:.6g}–{z['top']:.6g}] بالای قیمت — منتظر بازگشت قیمت داخل ناحیه تا پایان پنجره."))
    return out[:2]


def scan_all(items: list[dict], timeframe: str = "15m", with_gates: bool = True,
             calibrated: bool = True) -> dict:
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
        # --- v3.16 professional batch (liquidity / ICT / SMC / quant / session / levels)
        lambda: _liquidity_sweep(items, atr),
        lambda: _fvg_tap(items, atr),
        lambda: _ob_retest(items, atr),
        lambda: _eqh_eql_raid(items, atr),
        lambda: _rsi2_reversion(items, atr),
        lambda: _nr7_breakout(items, atr),
        lambda: _hikkake(items, atr),
        lambda: _triangle_break(items, atr),
        lambda: _three_drives(items, atr),
        lambda: _asian_sweep(items, atr, tf),
        lambda: _pivot_reject(items, atr, tf),
        lambda: _silver_bullet(items, atr, tf),
    ):
        try:
            results.extend(fn() or [])
        except Exception:
            continue
    # v3.17: measured-edge calibration (quality adjust + demote proven losers)
    cal_adjusted = _apply_calibration(results) if calibrated else 0
    # dedupe by (id, direction) keeping highest quality
    best: dict[tuple, dict] = {}
    for r in results:
        key = (r["id"], r["direction"])
        if key not in best or r["quality"] > best[key]["quality"]:
            best[key] = r
    results = sorted(best.values(), key=lambda r: (r["status"] != "active",
                                                     bool(r.get("calibration_demoted")), -r["quality"]))
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
    gates_info = None
    if with_gates:
        try:
            gates_info = _signal_gates(items, active + forming)
        except Exception:
            gates_info = None
    return {
        "available": True,
        "timeframe": tf,
        "active": active,
        "forming": forming[:6],
        "counts": {"active": len(active), "forming": len(forming), "long": longs, "short": shorts},
        "net_direction": net,
        "agreement_pct": int(max(longs, shorts) / total * 100) if (longs or shorts) else 0,
        "gates": gates_info,
        "calibration": {
            "source": EDGE_CALIBRATION_SOURCE,
            "min_n": EDGE_CALIBRATION_MIN_N,
            "detectors_measured": len(_EDGE_CALIBRATION),
            "adjusted": cal_adjusted,
        },
        "top": [
            {"id": r["id"], "name_fa": r["name_fa"], "direction": r["direction"], "quality": r["quality"],
             "gate_ok": r.get("gate_ok")}
            for r in active[:5]
        ],
    }


def build_context_text(scan: dict) -> str:
    if not scan.get("available"):
        return ""
    c = scan.get("counts") or {}
    lines = [f"استراتژی‌های کلاسیک (پک v2): {c.get('active', 0)} سیگنال فعال ({c.get('long', 0)} خرید / {c.get('short', 0)} فروش)، {c.get('forming', 0)} در حال شکل‌گیری — جهت خالص: {scan.get('net_direction')}"]
    for r in scan.get("active", [])[:8]:
        gate_tag = " 🛡️✓" if r.get("gate_ok") is True else (" 🛡️✗" if r.get("gate_ok") is False else "")
        edge_tag = ""
        me = r.get("measured_edge")
        if me:
            edge_tag = f" [edge واقعی: n={me.get('n')}, avgR={me.get('avgR'):+.2f}, WR={int(round((me.get('wr') or 0) * 100))}٪]"
        lines.append(f"  • {r['name_fa']} [{r['direction']}] کیفیت={r['quality']}{gate_tag}{edge_tag} — {r['reason_fa']}")
    for r in scan.get("forming", [])[:3]:
        lines.append(f"  ◌ (forming) {r['name_fa']} — {r['reason_fa']}")
    cal = scan.get("calibration") or {}
    if cal.get("detectors_measured"):
        lines.append(
            f"  📐 کالیبراسیون edge اندازه‌گیری‌شده: {cal.get('detectors_measured')} آشکارساز روی داده واقعی سنجیده و "
            f"{cal.get('adjusted')} سیگنال تنظیم کیفیت شد — منبع: {cal.get('source')}. "
            f"کیفیت هر سیگنال حالا شامل edge واقعی walk-forward است؛ بازنده‌های اثبات‌شده به رصد تنزل یافتند."
        )
    g = scan.get("gates") or {}
    gc = g.get("counts") or {}
    if gc.get("tagged"):
        lines.append(
            f"  🛡️ گیت هم‌جهتی زنده (EMA{g.get('ema_span')} + رأی پک اندیکاتور، آستانه ±{g.get('vote_threshold')}): "
            f"{gc.get('gate_ok', 0)} از {gc.get('tagged', 0)} سیگنال — خالص رأی {g.get('net_votes')}. "
            f"این گیت در بک‌تست 1h اندازه‌گیری شده (votes: PF 1.62 در برابر 1.35 بدون گیت)؛ در 5m هیچ گیتی کمک نکرد."
        )
    return "\n".join(lines)
