"""Apex AI — RTM (Read The Market) + Supply/Demand + Liquidity-Map engine.

Created by Amin Omidi. Deterministic, candle-based — computed exclusively from
REAL completed exchange candles (same contract as ict_engine / smc_engine).
No speculation, no repainting: every level carries the candle index that
created it, and every signal is mitigated/swept-checked against later bars.

Blocks:
  * QML   — Quasimodo levels (higher-high sweep + low break, and mirror)
  * FTR   — Fail To Return zones (impulse origin never revisited)
  * MPL   — Maximum Pain Level of RTM flags (stop-run level below/above flag)
  * CMP   — Compression into a flat target (shrinking swings = pending raid)
  * S/D   — Supply/Demand zones: RBR / DBD (supply) and RBR→ demand DBR / RBD,
            with departure strength, touches and mitigation state
  * LIQ   — Liquidity map: EQH/EQL, PDH/PDL, swing pools + Draw-On-Liquidity

summarize(items, report) is the single entry point used by main.py; it also
emits chart overlay items (lines/zones/labels) so the Android chart renders
RTM levels without any client change.
"""
from __future__ import annotations

from typing import Any

from app.services import ict_engine

_MIN_CANDLES = 30


def _r(value: float | None, digits: int = 6) -> Any:
    return round(value, digits) if value is not None else None


def _f(item: dict, key: str) -> float:
    return float(item.get(key) or 0.0)


def _atr(items: list[dict], period: int = 14) -> float:
    if len(items) < 2:
        return 0.0
    trs: list[float] = []
    for i in range(1, len(items)):
        h, l, pc = _f(items[i], "h"), _f(items[i], "l"), _f(items[i - 1], "c")
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    trs = trs[-period:]
    return sum(trs) / len(trs) if trs else 0.0


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2


def _swings(items: list[dict], k: int = 2) -> tuple[list[int], list[int]]:
    return ict_engine.swing_points(items, k)


# --------------------------------------------------------------------------- QML
def qml_levels(items: list[dict], atr: float, lookback: int = 140) -> list[dict]:
    """Quasimodo: a sweep of the previous swing extreme followed by a close
    through the opposite swing — the sweeping extreme becomes the QML level.

    Bearish QML: higher-high above the prior swing high, then a close below
    the intervening swing low → short entries on the return to the HH.
    Bullish QML is the exact mirror (lower-low sweep + close above prior high).
    """
    out: list[dict] = []
    if atr <= 0 or len(items) < 12:
        return out
    highs, lows = _swings(items, 2)
    n = len(items)
    start = max(0, n - lookback)
    tol = atr * 0.25

    for a in range(1, len(highs)):
        h_prev_i, h_new_i = highs[a - 1], highs[a]
        if h_new_i <= start or h_new_i - h_prev_i < 4:
            continue
        if _f(items[h_new_i], "h") <= _f(items[h_prev_i], "h"):
            continue  # not a higher high — no sweep
        # intervening swing low between the two highs
        between = [j for j in lows if h_prev_i < j < h_new_i]
        if not between:
            continue
        l_i = between[-1]
        level_low = _f(items[l_i], "l")
        # close below the intervening low after the sweep
        broke = next(
            (j for j in range(h_new_i + 1, min(n, h_new_i + 25))
             if _f(items[j], "c") < level_low),
            None,
        )
        if broke is None:
            continue
        zone_top = _f(items[h_new_i], "h")
        zone_bottom = min(_f(items[h_new_i], "o"), _f(items[h_new_i], "c"))
        mitigated_at = next(
            (j for j in range(broke + 1, n) if _f(items[j], "h") >= zone_bottom - tol),
            None,
        )
        out.append({
            "kind": "qml_bear",
            "price": _r(zone_top),
            "top": _r(zone_top),
            "bottom": _r(zone_bottom),
            "index": h_new_i,
            "confirmed_index": broke,
            "mitigated": mitigated_at is not None,
            "mitigated_index": mitigated_at,
            "distance_pct": _r((zone_top / max(_f(items[-1], "c"), 1e-9) - 1) * 100, 3),
        })

    for a in range(1, len(lows)):
        l_prev_i, l_new_i = lows[a - 1], lows[a]
        if l_new_i <= start or l_new_i - l_prev_i < 4:
            continue
        if _f(items[l_new_i], "l") >= _f(items[l_prev_i], "l"):
            continue  # not a lower low — no sweep
        between = [j for j in highs if l_prev_i < j < l_new_i]
        if not between:
            continue
        h_i = between[-1]
        level_high = _f(items[h_i], "h")
        broke = next(
            (j for j in range(l_new_i + 1, min(n, l_new_i + 25))
             if _f(items[j], "c") > level_high),
            None,
        )
        if broke is None:
            continue
        zone_bottom = _f(items[l_new_i], "l")
        zone_top = max(_f(items[l_new_i], "o"), _f(items[l_new_i], "c"))
        mitigated_at = next(
            (j for j in range(broke + 1, n) if _f(items[j], "l") <= zone_top + tol),
            None,
        )
        out.append({
            "kind": "qml_bull",
            "price": _r(zone_bottom),
            "top": _r(zone_top),
            "bottom": _r(zone_bottom),
            "index": l_new_i,
            "confirmed_index": broke,
            "mitigated": mitigated_at is not None,
            "mitigated_index": mitigated_at,
            "distance_pct": _r((zone_bottom / max(_f(items[-1], "c"), 1e-9) - 1) * 100, 3),
        })

    active_first = sorted(out, key=lambda z: (z["mitigated"], -(z["index"])))
    return active_first[:3]


