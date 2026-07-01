from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from app.models import ImpactLevel, NewsEvent


def evaluate_news_risk(news: Iterable[NewsEvent], now_utc: datetime | None = None) -> dict:
    now_utc = now_utc or datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)

    blocked = False
    score = 10.0
    warnings: list[str] = []

    for event in news:
        start = event.event_time - timedelta(minutes=event.minutes_buffer_before)
        end = event.event_time + timedelta(minutes=event.minutes_buffer_after)
        if start <= now_utc <= end:
            if event.impact == ImpactLevel.high:
                blocked = True
                score = 0.0
                warnings.append(f"High impact news active: {event.title}")
            elif event.impact == ImpactLevel.medium:
                score = min(score, 4.0)
                warnings.append(f"Medium impact news near market: {event.title}")
            else:
                score = min(score, 7.0)
                warnings.append(f"Low impact news near market: {event.title}")

    return {"blocked": blocked, "score": score, "warnings": warnings}


def mock_news(market: str) -> list[dict]:
    now = datetime.now(timezone.utc)
    return [
        {
            "title": "US CPI Release",
            "currency": "USD",
            "impact": "high",
            "event_time": (now + timedelta(hours=2)).isoformat(),
            "minutes_buffer_before": 45,
            "minutes_buffer_after": 45,
            "market": market,
        },
        {
            "title": "ECB Speech",
            "currency": "EUR",
            "impact": "medium",
            "event_time": (now + timedelta(hours=5)).isoformat(),
            "minutes_buffer_before": 20,
            "minutes_buffer_after": 20,
            "market": market,
        },
    ]
