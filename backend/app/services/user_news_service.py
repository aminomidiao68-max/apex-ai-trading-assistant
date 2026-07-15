from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.services.provider_secret_service import ProviderSecretService


class UserNewsService:
    async def build(self, user_id: int, vault: ProviderSecretService) -> dict:
        headlines: list[dict] = []
        providers: dict[str, str] = {}
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
            finnhub = vault.get_material(user_id, "finnhub")
            if finnhub:
                try:
                    response = await client.get(
                        "https://finnhub.io/api/v1/news",
                        params={"category": "general", "token": finnhub.api_key},
                    )
                    if response.is_success:
                        for item in (response.json() or [])[:20]:
                            headlines.append(
                                {
                                    "id": f"finnhub:{item.get('id') or item.get('datetime')}",
                                    "title": str(item.get("headline") or ""),
                                    "summary": str(item.get("summary") or ""),
                                    "source": str(item.get("source") or "Finnhub"),
                                    "category": "general",
                                    "url": str(item.get("url") or ""),
                                    "image": str(item.get("image") or ""),
                                    "time_unix": int(item.get("datetime") or 0),
                                    "published_at": "",
                                    "impact": "low",
                                    "country": "GLOBAL",
                                    "currency": "",
                                }
                            )
                        providers["finnhub"] = "connected"
                    else:
                        providers["finnhub"] = "auth_failed" if response.status_code in {401, 403} else "unavailable"
                except Exception:
                    providers["finnhub"] = "unavailable"
            newsapi = vault.get_material(user_id, "newsapi")
            if newsapi:
                try:
                    response = await client.get(
                        "https://newsapi.org/v2/top-headlines",
                        params={
                            "category": "business",
                            "language": "en",
                            "pageSize": 20,
                            "apiKey": newsapi.api_key,
                        },
                    )
                    if response.is_success:
                        for index, item in enumerate((response.json() or {}).get("articles") or []):
                            published = str(item.get("publishedAt") or "")
                            timestamp = 0
                            try:
                                timestamp = int(
                                    datetime.fromisoformat(published.replace("Z", "+00:00"))
                                    .astimezone(timezone.utc)
                                    .timestamp()
                                )
                            except Exception:
                                pass
                            source = item.get("source") or {}
                            headlines.append(
                                {
                                    "id": f"newsapi:{timestamp}:{index}",
                                    "title": str(item.get("title") or ""),
                                    "summary": str(item.get("description") or ""),
                                    "source": str(source.get("name") or "NewsAPI"),
                                    "category": "business",
                                    "url": str(item.get("url") or ""),
                                    "image": str(item.get("urlToImage") or ""),
                                    "time_unix": timestamp,
                                    "published_at": published,
                                    "impact": "low",
                                    "country": "GLOBAL",
                                    "currency": "",
                                }
                            )
                        providers["newsapi"] = "connected"
                    else:
                        providers["newsapi"] = "auth_failed" if response.status_code in {401, 403} else "unavailable"
                except Exception:
                    providers["newsapi"] = "unavailable"
        deduplicated = {}
        for item in headlines:
            key = (item["title"].strip().lower(), item["url"])
            if item["title"] and key not in deduplicated:
                deduplicated[key] = item
        items = sorted(
            deduplicated.values(),
            key=lambda item: int(item.get("time_unix") or 0),
            reverse=True,
        )[:30]
        return {
            "user_scoped": True,
            "provider_status": providers,
            "block": {
                "blocked": False,
                "reasons": [],
                "block_until": 0,
                "active_events": [],
            },
            "adjustment": {
                "bias": "neutral",
                "score_penalty": 0,
                "note": "User-scoped headlines are informational; no economic-calendar block is inferred.",
            },
            "events": {"upcoming": [], "live": [], "past": []},
            "headlines": items,
        }


user_news_service = UserNewsService()
