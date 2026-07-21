from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models import (
    MarketType,
    PaperExecutionControlUpdateRequest,
    PaperFundingSettlementRequest,
    PaperMarketTickRequest,
    PaperOrderCreateRequest,
)
from app.services.database_service import DatabaseManager, LATEST_SCHEMA_VERSION
from app.services.paper_oms_service import PaperOmsError, PaperOmsService


def _service(tmp_path) -> PaperOmsService:
    return PaperOmsService(DatabaseManager(db_path=str(tmp_path / "paper-margin.db")))


def _arm(service: PaperOmsService, **overrides):
    values = {
        "paper_trading_enabled": True,
        "kill_switch_engaged": False,
        "max_open_orders": 10,
        "max_order_notional": 1_000_000,
        "max_leverage": 10,
        "default_maintenance_margin_rate": 0.005,
        "liquidation_fee_bps": 20,
        "max_margin_utilization_pct": 70,
        "max_symbol_margin_pct": 100,
        "max_risk_group_margin_pct": 100,
        "max_directional_notional_multiple": 20,
        "acknowledgement": "I_UNDERSTAND_PAPER_ONLY",
    }
    values.update(overrides)
    return service.update_control(1, PaperExecutionControlUpdateRequest(**values))


def _order(**overrides) -> PaperOrderCreateRequest:
    values = {
        "idempotency_key": "margin-order-key-0001",
        "symbol": "BTCUSDT",
        "market": MarketType.crypto,
        "side": "buy",
        "order_type": "market",
        "quantity": 100.0,
        "reference_bid": 99.9,
        "reference_ask": 100.0,
        "available_quantity": 100.0,
        "leverage": 5.0,
        "margin_mode": "isolated",
        "max_slippage_bps": 1.0,
        "fee_bps": 4.0,
        "signal_score": 85.0,
        "risk_approved": True,
        "strategy_id": "margin-fixture",
    }
    values.update(overrides)
    return PaperOrderCreateRequest(**values)


def test_margin_control_defaults_leverage_and_utilization_gates(tmp_path):
    service = _service(tmp_path)
    control = service.get_control(1)
    assert control.max_leverage == 10
    assert control.default_maintenance_margin_rate == 0.005
    assert control.liquidation_fee_bps == 20
    assert control.max_margin_utilization_pct == 70
    _arm(service, max_leverage=5)

    with pytest.raises(PaperOmsError, match="paper_leverage_limit_exceeded"):
        service.submit(1, _order(leverage=6))
    with pytest.raises(PaperOmsError, match="paper_margin_utilization_limit_exceeded"):
        service.submit(
            1,
            _order(
                idempotency_key="margin-utilization-gate-1",
                quantity=800,
                leverage=1,
            ),
        )
    assert service.database.schema_version() == LATEST_SCHEMA_VERSION == 19


def test_isolated_margin_metrics_and_configuration_conflict(tmp_path):
    service = _service(tmp_path)
    _arm(service)
    order = service.submit(1, _order())
    assert order.leverage == 5
    assert order.margin_mode == "isolated"
    portfolio = service.get_portfolio(1)
    position = portfolio.positions[0]
    assert position.quantity == 100
    assert position.leverage == 5
    assert position.margin_mode == "isolated"
    assert position.initial_margin > 1_900
    assert position.maintenance_margin > 0
    assert 0 < position.liquidation_price < position.average_entry_price
    assert position.margin_ratio_pct is not None
    assert portfolio.used_margin == pytest.approx(position.initial_margin)
    assert portfolio.free_margin == pytest.approx(portfolio.equity - portfolio.used_margin)
    assert 0 < portfolio.margin_utilization_pct < 70
    assert portfolio.margin_level_pct is not None

    with pytest.raises(PaperOmsError, match="position_margin_configuration_conflict"):
        service.submit(
            1,
            _order(
                idempotency_key="margin-config-conflict-1",
                quantity=1,
                leverage=4,
            ),
        )


