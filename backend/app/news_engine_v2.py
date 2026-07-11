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

from .news_fallback import build_offline_brief

async def build_news_brief():
    # Try Finnhub live first; if not configured or key invalid, fall back to Persian calendar
    if FINNHUB_AVAILABLE:
        try:
            fh = get_finnhub()
            if fh and fh.is_configured:
                from datetime import datetime, timezone
                import asyncio
                try:
                    cal = await fh.get_economic_calendar()
                    h1 = await fh.get_general_news("general")
                    # Finnhub returns list even with invalid key; but invalid key returns {"error":"Invalid API key"}
                    if isinstance(cal, dict) and cal.get("error"):
                        raise RuntimeError(cal["error"])
                    if isinstance(h1, dict) and h1.get("error"):
                        raise RuntimeError(h1["error"])
                    now = datetime.now(timezone.utc)
                    return {
                        "finnhub_configured": True,
                        "server_time_unix": int(now.timestamp()),
                        "server_time_iso": now.isoformat(),
                        "block": {"blocked": False, "reasons": [], "block_until": 0, "active_events": []},
                        "adjustment": {"bias": "neutral", "score_penalty": 0, "note": "اخبار زنده فین‌هاب."},
                        "events": {"upcoming": (cal or [])[:20], "live": [], "past": []},
                        "headlines": (h1 or [])[:20],
                        "source": "finnhub",
                    }
                except Exception as inner:
                    logger.warning(f"Finnhub fetch failed, falling back: {inner}")
        except Exception as e:
            logger.warning(f"Finnhub init failed: {e}")
    # Fallback
    return build_offline_brief()
