"""Advanced ICT / Smart Money Concepts detectors (deterministic, candle-based).

Everything here is computed from real completed candles — no speculation.
Output feeds the market dossier, setups scoring and AI grounding.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _r(value: float | None, digits: int = 6) -> Any:
    return round(value, digits) if value is not None else None


def swing_points(items: list[dict], k: int = 2) -> tuple[list[int], list[int]]:
    """Fractal swing highs/lows: bar higher (or lower) than k bars on each side."""
    highs: list[int] = []
    lows: list[int] = []
    n = len(items)
    for i in range(k, n - k):
        window_h = [float(items[j]["h"]) for j in range(i - k, i + k + 1) if j != i]
        window_l = [float(items[j]["l"]) for j in range(i - k, i + k + 1) if j != i]
        if float(items[i]["h"]) > max(window_h):
            highs.append(i)
        if float(items[i]["l"]) < min(window_l):
            lows.append(i)
    return highs, lows


def equal_levels(items: list[dict], k: int = 2, tol_pct: float = 0.0008) -> dict:
    """Equal highs (EQH) / equal lows (EQL): liquidity resting at same price."""
    high_idx, low_idx = swing_points(items, k)
    eqh: list[dict] = []
    eql: list[dict] = []

    def cluster(indices: list[int], extractor) -> list[dict]:
        levels: list[dict] = []
        used = set()
        for a in indices:
            if a in used:
                continue
            group = [a]
            for b in indices:
                if b == a or b in used:
                    continue
                pa, pb = extractor(items[a]), extractor(items[b])
                if pa > 0 and abs(pa - pb) / pa <= tol_pct:
                    group.append(b)
            if len(group) >= 2:
                for g in group:
                    used.add(g)
                levels.append({
                    "price": _r(sum(extractor(items[g]) for g in group) / len(group)),
                    "count": len(group),
                    "index": group[-1],
                })
        return levels

    eqh = cluster(high_idx, lambda it: float(it["h"]))
    eql = cluster(low_idx, lambda it: float(it["l"]))
    return {"eqh": eqh[-3:], "eql": eql[-3:]}


def liquidity_sweeps(items: list[dict], k: int = 2, lookback: int = 40) -> list[dict]:
    """Sweep = price wicks beyond a prior swing level then closes back inside."""
    high_idx, low_idx = swing_points(items, k)
    events: list[dict] = []
    start = max(k + 1, len(items) - lookback)
    for i in range(start, len(items)):
        prior_highs = [j for j in high_idx if j < i - 1]
        prior_lows = [j for j in low_idx if j < i - 1]
        if prior_highs:
            level = float(items[max(prior_highs)]["h"])
            if float(items[i]["h"]) > level and float(items[i]["c"]) < level:
                events.append({"kind": "sweep_high", "dir": "bearish", "price": _r(level), "index": i})
        if prior_lows:
            level = float(items[min(prior_lows)]["l"])
            if float(items[i]["l"]) < level and float(items[i]["c"]) > level:
                events.append({"kind": "sweep_low", "dir": "bullish", "price": _r(level), "index": i})
    # de-duplicate consecutive same-kind sweeps, keep latest
    unique: dict[tuple, dict] = {}
    for event in events:
        unique[(event["kind"], event["price"])] = event
    return sorted(unique.values(), key=lambda e: e["index"])[-4:]


def displacement(items: list[dict], atr_period: int = 14, multiplier: float = 1.4) -> dict:
    """Institutional displacement: large-bodied candles pushing direction."""
    n = len(items)
    if n < atr_period + 2:
        return {"direction": "none", "candles": 0, "strength": 0.0}
    trs = [max(items[i]["h"] - items[i]["l"], abs(items[i]["h"] - items[i - 1]["c"]), abs(items[i]["l"] - items[i - 1]["c"])) for i in range(1, n)]
    atr = sum(trs[-atr_period:]) / atr_period
    if atr <= 0:
        return {"direction": "none", "candles": 0, "strength": 0.0}
    up = down = 0
    for item in items[-6:]:
        body = abs(item["c"] - item["o"])
        if body >= multiplier * atr:
            if item["c"] > item["o"]:
                up += 1
            else:
                down += 1
    direction = "up" if up > down else "down" if down > up else "none"
    strength = round(max(up, down) / 6 * 100, 1)
    return {"direction": direction, "candles": max(up, down), "strength": strength}


def fvg_states(fvgs: list[dict], items: list[dict]) -> list[dict]:
    """Fair Value Gaps with numeric fill state (fresh / partial / filled) + CE."""
    if not items or not fvgs:
        return []
    last_index = len(items) - 1
    states: list[dict] = []
    for zone in fvgs[:8]:
        try:
            top = float(zone["top"])
            bottom = float(zone["bottom"])
        except (KeyError, TypeError, ValueError):
            continue
        if top <= 0 or bottom <= 0 or top <= bottom:
            continue
        side = str(zone.get("side") or zone.get("kind") or "")
        depth = top - bottom
        zone_index = int(zone.get("index", 0) or 0)
        deepest = top
        for item in items[max(zone_index + 1, 0):]:
            deepest = min(deepest, float(item["l"])) if side.startswith("bull") else max(deepest, float(item["h"]))
        if side.startswith("bull"):
            filled_pct = max(0.0, min(100.0, (top - deepest) / depth * 100))
        else:
            filled_pct = max(0.0, min(100.0, (deepest - bottom) / depth * 100))
        state = "filled" if filled_pct >= 80 else "partial" if filled_pct >= 25 else "fresh"
        states.append({
            "top": _r(top), "bottom": _r(bottom), "ce": _r((top + bottom) / 2),
            "side": side, "filled_pct": round(filled_pct, 1), "state": state,
        })
    return states


def premium_discount_position(price: float, items: list[dict], lookback: int = 96) -> dict:
    """Position inside the dealing range (ICT premium/discount array)."""
    window = items[-lookback:] if items else []
    if not window or price <= 0:
        return {"position_pct": None, "zone": "unknown"}
    range_high = max(float(it["h"]) for it in window)
    range_low = min(float(it["l"]) for it in window)
    span = range_high - range_low
    if span <= 0:
        return {"position_pct": None, "zone": "unknown"}
    position = (price - range_low) / span * 100
    zone = "premium" if position >= 70 else "discount" if position <= 30 else "equilibrium"
    return {
        "position_pct": round(position, 1),
        "zone": zone,
        "range_high": _r(range_high),
        "range_low": _r(range_low),
        "eq_50": _r((range_high + range_low) / 2),
    }


def silver_bullet_active(now_utc: datetime | None = None) -> dict:
    """ICT Silver Bullet windows (New York 10-11 AM / London 4-5 AM / PM 2-3 PM)."""
    try:
        from zoneinfo import ZoneInfo
        local = (now_utc or datetime.now(timezone.utc)).astimezone(ZoneInfo("America/New_York"))
    except Exception:
        utc_hour = (now_utc or datetime.now(timezone.utc)).hour
        local_hour = (utc_hour - 4) % 24
        local = type("T", (), {"hour": local_hour, "weekday": lambda self: 2})()
    hour = local.hour
    weekday = local.weekday() if hasattr(local, "weekday") else 2
    window = None
    if weekday < 5:
        if hour == 10:
            window = "NY_AM_SilverBullet_10-11"
        elif hour == 15:
            window = "NY_PM_SilverBullet_15-16"
    active = window is not None
    return {"active": active, "window": window, "local_hour": hour}


# ---------------------------------------------------------------- v2 additions


def market_structure(items: list[dict], k: int = 2, lookback: int = 80) -> dict:
    """BOS / CHoCH state machine over confirmed fractal swings (no repaint)."""
    win = items[-lookback:] if len(items) > lookback else items
    high_idx, low_idx = swing_points(win, k)
    if len(high_idx) < 2 or len(low_idx) < 2:
        return {"state": "unknown", "events": [], "last_swing_high": None,
                "last_swing_low": None, "pattern": "unknown"}
    events: list[dict] = []
    state = "bullish" if win[high_idx[-1]]["h"] > win[high_idx[-2]]["h"] and win[low_idx[-1]]["l"] > win[low_idx[-2]]["l"] else (
        "bearish" if win[low_idx[-1]]["l"] < win[low_idx[-2]]["l"] and win[high_idx[-1]]["h"] < win[high_idx[-2]]["h"] else "ranging")
    last_sh = win[high_idx[-1]]["h"]
    last_sl = win[low_idx[-1]]["l"]
    for i in range(max(high_idx[-1], low_idx[-1]) + k + 1, len(win)):
        c = float(win[i]["c"])
        if state in ("bullish", "ranging") and c > last_sh:
            kind = "BOS" if state == "bullish" else "CHoCH"
            events.append({"kind": kind, "dir": "bullish", "price": _r(last_sh), "index": i})
            state = "bullish"
            highs_after = [j for j in high_idx if j < i]
            lows_after = [j for j in low_idx if j < i]
            if highs_after:
                last_sh = win[highs_after[-1]]["h"]
            if lows_after:
                last_sl = win[lows_after[-1]]["l"]
        elif state in ("bearish", "ranging") and c < last_sl:
            kind = "BOS" if state == "bearish" else "CHoCH"
            events.append({"kind": kind, "dir": "bearish", "price": _r(last_sl), "index": i})
            state = "bearish"
            highs_after = [j for j in high_idx if j < i]
            lows_after = [j for j in low_idx if j < i]
            if highs_after:
                last_sh = win[highs_after[-1]]["h"]
            if lows_after:
                last_sl = win[lows_after[-1]]["l"]
    hh_hl = state == "bullish"
    return {
        "state": state,
        "events": events[-4:],
        "last_swing_high": _r(last_sh),
        "last_swing_low": _r(last_sl),
        "pattern": "HH/HL" if hh_hl else "LH/LL" if state == "bearish" else "mixed",
    }


def ote_zone(items: list[dict], k: int = 2) -> dict:
    """Optimal Trade Entry: 0.62–0.79 retracement of the latest impulsive leg."""
    high_idx, low_idx = swing_points(items, k)
    if len(high_idx) < 1 or len(low_idx) < 1:
        return {"available": False}
    hi = high_idx[-1]
    lo = low_idx[-1]
    price = float(items[-1]["c"])
    if hi > lo:
        leg_low = float(items[lo]["l"])
        leg_high = float(items[hi]["h"])
        direction = "long"
    elif lo > hi:
        leg_low = float(items[lo]["l"])
        leg_high = float(items[hi]["h"])
        direction = "short"
    else:
        return {"available": False}
    span = leg_high - leg_low
    if span <= 0:
        return {"available": False}
    top = leg_high - 0.618 * span
    bottom = leg_high - 0.786 * span
    inside = bottom <= price <= top
    return {
        "available": True,
        "direction": direction,
        "leg_low": _r(leg_low), "leg_high": _r(leg_high),
        "ote_top": _r(top), "ote_bottom": _r(bottom),
        "ote_71": _r(leg_high - 0.705 * span),
        "price_in_zone": bool(inside),
    }


def killzone_state(items: list[dict] | None = None, now_utc: datetime | None = None) -> dict:
    """Active ICT killzone (UTC): Asia 00-06, London 07-10, NY 12-15, LondonClose 15-17."""
    ts = float(items[-1]["t"]) if items else None
    now = now_utc or (datetime.fromtimestamp(ts, timezone.utc) if ts else datetime.now(timezone.utc))
    minutes = now.hour * 60 + now.minute
    windows = [
        ("asia", 0, 360, "رنج آسیا — نقدینگی‌سازی؛ معمولاً بی‌روند"),
        ("london", 420, 600, "کیلزون لندن — بیشترین احتمال manipulation + جهت روز"),
        ("new_york", 720, 900, "کیلزون نیویورک — ادامه یا بازگشت جهت لندن"),
        ("london_close", 900, 1020, "بسته‌شدن لندن — تسویه و بازگشت‌های کوتاه"),
    ]
    active = None
    for name, start, end, note in windows:
        if start <= minutes < end:
            active = {"name": name, "note_fa": note, "minutes_left": end - minutes}
            break
    weekday = now.weekday()
    weekend = weekday >= 5
    return {"active": active, "utc_hour": now.hour, "utc_minute": now.minute, "weekend": weekend,
            "quality": "low" if weekend or not active else "high" if active and active["name"] in ("london", "new_york") else "medium"}


def inversion_fvgs(fvg_state_list: list[dict]) -> list[dict]:
    """Filled FVGs flip their role (ICT inversion): bull filled → resistance."""
    out: list[dict] = []
    for gap in fvg_state_list or []:
        if str(gap.get("state")) != "filled":
            continue
        side = str(gap.get("side") or "")
        new_role = "resistance" if side.startswith("bull") else "support" if side.startswith("bear") else "unknown"
        out.append({"top": gap.get("top"), "bottom": gap.get("bottom"), "ce": gap.get("ce"),
                    "original_side": side, "inverted_role": new_role})
    return out[:4]


def breaker_blocks(items: list[dict], k: int = 2, atr_period: int = 14) -> list[dict]:
    """Breaker: last opposite OB swept through by displacement; now flips role."""
    n = len(items)
    if n < atr_period + 10:
        return []
    trs = [max(items[i]["h"] - items[i]["l"], abs(items[i]["h"] - items[i - 1]["c"]), abs(items[i]["l"] - items[i - 1]["c"])) for i in range(1, n)]
    atr = sum(trs[-atr_period:]) / atr_period or 1e-9
    high_idx, low_idx = swing_points(items, k)
    out: list[dict] = []
    # bullish breaker: failed bearish OB (down-close cluster) broken by a strong up move
    for i in range(max(k + 2, n - 60), n - 2):
        body = items[i]["c"] - items[i]["o"]
        if body >= 1.4 * atr and high_idx:
            prior = [j for j in low_idx if j < i]
            if prior and float(items[i]["c"]) > float(items[prior[-1]]["l"]) + atr:
                # the last down-close candle before the impulse is the breaker
                cand = None
                for j in range(i - 1, max(i - 6, 0), -1):
                    if items[j]["c"] < items[j]["o"]:
                        cand = j
                        break
                if cand is not None:
                    zone = {"kind": "bullish_breaker", "top": _r(items[cand]["h"]), "bottom": _r(items[cand]["l"]),
                            "index": cand, "broken_index": i}
                    if zone not in out:
                        out.append(zone)
        if body <= -1.4 * atr and low_idx:
            prior = [j for j in high_idx if j < i]
            if prior and float(items[i]["c"]) < float(items[prior[-1]]["h"]) - atr:
                cand = None
                for j in range(i - 1, max(i - 6, 0), -1):
                    if items[j]["c"] > items[j]["o"]:
                        cand = j
                        break
                if cand is not None:
                    zone = {"kind": "bearish_breaker", "top": _r(items[cand]["h"]), "bottom": _r(items[cand]["l"]),
                            "index": cand, "broken_index": i}
                    if zone not in out:
                        out.append(zone)
    return out[-3:]



def summarize(items: list[dict], report: dict | None = None, now_utc: datetime | None = None, price: float | None = None) -> dict:
    report = report or {}
    price = float(price or (items[-1]["c"] if items else 0))
    eq = equal_levels(items)
    sweeps = liquidity_sweeps(items)
    disp = displacement(items)
    fvgs = fvg_states((report.get("fvg") or []), items)
    pd = premium_discount_position(price, items)
    sb = silver_bullet_active(now_utc)
    structure = market_structure(items)
    ote = ote_zone(items)
    kz = killzone_state(items, now_utc)
    inv = inversion_fvgs(fvgs)
    brk = breaker_blocks(items)

    bull = bear = 0
    for sweep in sweeps:
        if sweep["dir"] == "bullish":
            bull += 3
        else:
            bear += 3
    if disp["direction"] == "up":
        bull += 4
    elif disp["direction"] == "down":
        bear += 4
    if pd.get("zone") == "discount":
        bull += 2
    elif pd.get("zone") == "premium":
        bear += 2
    for gap in fvgs:
        if gap["state"] == "fresh":
            if gap["side"].startswith("bull") and price >= gap["bottom"]:
                bull += 2
            elif gap["side"].startswith("bear") and price <= gap["top"]:
                bear += 2
    # v2: market structure + OTE alignment
    if structure.get("state") == "bullish":
        bull += 3
    elif structure.get("state") == "bearish":
        bear += 3
    if ote.get("available") and ote.get("price_in_zone"):
        if ote.get("direction") == "long":
            bull += 2
        else:
            bear += 2
    events = [
        {"kind": s["kind"], "dir": s["dir"], "price": s["price"]} for s in sweeps
    ]
    if disp["direction"] != "none":
        events.append({"kind": "displacement", "dir": "bullish" if disp["direction"] == "up" else "bearish", "price": price})
    for ev in structure.get("events") or []:
        events.append({"kind": ev.get("kind"), "dir": ev.get("dir"), "price": ev.get("price")})
    return {
        "equal_highs_lows": eq,
        "sweeps": sweeps,
        "displacement": disp,
        "fvg_states": fvgs[:5],
        "premium_discount": pd,
        "silver_bullet": sb,
        "market_structure": structure,
        "ote": ote,
        "killzone": kz,
        "inversion_fvg": inv,
        "breakers": brk,
        "events": events[-6:],
        "points_bull": min(15, bull),
        "points_bear": min(15, bear),
    }