def test_funding_is_signed_idempotent_and_never_claimed_real(tmp_path):
    service = _service(tmp_path)
    _arm(service)
    service.submit(1, _order(quantity=10))
    before = service.get_portfolio(1)
    request = PaperFundingSettlementRequest(
        event_id="funding-event-key-0001",
        symbol="BTCUSDT",
        funding_rate=0.001,
        timestamp=datetime.now(timezone.utc),
        source="user_supplied_fixture",
    )
    first = service.settle_funding(1, request)
    second = service.settle_funding(1, request)
    economic_duplicate = service.settle_funding(
        1,
        request.model_copy(update={"event_id": "funding-event-key-0002"}),
    )
    assert first.duplicate is False
    assert second.duplicate is True
    assert economic_duplicate.duplicate is True
    assert economic_duplicate.event.event_id == request.event_id
    assert first.event.amount > 0  # Long pays a positive funding rate.
    assert first.event.is_real_rate is False
    assert first.event.live_routed is False
    assert first.cash_balance < before.cash_balance
    assert second.cash_balance == pytest.approx(first.cash_balance)
    portfolio = service.get_portfolio(1)
    assert portfolio.total_funding == pytest.approx(first.event.amount)
    assert portfolio.positions[0].accumulated_funding == pytest.approx(first.event.amount)
    assert service.list_margin_events(1).count == 1
    assert service.list_margin_events(2).count == 0

    with pytest.raises(PaperOmsError, match="funding_event_id_payload_conflict"):
        service.settle_funding(
            1,
            request.model_copy(update={"funding_rate": 0.002}),
        )


def test_short_receives_positive_funding(tmp_path):
    service = _service(tmp_path)
    _arm(service)
    service.submit(
        1,
        _order(
            idempotency_key="margin-short-funding-1",
            side="sell",
            quantity=10,
        ),
    )
    before = service.get_portfolio(1)
    result = service.settle_funding(
        1,
        PaperFundingSettlementRequest(
            event_id="funding-short-key-0001",
            symbol="BTCUSDT",
            funding_rate=0.001,
            timestamp=datetime.now(timezone.utc),
        ),
    )
    assert result.event.amount < 0
    assert result.cash_balance > before.cash_balance


def test_isolated_liquidation_is_conservative_and_engages_kill_switch(tmp_path):
    service = _service(tmp_path)
    _arm(service, max_daily_drawdown_pct=20)
    service.submit(1, _order(leverage=10, quantity=100))
    before = service.get_portfolio(1).positions[0]
    assert 89 < before.liquidation_price < 92

    result = service.mark_portfolio(
        1,
        PaperMarketTickRequest(
            symbol="BTCUSDT",
            bid=88.9,
            ask=89.1,
            available_quantity=1_000,
            timestamp=datetime.now(timezone.utc),
            source="liquidation_fixture",
            event_id="liquidation-tick-0001",
        ),
    )
    position = result.positions[0]
    assert position.quantity == 0
    assert position.position_status == "liquidated"
    assert position.liquidated_at is not None
    assert result.liquidation_count == 1
    assert result.used_margin == 0
    assert result.kill_switch_engaged is True
    assert service.get_control(1).automated_feed_enabled is False
    events = service.list_margin_events(1)
    assert events.count == 1
    assert events.items[0].event_type == "liquidation"
    assert events.items[0].amount > 0
    assert events.items[0].realized_pnl < 0
    assert events.items[0].live_routed is False


def test_tick_liquidity_is_shared_fifo_across_working_orders(tmp_path):
    service = _service(tmp_path)
    _arm(service)
    for index in (1, 2):
        service.submit(
            1,
            _order(
                idempotency_key=f"shared-liquidity-order-{index}",
                order_type="limit",
                quantity=5,
                available_quantity=5,
                limit_price=90,
            ),
        )
    result = service.process_tick(
        1,
        PaperMarketTickRequest(
            symbol="BTCUSDT",
            bid=89.8,
            ask=89.9,
            available_quantity=6,
            timestamp=datetime.now(timezone.utc),
            event_id="shared-liquidity-tick-1",
        ),
    )
    assert sorted(item.filled_quantity for item in result.items) == [1.0, 5.0]
    assert sorted(item.status for item in result.items) == ["filled", "partially_filled"]
    assert sum(item.filled_quantity for item in result.items) == 6


