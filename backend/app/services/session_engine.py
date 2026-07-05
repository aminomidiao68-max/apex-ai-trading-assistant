from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def evaluate_session(now_utc: datetime | None = None) -> dict:
    now_utc = now_utc or datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)

    london_time = now_utc.astimezone(ZoneInfo("Europe/London"))
    new_york_time = now_utc.astimezone(ZoneInfo("America/New_York"))

    london_open = 8 <= london_time.hour < 17
    new_york_open = 8 <= new_york_time.hour < 17
    overlap = london_open and new_york_open

    if overlap:
        return {
            "session_name": "London-New York Overlap",
            "quality": "high",
            "score": 10.0,
        }
    if london_open:
        return {"session_name": "London", "quality": "high", "score": 8.0}
    if new_york_open:
        return {"session_name": "New York", "quality": "high", "score": 8.0}
    return {"session_name": "Off Session", "quality": "low", "score": 3.0}
