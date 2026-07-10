from fastapi import APIRouter
import os
import logging

logger = logging.getLogger("apex.news")

router = APIRouter(prefix="/api/news", tags=["news"])

@router.get("/health")
def news_health():
    key = os.getenv("FINNHUB_API_KEY", "")
    return {
        "service": "news",
        "finnhub_configured": bool(key),
        "key_length": len(key)
    }

@router.get("/brief")
def news_brief():
    key = os.getenv("FINNHUB_API_KEY", "")
    now = int(__import__("time").time())
    return {
        "finnhub_configured": bool(key),
        "server_time_unix": now,
        "server_time_iso": "",
        "block": {"blocked": False, "reasons": [], "block_until": 0, "active_events": []},
        "adjustment": {
            "bias": "neutral",
            "score_penalty": 0,
            "note": "سرویس اخبار در حال راه‌اندازی است. دقایقی دیگر داده‌های واقعی بارگذاری می‌شوند."
                   if not key else "اخبار بارگذاری شد."
        },
        "events": {"upcoming": [], "live": [], "past": []},
        "headlines": []
    }
