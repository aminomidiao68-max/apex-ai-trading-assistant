from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx
import pytest

from app.models import (
    MarketType,
    PaperExecutionControlUpdateRequest,
    PaperFundingSettlementRequest,
    PaperOrderCreateRequest,
    PaperShadowOrderSnapshot,
    PaperShadowReconciliationRequest,
)
from app.services.database_service import DatabaseManager, LATEST_SCHEMA_VERSION
from app.services.paper_oms_service import PaperOmsError, PaperOmsService
from app.services.paper_recovery_service import PaperRecoveryError, PaperRecoveryService
import app.services.paper_recovery_service as recovery_module


def _services(tmp_path):
    database = DatabaseManager(db_path=str(tmp_path / "paper-recovery.db"))
    return database, PaperOmsService(database), PaperRecoveryService(database)


def _arm(oms: PaperOmsService, **overrides):
    values = {
        "paper_trading_enabled": True,
        "kill_switch_engaged": False,
        "max_open_orders": 10,
        "max_order_notional": 1_000_000,
        "max_leverage": 10,
        "max_margin_utilization_pct": 90,
        "max_symbol_margin_pct": 100,
        "max_risk_group_margin_pct": 100,
        "max_directional_notional_multiple": 20,
        "acknowledgement": "I_UNDERSTAND_PAPER_ONLY",
    }
    values.update(overrides)
    return oms.update_control(1, PaperExecutionControlUpdateRequest(**values))


def _order(**overrides):
    values = {
        "idempotency_key": "recovery-order-key-0001",
        "symbol": "BTCUSDT",
        "market": MarketType.crypto,
        "side": "buy",
        "order_type": "market",
        "quantity": 10,
        "reference_bid": 99.9,
        "reference_ask": 100,
        "available_quantity": 10,
        "leverage": 5,
        "margin_mode": "isolated",
        "signal_score": 85,
        "risk_approved": True,
    }
    values.update(overrides)
    return PaperOrderCreateRequest(**values)


def test_schema_checkpoint_defaults_and_user_isolation(tmp_path):
    database, _, recovery = _services(tmp_path)
    first = recovery.list_checkpoints(1)
    second = recovery.list_checkpoints(2)
    assert first.count == 2
    assert second.count == 2
    assert {item.connector for item in first.items} == {
        "binance_futures_testnet",
        "bybit_testnet",
    }
    assert all(item.state == "unknown" for item in first.items)
    assert all(item.public_connectivity_only for item in first.items)
    assert all(not item.authenticated for item in first.items)
    assert all(not item.order_routing_enabled for item in first.items)
    assert all(not item.live_execution_enabled for item in first.items)
    assert database.schema_version() == LATEST_SCHEMA_VERSION == 17


def test_public_testnet_probe_records_latency_clock_and_never_routes(monkeypatch, tmp_path):
    _, _, recovery = _services(tmp_path)

    class Response:
        is_success = True

        def json(self):
            return {"serverTime": int(datetime.now(timezone.utc).timestamp() * 1000)}

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, headers=None):
            assert url == "https://demo-fapi.binance.com/fapi/v1/time"
            return Response()

    monkeypatch.setattr(recovery_module.httpx, "AsyncClient", Client)
    result = asyncio.run(recovery.probe_connector(1, "binance_futures_testnet"))
    assert result.state == "connected"
    assert result.latency_ms is not None
    assert result.server_time_offset_ms is not None
    assert result.authenticated is False
    assert result.order_routing_enabled is False
    assert result.public_connectivity_only is True
    assert result.live_execution_enabled is False


def test_probe_failure_enters_sanitized_backoff(monkeypatch, tmp_path):
    _, _, recovery = _services(tmp_path)
    calls = {"count": 0}

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, headers=None):
            calls["count"] += 1
            raise httpx.ConnectError("fixture detail must not be stored")

    monkeypatch.setattr(recovery_module.httpx, "AsyncClient", Client)
    failed = asyncio.run(recovery.probe_connector(1, "bybit_testnet"))
    blocked = asyncio.run(recovery.probe_connector(1, "bybit_testnet"))
    assert failed.state == "backoff"
    assert failed.last_error_code == "public_probe_network_unavailable"
    assert "fixture" not in (failed.last_error_code or "")
    assert blocked.state == "backoff"
    assert calls["count"] == 1


