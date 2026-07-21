from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models import (
    MarketType,
    PaperExecutionControlUpdateRequest,
    PaperMarketTickRequest,
    PaperOrderCreateRequest,
)
from app.services.database_service import DatabaseManager, LATEST_SCHEMA_VERSION
from app.services.paper_oms_service import PaperOmsError, PaperOmsService


def _service(tmp_path) -> PaperOmsService:
    return PaperOmsService(DatabaseManager(db_path=str(tmp_path / "paper.db")))


def _arm(service: PaperOmsService, user_id: int = 1, **overrides):
    values = {
        "paper_trading_enabled": True,
        "kill_switch_engaged": False,
        "max_open_orders": 5,
        "max_order_notional": 100_000,
        "default_fee_bps": 4,
        "default_slippage_bps": 1,
        "acknowledgement": "I_UNDERSTAND_PAPER_ONLY",
    }
    values.update(overrides)
    return service.update_control(user_id, PaperExecutionControlUpdateRequest(**values))


def _market_order(**overrides):
    values = {
        "idempotency_key": "paper-order-key-0001",
        "symbol": "BTCUSDT",
        "market": MarketType.crypto,
        "side": "buy",
        "order_type": "market",
        "quantity": 2.0,
        "reference_bid": 99.9,
        "reference_ask": 100.0,
        "available_quantity": 2.0,
        "max_slippage_bps": 5.0,
        "fee_bps": 4.0,
        "signal_score": 85.0,
        "risk_approved": True,
        "strategy_id": "strict-core",
    }
    values.update(overrides)
    return PaperOrderCreateRequest(**values)


def test_paper_mode_is_disabled_and_kill_switch_engaged_by_default(tmp_path):
    service = _service(tmp_path)
    control = service.get_control(1)
    assert control.paper_trading_enabled is False
    assert control.kill_switch_engaged is True
    assert control.live_execution_enabled is False
    with pytest.raises(PaperOmsError, match="paper_trading_disabled"):
        service.submit(1, _market_order())
    with pytest.raises(ValueError, match="I_UNDERSTAND_PAPER_ONLY"):
        PaperExecutionControlUpdateRequest(
            paper_trading_enabled=True,
            kill_switch_engaged=False,
        )


def test_market_order_fill_is_conservative_idempotent_and_reconciled(tmp_path):
    service = _service(tmp_path)
    _arm(service)
    request = _market_order()
    order = service.submit(1, request)
    repeated = service.submit(1, request)

    assert order.order_id == repeated.order_id
    assert order.status == "filled"
    assert order.filled_quantity == 2.0
    assert order.remaining_quantity == 0.0
    assert order.average_fill_price > request.reference_ask
    assert order.total_fees > 0
    assert order.live_routed is False
    assert [event.sequence for event in order.events] == list(range(1, len(order.events) + 1))
    assert [event.to_status for event in order.events] == ["accepted", "working", "filled"]
    assert service.reconcile(1, order.order_id).consistent is True

    with pytest.raises(PaperOmsError, match="idempotency_key_payload_conflict"):
        service.submit(1, _market_order(quantity=3.0))


def test_limit_order_partial_fills_then_completes(tmp_path):
    service = _service(tmp_path)
    _arm(service)
    request = _market_order(
        idempotency_key="paper-limit-key-0001",
        order_type="limit",
        quantity=10.0,
        limit_price=100.0,
        reference_bid=100.5,
        reference_ask=101.0,
        available_quantity=10.0,
        max_slippage_bps=2.0,
    )
    working = service.submit(1, request)
    assert working.status == "working"
    assert not working.fills

    first = service.process_tick(
        1,
        PaperMarketTickRequest(
            symbol="BTCUSDT",
            bid=99.7,
            ask=99.8,
            available_quantity=4.0,
            timestamp=datetime.now(timezone.utc),
            source="paper_depth_fixture",
        ),
    ).items[0]
    assert first.status == "partially_filled"
    assert first.filled_quantity == 4.0
    assert first.remaining_quantity == 6.0
    assert first.average_fill_price <= request.limit_price

    second = service.process_tick(
        1,
        PaperMarketTickRequest(
            symbol="BTCUSDT",
            bid=99.8,
            ask=99.9,
            available_quantity=6.0,
            timestamp=datetime.now(timezone.utc),
            source="paper_depth_fixture",
        ),
    ).items[0]
    assert second.status == "filled"
    assert second.filled_quantity == 10.0
    assert len(second.fills) == 2
    assert service.reconcile(1, second.order_id).consistent is True


def test_ioc_and_fok_apply_liquidity_rules(tmp_path):
    service = _service(tmp_path)
    _arm(service)
    ioc = service.submit(
        1,
        _market_order(
            idempotency_key="paper-ioc-key-0001",
            quantity=10,
            available_quantity=3,
            time_in_force="IOC",
        ),
    )
    assert ioc.status == "canceled"
    assert ioc.filled_quantity == 3
    assert ioc.remaining_quantity == 7

    fok = service.submit(
        1,
        _market_order(
            idempotency_key="paper-fok-key-0001",
            quantity=10,
            available_quantity=3,
            time_in_force="FOK",
        ),
    )
    assert fok.status == "canceled"
    assert fok.filled_quantity == 0
    assert not fok.fills


