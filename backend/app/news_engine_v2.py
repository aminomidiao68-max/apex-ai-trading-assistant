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
    if FINNHUB_AVAILABLE:
        try:
            fh = get_finnhub()
            if fh and fh.is_configured:
                from datetime import datetime, timezone
                try:
                    cal = await fh.get_economic_calendar()
                    h1 = await fh.get_general_news("general")
                    # Treat None/dict-as-error as failure
                    cal_ok = isinstance(cal, list)
                    h1_ok = isinstance(h1, list)
                    if not cal_ok or not h1_ok:
                        raise RuntimeError(f"finnhub returned non-list: cal={type(cal).__name__}, news={type(h1).__name__}")
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
    return build_offline_brief()
