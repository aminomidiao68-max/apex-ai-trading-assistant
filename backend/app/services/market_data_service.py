from __future__ import annotations

from typing import Iterable, List

import httpx

from app.config import settings
from app.models import Candle, MarketSnapshot, MarketType


class MarketDataService:
    async def fetch_binance_ticker(self, symbol: str) -> MarketSnapshot:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params={"symbol": symbol.upper()})
            response.raise_for_status()
            data = response.json()
        return MarketSnapshot(
            symbol=symbol.upper(),
            market=MarketType.crypto,
            last_price=float(data["lastPrice"]),
            change_pct=float(data["priceChangePercent"]),
            source="binance",
            status="live",
        )

    async def fetch_binance_candles(self, symbol: str, interval: str = "15m", limit: int = 200) -> List[Candle]:
        url = "https://api.binance.com/api/v3/klines"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                url,
                params={"symbol": symbol.upper(), "interval": interval, "limit": limit},
            )
            response.raise_for_status()
            raw = response.json()
        candles: list[Candle] = []
        for item in raw:
            candles.append(
                Candle(
                    timestamp=item[0] / 1000,
                    open=float(item[1]),
                    high=float(item[2]),
                    low=float(item[3]),
                    close=float(item[4]),
                    volume=float(item[5]),
                )
            )
        return candles

    async def fetch_twelvedata_quote(self, symbol: str) -> MarketSnapshot:
        if not settings.twelve_data_api_key:
            return MarketSnapshot(
                symbol=symbol,
                market=MarketType.forex,
                source="twelvedata",
                status="missing_api_key",
            )

        normalized = self._normalize_twelvedata_symbol(symbol)
        url = "https://api.twelvedata.com/quote"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                url,
                params={"symbol": normalized, "apikey": settings.twelve_data_api_key},
            )
            response.raise_for_status()
            data = response.json()

        if data.get("status") == "error":
            return MarketSnapshot(
                symbol=symbol,
                market=MarketType.forex,
                source="twelvedata",
                status=data.get("message", "provider_error"),
            )

        percent_change = data.get("percent_change")
        return MarketSnapshot(
            symbol=symbol,
            market=MarketType.forex,
            last_price=float(data["close"]),
            change_pct=float(percent_change) if percent_change not in (None, "") else None,
            source="twelvedata",
            status="live",
        )

    async def fetch_twelvedata_candles(
        self, symbol: str, interval: str = "15min", outputsize: int = 200
    ) -> List[Candle]:
        if not settings.twelve_data_api_key:
            return []

        normalized = self._normalize_twelvedata_symbol(symbol)
        url = "https://api.twelvedata.com/time_series"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                url,
                params={
                    "symbol": normalized,
                    "interval": interval,
                    "outputsize": outputsize,
                    "apikey": settings.twelve_data_api_key,
                },
            )
            response.raise_for_status()
            data = response.json()

        values = data.get("values", [])
        candles: list[Candle] = []
        for item in reversed(values):
            candles.append(
                Candle(
                    timestamp=item["datetime"],
                    open=float(item["open"]),
                    high=float(item["high"]),
                    low=float(item["low"]),
                    close=float(item["close"]),
                    volume=float(item.get("volume") or 0.0),
                )
            )
        return candles

    async def market_overview(self, symbols: Iterable[str]) -> list[MarketSnapshot]:
        items: list[MarketSnapshot] = []
        for symbol in symbols:
            upper = symbol.upper()
            try:
                if upper.endswith("USDT"):
                    items.append(await self.fetch_binance_ticker(upper))
                else:
                    items.append(await self.fetch_twelvedata_quote(upper))
            except Exception as exc:
                items.append(
                    MarketSnapshot(
                        symbol=upper,
                        market=MarketType.crypto if upper.endswith("USDT") else MarketType.forex,
                        source="provider",
                        status=f"error: {exc}",
                    )
                )
        return items

    def _normalize_twelvedata_symbol(self, symbol: str) -> str:
        normalized = symbol.upper().replace("/", "")
        if normalized == "XAUUSD":
            return "XAU/USD"
        if len(normalized) == 6:
            return f"{normalized[:3]}/{normalized[3:]}"
        return symbol