# --------------------------------------------------------------------------- FTR
def ftr_zones(items: list[dict], atr: float, lookback: int = 140) -> list[dict]:
    """Fail To Return: a strong impulse whose origin zone is never revisited
    within the confirmation window — institutional footprint that price
    'failed to return' to. Zone stays active until finally touched."""
    out: list[dict] = []
    if atr <= 0 or len(items) < 15:
        return out
    n = len(items)
    start = max(1, n - lookback)
    bodies = [abs(_f(items[i], "c") - _f(items[i], "o")) for i in range(1, n)]
    med_body = max(_median(bodies[-40:]), atr * 0.05)

    for i in range(start + 3, n - 2):
        body = _f(items[i], "c") - _f(items[i], "o")
        if abs(body) < max(1.6 * atr, 2.2 * med_body):
            continue
        bullish = body > 0
        # origin = last opposite-colour bar before the impulse (max 3 back)
        origin = None
        for j in range(i - 1, max(start, i - 4), -1):
            jb = _f(items[j], "c") - _f(items[j], "o")
            if (jb <= 0) if bullish else (jb >= 0):
                origin = j
                break
        if origin is None:
            continue
        z_top = max(_f(items[origin], "h"), _f(items[i], "o"))
        z_bottom = min(_f(items[origin], "l"), _f(items[i], "o"))
        if z_top - z_bottom > 1.5 * atr:
            z_top, z_bottom = _f(items[origin], "h"), _f(items[origin], "l")
        window = range(i + 1, min(n, i + 13))
        returned = any(
            (_f(items[j], "l") <= z_top) if bullish else (_f(items[j], "h") >= z_bottom)
            for j in window
        )
        if returned:
            continue  # it DID return — not an FTR
        def _touches(j: int) -> bool:
            return (_f(items[j], "l") <= z_top) if bullish else (_f(items[j], "h") >= z_bottom)

        touched_after = next((j for j in range(i + 13, n) if _touches(j)), None)
        out.append({
            "kind": "ftr_bull" if bullish else "ftr_bear",
            "top": _r(z_top),
            "bottom": _r(z_bottom),
            "price": _r((z_top + z_bottom) / 2),
            "index": origin,
            "impulse_index": i,
            "strength": _r(min(abs(body) / atr, 6.0), 2),
            "mitigated": touched_after is not None,
            "mitigated_index": touched_after,
            "distance_pct": _r(((z_top + z_bottom) / 2 / max(_f(items[-1], "c"), 1e-9) - 1) * 100, 3),
        })

    out.sort(key=lambda z: (z["mitigated"], -z["strength"], -(z["index"])))
    return out[:3]


