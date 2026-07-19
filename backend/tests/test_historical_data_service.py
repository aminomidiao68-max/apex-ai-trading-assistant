from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from app.models import Candle, HistoricalDataCollectRequest, MarketType
from app.services.database_service import DatabaseManager, LATEST_SCHEMA_VERSION
from app.services.historical_data_service import (
    HistoricalDataError,
    HistoricalDataService,
    HistoricalFetchResult,
    YahooHistoricalProvider,
)


class _FakeHistoricalProvider:
    name = "fake"

    def __init__(self, candles: list[Candle]) -> None:
        self.candles = candles
        self.calls = 0

    async def fetch(self, request):
        self.calls += 1
        return HistoricalFetchResult(
            source="fake_versioned_provider",
            candles=list(self.candles),
            pages=3,
            raw_rows=len(self.candles),
            issues=["fixture provider"],
        )


def _candles() -> tuple[list[Candle], datetime]:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    items = []
    for index in range(60):
        # Deliberate missing bar at index 20.
        timestamp_index = index if index < 20 else index + 1
        items.append(
            Candle(
                timestamp=start + timedelta(minutes=15 * timestamp_index),
                open=100 + index * 0.1,
                high=101 + index * 0.1,
                low=99 + index * 0.1,
                close=100.5 + index * 0.1,
                volume=1000 + index,
            )
        )
    items.append(items[10])  # duplicate timestamp
    return items, start


def _request(start: datetime, **overrides) -> HistoricalDataCollectRequest:
    values = {
        "dataset_id": "btc-real-history",
        "version": "v1",
        "provider": "okx",
        "symbol": "BTCUSDT",
        "market": MarketType.crypto,
        "timeframe": "15m",
        "start_time": start,
        "end_time": start + timedelta(days=1),
        "max_candles": 500,
        "persist": True,
        "attest_point_in_time": True,
        "attest_survivorship_controlled": False,
        "attest_independent_holdout": False,
    }
    values.update(overrides)
    return HistoricalDataCollectRequest(**values)


def test_historical_collection_is_fingerprinted_finalized_and_persisted(tmp_path):
    candles, start = _candles()
    provider = _FakeHistoricalProvider(candles)
    database = DatabaseManager(db_path=str(tmp_path / "history.db"))
    service = HistoricalDataService(database, providers={"okx": provider})

    result = asyncio.run(service.collect(_request(start), user_id=1))

    assert result.stored is True
    assert result.storage_backend == "sqlite"
    assert result.provider_pages == 3
    assert result.raw_rows == 61
    assert result.accepted_rows == 60
    assert result.duplicate_rows == 1
    assert result.estimated_missing_bars == 1
    assert result.gap_ratio > 0
    assert result.finalized_only is True
    assert len(result.canonical_sha256) == 64
    assert result.manifest.source_sha256 == result.canonical_sha256
    assert result.manifest.sample_count == 60
    assert result.manifest.is_independent_holdout is False
    assert result.manifest.data_quality_score < 100
    assert any("not attested" in issue for issue in result.issues)

    listed = service.store.list(user_id=1)
    assert listed.count == 1
    assert listed.items[0].dataset_ref == "btc-real-history:v1"
    manifest = service.store.get_manifest(1, "btc-real-history", "v1")
    assert manifest.stored_candle_count == 60
    assert manifest.canonical_sha256 == result.canonical_sha256
    loaded = service.store.load_candles(1, "btc-real-history", "v1")
    assert len(loaded) == 60
    assert loaded[0].timestamp == result.first_candle.timestamp
    assert service.store.list(user_id=2).count == 0
    with pytest.raises(HistoricalDataError, match="historical_dataset_not_found"):
        service.store.get_manifest(2, "btc-real-history", "v1")
    assert database.schema_version() == LATEST_SCHEMA_VERSION == 18


def test_dataset_version_is_immutable_and_idempotent(tmp_path):
    candles, start = _candles()
    provider = _FakeHistoricalProvider(candles)
    service = HistoricalDataService(
        DatabaseManager(db_path=str(tmp_path / "immutable.db")),
        providers={"okx": provider},
    )
    first = asyncio.run(service.collect(_request(start), user_id=1))
    repeated = asyncio.run(service.collect(_request(start), user_id=1))
    assert repeated.canonical_sha256 == first.canonical_sha256
    assert service.store.list(user_id=1).count == 1

    changed = list(candles)
    changed[0] = changed[0].model_copy(update={"close": changed[0].close + 0.25})
    service.providers["okx"] = _FakeHistoricalProvider(changed)
    with pytest.raises(HistoricalDataError, match="immutable_dataset_version_conflict"):
        asyncio.run(service.collect(_request(start), user_id=1))


def test_current_open_candle_is_rejected(tmp_path):
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=10)
    candles = [
        Candle(
            timestamp=start + timedelta(minutes=15 * index),
            open=100,
            high=101,
            low=99,
            close=100.5,
            volume=1,
        )
        for index in range(40)
    ]
    candles.append(
        Candle(
            timestamp=now - timedelta(minutes=5),
            open=100,
            high=101,
            low=99,
            close=100.5,
            volume=1,
        )
    )
    service = HistoricalDataService(
        DatabaseManager(db_path=str(tmp_path / "finalized.db")),
        providers={"okx": _FakeHistoricalProvider(candles)},
    )
    result = asyncio.run(
        service.collect(
            _request(
                start,
                end_time=now + timedelta(hours=1),
                persist=False,
            ),
            user_id=1,
        )
    )
    assert result.accepted_rows == 40
    assert result.rejected_rows == 1
    assert result.last_candle.timestamp < now - timedelta(minutes=14)


def test_yahoo_range_limits_fail_before_network_call():
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    request = HistoricalDataCollectRequest(
        dataset_id="eurusd-long-intraday",
        version="v1",
        provider="yahoo",
        symbol="EURUSD",
        market=MarketType.forex,
        timeframe="15m",
        start_time=start,
        end_time=start + timedelta(days=365),
        max_candles=1000,
    )
    with pytest.raises(HistoricalDataError, match="yahoo_intraday_range_exceeds_provider_limit"):
        asyncio.run(YahooHistoricalProvider().fetch(request))


def test_missing_dataset_returns_sanitized_not_found(tmp_path):
    service = HistoricalDataService(
        DatabaseManager(db_path=str(tmp_path / "missing.db")),
        providers={},
    )
    with pytest.raises(HistoricalDataError, match="historical_dataset_not_found"):
        service.store.get_manifest(1, "missing", "v1")
