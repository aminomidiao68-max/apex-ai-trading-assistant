"""v3.25 weekly scarcity governor.

Hard cap: at most MAX_WEEKLY_SIGNALS fused ACTIONABLE candidates per ISO week
per deployment, one per symbol. When the quota is consumed, even a perfect
gate stack downgrades to WATCH with an explicit Persian-friendly reason. This
is the structural implementation of "1-2 precise setups per week instead of
several risky ones per day".
"""
from __future__ import annotations

from datetime import datetime

from app.services.precision_window import week_key


class WeeklySignalQuota:
    MAX_WEEKLY_SIGNALS = 2

    def __init__(self, db) -> None:
        self._db = db

    def consumed(self, now_utc: datetime | None = None) -> int:
        key = week_key(now_utc)
        with self._db.connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM weekly_signal_quota WHERE week_key=?", (key,)
            ).fetchone()
        return int(row["n"]) if row else 0

    def remaining(self, now_utc: datetime | None = None) -> int:
        return max(0, self.MAX_WEEKLY_SIGNALS - self.consumed(now_utc))

    def try_consume(self, symbol: str, now_utc: datetime | None = None) -> tuple[bool, dict]:
        key = week_key(now_utc)
        info = {"week_key": key, "max_weekly": self.MAX_WEEKLY_SIGNALS,
                "consumed_before": self.consumed(now_utc)}
        if self.remaining(now_utc) <= 0:
            return False, {**info, "reason": "weekly_quota_exhausted"}
        with self._db.connection() as conn:
            exists = conn.execute(
                "SELECT 1 AS x FROM weekly_signal_quota WHERE week_key=? AND symbol=?",
                (key, str(symbol).upper()),
            ).fetchone()
            if exists:
                return False, {**info, "reason": "symbol_already_signaled_this_week"}
            conn.execute(
                "INSERT INTO weekly_signal_quota (week_key, symbol, consumed_at) VALUES (?,?,?)",
                (key, str(symbol).upper(), (now_utc or datetime.now()).isoformat()),
            )
            conn.commit()
        return True, {**info, "reason": "consumed", "remaining_after": self.remaining(now_utc)}