def test_fill_time_margin_gate_cancels_overcommitted_working_order(tmp_path):
    service = _service(tmp_path)
    _arm(service, max_margin_utilization_pct=70)
    for index in (1, 2):
        working = service.submit(
            1,
            _order(
                idempotency_key=f"margin-working-reservation-{index}",
                order_type="limit",
                quantity=400,
                available_quantity=400,
                leverage=1,
                limit_price=90,
                reference_bid=99.9,
                reference_ask=100,
            ),
        )
        assert working.status == "working"
    processed = service.process_tick(
        1,
        PaperMarketTickRequest(
            symbol="BTCUSDT",
            bid=89.8,
            ask=89.9,
            available_quantity=800,
            timestamp=datetime.now(timezone.utc),
            event_id="margin-fill-gate-tick-1",
        ),
    )
    statuses = sorted(item.status for item in processed.items)
    assert statuses == ["canceled", "filled"]
    canceled = next(item for item in processed.items if item.status == "canceled")
    assert canceled.events[-1].reason == "margin_utilization_changed_before_fill"
    assert service.get_portfolio(1).margin_utilization_pct <= 70


def test_cross_margin_liquidates_group_when_shared_collateral_is_exhausted(tmp_path):
    service = _service(tmp_path)
    _arm(service, max_daily_drawdown_pct=20)
    service.submit(
        1,
        _order(
            idempotency_key="cross-liquidation-order-1",
            quantity=6_000,
            available_quantity=6_000,
            leverage=10,
            margin_mode="cross",
        ),
    )
    before = service.get_portfolio(1)
    assert before.positions[0].margin_mode == "cross"
    assert before.margin_utilization_pct < 70
    result = service.mark_portfolio(
        1,
        PaperMarketTickRequest(
            symbol="BTCUSDT",
            bid=82.9,
            ask=83.1,
            available_quantity=10_000,
            timestamp=datetime.now(timezone.utc),
            event_id="cross-liquidation-tick-1",
        ),
    )
    assert result.positions[0].position_status == "liquidated"
    assert result.positions[0].quantity == 0
    assert result.liquidation_count == 1
    assert result.kill_switch_engaged is True


def test_mark_to_market_remains_available_while_kill_switch_is_engaged(tmp_path):
    service = _service(tmp_path)
    _arm(service)
    service.submit(1, _order(quantity=10, leverage=2))
    service.update_control(
        1,
        PaperExecutionControlUpdateRequest(
            paper_trading_enabled=True,
            kill_switch_engaged=True,
            acknowledgement="I_UNDERSTAND_PAPER_ONLY",
        ),
    )
    marked = service.mark_portfolio(
        1,
        PaperMarketTickRequest(
            symbol="BTCUSDT",
            bid=109.9,
            ask=110.1,
            available_quantity=100,
            timestamp=datetime.now(timezone.utc),
            event_id="kill-switch-mark-tick-1",
        ),
    )
    assert marked.kill_switch_engaged is True
    assert marked.positions[0].quantity == 10
    assert marked.unrealized_pnl > 0


def test_risk_reducing_close_remains_allowed_after_leverage_limit_is_lowered(tmp_path):
    service = _service(tmp_path)
    _arm(service, max_leverage=10)
    service.submit(1, _order(leverage=10, quantity=10))
    _arm(service, max_leverage=5)
    closed = service.submit(
        1,
        _order(
            idempotency_key="margin-risk-reducing-close-1",
            side="sell",
            leverage=10,
            quantity=10,
        ),
    )
    assert closed.status == "filled"
    assert service.get_portfolio(1).positions[0].quantity == 0


def test_partial_close_releases_margin_and_direction_flip_reallocates(tmp_path):
    service = _service(tmp_path)
    _arm(service)
    service.submit(1, _order(quantity=10, leverage=5))
    initial = service.get_portfolio(1).positions[0]
    service.submit(
        1,
        _order(
            idempotency_key="margin-partial-close-1",
            side="sell",
            quantity=4,
            leverage=5,
        ),
    )
    partial = service.get_portfolio(1).positions[0]
    assert partial.quantity == 6
    assert partial.initial_margin < initial.initial_margin

    service.submit(
        1,
        _order(
            idempotency_key="margin-direction-flip-1",
            side="sell",
            quantity=10,
            leverage=4,
            margin_mode="cross",
        ),
    )
    flipped = service.get_portfolio(1).positions[0]
    assert flipped.quantity == -4
    assert flipped.leverage == 4
    assert flipped.margin_mode == "cross"
    assert flipped.initial_margin > 0