# ---------------------------------------------------------------------- Flag/MPL
def flags_mpl(items: list[dict], atr: float, lookback: int = 140) -> list[dict]:
    """RTM flag + Maximum Pain Level: an impulse pole followed by a tight
    consolidation. MPL is the flag extreme opposite the pole direction — where
    late entries keep their stops; a sweep-and-hold of MPL is the RTM entry."""
    out: list[dict] = []
    if atr <= 0 or len(items) < 20:
        return out
    n = len(items)
    start = max(0, n - lookback)
    i = start + 3
    while i < n - 6:
        advanced = False
        # pole: 3..8 bars with net move >= 3 ATR and >=60% aligned bodies
        for p_len in range(3, 9):
            if i + p_len >= n:
                break
            seg = items[i:i + p_len + 1]
            net = _f(seg[-1], "c") - _f(seg[0], "o")
            aligned = sum(
                1 for b in seg
                if (net > 0 and _f(b, "c") > _f(b, "o")) or (net < 0 and _f(b, "c") < _f(b, "o"))
            )
            pole_range = max(_f(b, "h") for b in seg) - min(_f(b, "l") for b in seg)
            if abs(net) >= 3.0 * atr and aligned >= 0.6 * len(seg) and pole_range <= abs(net) * 1.8:
                bullish = net > 0
                # flag: next 3..12 tight bars staying in the pole's upper/lower half
                f_start = i + p_len + 1
                best = None
                for f_len in range(3, 13):
                    if f_start + f_len > n:
                        break
                    flag = items[f_start:f_start + f_len]
                    if any(
                        abs(_f(b, "c") - _f(b, "o")) > 0.5 * atr
                        or (_f(b, "h") - _f(b, "l")) > 0.9 * atr
                        for b in flag
                    ):
                        # every flag bar must be tight; a longer window can only
                        # re-include the same offender → stop extending
                        break
                    f_high = max(_f(b, "h") for b in flag)
                    f_low = min(_f(b, "l") for b in flag)
                    holds_half = (
                        f_low >= _f(seg[0], "o") + abs(net) * 0.5
                        if bullish
                        else f_high <= _f(seg[0], "o") - abs(net) * 0.5
                    )
                    if (f_high - f_low) <= 0.45 * pole_range and holds_half:
                        best = (flag, f_high, f_low, f_start + f_len - 1)
                if best:
                    flag, f_high, f_low, f_end = best
                    mpl = f_low if bullish else f_high
                    swept_at = next(
                        (j for j in range(f_end + 1, n)
                         if ((_f(items[j], "l") < mpl) if bullish else (_f(items[j], "h") > mpl))),
                        None,
                    )
                    swept_back = False
                    if swept_at is not None:
                        close_at_sweep = _f(items[swept_at], "c")
                        swept_back = close_at_sweep > mpl if bullish else close_at_sweep < mpl
                    out.append({
                        "kind": "flag_bull" if bullish else "flag_bear",
                        "pole_index": i,
                        "flag_start": f_start,
                        "flag_end": f_end,
                        "flag_high": _r(f_high),
                        "flag_low": _r(f_low),
                        "mpl": _r(mpl),
                        "pole_atr": _r(abs(net) / atr, 2),
                        "mpl_swept": swept_at is not None,
                        "sweep_reclaimed": bool(swept_back),
                        "index": f_end,
                        "distance_pct": _r((mpl / max(_f(items[-1], "c"), 1e-9) - 1) * 100, 3),
                    })
                    i = f_end + 1
                    advanced = True
                    break
        if not advanced:
            i += 1
        if len(out) >= 2:
            break
    out.sort(key=lambda z: -z["index"])
    return out[:2]


