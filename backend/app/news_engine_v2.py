from __future__ import annotations
import os, logging
logger = logging.getLogger("apex.news_engine")

FINNHUB_AVAILABLE = False
try:
    from .finnhub_client import get_finnhub
    FINNHUB_AVAILABLE = True
except Exception as e:
    logger.warning(f"Finnhub client not available: {e}")
    get_finnhub = None

async def build_news_brief():
    if not FINNHUB_AVAILABLE:
        return {
            "finnhub_configured": False,
            "server_time_unix": 0, "server_time_iso": "",
            "block": {"blocked": False, "reasons": [], "block_until": 0, "active_events": []},
            "adjustment": {"bias": "neutral", "score_penalty": 0,
                          "note": "ماژول فین‌هاب در حال بارگذاری است."},
            "events": {"upcoming": [], "live": [], "past": []},
            "headlines": []
        }
    try:
        import asyncio
        from datetime import datetime, timezone
        fh = get_finnhub()
        cal = await fh.get_economic_calendar()
        h1 = await fh.get_general_news("general")
        now = datetime.now(timezone.utc)
        return {
            "finnhub_configured": fh.is_configured,
            "server_time_unix": int(now.timestamp()),
            "server_time_iso": now.isoformat(),
            "block": {"blocked": False, "reasons": [], "block_until": 0, "active_events": []},
            "adjustment": {"bias": "neutral", "score_penalty": 0,
                          "note": "اخبار در حال بارگذاری است."},
            "events": {"upcoming": cal[:20], "live": [], "past": []},
            "headlines": (h1)[:20]
        }
    except Exception as e:
        logger.exception("news brief failed")
        return {"finnhub_configured": bool(os.getenv("FINNHUB_API_KEY")),
                "server_time_unix":0,"server_time_iso":"",
                "block":{"blocked":False,"reasons":[],"block_until":0,"active_events":[]},
                "adjustment":{"bias":"neutral","score_penalty":0,"note":f"error: {e}"},
                "events":{"upcoming":[],"live":[],"past":[]},"headlines":[]}
