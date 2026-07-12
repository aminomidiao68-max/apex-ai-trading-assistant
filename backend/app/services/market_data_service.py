from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Iterable, List
from urllib.parse import quote

import httpx

from app.config import settings
from app.models import Candle, MarketSnapshot, MarketType


class MarketDataProviderError(RuntimeError):
    """A sanitized provider failure that never contains credentials or URLs."""

    def __init__(self, provider: str, code: str = "unavailable") -> None:
        self.provider = provider
        self.code = code
        super().__init__(f"{provider} market data is temporarily unavailable ({code})")


class MarketDataService:
    """Market data with provider fallback, quota protection and safe errors."""

    def __init__(self) -> None:
        self._twelve_blocked_until = 0.0
        self._twelve_lock = asyncio.Lock()

    async def fetch_binance_ticker(self, symbol: str) -> MarketSnapshot:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.get(url, params={"symbol": symbol.upper()})
            if response.status_code == 451:
                return await self.fetch_okx_ticker(symbol)
            if not response.is_success:
                raise MarketDataProviderError("binance", str(response.status_code))
            data = response.json()
        return MarketSnapshot(
            symbol=symbol.upper(),
            market=MarketType.crypto,
            last_price=float(data["lastPrice"]),
            change_pct=float(data["priceChangePercent"]),
            source="binance",
            status="live",
        )

    async def fetch_binance_candles(
        self, symbol: str, interval: str = "15m", limit: int = 260
    ) -> List[Candle]:
        url = "https://api.binance.com/api/v3/klines"
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                url,
                params={"symbol": symbol.upper(), "interval": interval, "limit": limit},
            )
            if response.status_code == 451:
                return await self.fetch_okx_candles(symbol, interval=interval, limit=limit)
            if not response.is_success:
                raise MarketDataProviderError("binance", str(response.status_code))
            raw = response.json()
        return [
            Candle(
                timestamp=datetime.fromtimestamp(item[0] / 1000, tz=timezone.utc),
                open=float(item[1]),
                high=float(item[2]),
                low=float(item[3]),
                close=float(item[4]),
                volume=float(item[5]),
            )
            for item in raw
        ]

    async def fetch_okx_ticker(self, symbol: str) -> MarketSnapshot:
        inst_id = self._normalize_okx_symbol(symbol)
        url = "https://www.okx.com/api/v5/market/ticker"
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.get(url, params={"instId": inst_id})
            if not response.is_success:
                raise MarketDataProviderError("okx", str(response.status_code))
            data = response.json()
        items = data.get("data") or []
        if not items:
            raise MarketDataProviderError("okx", "empty_response")
        item = items[0]
        last_price = float(item["last"])
        open_24h = float(item.get("open24h") or last_price)
        change_pct = ((last_price - open_24h) / open_24h * 100.0) if open_24h else 0.0
        return MarketSnapshot(
            symbol=symbol.upper(),
            market=MarketType.crypto,
            last_price=last_price,
            change_pct=round(change_pct, 4),
            source="okx",
            status="live-fallback",
        )

    async def fetch_okx_candles(
        self, symbol: str, interval: str = "15m", limit: int = 260
    ) -> List[Candle]:
        inst_id = self._normalize_okx_symbol(symbol)
        bar = self._normalize_okx_interval(interval)
        url = "https://www.okx.com/api/v5/market/candles"
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                url, params={"instId": inst_id, "bar": bar, "limit": limit}
            )
            if not response.is_success:
                raise MarketDataProviderError("okx", str(response.status_code))
            data = response.json()
        raw = data.get("data") or []
        return [
            Candle(
                timestamp=datetime.fromtimestamp(int(item[0]) / 1000, tz=timezone.utc),
                open=float(item[1]),
                high=float(item[2]),
                low=float(item[3]),
                close=float(item[4]),
                volume=float(item[5]) if len(item) > 5 else 0.0,
            )
            for item in reversed(raw)
        ]

    async def fetch_forex_quote(self, symbol: str) -> MarketSnapshot:
        """Use quota-free Yahoo first, with TwelveData as a controlled fallback."""
        try:
            return await self.fetch_yahoo_quote(symbol)
        except Exception:
            pass
        if settings.twelve_data_api_key:
            try:
                return await self.fetch_twelvedata_quote(symbol)
            except Exception:
                pass
        return MarketSnapshot(
            symbol=symbol.upper(),
            market=MarketType.forex,
            source="fallback",
            status="provider_unavailable",
        )

    async def fetch_forex_candles(
        self, symbol: str, interval: str = "15m", outputsize: int = 260
    ) -> List[Candle]:
        """Fetch Forex/index/gold candles without exhausting TwelveData quota.

        Yahoo is the primary chart provider for supported symbols. TwelveData
        remains a fallback and is circuit-broken for 90 seconds after HTTP 429.
        No provider exception may contain an API key or request URL.
        """
        try:
            candles = await self.fetch_yahoo_candles(symbol, interval, outputsize)
            if len(candles) >= 30:
                return candles
        except Exception:
            pass

        if settings.twelve_data_api_key and time.monotonic() >= self._twelve_blocked_until:
            try:
                return await self.fetch_twelvedata_candles(symbol, interval, outputsize)
            except Exception:
                pass
        raise MarketDataProviderError("forex", "all_providers_unavailable")

    async def fetch_twelvedata_quote(self, symbol: str) -> MarketSnapshot:
        if not settings.twelve_data_api_key:
            raise MarketDataProviderError("twelvedata", "missing_key")
        if time.monotonic() < self._twelve_blocked_until:
            raise MarketDataProviderError("twelvedata", "rate_limited")

        normalized = self._normalize_twelvedata_symbol(symbol)
        async with self._twelve_lock:
            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.get(
                    "https://api.twelvedata.com/quote",
                    params={"symbol": normalized, "apikey": settings.twelve_data_api_key},
                )
        if response.status_code == 429:
            self._twelve_blocked_until = time.monotonic() + 90
            raise MarketDataProviderError("twelvedata", "rate_limited")
        if not response.is_success:
            raise MarketDataProviderError("twelvedata", str(response.status_code))
        data = response.json()
        if data.get("status") == "error":
            raise MarketDataProviderError("twelvedata", "provider_error")

        last_price = float(data["close"])
        percent_change = data.get("percent_change")
        return MarketSnapshot(
            symbol=symbol.upper(),
            market=MarketType.forex,
            last_price=last_price,
            change_pct=float(percent_change) if percent_change not in (None, "") else None,
            source="twelvedata",
            status="live",
        )

    async def fetch_twelvedata_candles(
        self, symbol: str, interval: str = "15m", outputsize: int = 260
    ) -> List[Candle]:
        if not settings.twelve_data_api_key:
            raise MarketDataProviderError("twelvedata", "missing_key")
        if time.monotonic() < self._twelve_blocked_until:
            raise MarketDataProviderError("twelvedata", "rate_limited")

        normalized = self._normalize_twelvedata_symbol(symbol)
        normalized_interval = self._normalize_twelvedata_interval(interval)
        async with self._twelve_lock:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    "https://api.twelvedata.com/time_series",
                    params={
                        "symbol": normalized,
                        "interval": normalized_interval,
                        "outputsize": outputsize,
                        "apikey": settings.twelve_data_api_key,
                    },
                )
        if response.status_code == 429:
            self._twelve_blocked_until = time.monotonic() + 90
            raise MarketDataProviderError("twelvedata", "rate_limited")
        if not response.is_success:
            raise MarketDataProviderError("twelvedata", str(response.status_code))
        data = response.json()
        if data.get("status") == "error":
            raise MarketDataProviderError("twelvedata", "provider_error")

        values = data.get("values") or []
        candles = []
        for item in reversed(values):
            timestamp = datetime.fromisoformat(str(item["datetime"]).replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            candles.append(
                Candle(
                    timestamp=timestamp,
                    open=float(item["open"]),
                    high=float(item["high"]),
                    low=float(item["low"]),
                    close=float(item["close"]),
                    volume=float(item.get("volume") or 0.0),
                )
            )
        if len(candles) < 30:
            raise MarketDataProviderError("twelvedata", "insufficient_data")
        return candles

    async def fetch_yahoo_quote(self, symbol: str) -> MarketSnapshot:
        yahoo_symbol = self._normalize_yahoo_symbol(symbol)
        encoded = quote(yahoo_symbol, safe="")
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}"
        async with httpx.AsyncClient(
            timeout=12.0, headers={"User-Agent": "Mozilla/5.0 APEX-AI/2.1"}
        ) as client:
            response = await client.get(url, params={"interval": "1m", "range": "1d"})
        if not response.is_success:
            raise MarketDataProviderError("yahoo", str(response.status_code))
        result = ((response.json().get("chart") or {}).get("result") or [None])[0]
        if not result:
            raise MarketDataProviderError("yahoo", "empty_response")
        meta = result.get("meta") or {}
        price = meta.get("regularMarketPrice")
        if price is None:
            closes = (((result.get("indicators") or {}).get("quote") or [{}])[0].get("close") or [])
            price = next((value for value in reversed(closes) if value is not None), None)
        if price is None:
            raise MarketDataProviderError("yahoo", "missing_price")
        previous = meta.get("chartPreviousClose") or meta.get("previousClose")
        change = ((float(price) - float(previous)) / float(previous) * 100) if previous else None
        return MarketSnapshot(
            symbol=symbol.upper(),
            market=MarketType.forex,
            last_price=float(price),
            change_pct=round(change, 4) if change is not None else None,
            source="yahoo",
            status="live-fallback",
        )

    async def fetch_yahoo_candles(
        self, symbol: str, interval: str = "15m", outputsize: int = 260
    ) -> List[Candle]:
        normalized_interval = self._canonical_interval(interval)
        yahoo_interval, range_value, aggregate_seconds = self._yahoo_interval(normalized_interval)
        yahoo_symbol = self._normalize_yahoo_symbol(symbol)
        encoded = quote(yahoo_symbol, safe="")
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}"
        async with httpx.AsyncClient(
            timeout=18.0, headers={"User-Agent": "Mozilla/5.0 APEX-AI/2.1"}
        ) as client:
            response = await client.get(
                url, params={"interval": yahoo_interval, "range": range_value}
            )
        if not response.is_success:
            raise MarketDataProviderError("yahoo", str(response.status_code))
        chart = response.json().get("chart") or {}
        if chart.get("error"):
            raise MarketDataProviderError("yahoo", "provider_error")
        result = (chart.get("result") or [None])[0]
        if not result:
            raise MarketDataProviderError("yahoo", "empty_response")
        timestamps = result.get("timestamp") or []
        quote_data = ((result.get("indicators") or {}).get("quote") or [{}])[0]
        opens = quote_data.get("open") or []
        highs = quote_data.get("high") or []
        lows = quote_data.get("low") or []
        closes = quote_data.get("close") or []
        volumes = quote_data.get("volume") or []

        candles = []
        for index, timestamp in enumerate(timestamps):
            try:
                values = (opens[index], highs[index], lows[index], closes[index])
                if any(value is None for value in values):
                    continue
                candles.append(
                    Candle(
                        timestamp=datetime.fromtimestamp(int(timestamp), tz=timezone.utc),
                        open=float(values[0]),
                        high=float(values[1]),
                        low=float(values[2]),
                        close=float(values[3]),
                        volume=float(volumes[index] or 0.0) if index < len(volumes) else 0.0,
                    )
                )
            except (IndexError, TypeError, ValueError):
                continue
        if aggregate_seconds:
            candles = self.aggregate_candles(candles, aggregate_seconds)
        candles = candles[-outputsize:]
        if len(candles) < 30:
            raise MarketDataProviderError("yahoo", "insufficient_data")
        return candles

    async def market_overview(self, symbols: Iterable[str]) -> list[MarketSnapshot]:
        items = []
        for symbol in symbols:
            upper = symbol.upper()
            try:
                if upper.endswith("USDT"):
                    items.append(await self.fetch_binance_ticker(upper))
                else:
                    items.append(await self.fetch_forex_quote(upper))
            except Exception:
                items.append(
                    MarketSnapshot(
                        symbol=upper,
                        market=MarketType.crypto if upper.endswith("USDT") else MarketType.forex,
                        source="provider",
                        status="provider_unavailable",
                    )
                )
        return items

    @staticmethod
    def aggregate_candles(candles: List[Candle], period_seconds: int) -> List[Candle]:
        if not candles or period_seconds <= 0:
            return []
        grouped: dict[int, list[Candle]] = {}
        for candle in candles:
            timestamp = candle.timestamp
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            epoch = int(timestamp.timestamp())
            bucket = epoch - (epoch % period_seconds)
            grouped.setdefault(bucket, []).append(candle)
        result = []
        for bucket in sorted(grouped):
            group = grouped[bucket]
            result.append(
                Candle(
                    timestamp=datetime.fromtimestamp(bucket, tz=timezone.utc),
                    open=group[0].open,
                    high=max(item.high for item in group),
                    low=min(item.low for item in group),
                    close=group[-1].close,
                    volume=sum(item.volume for item in group),
                )
            )
        return result

    def _normalize_twelvedata_symbol(self, symbol: str) -> str:
        normalized = symbol.upper().replace("/", "")
        if normalized == "XAUUSD":
            return "XAU/USD"
        if len(normalized) == 6 and normalized.isalpha():
            return f"{normalized[:3]}/{normalized[3:]}"
        return normalized

    def _normalize_yahoo_symbol(self, symbol: str) -> str:
        normalized = symbol.upper().replace("/", "").replace("_", "")
        mapping = {
            "XAUUSD": "GC=F",
            "US30": "^DJI",
            "DJI": "^DJI",
            "NAS100": "^NDX",
            "NDX": "^NDX",
            "USDJPY": "JPY=X",
        }
        if normalized in mapping:
            return mapping[normalized]
        if len(normalized) == 6 and normalized.isalpha():
            return f"{normalized}=X"
        return normalized

    def _normalize_twelvedata_interval(self, interval: str) -> str:
        canonical = self._canonical_interval(interval)
        return {
            "1m": "1min",
            "3m": "1min",
            "5m": "5min",
            "15m": "15min",
            "30m": "30min",
            "1h": "1h",
            "2h": "2h",
            "4h": "4h",
            "6h": "4h",
            "12h": "4h",
            "1d": "1day",
        }.get(canonical, "15min")

    def _canonical_interval(self, interval: str) -> str:
        value = interval.lower().strip().replace("minutes", "m").replace("minute", "m")
        if value.endswith("min"):
            value = value[:-3] + "m"
        aliases = {"60m": "1h", "240m": "4h", "1day": "1d", "day": "1d"}
        return aliases.get(value, value)

    def _yahoo_interval(self, interval: str) -> tuple[str, str, int | None]:
        return {
            "1m": ("1m", "5d", None),
            "3m": ("1m", "5d", 3 * 60),
            "5m": ("5m", "1mo", None),
            "15m": ("15m", "1mo", None),
            "30m": ("30m", "1mo", None),
            "1h": ("60m", "6mo", None),
            "2h": ("60m", "6mo", 2 * 3600),
            "4h": ("60m", "1y", 4 * 3600),
            "6h": ("60m", "1y", 6 * 3600),
            "12h": ("60m", "1y", 12 * 3600),
            "1d": ("1d", "2y", None),
        }.get(interval, ("15m", "1mo", None))

    def _normalize_okx_symbol(self, symbol: str) -> str:
        upper = symbol.upper()
        if upper.endswith("USDT"):
            return f"{upper[:-4]}-USDT"
        return upper

    def _normalize_okx_interval(self, interval: str) -> str:
        mapping = {
            "1m": "1m",
            "3m": "3m",
            "5m": "5m",
            "15m": "15m",
            "30m": "30m",
            "1h": "1H",
            "2h": "2H",
            "4h": "4H",
            "6h": "6H",
            "12h": "12H",
            "1d": "1D",
        }
        return mapping.get(self._canonical_interval(interval), "15m")