# ------------------------------------------------------------------- Compression
def compression(items: list[dict], atr: float, lookback: int = 140) -> list[dict]:
    """Compression: successive swings of shrinking amplitude pressing into a
    flat target level (resting liquidity). RTM reads this as a pending raid
    of the target — direction of the press is the expected breakout side."""
    out: list[dict] = []
    if atr <= 0 or len(items) < 20:
        return out
    highs, lows = _swings(items, 2)
    n = len(items)
    start = max(0, n - lookback)
    price_tol = atr * 0.35

    hs = [j for j in highs if j >= start]
    ls = [j for j in lows if j >= start]

    def press(flat: list[int], pressing: list[int], flat_ext, press_ext, kind: str, direction: str) -> None:
        if len(flat) < 2 or len(pressing) < 3:
            return
        f0, f1 = flat[-2], flat[-1]
        if f1 - f0 < 3:
            return
        if abs(flat_ext(items[f0]) - flat_ext(items[f1])) > price_tol:
            return  # target not flat
        tail = [j for j in pressing if f0 < j < f1 or j > f1]
        tail = sorted(set(tail))[-4:]
        if len(tail) < 3:
            return
        amplitudes: list[float] = []
        for a, b in zip(tail, tail[1:]):
            amplitudes.append(abs(press_ext(items[b]) - press_ext(items[a])))
        rising = all(
            (press_ext(items[b]) > press_ext(items[a])) if direction == "bull"
            else (press_ext(items[b]) < press_ext(items[a]))
            for a, b in zip(tail, tail[1:])
        )
        shrinking = all(b < a * 1.05 and b < amplitudes[0] * 1.35 for a, b in zip(amplitudes, amplitudes[1:])) if len(amplitudes) >= 2 else False
        if not (rising and shrinking):
            return
        target = (flat_ext(items[f0]) + flat_ext(items[f1])) / 2
        out.append({
            "kind": kind,
            "target": _r(target),
            "direction": direction,
            "swings": len(tail),
            "index": f1,
            "last_press_index": tail[-1],
            "distance_pct": _r((target / max(_f(items[-1], "c"), 1e-9) - 1) * 100, 3),
        })

    # bull compression: rising lows pressing into flat highs (target above)
    press(hs, ls, lambda it: _f(it, "h"), lambda it: _f(it, "l"), "compression_bull", "bull")
    # bear compression: falling highs pressing into flat lows (target below)
    press(ls, hs, lambda it: _f(it, "l"), lambda it: _f(it, "h"), "compression_bear", "bear")
    return out[:2]


