from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.config import settings
from app.models import PaperTestnetExecutionControlUpdate, PaperTestnetOrderRequest
from app.services.database_service import DatabaseManager, LATEST_SCHEMA_VERSION
from app.services.paper_testnet_execution_service import PaperTestnetExecutionError, PaperTestnetExecutionService


class Vault:
    def get_material(self, user_id, provider):
        return SimpleNamespace(api_key="fixture", api_secret="fixture-secret")


def _service(tmp_path):
    return PaperTestnetExecutionService(DatabaseManager(db_path=str(tmp_path / "testnet.db")), Vault())


def _request(**overrides):
    values=dict(idempotency_key="testnet-order-key-0001",connector="binance_futures_testnet",symbol="BTCUSDT",side="buy",quantity=0.001,reference_price=50000,reduce_only=False)
    values.update(overrides);return PaperTestnetOrderRequest(**values)


def _enable(monkeypatch):
    monkeypatch.setattr(settings,"app_env","staging");monkeypatch.setattr(settings,"enable_testnet_execution",True);monkeypatch.setattr(settings,"enable_live_execution",False)


def test_testnet_execution_is_disabled_and_killed_by_default(tmp_path):
    service=_service(tmp_path);control=service.get_control(1)
    assert control.enabled is False and control.kill_switch_engaged is True
    assert control.testnet_execution_flag is False and control.live_execution_enabled is False
    with pytest.raises(PaperTestnetExecutionError,match="environment_gate"):
        service.update_control(1,PaperTestnetExecutionControlUpdate(enabled=True,kill_switch_engaged=False,acknowledgement="I_UNDERSTAND_TESTNET_ONLY"))
    assert service.database.schema_version()==LATEST_SCHEMA_VERSION==15


def test_idempotent_testnet_place_is_allowlisted_and_never_live(monkeypatch,tmp_path):
    _enable(monkeypatch);service=_service(tmp_path)
    service.update_control(1,PaperTestnetExecutionControlUpdate(enabled=True,kill_switch_engaged=False,max_order_notional=100,max_open_orders=2,allowed_symbols=["BTCUSDT"],acknowledgement="I_UNDERSTAND_TESTNET_ONLY"))
    calls={"n":0}
    async def fake(material,request,client_id): calls["n"]+=1;return "external-1","accepted"
    monkeypatch.setattr(service,"_binance_place",fake)
    first=asyncio.run(service.place(1,_request()));second=asyncio.run(service.place(1,_request()))
    assert first.status=="accepted" and first.testnet_only is True and first.live_routed is False
    assert second.idempotent_replay is True and calls["n"]==1
    cancel_calls={"n":0}
    async def fake_cancel(material,row): cancel_calls["n"]+=1
    monkeypatch.setattr(service,"_cancel_provider",fake_cancel)
    canceled=asyncio.run(service.cancel(1,first.order_id));replayed_cancel=asyncio.run(service.cancel(1,first.order_id))
    assert canceled.status=="canceled" and replayed_cancel.idempotent_replay is True and cancel_calls["n"]==1
    with pytest.raises(PaperTestnetExecutionError,match="idempotency_conflict"):
        asyncio.run(service.place(1,_request(quantity=0.002)))
    with pytest.raises(PaperTestnetExecutionError,match="symbol_not_allowed"):
        asyncio.run(service.place(1,_request(idempotency_key="testnet-order-key-0002",symbol="ETHUSDT")))


def test_unknown_transport_engages_testnet_kill_switch(monkeypatch,tmp_path):
    _enable(monkeypatch);service=_service(tmp_path)
    service.update_control(1,PaperTestnetExecutionControlUpdate(enabled=True,kill_switch_engaged=False,max_order_notional=100,allowed_symbols=["BTCUSDT"],acknowledgement="I_UNDERSTAND_TESTNET_ONLY"))
    async def broken(*args): raise RuntimeError("disconnect")
    monkeypatch.setattr(service,"_binance_place",broken)
    result=asyncio.run(service.place(1,_request()))
    assert result.status=="unknown" and result.last_error_code=="testnet_transport_unknown"
    control=service.get_control(1);assert control.kill_switch_engaged is True and control.enabled is False
