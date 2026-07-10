from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Any, Dict, Optional
from .finnhub_client import get_finnhub
from .news_engine_v2 import build_news_brief

router = APIRouter(prefix="/api/news", tags=["news"])

@router.get("/brief")
async def brief():
    try:
        return await build_news_brief()
    except Exception as e:
        return {
            "finnhub_configured": get_finnhub().is_configured,
            "server_time_unix": 0, "server_time_iso": "",
            "block": {"blocked": False, "reasons": [], "block_until": 0, "active_events": []},
            "adjustment": {"bias": "neutral", "score_penalty": 0, "note": f"news error: {e}"},
            "events": {"upcoming":[], "live":[], "past":[]},
            "headlines": [],
        }

@router.get("/health")
async def health():
    return {"service":"news","finnhub_configured": get_finnhub().is_configured}
