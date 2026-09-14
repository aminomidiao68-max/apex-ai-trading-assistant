"""Deterministic proximity-alert engine.

Pure evaluation + per-process dedup/cooldown state. Zero randomness: given
the same price, ATR and level set, the output is always identical.

Levels come from the deterministic pipeline only (numbered liquidity pools,
FVG edges, EQH/EQL, volume-profile POC/VAH/VAL and real L2 walls). The
service never invents levels — it measures distance to what already exists.

Thresholds are ATR-adaptive with hard floors:
  warning  = max(min_warn_pct, warn_mult * ATR%)
  critical = max(min_crit_pct, crit_mult * ATR%)
A level re-arms only after price moves away beyond REARM_FACTOR * warning
(hysteresis), so a symbol hovering at a level cannot spam alerts.
"""
from __future__ import annotations

import time as _time
from typing import Any

DEFAULT_COOLDOWN_S = 600.0
REARM_FACTOR = 2.0
DEFAULT_WARN_PCT = 0.25
DEFAULT_CRIT_PCT = 0.10
DEFAULT_WARN_MULT = 0.5   # x ATR%
DEFAULT_CRIT_MULT = 0.25  # x ATR%

KIND_FA = {
    "liquidity": "نقدینگی شماره‌دار",
    "fvg_edge": "لبه گپ FVG",
    "eqh": "سقف برابر (EQH)",
    "eql": "کف برابر (EQL)",
    "poc": "POC پروفایل حجم",
    "vah": "VAH (سقف ناحیه ارزش)",
    "val": "VAL (کف ناحیه ارزش)",
    "l2_bid_wall": "دیوار خرید L2",
    "l2_ask_wall": "دیوار فروش L2",
    "order_block": "اوردر بلاک",
}


def atr_percent(items: list[dict], period: int = 14) -> float | None:
    """ATR(period) as a percentage of the latest close. None when impossible."""
    n = len(items)
    if n < period + 1 or period <= 0:
        return None
    trs: list[float] = []
    for i in range(1, n):
        try:
            h = float(items[i]["h"])
            l = float(items[i]["l"])
            pc = float(items[i - 1]["c"])
        except (KeyError, TypeError, ValueError):
            continue
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    if len(trs) < period:
        return None
    atr = sum(trs[-period:]) / period
    close = float(items[-1]["c"])
    if close <= 0:
        return None
    return atr / close * 100.0


def evaluate_levels(
    price: float,
    atr_pct: float | None,
    levels: list[dict],
    warn_mult: float = DEFAULT_WARN_MULT,
    crit_mult: float = DEFAULT_CRIT_MULT,
    min_warn_pct: float = DEFAULT_WARN_PCT,
    min_crit_pct: float = DEFAULT_CRIT_PCT,
) -> list[dict]:
    """Measure every level against the price.

    Returns one row per valid level (sorted by distance) with:
      distance_pct, side, severity ("critical"/"warning"/None), in_range.
    Rows outside the warning threshold are kept (in_range=False) so the
    caller can build "nearest levels" views and re-arm hysteresis.
    """
    rows: list[dict] = []
    if price is None or price <= 0 or not levels:
        return rows
    warn_thr = max(min_warn_pct, warn_mult * float(atr_pct or 0.0))
    crit_thr = max(min_crit_pct, crit_mult * float(atr_pct or 0.0))
    crit_thr = min(crit_thr, warn_thr)
    seen: set[tuple[str, float]] = set()
    for level in levels:
        try:
            lp = float(level.get("price"))
        except (TypeError, ValueError):
            continue
        if lp <= 0:
            continue
        kind = str(level.get("kind") or "level")
        dedup_key = (kind, round(lp, 8))
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        distance = abs(price - lp) / price * 100.0
        in_range = distance <= warn_thr
        severity = None
        if in_range:
            severity = "critical" if distance <= crit_thr else "warning"
        rows.append({
            "kind": kind,
            "ref": str(level.get("label") or kind),
            "level_price": _round_sig(lp),
            "distance_pct": round(distance, 4),
            "side": "above" if lp > price else "below",
            "severity": severity,
            "in_range": in_range,
            "threshold_pct": {"warning": round(warn_thr, 4), "critical": round(crit_thr, 4)},
        })
    rows.sort(key=lambda row: row["distance_pct"])
    return rows


def _round_sig(value: float) -> float:
    if value >= 1000:
        return round(value, 2)
    if value >= 1:
        return round(value, 4)
    return round(value, 8)


def message_fa(symbol: str, row: dict) -> str:
    """Human-readable Persian alert message for one proximity row."""
    label = row.get("ref") or KIND_FA.get(row.get("kind") or "", "سطح")
    kind_fa = KIND_FA.get(row.get("kind") or "", "")
    if kind_fa and kind_fa.split(" (")[0] not in str(label):
        label = f"{label} ({kind_fa})"
    side_fa = "بالاتر از قیمت فعلی" if row.get("side") == "above" else "پایین‌تر از قیمت فعلی"
    icon = "🔴" if row.get("severity") == "critical" else "🟡"
    return (
        f"{icon} {symbol}: قیمت با {label} در {row.get('level_price'):g} "
        f"فقط {float(row.get('distance_pct') or 0):.3f}٪ فاصله دارد — {side_fa}."
    )


class ProximityAlertState:
    """Per-connection dedup/cooldown state (hysteresis re-arm)."""

    def __init__(self, cooldown_s: float = DEFAULT_COOLDOWN_S) -> None:
        self.cooldown_s = float(cooldown_s)
        self._last_fired: dict[tuple, float] = {}
        self._armed: dict[tuple, bool] = {}

    @staticmethod
    def _key(symbol: str, row: dict) -> tuple:
        return (symbol.upper(), row.get("kind"), round(float(row.get("level_price") or 0.0), 8))

    def filter_new(
        self,
        symbol: str,
        rows: list[dict],
        now: float | None = None,
    ) -> list[dict]:
        """Given ALL evaluated rows, return only rows that should fire now.

        Rows far away (> REARM_FACTOR x warning threshold) re-arm their key.
        In-range rows fire at most once per cooldown window per key.
        """
        now = _time.time() if now is None else float(now)
        fresh: list[dict] = []
        for row in rows:
            try:
                key = self._key(symbol, row)
            except (TypeError, ValueError):
                continue
            warn_thr = float((row.get("threshold_pct") or {}).get("warning") or DEFAULT_WARN_PCT)
            distance = float(row.get("distance_pct") or 0.0)
            if not row.get("in_range"):
                if distance > warn_thr * REARM_FACTOR:
                    self._armed[key] = True
                continue
            if not self._armed.get(key, True):
                continue
            last = self._last_fired.get(key)
            if last is not None and now - last < self.cooldown_s:
                continue
            self._last_fired[key] = now
            self._armed[key] = False
            fresh.append(row)
        return fresh
