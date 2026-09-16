"""Trade cost & geometry gate — v3.20 (audit-driven, deterministic, no look-ahead).

Audit finding (2026-09-16, post-fee walk-forward on real OKX data): the single
biggest destroyer of expectancy was NOT direction quality — it was trade
geometry. Many pack/plans carry stops of 0.05-0.30% of price; at a 0.05%/side
taker fee the round trip alone costs 0.3R-3.7R, turning every -1R stop-loss
into a -2R..-5R loss. Measured: raw pack -616.9R over 1881 trades post-fee.

Pre-registered rules (fixed BEFORE measuring the effect; see commit message):
  1. fee_r  = (fee_pct/100) * (entry + exit_ref) / risk  <= MAX_FEE_R
     round-trip cost expressed in R. exit_ref = tp when known else entry.
  2. risk >= MIN_RISK_ATR * ATR(14)          stop inside the noise band = hunt bait
  3. net_rr = |tp - entry| / risk - fee_r >= MIN_NET_RR   (when tp known)

A plan that fails is not "wrong direction" — it is untradable geometry: even a
correct call loses money after costs. The live strict engine and both backtest
replayers apply the exact same gate so replayed numbers match live behaviour.
"""
from __future__ import annotations

from typing import Any

DEFAULT_FEE_PCT = 0.05     # per side, OKX taker
MAX_FEE_R = 0.30           # round-trip fee must not exceed 0.30R
MIN_RISK_ATR = 0.35        # stop distance floor, multiples of ATR(14)
MIN_NET_RR = 1.5           # fee-adjusted reward:risk floor


def atr14(candles: list[dict] | None) -> float | None:
    """Plain ATR(14) from ascending OHLC dicts; None when data is too short."""
    if not candles or len(candles) < 15:
        return None
    trs: list[float] = []
    prev_close: float | None = None
    for bar in candles[-15:]:
        try:
            h = float(bar.get("h") or bar.get("high") or 0)
            l = float(bar.get("l") or bar.get("low") or 0)
            c = float(bar.get("c") or bar.get("close") or 0)
        except (TypeError, ValueError):
            return None
        if h <= 0 or l <= 0 or c <= 0:
            return None
        tr = h - l if prev_close is None else max(h - l, abs(h - prev_close), abs(l - prev_close))
        trs.append(tr)
        prev_close = c
    if len(trs) < 14:
        return None
    return sum(trs[-14:]) / 14.0


def evaluate(
    entry: Any,
    sl: Any,
    tp: Any = None,
    direction: str = "",
    fee_pct: float = DEFAULT_FEE_PCT,
    atr: float | None = None,
    max_fee_r: float = MAX_FEE_R,
    min_risk_atr: float = MIN_RISK_ATR,
    min_net_rr: float = MIN_NET_RR,
) -> dict:
    """Deterministic pass/fail for one plan's cost geometry.

    Returns {"applicable": bool, "passed": bool, ...metrics, "reasons_fa": [...]}.
    applicable=False (pass-through) when the plan lacks entry/sl — plan
    existence is enforced by other gates, not here.
    """
    out: dict = {
        "applicable": False, "passed": True, "fee_pct": fee_pct,
        "max_fee_r": max_fee_r, "min_risk_atr": min_risk_atr, "min_net_rr": min_net_rr,
        "fee_r": None, "risk": None, "risk_pct": None, "net_rr": None, "reasons_fa": [],
    }
    try:
        entry_f = float(entry or 0)
        sl_f = float(sl or 0)
    except (TypeError, ValueError):
        return out
    if entry_f <= 0 or sl_f <= 0:
        return out
    if direction not in ("long", "short"):
        direction = "long" if sl_f < entry_f else "short"
    risk = abs(entry_f - sl_f)
    if risk <= 0:
        return out
    if direction == "long" and sl_f >= entry_f:
        return out
    if direction == "short" and sl_f <= entry_f:
        return out

    out["applicable"] = True
    out["risk"] = round(risk, 8)
    out["risk_pct"] = round(100.0 * risk / entry_f, 4)

    try:
        tp_f = float(tp) if tp else None
    except (TypeError, ValueError):
        tp_f = None
    exit_ref = tp_f if (tp_f and tp_f > 0) else entry_f
    fee_r = (float(fee_pct) / 100.0) * (entry_f + exit_ref) / risk
    out["fee_r"] = round(fee_r, 3)

    net_rr: float | None = None
    if tp_f and tp_f > 0:
        gross = abs(tp_f - entry_f) / risk
        net_rr = gross - fee_r
        out["net_rr"] = round(net_rr, 3)

    reasons: list[str] = []
    if fee_r > max_fee_r:
        reasons.append(
            f"کارمزد رفت‌وبرگشت {fee_r:.2f}R از ریسک است (حداکثر {max_fee_r:.2f}R) — "
            f"فاصله استاپ فقط {out['risk_pct']:.3f}% قیمت است"
        )
    if atr and atr > 0 and risk < min_risk_atr * float(atr):
        reasons.append(
            f"استاپ ({risk:.6g}) کوچک‌تر از {min_risk_atr:g}×ATR ({min_risk_atr * float(atr):.6g}) است — "
            "داخل نویز بازار، طعمه استاپ‌هانت"
        )
    if net_rr is not None and net_rr < min_net_rr:
        reasons.append(
            f"RR خالص پس از کارمزد {net_rr:.2f} کمتر از {min_net_rr:g} است"
        )
    out["reasons_fa"] = reasons
    out["passed"] = not reasons
    return out
