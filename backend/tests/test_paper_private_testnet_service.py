from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.models import MarketType, PaperExecutionControlUpdateRequest, PaperOrderCreateRequest, PaperRecoveryDrillRequest
from app.services.database_service import DatabaseManager, LATEST_SCHEMA_VERSION
from app.services.paper_oms_service import PaperOmsService
from app.services.paper_private_testnet_service import PaperPrivateTestnetError, PaperPrivateTestnetService


class Vault:
    def __init__(self, material=None): self.material = material
    def get_material(self, user_id, provider): return self.material


def _order(oms):
    oms.update_control(1, PaperExecutionControlUpdateRequest(
        paper_trading_enabled=True, kill_switch_engaged=False,
        max_symbol_margin_pct=100, max_risk_group_margin_pct=100,
        max_directional_notional_multiple=20,
        acknowledgement="I_UNDERSTAND_PAPER_ONLY",
    ))
    return oms.submit(1, PaperOrderCreateRequest(
        idempotency_key="private-testnet-order-1", symbol="BTCUSDT", market=MarketType.crypto,
        side="buy", quantity=2, reference_bid=99.9, reference_ask=100,
        available_quantity=2, leverage=2, signal_score=85, risk_approved=True,
    ))


def test_authenticated_private_snapshot_is_read_only_verified_and_persisted(monkeypatch, tmp_path):
    database = DatabaseManager(db_path=str(tmp_path / "private.db"))
    oms = PaperOmsService(database); order = _order(oms)
    material = SimpleNamespace(api_key="fixture-key", api_secret="fixture-secret")
    service = PaperPrivateTestnetService(database, Vault(material))

    async def fake_binance(api_key, secret):
        assert api_key == "fixture-key" and secret == "fixture-secret"
        return ([{"clientOrderId": order.order_id, "status": "FILLED", "executedQty": "2"}], [{"id": 1}])

    monkeypatch.setattr(service, "_binance", fake_binance)
    result = asyncio.run(service.reconcile(1, "binance_futures_testnet"))
    assert result.status == "CONSISTENT"
    assert result.matched_orders == 1
    assert result.provider_authenticated is True
    assert result.provider_snapshot_verified is True
    assert result.read_only is True
    assert result.order_routing_enabled is False
    assert result.actionable_for_live is False
    assert result.live_execution_enabled is False
    with database.connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS count FROM paper_private_testnet_reconciliations WHERE user_id = ?", (1,)).fetchone()
    assert int(row["count"]) == 1
    assert database.schema_version() == LATEST_SCHEMA_VERSION == 20


def test_private_reconcile_fails_closed_without_credentials(tmp_path):
    database = DatabaseManager(db_path=str(tmp_path / "missing.db"))
    service = PaperPrivateTestnetService(database, Vault())
    with pytest.raises(PaperPrivateTestnetError, match="credentials_not_configured"):
        asyncio.run(service.reconcile(1, "binance_futures_testnet"))


def test_recovery_drill_is_deterministic_offline_and_capped():
    request = PaperRecoveryDrillRequest(
        connector="bybit_testnet",
        outcomes=[False, False, False, True, False],
    )
    first = PaperPrivateTestnetService.recovery_drill(request)
    second = PaperPrivateTestnetService.recovery_drill(request)
    assert first == second
    assert first.transitions == ["backoff:10", "backoff:20", "backoff:40", "connected", "backoff:10"]
    assert first.final_state == "backoff"
    assert first.network_called is False
    assert first.order_routing_enabled is False
