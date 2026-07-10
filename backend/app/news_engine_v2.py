from __future__ import annotations
from typing import Dict, Any, List
from datetime import datetime, timezone
from .finnhub_client import get_finnhub

BLOCK_BEFORE_MIN = 30
BLOCK_AFTER_MIN = 15

def _classify(events: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    now_unix = int(datetime.now(timezone.utc).timestamp())
    past, upcoming, live = [], [], []
    for e in events:
        ts = e.get("time_unix", 0)
        mins = (ts - now_unix) // 60
        en = {**e, "minutes_until": int(mins)}
        if mins < -BLOCK_AFTER_MIN:
            past.append(en)
        elif mins <= BLOCK_AFTER_MIN:
            live.append(en)
        else:
            upcoming.append(en)
    upcoming.sort(key=lambda x: x["time_unix"])
    live.sort(key=lambda x: x["time_unix"])
    past.sort(key=lambda x: -x["time_unix"])
    return {"upcoming": upcoming, "live": live, "past": past[:10]}

def _is_blocked(c: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    blocked = False
    reasons: List[str] = []
    events: List[Dict[str, Any]] = []
    for ev in c["live"]:
        if ev.get("impact") == "high":
            blocked = True
            reasons.append(f"خبر پرریسک {ev.get('currency','')} در حال انتشار")
            events.append(ev)
    for ev in c["upcoming"]:
        mins = ev.get("minutes_until", 9999)
        if ev.get("impact") == "high" and 0 <= mins <= BLOCK_BEFORE_MIN:
            blocked = True
            reasons.append(f"{mins} دقیقه تا خبر پرریسک {ev.get('currency','')}")
            events.append(ev)
    next_unblock = 0
    if blocked and events:
        next_unblock = max(e["time_unix"] for e in events) + BLOCK_AFTER_MIN * 60
    return {
        "blocked": blocked,
        "reasons": reasons,
        "block_until": next_unblock,
        "active_events": [
            {
                "title": e.get("title",""),
                "currency": e.get("currency",""),
                "impact": e.get("impact",""),
                "minutes_until": e.get("minutes_until",0),
                "time_unix": e.get("time_unix",0),
            } for e in events[:5]
        ],
    }

def _adjustment(c: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    hi_live = [e for e in c["live"] if e.get("impact") == "high"]
    hi_up = [e for e in c["upcoming"] if e.get("impact") == "high" and 0 <= e.get("minutes_until",9999) <= 120]
    if hi_live:
        ccy = ", ".join(sorted({e.get("currency","") for e in hi_live if e.get("currency")}))
        return {"bias":"risk_off","score_penalty":5,
                "note": f"اخبار پرریسک {ccy} در حال انتشار است. ورود به معامله جدید توصیه نمی‌شود."}
    if hi_up:
        n = hi_up[0]
        return {"bias":"risk_off","score_penalty":min(3,len(hi_up)),
                "note": f"{n.get('minutes_until')} دقیقه تا خبر پرریسک {n.get('currency','')} ({n.get('title','')}). حجم را کم کنید."}
    return {"bias":"neutral","score_penalty":0,
            "note":"اخبار مهمی نزدیک نیست. می‌توان با مدیریت ریسک ترید کرد."}

async def build_news_brief() -> Dict[str, Any]:
    fh = get_finnhub()
    cal = await fh.get_economic_calendar()
    h1 = await fh.get_general_news("general")
    h2 = await fh.get_general_news("forex")
    c = _classify(cal)
    now = datetime.now(timezone.utc)
    return {
        "finnhub_configured": fh.is_configured,
        "server_time_unix": int(now.timestamp()),
        "server_time_iso": now.isoformat(),
        "block": _is_blocked(c),
        "adjustment": _adjustment(c),
        "events": c,
        "headlines": (h1 + h2)[:20],
    }
