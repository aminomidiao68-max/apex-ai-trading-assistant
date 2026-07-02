from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List

import httpx

from app.config import settings
from app.models import Candle, MarketSnapshot, MarketType


class MarketDataService:
    async def fetch_binance_ticker(self, symbol: str) -> MarketSnapshot:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params={"symbol": symbol.upper()})
            if response.status_code == 451:
                return await self.fetch_bybit_ticker(symbol)
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
            if response.status_code == 451:
                return await self.fetch_bybit_candles(symbol, interval=interval, limit=limit)
            response.raise_for_status()
            raw = response.json()
        candles: list[Candle] = []
        for item in raw:
            candles.append(
                Candle(
                    timestamp=datetime.fromtimestamp(item[0] / 1000, tz=timezone.utc),
                    open=float(item[1]),
                    high=float(item[2]),
                    low=float(item[3]),
                    close=float(item[4]),
                    volume=float(item[5]),
                )
            )
        return candles

    async def fetch_bybit_ticker(self, symbol: str) -> MarketSnapshot:
        url = f"{settings.bybit_base_url}/v5/market/tickers"
        params = {"category": "linear", "symbol": symbol.upper()}
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        items = (data.get("result") or {}).get("list") or []
        if not items:
            return MarketSnapshot(
                symbol=symbol.upper(),
                market=MarketType.crypto,
                source="bybit",
                status="empty_response",
            )
        item = items[0]
        last_price = item.get("lastPrice")
        change_pct = item.get("price24hPcnt")
        return MarketSnapshot(
            symbol=symbol.upper(),
            market=MarketType.crypto,
            last_price=float(last_price) if last_price is not None else None,
            change_pct=(float(change_pct) * 100.0) if change_pct not in (None, "") else None,
            source="bybit",
            status="live-fallback",
        )

    async def fetch_bybit_candles(self, symbol: str, interval: str = "15m", limit: int = 200) -> List[Candle]:
        url = f"{settings.bybit_base_url}/v5/market/kline"
        params = {
            "category": "linear",
            "symbol": symbol.upper(),
            "interval": self._normalize_bybit_interval(interval),
            "limit": limit,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        raw = (data.get("result") or {}).get("list") or []
        candles: list[Candle] = []
        for item in reversed(raw):
            candles.append(
                Candle(
                    timestamp=datetime.fromtimestamp(int(item[0]) / 1000, tz=timezone.utc),
                    open=float(item[1]),
                    high=float(item[2]),
                    low=float(item[3]),
                    close=float(item[4]),
                    volume=float(item[5]) if len(item) > 5 else 0.0,
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

    def _normalize_bybit_interval(self, interval: str) -> str:
        mapping = {
            "1m": "1",
            "3m": "3",
            "5m": "5",
            "15m": "15",
            "30m": "30",
            "1h": "60",
            "2h": "120",
            "4h": "240",
            "6h": "360",
            "12h": "720",
            "1d": "D",
        }
        return mapping.get(interval, "15")
