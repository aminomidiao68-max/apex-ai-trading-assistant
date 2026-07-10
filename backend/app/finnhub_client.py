from __future__ import annotations
import os
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
import httpx

logger = logging.getLogger("apex.finnhub")
FINNHUB_BASE = "https://finnhub.io/api/v1"
CACHE_TTL_SEC = 120

class FinnhubClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("FINNHUB_API_KEY", "")
        self._cache: Dict[str, tuple] = {}
        self._client = httpx.AsyncClient(timeout=10.0)

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        params = params or {}
        params["token"] = self.api_key
        url = f"{FINNHUB_BASE}{path}"
        key = f"{path}?{tuple(sorted(params.items()))}"
        now = time.time()
        if key in self._cache:
            ts, val = self._cache[key]
            if now - ts < CACHE_TTL_SEC:
                return val
        try:
            r = await self._client.get(url, params=params)
            if r.status_code != 200:
                logger.warning("Finnhub %s -> %s", path, r.status_code)
                return None
            data = r.json()
            self._cache[key] = (now, data)
            return data
        except Exception as e:
            logger.warning("Finnhub fail: %s", e)
            return None

    async def get_economic_calendar(self) -> List[Dict[str, Any]]:
        today = datetime.now(timezone.utc).date()
        params = {"from": today.isoformat(), "to": (today + timedelta(days=1)).isoformat()}
        data = await self._get("/calendar/economic", params)
        if not isinstance(data, dict):
            return []
        events = data.get("economicCalendar") or []
        out: List[Dict[str, Any]] = []
        for ev in events:
            try:
                ts = ev.get("time", "")
                dt = None
                ts_unix = 0
                if ts:
                    dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                    ts_unix = int(dt.timestamp())
                impact = (ev.get("impact") or "").lower()
                out.append({
                    "id": f"econ::{ev.get('event','')}::{ev.get('time','')}::{ev.get('country','')}",
                    "title": ev.get("event") or "Economic event",
                    "country": (ev.get("country") or "").upper(),
                    "currency": (ev.get("currency") or "").upper(),
                    "impact": impact if impact in ("low","medium","high") else "low",
                    "actual": ev.get("actual"),
                    "forecast": ev.get("estimate") or ev.get("consensus"),
                    "previous": ev.get("prev"),
                    "unit": ev.get("unit") or "",
                    "time_unix": ts_unix,
                    "time_iso": ev.get("time",""),
                    "source": "finnhub",
                })
            except Exception:
                continue
        out.sort(key=lambda x: x["time_unix"])
        return out

    async def get_general_news(self, category: str = "general") -> List[Dict[str, Any]]:
        data = await self._get("/news", {"category": category})
        if not isinstance(data, list):
            return []
        out: List[Dict[str, Any]] = []
        for n in data[:30]:
            out.append({
                "id": str(n.get("id") or f"news::{n.get('datetime','')}"),
                "title": n.get("headline",""),
                "summary": n.get("summary",""),
                "source": n.get("source","Finnhub"),
                "category": category,
                "url": n.get("url",""),
                "image": n.get("image",""),
                "time_unix": int(n.get("datetime") or 0),
                "impact": "low",
                "country": "GLOBAL",
                "currency": "",
            })
        out.sort(key=lambda x: x["time_unix"], reverse=True)
        return out

    async def close(self):
        await self._client.aclose()

_client: Optional[FinnhubClient] = None
def get_finnhub() -> FinnhubClient:
    global _client
    if _client is None:
        _client = FinnhubClient()
    return _client