def test_kill_switch_cancels_open_orders_and_blocks_ticks(tmp_path):
    service = _service(tmp_path)
    _arm(service)
    working = service.submit(
        1,
        _market_order(
            idempotency_key="paper-kill-key-0001",
            order_type="limit",
            limit_price=90,
            reference_bid=99,
            reference_ask=100,
        ),
    )
    assert working.status == "working"
    control = service.update_control(
        1,
        PaperExecutionControlUpdateRequest(
            paper_trading_enabled=True,
            kill_switch_engaged=True,
            acknowledgement="I_UNDERSTAND_PAPER_ONLY",
        ),
    )
    assert control.kill_switch_engaged is True
    canceled = service.get(1, working.order_id)
    assert canceled.status == "canceled"
    assert canceled.events[-1].event_type == "kill_switch_cancel"
    with pytest.raises(PaperOmsError, match="paper_execution_not_armed"):
        service.process_tick(
            1,
            PaperMarketTickRequest(
                symbol="BTCUSDT",
                bid=89,
                ask=90,
                available_quantity=10,
                timestamp=datetime.now(timezone.utc),
            ),
        )


def test_risk_notional_open_order_and_user_isolation_gates(tmp_path):
    service = _service(tmp_path)
    _arm(service, max_open_orders=1, max_order_notional=1_000)
    with pytest.raises(PaperOmsError, match="risk_approval_required"):
        service.submit(1, _market_order(risk_approved=False))
    with pytest.raises(PaperOmsError, match="signal_score"):
        service.submit(1, _market_order(signal_score=70))
    with pytest.raises(PaperOmsError, match="notional"):
        service.submit(1, _market_order(quantity=100))

    working = service.submit(
        1,
        _market_order(
            idempotency_key="paper-open-key-0001",
            order_type="limit",
            limit_price=90,
        ),
    )
    with pytest.raises(PaperOmsError, match="max_open"):
        service.submit(
            1,
            _market_order(
                idempotency_key="paper-open-key-0002",
                order_type="limit",
                limit_price=90,
            ),
        )
    with pytest.raises(PaperOmsError, match="paper_order_not_found"):
        service.get(2, working.order_id)


def test_reconciliation_detects_database_inconsistency(tmp_path):
    service = _service(tmp_path)
    _arm(service)
    order = service.submit(1, _market_order())
    with service.database.connection() as conn:
        conn.execute(
            "UPDATE paper_orders SET filled_quantity = ? WHERE order_id = ?",
            (999.0, order.order_id),
        )
        conn.commit()
    result = service.reconcile(1, order.order_id)
    assert result.consistent is False
    assert result.filled_quantity_matches is False
    assert "filled_quantity_mismatch" in result.issues
    assert service.database.schema_version() == LATEST_SCHEMA_VERSION == 20


def test_portfolio_netting_realized_unrealized_and_fees(tmp_path):
    service = _service(tmp_path)
    _arm(service)
    buy = service.submit(
        1,
        _market_order(
            idempotency_key="paper-portfolio-buy-1",
            quantity=2,
            reference_bid=99.9,
            reference_ask=100,
        ),
    )
    portfolio = service.get_portfolio(1)
    position = next(item for item in portfolio.positions if item.symbol == "BTCUSDT")
    assert position.quantity == 2
    assert position.total_fees == buy.total_fees
    assert portfolio.cash_balance < portfolio.initial_cash

    service.mark_portfolio(
        1,
        PaperMarketTickRequest(
            symbol="BTCUSDT",
            bid=109.9,
            ask=110.1,
            available_quantity=100,
            timestamp=datetime.now(timezone.utc),
        ),
    )
    marked = service.get_portfolio(1)
    assert marked.unrealized_pnl > 0
    assert marked.equity > marked.cash_balance

    service.submit(
        1,
        _market_order(
            idempotency_key="paper-portfolio-sell-1",
            side="sell",
            quantity=2,
            reference_bid=110,
            reference_ask=110.1,
        ),
    )
    closed = service.get_portfolio(1)
    closed_position = next(item for item in closed.positions if item.symbol == "BTCUSDT")
    assert closed_position.quantity == 0
    assert closed.realized_pnl > 0
    assert closed.unrealized_pnl == 0
    assert closed.total_fees > 0


def test_daily_drawdown_automatically_engages_kill_switch(tmp_path):
    service = _service(tmp_path)
    _arm(
        service,
        max_order_notional=100_000,
        max_daily_drawdown_pct=3.0,
        automated_feed_enabled=True,
    )
    service.submit(
        1,
        _market_order(
            idempotency_key="paper-drawdown-buy-1",
                quantity=100,
                available_quantity=100,
                reference_bid=99.9,
                reference_ask=100,
        ),
    )
    portfolio = service.mark_portfolio(
        1,
        PaperMarketTickRequest(
            symbol="BTCUSDT",
            bid=59.9,
            ask=60.1,
            available_quantity=100,
            timestamp=datetime.now(timezone.utc),
        ),
    )
    assert portfolio.daily_drawdown_pct >= 3.0
    control = service.get_control(1)
    assert control.kill_switch_engaged is True
    assert control.automated_feed_enabled is False
