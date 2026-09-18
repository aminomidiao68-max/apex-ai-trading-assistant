"""v3.25 WEEKLY-GRADE precision windows & deterministic market-state helpers.

Pure functions of candles/time only — no randomness, no model calls. The point
of this module is scarcity: a signal must arrive inside an institutional
session window, on a decisive confirmed candle, in an efficiently moving and
normally volatile market. Outside those conditions even a perfect setup stays
NO_TRADE, because "no signal beats a wrong signal".
"""
from __future__ import annotations

from datetime import datetime, timezone
from statistics import median

# v3.26 ZERO-ERROR: ONLY the London/NY overlap (12:00-16:59 UTC) remains —
# the single most liquid, most institutionally participative window of the day.
# v3.25 also allowed London AM; that exception is retired.
KILLZONE_UTC_WINDOWS = ((12, 16),)

# ATR% (median true range / price) bands per market family. Dead markets and
# wild markets both destroy execution quality, so both are rejected.
VOLATILITY_BANDS = {
    "crypto": (0.003, 0.025),
    "forex": (0.0008, 0.010),
    "fx": (0.0008, 0.010),
    "indices": (0.001, 0.015),
    "index": (0.001, 0.015),
    "metals": (0.001, 0.015),
    "metal": (0.001, 0.015),
}
DEFAULT_BAND = (0.0012, 0.025)

MIN_EFFICIENCY_RATIO = 0.30  # v3.26 (was 0.25): Kaufman ER over last 100 closes


def in_killzone(now_utc: datetime | None = None) -> bool:
    now = now_utc or datetime.now(timezone.utc)
    return any(start <= now.hour <= end for start, end in KILLZONE_UTC_WINDOWS)


def is_liquidity_weekday(now_utc: datetime | None = None) -> bool:
    """v3.28: Mon-Fri only. Weekend crypto liquidity is thin retail flow with
    widened spreads and absent institutional participation; forex is closed."""
    now = now_utc or datetime.now(timezone.utc)
    return now.weekday() <= 4


def week_key(now_utc: datetime | None = None) -> str:
    now = now_utc or datetime.now(timezone.utc)
    year, week, _ = now.isocalendar()
    return f"{year}-W{week:02d}"


def _true_ranges(candles: list[dict], lookback: int = 100) -> list[float]:
    rows = candles[-(lookback + 1):]
    out = []
    for i in range(1, len(rows)):
        high = float(rows[i]["h"]); low = float(rows[i]["l"]); pc = float(rows[i - 1]["c"])
        out.append(max(high - low, abs(high - pc), abs(low - pc)))
    return out


def atr_pct(candles: list[dict]) -> float:
    if len(candles) < 3:
        return 0.0
    trs = _true_ranges(candles)
    if not trs:
        return 0.0
    return median(trs) / float(candles[-1]["c"]) if float(candles[-1]["c"]) else 0.0


def in_volatility_band(candles: list[dict], market: str) -> tuple[bool, float]:
    value = atr_pct(candles)
    low, high = VOLATILITY_BANDS.get(str(market).lower(), DEFAULT_BAND)
    return (low <= value <= high), value


def efficiency_ratio(candles: list[dict], lookback: int = 100) -> float:
    closes = [float(item["c"]) for item in candles[-(lookback + 1):]]
    if len(closes) < 10:
        return 0.0
    path = sum(abs(closes[i] - closes[i - 1]) for i in range(1, len(closes)))
    if not path:
        return 0.0
    return abs(closes[-1] - closes[0]) / path


def confirmation_close_ok(candles: list[dict], direction: str) -> tuple[bool, dict]:
    """Last CLOSED candle must be decisive in the trade direction.

    long : body up, body >= 50% of range, close ABOVE previous high (engulfing)
    short: mirror. v3.26 ZERO-ERROR: mere directional close is not enough —
    the confirmation candle must consume the previous candle's range.
    """
    detail = {"direction": direction, "ok": False}
    if len(candles) < 2 or direction not in ("long", "short"):
        return False, detail
    last = candles[-1]; prev = candles[-2]
    o, h, l, c = (float(last[k]) for k in ("o", "h", "l", "c"))
    pc = float(prev["c"])
    rng = h - l
    body = abs(c - o)
    decisive = rng > 0 and body >= 0.50 * rng
    prev_high = float(prev["h"]); prev_low = float(prev["l"])
    if direction == "long":
        ok = c > o and decisive and c > prev_high
    else:
        ok = c < o and decisive and c < prev_low
    detail = {"direction": direction, "ok": ok, "body_ratio": round(body / rng, 3) if rng else 0.0,
              "close_vs_prev": round(c - pc, 6),
              "engulfing": bool(c > prev_high if direction == "long" else c < prev_low)}
    return ok, detail


def atr_value(candles: list[dict], lookback: int = 100) -> float:
    trs = _true_ranges(candles, lookback)
    return median(trs) if trs else 0.0
