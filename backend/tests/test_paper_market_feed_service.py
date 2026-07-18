from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models import (
    MarketType,
    PaperExecutionControlUpdateRequest,
    PaperFeedSubscriptionUpsertRequest,
    PaperFeedSyncRequest,
    PaperOrderCreateRequest,
)
from app.services.database_service import DatabaseManager, LATEST_SCHEMA_VERSION
from app.services.paper_market_feed_service import (
    PaperFeedError,
    PaperMarketFeedService,
    PaperProviderQuote,
)
from app.services.paper_oms_service import PaperOmsService


class FixedProvider:
    provider_name = "okx_public"

    def __init__(self, quote: PaperProviderQuote) -> None:
        self.quote = quote
        self.calls = 0

    async def fetch(self, symbol: str) -> PaperProviderQuote:
        self.calls += 1
        return self.quote


def _services(tmp_path, quote: PaperProviderQuote):
    database = DatabaseManager(db_path=str(tmp_path / "paper-feed.db"))
    oms = PaperOmsService(database)
    provider = FixedProvider(quote)
    feed = PaperMarketFeedService(database, oms, provider=provider)
    return database, oms, feed, provider


def _quote(**overrides) -> PaperProviderQuote:
    values = {
        "symbol": "BTCUSDT",
        "bid": 99.8,
        "ask": 99.9,
        "available_quantity": 4.0,
        "timestamp": datetime.now(timezone.utc),
        "provider": "okx_public",
        "source": "okx_public_real_best_bid_ask",
        "event_id": "okx_1234567890abcdef1234567890abcdef1234567890abcdef",
    }
    values.update(overrides)
    return PaperProviderQuote(**values)


def _arm(oms: PaperOmsService, user_id: int = 1, feed: bool = True):
    return oms.update_control(
        user_id,
        PaperExecutionControlUpdateRequest(
            paper_trading_enabled=True,
            kill_switch_engaged=False,
            automated_feed_enabled=feed,
            max_order_notional=100_000,
            max_tick_age_seconds=30,
            acknowledgement="I_UNDERSTAND_PAPER_ONLY",
        ),
    )


def _subscribe(feed: PaperMarketFeedService, user_id: int = 1):
    return feed.upsert_subscription(
        user_id,
        PaperFeedSubscriptionUpsertRequest(
            symbol="BTCUSDT",
            market=MarketType.crypto,
            poll_interval_seconds=15,
            acknowledgement="I_UNDERSTAND_PAPER_ONLY",
        ),
    )


def _working_limit(oms: PaperOmsService, user_id: int = 1):
    return oms.submit(
        user_id,
        PaperOrderCreateRequest(
            idempotency_key="feed-limit-order-0001",
            symbol="BTCUSDT",
            market=MarketType.crypto,
            side="buy",
            order_type="limit",
            quantity=4,
            limit_price=100,
            reference_bid=109.9,
            reference_ask=110,
            available_quantity=4,
            signal_score=85,
            risk_approved=True,
            strategy_id="feed-fixture",
        ),
    )


def test_feed_is_opt_in_real_quote_only_and_user_scoped(tmp_path):
    database, oms, feed, _ = _services(tmp_path, _quote())
    default = oms.get_control(1)
    assert default.automated_feed_enabled is False
    assert default.max_tick_age_seconds == 30
    with pytest.raises(PaperFeedError, match="paper_mode_must_be_armed"):
        _subscribe(feed)

    _arm(oms)
    subscription = _subscribe(feed)
    assert subscription.provider == "okx_public"
    assert subscription.is_real_market_quote is True
    assert subscription.live_routed is False
    assert feed.list_subscriptions(1).count == 1
    assert feed.list_subscriptions(2).count == 0
    assert database.schema_version() == LATEST_SCHEMA_VERSION == 12


def test_real_feed_fills_once_and_duplicate_tick_is_idempotent(tmp_path):
    quote = _quote()
    database, oms, feed, provider = _services(tmp_path, quote)
    _arm(oms)
    _subscribe(feed)
    order = _working_limit(oms)
    assert order.status == "working"

    # pytest-asyncio is intentionally not required by the project.
    import asyncio

    first = asyncio.run(feed.sync_user(1, PaperFeedSyncRequest()))
    assert first.success_count == 1
    assert first.items[0].event_id == quote.event_id
    assert first.items[0].duplicate_tick is False
    filled = oms.get(1, order.order_id)
    assert filled.status == "filled"
    assert len(filled.fills) == 1
    assert filled.fills[0].source == "okx_public_real_best_bid_ask"

    second = asyncio.run(feed.sync_user(1, PaperFeedSyncRequest()))
    assert second.success_count == 1
    assert second.items[0].duplicate_tick is True
    repeated = oms.get(1, order.order_id)
    assert len(repeated.fills) == 1
    with database.connection() as conn:
        ticks = conn.execute(
            "SELECT COUNT(*) AS count FROM paper_market_ticks WHERE user_id = ?",
            (1,),
        ).fetchone()
    assert int(ticks["count"]) == 1
    assert provider.calls == 2


def test_stale_provider_quote_is_rejected_and_backed_off(tmp_path):
    stale = _quote(timestamp=datetime.now(timezone.utc) - timedelta(minutes=5))
    _, oms, feed, _ = _services(tmp_path, stale)
    _arm(oms)
    _subscribe(feed)
    import asyncio

    result = asyncio.run(feed.sync_user(1, PaperFeedSyncRequest()))
    assert result.failure_count == 1
    assert result.items[0].error_code == "paper_tick_stale"
    subscription = feed.list_subscriptions(1).items[0]
    assert subscription.consecutive_failures == 1
    assert subscription.last_error_code == "paper_tick_stale"
    assert subscription.last_success_at is None


def test_feed_requires_armed_control_and_kill_switch_disables_it(tmp_path):
    _, oms, feed, _ = _services(tmp_path, _quote())
    _arm(oms)
    _subscribe(feed)
    control = oms.update_control(
        1,
        PaperExecutionControlUpdateRequest(
            paper_trading_enabled=True,
            kill_switch_engaged=True,
            automated_feed_enabled=False,
            acknowledgement="I_UNDERSTAND_PAPER_ONLY",
        ),
    )
    assert control.kill_switch_engaged is True
    assert control.automated_feed_enabled is False
    import asyncio

    result = asyncio.run(feed.sync_user(1, PaperFeedSyncRequest()))
    assert result.failure_count == 1
    assert result.items[0].error_code == "automated_paper_feed_not_armed"

    with pytest.raises(PaperFeedError, match="paper_mode_must_be_armed"):
        feed.upsert_subscription(
            1,
            PaperFeedSubscriptionUpsertRequest(
                symbol="ETHUSDT",
                market=MarketType.crypto,
                acknowledgement="I_UNDERSTAND_PAPER_ONLY",
            ),
        )


def test_tick_event_payload_conflict_is_detected(tmp_path):
    _, oms, feed, provider = _services(tmp_path, _quote())
    _arm(oms)
    _subscribe(feed)
    import asyncio

    first = asyncio.run(feed.sync_user(1, PaperFeedSyncRequest()))
    assert first.success_count == 1
    provider.quote = _quote(ask=100.1)
    second = asyncio.run(feed.sync_user(1, PaperFeedSyncRequest()))
    assert second.failure_count == 1
    assert second.items[0].error_code == "tick_event_id_payload_conflict"