# ------------------------------------------------------------------ Supply/Demand
def supply_demand_zones(items: list[dict], atr: float, lookback: int = 200) -> list[dict]:
    """RTM-style supply/demand: tight base (1-3 bars) + strong departure.

    demand: DBR (drop-base-rally, reversal) / RBR (rally-base-rally, continuation)
    supply: RBD (rally-base-drop, reversal) / DBD (drop-base-drop, continuation)
    Strength = departure body in ATRs; touches counted after formation;
    mitigated once a CLOSE crosses the zone midpoint against it.
    """
    out: list[dict] = []
    if atr <= 0 or len(items) < 12:
        return out
    n = len(items)
    start = max(1, n - lookback)

    for base_start in range(start, n - 3):
        for base_len in (1, 2, 3):
            base_end = base_start + base_len - 1
            dep = base_end + 1
            if dep >= n:
                break
            base = items[base_start:base_end + 1]
            z_top = max(_f(b, "h") for b in base)
            z_bottom = min(_f(b, "l") for b in base)
            if z_top - z_bottom > 1.2 * atr:
                continue
            if any(abs(_f(b, "c") - _f(b, "o")) > 0.6 * atr for b in base):
                continue  # base must be tight
            body = _f(items[dep], "c") - _f(items[dep], "o")
            if abs(body) < 1.2 * atr:
                continue
            # approach move before the base (avg of up to 3 bars)
            a0 = max(start, base_start - 3)
            approach = _f(items[base_start - 1], "c") - _f(items[a0], "o") if base_start - 1 >= a0 else 0.0
            if body > 0:
                kind = "DBR" if approach < 0 else "RBR"
                side = "bullish"
            else:
                kind = "RBD" if approach > 0 else "DBD"
                side = "bearish"
            mid = (z_top + z_bottom) / 2
            touches = 0
            mitigated_at = None
            for j in range(dep + 1, n):
                if _f(items[j], "l") <= z_top and _f(items[j], "h") >= z_bottom:
                    touches += 1
                if (side == "bullish" and _f(items[j], "c") < mid) or \
                   (side == "bearish" and _f(items[j], "c") > mid):
                    mitigated_at = j
                    break
            if mitigated_at is not None and mitigated_at < n - 2:
                continue  # long-dead zone; only just-mitigated ones stay for context
            price = _f(items[-1], "c")
            out.append({
                "kind": kind,
                "side": side,
                "top": _r(z_top),
                "bottom": _r(z_bottom),
                "price": _r(mid),
                "index": base_start,
                "departure_index": dep,
                "strength": _r(min(abs(body) / atr, 6.0), 2),
                "touches": touches,
                "fresh": touches == 0,
                "mitigated": mitigated_at is not None,
                "quality": int(min(10, round(abs(body) / atr * 2 - touches))),
                "distance_pct": _r((mid / max(price, 1e-9) - 1) * 100, 3),
            })
            break

    # dedupe overlapping zones (keep the strongest departure)
    out.sort(key=lambda z: (-z["strength"], -z["index"]))
    kept: list[dict] = []
    for z in out:
        overlap = any(
            not (z["top"] < k["bottom"] or z["bottom"] > k["top"]) for k in kept
        )
        if not overlap:
            kept.append(z)
    price = _f(items[-1], "c")
    kept.sort(key=lambda z: abs((z["top"] + z["bottom"]) / 2 - price))
    return kept[:8]


