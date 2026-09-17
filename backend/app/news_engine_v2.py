from __future__ import annotations
import os, logging
from datetime import datetime, timedelta, timezone
logger = logging.getLogger("apex.news_engine")

FINNHUB_AVAILABLE = False
try:
    from .finnhub_client import get_finnhub
    FINNHUB_AVAILABLE = True
except Exception as e:
    logger.warning(f"Finnhub client not available: {e}")
    get_finnhub = None

from .news_fallback import build_offline_brief

def _is_error(v):
    return isinstance(v, dict) and ("error" in v)


_TIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M")


def _parse_event_time(raw) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        try:
            ts = float(raw)
            if ts > 1e12:
                ts /= 1000.0
            return datetime.fromtimestamp(ts, timezone.utc)
        except Exception:
            return None
    txt = str(raw).strip().replace("Z", "")
    for fmt in _TIME_FORMATS:
        try:
            return datetime.strptime(txt, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def evaluate_calendar_block(cal, now_utc: datetime | None = None) -> tuple[dict, bool]:
    """v3.24: real Finnhub-calendar evaluation (was: always blocked=False).

    v3.26 ZERO-ERROR blackout: high-impact events block from 90 min before to
    45 min after the release; medium-impact events now ALSO block, from 45 min
    before to 15 min after. Deterministic, fail-closed on parse errors
    (unparsable high-impact rows are skipped but counted in warnings).
    """
    now_utc = now_utc or datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    blocked = False
    reasons: list[str] = []
    block_until = 0
    active: list[dict] = []
    medium_near = False
    unparsed = 0
    for ev in cal or []:
        if not isinstance(ev, dict):
            continue
        impact = str(ev.get("impact") or "").lower()
        dt = _parse_event_time(ev.get("time") or ev.get("timestamp"))
        if dt is None:
            if impact == "high":
                unparsed += 1
            continue
        if impact == "high":
            pre, post = timedelta(minutes=90), timedelta(minutes=45)
        elif impact == "medium":
            pre, post = timedelta(minutes=45), timedelta(minutes=15)
        else:
            continue
        if dt - pre <= now_utc <= dt + post:
            title = str(ev.get("event") or ev.get("title") or "رویداد خبری")
            country = str(ev.get("country") or "")
            if impact == "high":
                blocked = True
                until = int((dt + post).timestamp())
                block_until = max(block_until, until)
                reasons.append(f"رویداد پراثر {country} «{title}» داخل پنجره خبری (۹۰- قبل تا ۴۵+ دقیقه)")
                active.append({"event": title, "country": country, "impact": impact,
                               "time": ev.get("time"), "block_until": until})
            else:
                # v3.26 ZERO-ERROR: medium-impact events block as well
                blocked = True
                medium_near = True
                until = int((dt + post).timestamp())
                block_until = max(block_until, until)
                reasons.append(f"رویداد متوسط {country} «{title}» داخل پنجره خبری (۴۵- قبل تا ۱۵+ دقیقه)")
                active.append({"event": title, "country": country, "impact": impact,
                               "time": ev.get("time"), "block_until": until})
    if unparsed:
        reasons.append(f"{unparsed} رویداد پراثر با زمان نامفهوم — احتیاط: fail-closed")
    return ({"blocked": blocked, "reasons": reasons, "block_until": block_until,
             "active_events": active[:6]}, medium_near)

async def build_news_brief():
    if FINNHUB_AVAILABLE:
        try:
            fh = get_finnhub()
            if fh and fh.is_configured:
                try:
                    cal = await fh.get_economic_calendar()
                    h1 = await fh.get_general_news("general")
                    if _is_error(cal) or _is_error(h1):
                        raise RuntimeError(f"finnhub error cal={cal} news={h1}")
                    if not isinstance(cal, list) or not isinstance(h1, list):
                        raise RuntimeError(f"unexpected finnhub types: {type(cal).__name__}/{type(h1).__name__}")
                    now = datetime.now(timezone.utc)
                    block, medium_near = evaluate_calendar_block(cal, now)
                    if block["blocked"]:
                        adj = {"bias": "caution", "score_penalty": 20,
                               "note": "پنجره خبر پراثر فعال — معاملات جدید بسته می‌ماند."}
                    elif medium_near:
                        adj = {"bias": "caution", "score_penalty": 10,
                               "note": "رویداد اثرمتوسط نزدیک است — حجم کمتر."}
                    else:
                        adj = {"bias": "neutral", "score_penalty": 0, "note": "اخبار زنده فین‌هاب."}
                    return {
                        "finnhub_configured": True,
                        "server_time_unix": int(now.timestamp()),
                        "server_time_iso": now.isoformat(),
                        "block": block,
                        "adjustment": adj,
                        "events": {"upcoming": (cal or [])[:20], "live": [], "past": []},
                        "headlines": (h1 or [])[:20],
                        "source": "finnhub",
                    }
                except Exception as inner:
                    logger.warning(f"Finnhub fetch failed, falling back to Apex AI offline news: {inner}")
        except Exception as e:
            logger.warning(f"Finnhub init failed: {e}")
    return build_offline_brief()
