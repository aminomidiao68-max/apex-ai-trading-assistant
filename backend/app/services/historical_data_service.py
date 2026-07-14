from __future__ import annotations

import gzip
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol
from urllib.parse import quote

import httpx

from app.config import settings
from app.models import (
    Candle,
    HistoricalDataCollectRequest,
    HistoricalDataCollectResponse,
    HistoricalDatasetListResponse,
    HistoricalDatasetManifestResponse,
    HistoricalDatasetRecord,
    MarketType,
    QuantDatasetManifest,
)
from app.services.database_service import DatabaseManager


class HistoricalDataError(RuntimeError):
    """Sanitized historical-provider or dataset-contract failure."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass
class HistoricalFetchResult:
    source: str
    candles: list[Candle]
    pages: int
    raw_rows: int
    issues: list[str] = field(default_factory=list)


class HistoricalProvider(Protocol):
    name: str

    async def fetch(self, request: HistoricalDataCollectRequest) -> HistoricalFetchResult: ...


def _timeframe_seconds(timeframe: str) -> int:
    value = timeframe.lower().replace("min", "m")
    mapping = {
        "1m": 60,
        "3m": 180,
        "5m": 300,
        "15m": 900,
        "30m": 1800,
        "1h": 3600,
        "2h": 7200,
        "4h": 14400,
        "6h": 21600,
        "12h": 43200,
        "1d": 86400,
    }
    if value not in mapping:
        raise HistoricalDataError("unsupported_timeframe")
    return mapping[value]


def _okx_bar(timeframe: str) -> str:
    value = timeframe.lower().replace("min", "m")
    mapping = {
        "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
        "1h": "1H", "2h": "2H", "4h": "4H", "6h": "6H", "12h": "12H", "1d": "1D",
    }
    if value not in mapping:
        raise HistoricalDataError("okx_unsupported_timeframe")
    return mapping[value]


def _okx_instrument(symbol: str) -> str:
    upper = symbol.upper().replace("/", "").replace("-", "")
    if upper.endswith("USDT"):
        return f"{upper[:-4]}-USDT-SWAP"
    raise HistoricalDataError("okx_symbol_requires_usdt_swap")


class OkxHistoricalProvider:
    name = "okx"

    async def fetch(self, request: HistoricalDataCollectRequest) -> HistoricalFetchResult:
        if request.market != MarketType.crypto:
            raise HistoricalDataError("okx_provider_supports_crypto_only")
        start_ms = int(request.start_time.timestamp() * 1000)
        cursor_ms = int(request.end_time.timestamp() * 1000)
        rows: list = []
        pages = 0
        previous_cursor = None
        async with httpx.AsyncClient(timeout=20.0) as client:
            while len(rows) < request.max_candles and pages < 220:
                response = await client.get(
                    "https://www.okx.com/api/v5/market/history-candles",
                    params={
                        "instId": _okx_instrument(request.symbol),
                        "bar": _okx_bar(request.timeframe),
                        "after": str(cursor_ms),
                        "limit": "100",
                    },
                )
                if not response.is_success:
                    raise HistoricalDataError("okx_historical_unavailable")
                data = response.json()
                page = data.get("data") or []
                pages += 1
                if not page:
                    break
                rows.extend(page)
                oldest = min(int(item[0]) for item in page)
                if oldest <= start_ms:
                    break
                if previous_cursor == oldest:
                    raise HistoricalDataError("okx_pagination_stalled")
                previous_cursor = oldest
                cursor_ms = oldest

        candles = []
        for item in rows:
            try:
                # OKX confirm=1 means the candle is complete.
                if len(item) > 8 and str(item[8]) != "1":
                    continue
                candles.append(
                    Candle(
                        timestamp=datetime.fromtimestamp(int(item[0]) / 1000, tz=timezone.utc),
                        open=float(item[1]),
                        high=float(item[2]),
                        low=float(item[3]),
                        close=float(item[4]),
                        volume=float(item[5]),
                    )
                )
            except (ValueError, TypeError, IndexError):
                continue
        return HistoricalFetchResult(
            source="okx_swap_history_public",
            candles=candles,
            pages=pages,
            raw_rows=len(rows),
            issues=["OKX data is exchange-specific and does not represent the entire crypto market."],
        )


class YahooHistoricalProvider:
    name = "yahoo"

    def _symbol(self, symbol: str) -> str:
        normalized = symbol.upper().replace("/", "").replace("_", "")
        mapping = {"XAUUSD": "GC=F", "US30": "^DJI", "NAS100": "^NDX", "USDJPY": "JPY=X"}
        if normalized in mapping:
            return mapping[normalized]
        if len(normalized) == 6 and normalized.isalpha():
            return f"{normalized}=X"
        return normalized

    async def fetch(self, request: HistoricalDataCollectRequest) -> HistoricalFetchResult:
        if request.market != MarketType.forex:
            raise HistoricalDataError("yahoo_provider_is_restricted_to_forex_index_pipeline")
        value = request.timeframe.lower().replace("min", "m")
        interval_map = {"1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1h": "60m", "1d": "1d"}
        if value not in interval_map:
            raise HistoricalDataError("yahoo_unsupported_timeframe")
        range_days = (request.end_time - request.start_time).total_seconds() / 86400
        if value == "1m" and range_days > 7:
            raise HistoricalDataError("yahoo_1m_range_exceeds_provider_limit")
        if value in {"5m", "15m", "30m"} and range_days > 60:
            raise HistoricalDataError("yahoo_intraday_range_exceeds_provider_limit")
        if value == "1h" and range_days > 730:
            raise HistoricalDataError("yahoo_hourly_range_exceeds_provider_limit")

        encoded = quote(self._symbol(request.symbol), safe="")
        async with httpx.AsyncClient(
            timeout=25.0,
            headers={"User-Agent": "Mozilla/5.0 APEX-Historical/3.1"},
        ) as client:
            response = await client.get(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}",
                params={
                    "period1": int(request.start_time.timestamp()),
                    "period2": int(request.end_time.timestamp()),
                    "interval": interval_map[value],
                    "events": "div,splits",
                },
            )
        if not response.is_success:
            raise HistoricalDataError("yahoo_historical_unavailable")
        chart = response.json().get("chart") or {}
        if chart.get("error"):
            raise HistoricalDataError("yahoo_provider_error")
        result = (chart.get("result") or [None])[0]
        if not result:
            raise HistoricalDataError("yahoo_empty_history")
        timestamps = result.get("timestamp") or []
        quote_data = ((result.get("indicators") or {}).get("quote") or [{}])[0]
        candles = []
        for index, timestamp in enumerate(timestamps):
            try:
                values = [quote_data[name][index] for name in ("open", "high", "low", "close")]
                if any(value is None for value in values):
                    continue
                volumes = quote_data.get("volume") or []
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
            except (IndexError, TypeError, ValueError, KeyError):
                continue
        return HistoricalFetchResult(
            source="yahoo_chart_unofficial",
            candles=candles,
            pages=1,
            raw_rows=len(timestamps),
            issues=[
                "Yahoo chart data is an unofficial fallback without an institutional SLA.",
                "Intraday lookback is provider-limited; unsupported ranges fail instead of truncating silently.",
            ],
        )


class TwelveDataHistoricalProvider:
    name = "twelvedata"

    def _symbol(self, symbol: str) -> str:
        normalized = symbol.upper().replace("/", "")
        if len(normalized) == 6 and normalized.isalpha():
            return f"{normalized[:3]}/{normalized[3:]}"
        return normalized

    async def fetch(self, request: HistoricalDataCollectRequest) -> HistoricalFetchResult:
        if not settings.twelve_data_api_key:
            raise HistoricalDataError("twelvedata_not_configured")
        if request.max_candles > 5_000:
            raise HistoricalDataError("twelvedata_request_exceeds_single_call_limit")
        interval = request.timeframe.lower().replace("min", "m")
        interval_map = {
            "1m": "1min", "5m": "5min", "15m": "15min", "30m": "30min",
            "1h": "1h", "2h": "2h", "4h": "4h", "1d": "1day",
        }
        if interval not in interval_map:
            raise HistoricalDataError("twelvedata_unsupported_timeframe")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.twelvedata.com/time_series",
                params={
                    "symbol": self._symbol(request.symbol),
                    "interval": interval_map[interval],
                    "start_date": request.start_time.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    "end_date": request.end_time.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    "outputsize": request.max_candles,
                    "order": "ASC",
                    "timezone": "UTC",
                    "apikey": settings.twelve_data_api_key,
                },
            )
        if not response.is_success:
            raise HistoricalDataError("twelvedata_historical_unavailable")
        data = response.json()
        if data.get("status") == "error":
            raise HistoricalDataError("twelvedata_provider_error")
        rows = data.get("values") or []
        candles = []
        for item in rows:
            try:
                timestamp = datetime.fromisoformat(str(item["datetime"]).replace("Z", "+00:00"))
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                candles.append(
                    Candle(
                        timestamp=timestamp.astimezone(timezone.utc),
                        open=float(item["open"]),
                        high=float(item["high"]),
                        low=float(item["low"]),
                        close=float(item["close"]),
                        volume=float(item.get("volume") or 0.0),
                    )
                )
            except (ValueError, TypeError, KeyError):
                continue
        return HistoricalFetchResult(
            source="twelvedata_time_series",
            candles=candles,
            pages=1,
            raw_rows=len(rows),
            issues=["Provider licensing and redistribution terms must be reviewed before external dataset distribution."],
        )


class HistoricalDatasetStore:
    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def save(
        self,
        user_id: int,
        manifest: QuantDatasetManifest,
        canonical_sha256: str,
        candles: list[Candle],
    ) -> None:
        manifest_json = json.dumps(manifest.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        candle_payload = json.dumps(
            [item.model_dump(mode="json") for item in candles],
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        compressed = gzip.compress(candle_payload, compresslevel=9, mtime=0)
        now = datetime.now(timezone.utc).isoformat()
        with self.database.connection() as conn:
            existing = conn.execute(
                "SELECT canonical_sha256 FROM quant_datasets WHERE user_id = ? AND dataset_id = ? AND version = ?",
                (user_id, manifest.dataset_id, manifest.version),
            ).fetchone()
            if existing is not None and existing["canonical_sha256"] != canonical_sha256:
                raise HistoricalDataError("immutable_dataset_version_conflict")
            if existing is None:
                conn.execute(
                    """
                    INSERT INTO quant_datasets (
                        user_id, dataset_id, version, source, symbol, market, timeframe,
                        start_time, end_time, sample_count, source_sha256,
                        canonical_sha256, data_quality_score, manifest_json,
                        candles_gzip, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        manifest.dataset_id,
                        manifest.version,
                        manifest.source,
                        manifest.symbol,
                        manifest.market.value,
                        manifest.timeframe,
                        manifest.start_time.isoformat(),
                        manifest.end_time.isoformat(),
                        manifest.sample_count,
                        manifest.source_sha256,
                        canonical_sha256,
                        manifest.data_quality_score,
                        manifest_json,
                        compressed,
                        now,
                    ),
                )
                conn.commit()

    def list(self, user_id: int, limit: int = 100) -> HistoricalDatasetListResponse:
        with self.database.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM quant_datasets WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, max(1, min(limit, 500))),
            ).fetchall()
        items = [
            HistoricalDatasetRecord(
                dataset_ref=f"{row['dataset_id']}:{row['version']}",
                dataset_id=row["dataset_id"],
                version=row["version"],
                source=row["source"],
                symbol=row["symbol"],
                market=MarketType(row["market"]),
                timeframe=row["timeframe"],
                start_time=datetime.fromisoformat(row["start_time"]),
                end_time=datetime.fromisoformat(row["end_time"]),
                sample_count=int(row["sample_count"]),
                source_sha256=row["source_sha256"],
                canonical_sha256=row["canonical_sha256"],
                data_quality_score=float(row["data_quality_score"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]
        return HistoricalDatasetListResponse(items=items, count=len(items))

    def get_manifest(self, user_id: int, dataset_id: str, version: str) -> HistoricalDatasetManifestResponse:
        with self.database.connection() as conn:
            row = conn.execute(
                "SELECT * FROM quant_datasets WHERE user_id = ? AND dataset_id = ? AND version = ?",
                (user_id, dataset_id, version),
            ).fetchone()
        if row is None:
            raise HistoricalDataError("historical_dataset_not_found")
        manifest = QuantDatasetManifest(**json.loads(row["manifest_json"]))
        candles = json.loads(gzip.decompress(bytes(row["candles_gzip"])).decode("utf-8"))
        return HistoricalDatasetManifestResponse(
            dataset_ref=f"{dataset_id}:{version}",
            manifest=manifest,
            canonical_sha256=row["canonical_sha256"],
            stored_candle_count=len(candles),
            storage_backend=self.database.backend,
        )

    def load_candles(self, user_id: int, dataset_id: str, version: str) -> list[Candle]:
        with self.database.connection() as conn:
            row = conn.execute(
                "SELECT candles_gzip FROM quant_datasets WHERE user_id = ? AND dataset_id = ? AND version = ?",
                (user_id, dataset_id, version),
            ).fetchone()
        if row is None:
            raise HistoricalDataError("historical_dataset_not_found")
        payload = json.loads(gzip.decompress(bytes(row["candles_gzip"])).decode("utf-8"))
        return [Candle(**item) for item in payload]


class HistoricalDataService:
    def __init__(
        self,
        database: DatabaseManager,
        providers: dict[str, HistoricalProvider] | None = None,
    ) -> None:
        self.database = database
        self.store = HistoricalDatasetStore(database)
        self.providers = providers or {
            "okx": OkxHistoricalProvider(),
            "yahoo": YahooHistoricalProvider(),
            "twelvedata": TwelveDataHistoricalProvider(),
        }

    def _select_provider(self, request: HistoricalDataCollectRequest) -> str:
        if request.provider != "auto":
            return request.provider
        if request.market == MarketType.crypto:
            return "okx"
        if settings.twelve_data_api_key:
            return "twelvedata"
        return "yahoo"

    def _canonicalize(
        self,
        request: HistoricalDataCollectRequest,
        result: HistoricalFetchResult,
    ) -> tuple[list[Candle], dict]:
        timeframe_seconds = _timeframe_seconds(request.timeframe)
        now = datetime.now(timezone.utc).timestamp()
        ordered = sorted(result.candles, key=lambda item: item.timestamp)
        unique: dict[datetime, Candle] = {}
        duplicates = 0
        rejected = 0
        for candle in ordered:
            timestamp = candle.timestamp
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
                candle = candle.model_copy(update={"timestamp": timestamp})
            timestamp = timestamp.astimezone(timezone.utc)
            if not (request.start_time <= timestamp < request.end_time):
                rejected += 1
                continue
            if timestamp.timestamp() + timeframe_seconds > now:
                rejected += 1
                continue
            if timestamp in unique:
                duplicates += 1
                continue
            unique[timestamp] = candle.model_copy(update={"timestamp": timestamp})
        candles = list(unique.values())[: request.max_candles]
        if len(candles) < 30:
            raise HistoricalDataError("historical_dataset_has_fewer_than_30_finalized_candles")

        missing = 0
        for previous, current in zip(candles, candles[1:]):
            difference = int((current.timestamp - previous.timestamp).total_seconds())
            if difference <= int(timeframe_seconds * 1.5):
                continue
            if request.market == MarketType.forex and previous.timestamp.weekday() == 4 and current.timestamp.weekday() in {6, 0}:
                continue
            missing += max(0, round(difference / timeframe_seconds) - 1)
        gap_ratio = missing / max(1, len(candles) + missing)
        raw = max(1, result.raw_rows)
        quality = 100.0
        quality -= min(20.0, duplicates / raw * 100.0)
        quality -= min(20.0, rejected / raw * 100.0)
        quality -= min(40.0, gap_ratio * 100.0)
        quality = max(0.0, quality)
        return candles, {
            "duplicates": duplicates,
            "rejected": rejected,
            "missing": missing,
            "gap_ratio": gap_ratio,
            "quality": quality,
        }

    async def collect(self, request: HistoricalDataCollectRequest, user_id: int) -> HistoricalDataCollectResponse:
        provider_name = self._select_provider(request)
        provider = self.providers.get(provider_name)
        if provider is None:
            raise HistoricalDataError("historical_provider_not_available")
        result = await provider.fetch(request)
        candles, diagnostics = self._canonicalize(request, result)
        canonical_payload = json.dumps(
            [item.model_dump(mode="json") for item in candles],
            sort_keys=True,
            separators=(",", ":"),
        )
        canonical_sha = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()
        issues = list(result.issues)
        if diagnostics["duplicates"]:
            issues.append(f"Removed {diagnostics['duplicates']} duplicate timestamps.")
        if diagnostics["missing"]:
            issues.append(f"Estimated {diagnostics['missing']} missing bars after market-closure adjustment.")
        if not request.attest_independent_holdout:
            issues.append("Dataset is not attested as an independent holdout.")
        if not request.attest_survivorship_controlled:
            issues.append("Survivorship-bias control is not attested.")
        manifest = QuantDatasetManifest(
            dataset_id=request.dataset_id,
            version=request.version,
            source=result.source,
            symbol=request.symbol.upper(),
            market=request.market,
            timeframe=request.timeframe,
            start_time=candles[0].timestamp,
            end_time=candles[-1].timestamp,
            sample_count=len(candles),
            source_sha256=canonical_sha,
            is_point_in_time=request.attest_point_in_time,
            is_survivorship_bias_controlled=request.attest_survivorship_controlled,
            is_independent_holdout=request.attest_independent_holdout,
            data_quality_score=round(diagnostics["quality"], 4),
            notes=(request.notes + issues)[:30],
        )
        stored = False
        if request.persist:
            self.store.save(user_id, manifest, canonical_sha, candles)
            stored = True
        return HistoricalDataCollectResponse(
            dataset_ref=f"{request.dataset_id}:{request.version}",
            manifest=manifest,
            canonical_sha256=canonical_sha,
            provider=result.source,
            provider_pages=result.pages,
            raw_rows=result.raw_rows,
            accepted_rows=len(candles),
            duplicate_rows=int(diagnostics["duplicates"]),
            rejected_rows=int(diagnostics["rejected"]),
            estimated_missing_bars=int(diagnostics["missing"]),
            gap_ratio=round(float(diagnostics["gap_ratio"]), 8),
            finalized_only=True,
            stored=stored,
            storage_backend=self.database.backend if stored else "not_persisted",
            issues=issues,
            first_candle=candles[0],
            last_candle=candles[-1],
        )
