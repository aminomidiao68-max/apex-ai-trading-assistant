from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import pytest

from app.models import (
    Candle,
    MarketType,
    PaperCorrelationDatasetRef,
    PaperCorrelationSnapshotRequest,
    PaperExecutionControlUpdateRequest,
    PaperOrderCreateRequest,
    QuantDatasetManifest,
)
from app.services.database_service import DatabaseManager, LATEST_SCHEMA_VERSION
from app.services.historical_data_service import HistoricalDatasetStore
from app.services.paper_correlation_service import PaperCorrelationError, PaperCorrelationService
from app.services.paper_oms_service import PaperOmsError, PaperOmsService


def _services(tmp_path):
    database = DatabaseManager(db_path=str(tmp_path / "correlation.db"))
    store = HistoricalDatasetStore(database)
    return database, store, PaperCorrelationService(database, store), PaperOmsService(database)


def _save_series(store, user_id: int, dataset_id: str, symbol: str, returns: list[float], timeframe: str = "1h"):
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    close = 100.0
    candles = [Candle(timestamp=start, open=close, high=close, low=close, close=close, volume=1000)]
    for index, value in enumerate(returns, start=1):
        previous = close
        close = close * math.exp(value)
        candles.append(
            Candle(
                timestamp=start + timedelta(hours=index),
                open=previous,
                high=max(previous, close) * 1.001,
                low=min(previous, close) * 0.999,
                close=close,
                volume=1000 + index,
            )
        )
    manifest = QuantDatasetManifest(
        dataset_id=dataset_id,
        version="v1",
        source="correlation_fixture",
        symbol=symbol,
        market=MarketType.crypto,
        timeframe=timeframe,
        start_time=candles[0].timestamp,
        end_time=candles[-1].timestamp,
        sample_count=len(candles),
        source_sha256=(dataset_id[0].lower() if dataset_id[0].lower() in "abcdef" else "a") * 64,
        is_point_in_time=True,
        data_quality_score=100,
    )
    canonical = ("b" if symbol.startswith("BTC") else "c") * 64
    store.save(user_id, manifest, canonical, candles)


def _returns(count: int = 120):
    return [0.002 * math.sin(index / 4.0) + (0.0004 if index % 3 == 0 else -0.0002) for index in range(count)]


def _request(snapshot_id: str = "correlation-snapshot-0001"):
    return PaperCorrelationSnapshotRequest(
        snapshot_id=snapshot_id,
        datasets=[
            PaperCorrelationDatasetRef(dataset_id="btc-correlation", version="v1"),
            PaperCorrelationDatasetRef(dataset_id="eth-correlation", version="v1"),
        ],
        minimum_observations=60,
        cluster_threshold=0.70,
    )


def test_stored_dataset_correlation_is_aligned_shrunk_idempotent_and_user_scoped(tmp_path):
    database, store, service, _ = _services(tmp_path)
    base = _returns()
    _save_series(store, 1, "btc-correlation", "BTCUSDT", base)
    _save_series(store, 1, "eth-correlation", "ETHUSDT", [value * 0.98 + 0.00001 for value in base])
    first = service.build_snapshot(1, _request())
    second = service.build_snapshot(1, _request())
    assert first.observations == 120
    assert first.matrix["BTCUSDT"]["ETHUSDT"] > 0.70
    assert first.matrix["BTCUSDT"]["ETHUSDT"] < 1.0
    assert first.clusters == [["BTCUSDT", "ETHUSDT"]]
    assert 0 < first.shrinkage_weight < 1
    assert len(first.canonical_sha256) == 64
    assert first.correlation_source == "stored_dataset_statistical"
    assert first.actionable_for_live is False
    assert first.live_execution_enabled is False
    assert first.duplicate is False
    assert second.duplicate is True
    with pytest.raises(PaperCorrelationError, match="historical_dataset_not_found"):
        service.build_snapshot(2, _request("correlation-snapshot-user2"))
    assert database.schema_version() == LATEST_SCHEMA_VERSION == 21


def test_correlation_snapshot_requires_aligned_evidence(tmp_path):
    _, store, service, _ = _services(tmp_path)
    short = _returns(40)
    _save_series(store, 1, "btc-correlation", "BTCUSDT", short)
    _save_series(store, 1, "eth-correlation", "ETHUSDT", short)
    with pytest.raises(PaperCorrelationError, match="insufficient_aligned"):
        service.build_snapshot(1, _request())


def test_statistical_snapshot_drives_portfolio_group_gate(tmp_path):
    _, store, correlation, oms = _services(tmp_path)
    base = _returns()
    _save_series(store, 1, "btc-correlation", "BTCUSDT", base)
    _save_series(store, 1, "eth-correlation", "ETHUSDT", [value * 0.99 for value in base])
    snapshot = correlation.build_snapshot(1, _request())
    oms.update_control(
        1,
        PaperExecutionControlUpdateRequest(
            paper_trading_enabled=True,
            kill_switch_engaged=False,
            max_open_orders=10,
            max_order_notional=1_000_000,
            max_leverage=10,
            max_margin_utilization_pct=90,
            max_symbol_margin_pct=100,
            max_risk_group_margin_pct=5,
            max_directional_notional_multiple=20,
            acknowledgement="I_UNDERSTAND_PAPER_ONLY",
        ),
    )

    def order(key: str, symbol: str):
        return PaperOrderCreateRequest(
            idempotency_key=key,
            symbol=symbol,
            market=MarketType.crypto,
            side="buy",
            quantity=30,
            reference_bid=99.9,
            reference_ask=100,
            available_quantity=30,
            leverage=1,
            correlation_snapshot_id=snapshot.snapshot_id,
            signal_score=85,
            risk_approved=True,
        )

    first = oms.submit(1, order("statistical-correlation-btc-1", "BTCUSDT"))
    assert first.correlation_source == "stored_dataset_statistical"
    assert first.correlation_snapshot_id == snapshot.snapshot_id
    assert first.risk_group.startswith("statistical_cluster_")
    with pytest.raises(PaperOmsError, match="paper_risk_group_concentration_limit_exceeded"):
        oms.submit(1, order("statistical-correlation-eth-1", "ETHUSDT"))

    with pytest.raises(PaperOmsError, match="correlation_snapshot_symbol_not_found"):
        oms.submit(1, order("statistical-correlation-sol-1", "SOLUSDT"))
