"""Scale-out exit management — v3.21 (deterministic, no look-ahead).

Professional trade management, pre-registered before measuring its effect:

  Phase 1 (full size): stop at the plan's structural SL. If price reaches
  +1R first, close 50% at +1R and move the stop of the remainder to
  breakeven (entry).
  Phase 2 (half size): stop at breakeven. Remainder runs to the plan's
  target; if price returns to entry first, close at 0R (small net win from
  the first half); timeout closes at the last bar's close.

Conservative fill rules (same philosophy as the existing simulators):
  - the entry bar checks the stop-loss only;
  - same-bar ambiguity resolves against the trade: SL before +1R in phase 1,
    breakeven before target in phase 2;
  - phase 2 evaluation starts on the bar AFTER the +1R fill (we cannot know
    the intra-bar path).

Why this raises win rate honestly: a trade that moves +1R in our favour and
then retraces is a small WIN (net +0.5R minus fees) instead of a full -1R
loss. Losses keep the same -1R cap. Fee burden is unchanged (one entry
notional, two exits totalling the same notional). This is exit management —
not curve-fitting: no parameter is tuned on the measured window.
"""
from __future__ import annotations


def _bar_prices(bar: dict) -> tuple[float, float, float]:
    return float(bar["h"]), float(bar["l"]), float(bar.get("c") or bar["l"])


def simulate_scale(
    items: list[dict],
    entry_index: int,
    direction: str,
    entry: float,
    sl: float,
    target: float,
    exit_horizon: int,
    fee_pct: float,
) -> dict | None:
    """Simulate one scaled trade already triggered at `entry_index`.

    Returns a trade row compatible with the existing books:
    r = net R after fees (win when r > 0), plus `legs` detail.
    """
    risk = abs(entry - sl)
    if risk <= 0:
        return None
    sign = 1.0 if direction == "long" else -1.0
    target_r = (target - entry) * sign / risk
    if target_r <= 0:
        return None
    leg1_r = min(1.0, target_r)                 # first take-profit at +1R (or the target when < 1R)
    p1 = entry + sign * leg1_r * risk
    last_j = min(entry_index + exit_horizon, len(items) - 1)

    def fee_r_for(exits: list[tuple[float, float]]) -> float:
        """exits = [(price, weight)] — per-side fee on entry notional + exit legs."""
        if fee_pct <= 0:
            return 0.0
        total = sum(w * (entry + px) for px, w in exits)
        return (fee_pct / 100.0) * total / risk

    # --- entry bar: conservative — stop-loss only
    h, l, _c = _bar_prices(items[entry_index])
    if (direction == "long" and l <= sl) or (direction == "short" and h >= sl):
        r = -1.0 - fee_r_for([(sl, 1.0)])
        return {
            "exit_price": round(sl, 8), "exit_reason": "sl", "exit_index": entry_index,
            "bars_held": 0, "r": round(r, 3), "legs": [{"price": sl, "weight": 1.0, "r": -1.0}],
        }

    leg1_index = None
    # --- phase 1: full size, stop = sl
    for k in range(entry_index + 1, last_j + 1):
        h, l, _c = _bar_prices(items[k])
        sl_hit = (direction == "long" and l <= sl) or (direction == "short" and h >= sl)
        if sl_hit:  # conservative: SL first in any ambiguous bar
            r = -1.0 - fee_r_for([(sl, 1.0)])
            return {
                "exit_price": round(sl, 8), "exit_reason": "sl", "exit_index": k,
                "bars_held": k - entry_index, "r": round(r, 3),
                "legs": [{"price": sl, "weight": 1.0, "r": -1.0}],
            }
        leg1_hit = (direction == "long" and h >= p1) or (direction == "short" and l <= p1)
        if leg1_hit:
            leg1_index = k
            break
    if leg1_index is None:  # phase-1 timeout — close everything at the last close
        _h, _l, c = _bar_prices(items[last_j])
        r_to = (c - entry) * sign / risk
        r = r_to - fee_r_for([(c, 1.0)])
        return {
            "exit_price": round(c, 8), "exit_reason": "timeout", "exit_index": last_j,
            "bars_held": last_j - entry_index, "r": round(r, 3),
            "legs": [{"price": c, "weight": 1.0, "r": round(r_to, 3)}],
        }

    # --- phase 2: half size, stop = breakeven (entry), starts on the NEXT bar
    for k in range(leg1_index + 1, last_j + 1):
        h, l, _c = _bar_prices(items[k])
        be_hit = (direction == "long" and l <= entry) or (direction == "short" and h >= entry)
        tgt_hit = (direction == "long" and h >= target) or (direction == "short" and l <= target)
        if be_hit:  # conservative: breakeven before target in an ambiguous bar
            r = 0.5 * leg1_r - fee_r_for([(p1, 0.5), (entry, 0.5)])
            wavg = 0.5 * p1 + 0.5 * entry
            return {
                "exit_price": round(wavg, 8), "exit_reason": "scale_be", "exit_index": k,
                "bars_held": k - entry_index, "r": round(r, 3),
                "legs": [{"price": p1, "weight": 0.5, "r": leg1_r},
                         {"price": entry, "weight": 0.5, "r": 0.0}],
            }
        if tgt_hit:
            r = 0.5 * leg1_r + 0.5 * target_r - fee_r_for([(p1, 0.5), (target, 0.5)])
            wavg = 0.5 * p1 + 0.5 * target
            return {
                "exit_price": round(wavg, 8), "exit_reason": "scale_target", "exit_index": k,
                "bars_held": k - entry_index, "r": round(r, 3),
                "legs": [{"price": p1, "weight": 0.5, "r": leg1_r},
                         {"price": target, "weight": 0.5, "r": target_r}],
            }
    # phase-2 timeout — remainder closes at the last close
    _h, _l, c = _bar_prices(items[last_j])
    r_rest = (c - entry) * sign / risk
    r = 0.5 * leg1_r + 0.5 * r_rest - fee_r_for([(p1, 0.5), (c, 0.5)])
    wavg = 0.5 * p1 + 0.5 * c
    return {
        "exit_price": round(wavg, 8), "exit_reason": "scale_timeout", "exit_index": last_j,
        "bars_held": last_j - entry_index, "r": round(r, 3),
        "legs": [{"price": p1, "weight": 0.5, "r": leg1_r},
                 {"price": c, "weight": 0.5, "r": round(r_rest, 3)}],
    }