# ------------------------------------------------------------------ Liquidity map
def liquidity_map(items: list[dict], report: dict | None, atr: float) -> dict:
    """Resting-liquidity pools + Draw-On-Liquidity (the magnet price is most
    likely to raid next, given the deterministic bias)."""
    pools: list[dict] = []
    if len(items) < 10 or atr <= 0:
        return {"pools": [], "dol": None}
    n = len(items)
    price = _f(items[-1], "c")
    highs, lows = _swings(items, 2)

    eq = ict_engine.equal_levels(items, 2)
    for lvl in eq.get("eqh") or []:
        pools.append({"kind": "eqh", "side": "buy", "price": lvl.get("price"),
                      "index": lvl.get("index"), "count": lvl.get("count", 2)})
    for lvl in eq.get("eql") or []:
        pools.append({"kind": "eql", "side": "sell", "price": lvl.get("price"),
                      "index": lvl.get("index"), "count": lvl.get("count", 2)})

    # PDH / PDL — previous UTC-day extremes from real candle timestamps
    try:
        days: dict[int, dict] = {}
        for idx, it in enumerate(items):
            t = _f(it, "t")
            if t <= 0:
                continue
            day = int(t // 86400)
            slot = days.setdefault(day, {"high": -1e18, "low": 1e18, "index": idx})
            slot["high"] = max(slot["high"], _f(it, "h"))
            slot["low"] = min(slot["low"], _f(it, "l"))
            slot["index"] = idx
        ordered_days = sorted(days.items())
        if len(ordered_days) >= 2 and (ordered_days[-1][1]["high"] - ordered_days[-1][1]["low"]) < 60 * atr * 24:
            prev = ordered_days[-2][1]
            pools.append({"kind": "pdh", "side": "buy", "price": _r(prev["high"]),
                          "index": prev["index"], "count": 1})
            pools.append({"kind": "pdl", "side": "sell", "price": _r(prev["low"]),
                          "index": prev["index"], "count": 1})
    except Exception:
        pass

    # major untested swing pools (last 3 each side)
    for j in highs[-3:]:
        pools.append({"kind": "swing_high", "side": "buy", "price": _r(_f(items[j], "h")),
                      "index": j, "count": 1})
    for j in lows[-3:]:
        pools.append({"kind": "swing_low", "side": "sell", "price": _r(_f(items[j], "l")),
                      "index": j, "count": 1})

    tol = atr * 0.15
    for pool in pools:
        p = float(pool.get("price") or 0)
        idx = int(pool.get("index") or 0)
        pool["distance_pct"] = _r((p / max(price, 1e-9) - 1) * 100, 3)
        pool["swept"] = any(
            (_f(items[j], "h") > p + tol) if pool["side"] == "buy" else (_f(items[j], "l") < p - tol)
            for j in range(idx + 2, n)
        )

    pools.sort(key=lambda z: abs(z.get("distance_pct") or 0))
    pools = pools[:8]

    bias = str((report or {}).get("bias") or "neutral").lower()
    want_side = "buy" if "bull" in bias else "sell" if "bear" in bias else None
    candidates = [p for p in pools if not p["swept"]]
    dol = None
    if want_side:
        directional = [
            p for p in candidates
            if p["side"] == want_side
            and ((p.get("price") or 0) > price if want_side == "buy" else (p.get("price") or 0) < price)
        ]
        if directional:
            dol = min(directional, key=lambda p: abs(p.get("distance_pct") or 999))
    if dol is None and candidates:
        dol = min(candidates, key=lambda p: abs(p.get("distance_pct") or 999))
    dol_out = None
    if dol:
        kind_fa = {"eqh": "سقف‌های برابر (EQH)", "eql": "کف‌های برابر (EQL)",
                   "pdh": "سقف روز قبل", "pdl": "کف روز قبل",
                   "swing_high": "سقف سوئینگ", "swing_low": "کف سوئینگ"}.get(dol["kind"], dol["kind"])
        dol_out = {
            "kind": dol["kind"],
            "side": dol["side"],
            "target": dol["price"],
            "distance_pct": dol["distance_pct"],
            "rationale_fa": f"نقدینگیِ هدف (Draw-On-Liquidity): {kind_fa} در {dol['price']} — نزدیک‌ترین استخر نقدینگی دست‌نخورده در جهت بایاس قطعی.",
        }
    return {"pools": pools, "dol": dol_out}


# ---------------------------------------------------------------------- summarize
def summarize(items: list[dict], report: dict | None = None) -> dict:
    """Single entry point — pure deterministic RTM dossier for the report."""
    empty = {
        "available": False, "qml": [], "ftr": [], "flags": [], "compression": [],
        "supply_demand": [], "liquidity": {"pools": [], "dol": None},
        "points_bull": 0, "points_bear": 0, "summary_fa": "داده کافی برای تحلیل RTM نیست.",
    }
    if not items or len(items) < _MIN_CANDLES:
        return empty
    atr = _atr(items)
    if atr <= 0:
        return empty
    price = _f(items[-1], "c")

    qml = qml_levels(items, atr)
    ftr = ftr_zones(items, atr)
    flags = flags_mpl(items, atr)
    comp = compression(items, atr)
    sd = supply_demand_zones(items, atr)
    liq = liquidity_map(items, report, atr)

    active_qml = [z for z in qml if not z["mitigated"]]
    active_ftr = [z for z in ftr if not z["mitigated"]]
    points_bull = sum(1 for z in active_qml if z["kind"] == "qml_bull" and (z.get("distance_pct") or 0) < 0)
    points_bull += sum(1 for z in active_qml if z["kind"] == "qml_bear" and abs(z.get("distance_pct") or 0) < 3)
    points_bull += sum(1 for z in active_ftr if z["kind"] == "ftr_bull")
    points_bull += sum(1 for z in comp if z["kind"] == "compression_bull")
    points_bull += sum(1 for z in flags if z["kind"] == "flag_bull" and z.get("sweep_reclaimed"))
    points_bull += sum(1 for z in sd if z["side"] == "bullish" and z["fresh"] and (z.get("distance_pct") or 99) < 0 and abs(z.get("distance_pct") or 99) < 3)
    points_bear = sum(1 for z in active_qml if z["kind"] == "qml_bear" and (z.get("distance_pct") or 0) > 0)
    points_bear += sum(1 for z in active_qml if z["kind"] == "qml_bull" and abs(z.get("distance_pct") or 0) < 3)
    points_bear += sum(1 for z in active_ftr if z["kind"] == "ftr_bear")
    points_bear += sum(1 for z in comp if z["kind"] == "compression_bear")
    points_bear += sum(1 for z in flags if z["kind"] == "flag_bear" and z.get("sweep_reclaimed"))
    points_bear += sum(1 for z in sd if z["side"] == "bearish" and z["fresh"] and (z.get("distance_pct") or -99) > 0 and abs(z.get("distance_pct") or -99) < 3)

    notes: list[str] = []
    dol = (liq or {}).get("dol")
    if dol:
        notes.append(f"هدف نقدینگی: {dol['kind']} @ {dol['target']} ({dol['distance_pct']}%)")
    if active_qml:
        notes.append(f"QML فعال {'نزولی' if active_qml[0]['kind'] == 'qml_bear' else 'صعودی'} @ {active_qml[0]['price']}")
    if active_ftr:
        notes.append(f"FTR {'صعودی' if active_ftr[0]['kind'] == 'ftr_bull' else 'نزولی'} با قدرت {active_ftr[0]['strength']}ATR")
    if comp:
        notes.append(f"فشرده‌سازی به سمت {comp[0]['target']}")
    if sd:
        notes.append(f"نزدیک‌ترین زون عرضه/تقاضا: {sd[0]['kind']} @ {sd[0]['price']} (تازگی: {'تازه' if sd[0]['fresh'] else f"{sd[0]['touches']} لمس"})")

    return {
        "available": True,
        "last_index": len(items) - 1,
        "qml": qml,
        "ftr": ftr,
        "flags": flags,
        "compression": comp,
        "supply_demand": sd,
        "liquidity": liq,
        "points_bull": int(points_bull),
        "points_bear": int(points_bear),
        "summary_fa": " | ".join(notes) if notes else "سیگنال RTM فعالی در نگاه‌بک جاری نیست.",
    }


def overlay_items(summary: dict | None) -> dict:
    """Chart overlay entries (lines/zones/labels) so the existing Android
    renderer shows RTM levels with zero client changes."""
    lines: list[dict] = []
    zones: list[dict] = []
    labels: list[dict] = []
    if not summary or not summary.get("available"):
        return {"lines": lines, "zones": zones, "labels": labels}

    for z in summary.get("qml") or []:
        if z.get("mitigated"):
            continue
        lines.append({
            "kind": "QML", "price": z["price"], "index": z["index"],
            "label": "QML نزولی" if z["kind"] == "qml_bear" else "QML صعودی",
            "color": "#f59e0b", "style": "dashed",
        })
    for f in summary.get("flags") or []:
        lines.append({
            "kind": "MPL", "price": f["mpl"], "index": f["index"],
            "label": "MPL پرچم", "color": "#8b5cf6", "style": "dotted",
        })
    dol = (summary.get("liquidity") or {}).get("dol")
    if dol and dol.get("target"):
        lines.append({
            "kind": "DOL", "price": dol["target"], "index": int(summary.get("last_index") or 0),
            "label": "هدف نقدینگی", "color": "#38bdf8", "style": "dashed",
        })
    for z in summary.get("supply_demand") or []:
        if z.get("mitigated"):
            continue
        zones.append({
            "kind": "SD",
            "side": z["side"],
            "top": z["top"], "bottom": z["bottom"], "index": z["index"],
            "quality": z.get("quality", 1), "fresh": z.get("fresh", False),
            "label": f"{'تقاضا' if z['side'] == 'bullish' else 'عرضه'} {z['kind']}",
            "color": "#10b981" if z["side"] == "bullish" else "#ef4444",
        })
    return {"lines": lines[:6], "zones": zones[:6], "labels": labels}
