"""SMT (Smart Money Technique) divergence engine — fully deterministic.

Compares two correlated instruments candle-by-candle (aligned by timestamp)
and detects classic ICT SMT divergences at fractal swing points:

- bearish SMT: one leg prints a higher high while the correlated leg fails
  to follow (lower high) -> distribution / relative weakness of the laggard.
- bullish SMT: one leg prints a lower low while the correlated leg refuses
  (higher low) -> accumulation / relative strength of the laggard.

Pearson correlation of close-to-close returns is reported too, so the AI and
the user can judge whether the pair is correlated enough for SMT to mean
anything. Everything is computed from real completed candles — no speculation.
"""
from __future__ import annotations

from typing import Any

MIN_CORRELATION = 0.5      # below this |r| the pair is not reliable for SMT
DEFAULT_MIN_MOVE_PCT = 0.05  # 5 bps: minimum swing progression to count


def _r(value: float | None, digits: int = 6) -> Any:
    return round(value, digits) if value is not None else None


def align_series(items_a: list[dict], items_b: list[dict]) -> tuple[list[dict], list[dict]]:
    """Inner-join two candle lists on their unix timestamp."""
    if not items_a or not items_b:
        return [], []
    index_b: dict[int, dict] = {}
    for item in items_b:
        try:
            index_b[int(float(item["t"]))] = item
        except (KeyError, TypeError, ValueError):
            continue
    a: list[dict] = []
    b: list[dict] = []
    for item in items_a:
        try:
            key = int(float(item["t"]))
        except (KeyError, TypeError, ValueError):
            continue
        match = index_b.get(key)
        if match is not None:
            a.append(item)
            b.append(match)
    return a, b


def returns_correlation(items_a: list[dict], items_b: list[dict], window: int = 60) -> float | None:
    """Pearson r of per-candle close returns over the last `window` candles."""
    closes_a = [float(it["c"]) for it in items_a][-window:]
    closes_b = [float(it["c"]) for it in items_b][-window:]
    n = min(len(closes_a), len(closes_b))
    if n < 10:
        return None
    closes_a, closes_b = closes_a[-n:], closes_b[-n:]
    ret_a = [
        (closes_a[i] - closes_a[i - 1]) / closes_a[i - 1]
        for i in range(1, n) if closes_a[i - 1] > 0
    ]
    ret_b = [
        (closes_b[i] - closes_b[i - 1]) / closes_b[i - 1]
        for i in range(1, n) if closes_b[i - 1] > 0
    ]
    m = min(len(ret_a), len(ret_b))
    if m < 9:
        return None
    ret_a, ret_b = ret_a[-m:], ret_b[-m:]
    mean_a = sum(ret_a) / m
    mean_b = sum(ret_b) / m
    cov = sum((ret_a[i] - mean_a) * (ret_b[i] - mean_b) for i in range(m))
    var_a = sum((x - mean_a) ** 2 for x in ret_a)
    var_b = sum((x - mean_b) ** 2 for x in ret_b)
    if var_a <= 0 or var_b <= 0:
        return None
    return cov / ((var_a ** 0.5) * (var_b ** 0.5))


def _swings(items: list[dict], k: int = 2) -> tuple[list[int], list[int]]:
    """Fractal swing high/low indices (same rule as ict_engine.swing_points)."""
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


def _match_swings(idx_a: list[int], idx_b: list[int], tol: int) -> list[tuple[int, int]]:
    """Pair swing indices of the two series that happen at (nearly) the same time."""
    pairs: list[tuple[int, int]] = []
    used_b: set[int] = set()
    for ia in idx_a:
        best = None
        for ib in idx_b:
            if ib in used_b:
                continue
            if abs(ia - ib) <= tol:
                if best is None or abs(ia - ib) < abs(ia - best):
                    best = ib
        if best is not None:
            used_b.add(best)
            pairs.append((ia, best))
    return pairs


def _progression(items: list[dict], pairs: list[tuple[int, int]], key: str) -> list[dict]:
    """Consecutive matched-swing progressions: (prev, new) level pairs."""
    rows: list[dict] = []
    for (ia1, ib1), (ia2, ib2) in zip(pairs, pairs[1:]):
        if ia2 <= ia1 or ib2 <= ib1:
            continue
        a1 = float(items[ia1][key])
        a2 = float(items[ia2][key])
        rows.append({"index": ia2, "time": items[ia2].get("t"), "prev": a1, "new": a2})
    return rows