def test_shadow_reconciliation_is_idempotent_unverified_and_user_scoped(tmp_path):
    _, oms, recovery = _services(tmp_path)
    _arm(oms)
    order = oms.submit(1, _order())
    request = PaperShadowReconciliationRequest(
        run_id="shadow-reconcile-run-0001",
        connector="binance_futures_testnet",
        snapshot_id="snapshot-0001",
        snapshot_timestamp=datetime.now(timezone.utc),
        orders=[
            PaperShadowOrderSnapshot(
                order_id=order.order_id,
                status=order.status,
                filled_quantity=order.filled_quantity,
                average_fill_price=order.average_fill_price,
                total_fees=order.total_fees,
            )
        ],
    )
    first = recovery.reconcile_shadow_snapshot(1, request)
    second = recovery.reconcile_shadow_snapshot(1, request)
    economic_duplicate = recovery.reconcile_shadow_snapshot(
        1,
        request.model_copy(update={"run_id": "shadow-reconcile-run-0002"}),
    )
    assert first.status == "CONSISTENT"
    assert first.matched_orders == 1
    assert first.duplicate is False
    assert second.duplicate is True
    assert economic_duplicate.duplicate is True
    assert first.snapshot_verified_by_provider is False
    assert first.actionable_for_live is False
    assert first.live_execution_enabled is False

    with pytest.raises(PaperRecoveryError, match="shadow_run_id_payload_conflict"):
        recovery.reconcile_shadow_snapshot(
            1,
            request.model_copy(
                update={
                    "orders": [
                        request.orders[0].model_copy(update={"filled_quantity": 999})
                    ]
                }
            ),
        )


def test_ledger_audit_replays_fills_funding_and_detects_tampering(tmp_path):
    _, oms, recovery = _services(tmp_path)
    _arm(oms)
    order = oms.submit(1, _order())
    oms.settle_funding(
        1,
        PaperFundingSettlementRequest(
            event_id="audit-funding-event-0001",
            symbol="BTCUSDT",
            funding_rate=0.001,
            timestamp=datetime.now(timezone.utc),
        ),
    )
    audit = recovery.audit_ledger(1)
    assert audit.consistent is True
    assert audit.order_count == 1
    assert audit.fill_count == 1
    assert audit.margin_event_count == 1
    assert audit.repair_performed is False
    assert audit.actionable_for_live is False

    with oms.database.connection() as conn:
        conn.execute(
            "UPDATE paper_orders SET filled_quantity = ? WHERE order_id = ?",
            (999, order.order_id),
        )
        conn.commit()
    broken = recovery.audit_ledger(1)
    assert broken.consistent is False
    assert f"order_fill_quantity_mismatch:{order.order_id}" in broken.issues


def test_structural_proxy_concentration_gates(tmp_path):
    _, oms, _ = _services(tmp_path)
    _arm(
        oms,
        max_symbol_margin_pct=5,
        max_risk_group_margin_pct=10,
        max_directional_notional_multiple=20,
    )
    with pytest.raises(PaperOmsError, match="paper_symbol_margin_concentration_limit_exceeded"):
        oms.submit(
            1,
            _order(quantity=60, leverage=1),
        )

    _arm(
        oms,
        max_symbol_margin_pct=10,
        max_risk_group_margin_pct=10,
        max_directional_notional_multiple=20,
    )
    first = oms.submit(
        1,
        _order(
            idempotency_key="risk-group-major-btc-1",
            quantity=60,
            available_quantity=60,
            leverage=1,
        ),
    )
    assert first.risk_group == "crypto_major_structural_proxy"
    assert first.correlation_source == "structural_proxy"
    with pytest.raises(PaperOmsError, match="paper_risk_group_concentration_limit_exceeded"):
        oms.submit(
            1,
            _order(
                idempotency_key="risk-group-major-eth-1",
                symbol="ETHUSDT",
                quantity=60,
                available_quantity=60,
                leverage=1,
            ),
        )


def test_fill_time_structural_group_gate_blocks_overcommitted_working_order(tmp_path):
    _, oms, _ = _services(tmp_path)
    _arm(
        oms,
        max_symbol_margin_pct=100,
        max_risk_group_margin_pct=10,
        max_directional_notional_multiple=20,
    )
    for symbol, suffix in (("BTCUSDT", "btc"), ("ETHUSDT", "eth")):
        working = oms.submit(
            1,
            _order(
                idempotency_key=f"working-group-{suffix}-1",
                symbol=symbol,
                order_type="limit",
                quantity=60,
                available_quantity=60,
                leverage=1,
                limit_price=90,
            ),
        )
        assert working.status == "working"
    from app.models import PaperMarketTickRequest

    oms.process_tick(
        1,
        PaperMarketTickRequest(
            symbol="BTCUSDT",
            bid=89.8,
            ask=89.9,
            available_quantity=60,
            timestamp=datetime.now(timezone.utc),
            event_id="working-group-btc-tick-1",
        ),
    )
    eth = oms.process_tick(
        1,
        PaperMarketTickRequest(
            symbol="ETHUSDT",
            bid=89.8,
            ask=89.9,
            available_quantity=60,
            timestamp=datetime.now(timezone.utc),
            event_id="working-group-eth-tick-1",
        ),
    ).items[0]
    assert eth.status == "canceled"
    assert eth.events[-1].reason == "risk_group_concentration_changed_before_fill"


def test_directional_exposure_gate_is_independent(tmp_path):
    _, oms, _ = _services(tmp_path)
    _arm(
        oms,
        max_symbol_margin_pct=100,
        max_risk_group_margin_pct=100,
        max_directional_notional_multiple=0.1,
    )
    with pytest.raises(PaperOmsError, match="paper_directional_exposure_limit_exceeded"):
        oms.submit(1, _order(quantity=200, leverage=10))