def detect_smt(
    items_a: list[dict],
    items_b: list[dict],
    symbol_a: str = "A",
    symbol_b: str = "B",
    k: int = 2,
    min_move_pct: float = DEFAULT_MIN_MOVE_PCT,
    max_lookback_pairs: int = 6,
) -> dict:
    """Detect SMT divergences between primary (A) and correlated (B) series.

    Returns a deterministic payload; `available=False` when there is not
    enough aligned data. Never raises for bad input.
    """
    aligned_a, aligned_b = align_series(items_a, items_b)
    if len(aligned_a) < max(30, 4 * k + 6):
        return {
            "available": False,
            "primary": symbol_a,
            "correlated": symbol_b,
            "aligned_candles": len(aligned_a),
            "reason": "insufficient_aligned_candles",
        }

    corr = returns_correlation(aligned_a, aligned_b)
    corr_reliable = bool(corr is not None and abs(corr) >= MIN_CORRELATION)

    highs_a, lows_a = _swings(aligned_a, k)
    highs_b, lows_b = _swings(aligned_b, k)
    tol = k + 1

    divergences: list[dict] = []

    def scan(pairs: list[tuple[int, int]], key: str, kind_high: bool) -> None:
        prog_a = _progression(aligned_a, pairs, key)
        # progression of B at the same matched indices
        prog_b: list[dict] = []
        for (ia1, ib1), (ia2, ib2) in zip(pairs, pairs[1:]):
            if ia2 <= ia1 or ib2 <= ib1:
                continue
            prog_b.append({
                "index": ib2,
                "time": aligned_b[ib2].get("t"),
                "prev": float(aligned_b[ib1][key]),
                "new": float(aligned_b[ib2][key]),
            })
        for pa, pb in zip(prog_a, prog_b):
            if pa["index"] != pb["index"] and abs(pa["index"] - pb["index"]) > tol:
                continue
            move_a = (pa["new"] - pa["prev"]) / pa["prev"] * 100 if pa["prev"] else 0.0
            move_b = (pb["new"] - pb["prev"]) / pb["prev"] * 100 if pb["prev"] else 0.0
            if kind_high:
                # higher-high vs lower-high mismatch
                if move_a >= min_move_pct and move_b <= -min_move_pct:
                    strong, weak = symbol_a, symbol_b
                    sl, wl = (pa, pb)
                elif move_b >= min_move_pct and move_a <= -min_move_pct:
                    strong, weak = symbol_b, symbol_a
                    sl, wl = (pb, pa)
                else:
                    continue
                divergences.append({
                    "kind": "smt_bearish",
                    "side": "high",
                    "index": pa["index"],
                    "time": pa["time"],
                    "strong": strong,
                    "weak": weak,
                    "strong_levels": {"prev": _r(sl["prev"]), "new": _r(sl["new"])},
                    "weak_levels": {"prev": _r(wl["prev"]), "new": _r(wl["new"])},
                })
            else:
                # lower-low vs higher-low mismatch
                if move_a <= -min_move_pct and move_b >= min_move_pct:
                    strong, weak = symbol_b, symbol_a  # B refused the low = strong
                    sl, wl = (pb, pa)
                elif move_b <= -min_move_pct and move_a >= min_move_pct:
                    strong, weak = symbol_a, symbol_b
                    sl, wl = (pa, pb)
                else:
                    continue
                divergences.append({
                    "kind": "smt_bullish",
                    "side": "low",
                    "index": pa["index"],
                    "time": pa["time"],
                    "strong": strong,
                    "weak": weak,
                    "strong_levels": {"prev": _r(sl["prev"]), "new": _r(sl["new"])},
                    "weak_levels": {"prev": _r(wl["prev"]), "new": _r(wl["new"])},
                })

    high_pairs = _match_swings(highs_a[-max_lookback_pairs:], highs_b[-max_lookback_pairs:], tol)
    low_pairs = _match_swings(lows_a[-max_lookback_pairs:], lows_b[-max_lookback_pairs:], tol)
    scan(high_pairs, "h", True)
    scan(low_pairs, "l", False)

    # keep the most recent 4, unique by (kind, index)
    unique: dict[tuple, dict] = {}
    for row in divergences:
        unique[(row["kind"], row["index"])] = row
    divergences = sorted(unique.values(), key=lambda row: row["index"])[-4:]

    score = 0
    for row in divergences[-3:]:
        if row["kind"] == "smt_bullish":
            score += 2
        else:
            score -= 2
    score = max(-6, min(6, score))

    summary = _summary_fa(symbol_a, symbol_b, corr, corr_reliable, divergences)
    return {
        "available": True,
        "primary": symbol_a,
        "correlated": symbol_b,
        "aligned_candles": len(aligned_a),
        "correlation": _r(corr, 4) if corr is not None else None,
        "correlation_reliable": corr_reliable,
        "divergences": divergences,
        "score": score,
        "summary_fa": summary,
    }


def _summary_fa(
    symbol_a: str,
    symbol_b: str,
    corr: float | None,
    corr_reliable: bool,
    divergences: list[dict],
) -> str:
    corr_txt = f"{corr:.2f}" if corr is not None else "نامعلوم"
    if not divergences:
        base = f"SMT در برابر {symbol_b}: همبستگی {corr_txt} — واگرایی SMT اخیر یافت نشد (حرکت هم‌راستا)."
    else:
        last = divergences[-1]
        kind_fa = "صعودی (تجمع/اکومولیشن)" if last["kind"] == "smt_bullish" else "نزولی (توزیع/دیستریبیوشن)"
        side_fa = "سقف بالاتر (HH)" if last["side"] == "high" else "کف پایین‌تر (LL)"
        base = (
            f"SMT در برابر {symbol_b}: همبستگی {corr_txt} — آخرین واگرایی {kind_fa}؛ "
            f"{last['strong']} روی {side_fa} عمل کرد ولی {last['weak']} ناتوان ماند "
            f"(قدرت نسبی: {last['strong']}). تعداد واگرایی‌های اخیر: {len(divergences)}."
        )
    if not corr_reliable:
        base += " ⚠️ همبستگی زوج زیر آستانه اطمینان است؛ واگرایی SMT اعتبار نهادی ندارد."
    return base
