from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx

from app.config import settings
from app.models import (
    MarketType,
    PaperFeedStatus,
    PaperFeedSubscription,
    PaperFeedSubscriptionListResponse,
    PaperFeedSubscriptionUpsertRequest,
    PaperFeedSyncItem,
    PaperFeedSyncRequest,
    PaperFeedSyncResponse,
    PaperMarketTickRequest,
)
from app.services.database_service import DatabaseManager
from app.services.paper_oms_service import PaperOmsError, PaperOmsService


class PaperFeedError(RuntimeError):
    """A sanitized feed failure that cannot expose provider URLs or credentials."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class PaperProviderQuote:
    symbol: str
    bid: float
    ask: float
    available_quantity: float
    timestamp: datetime
    provider: str
    source: str
    event_id: str


class OkxPublicPaperQuoteProvider:
    """Public real best-bid/ask adapter. It never routes an order."""

    provider_name = "okx_public"

    @staticmethod
    def _instrument(symbol: str) -> str:
        upper = symbol.strip().upper()
        if upper.endswith("USDT") and "-" not in upper:
            return f"{upper[:-4]}-USDT"
        return upper

    async def fetch(self, symbol: str) -> PaperProviderQuote:
        instrument = self._instrument(symbol)
        try:
            async with httpx.AsyncClient(timeout=settings.paper_feed_provider_timeout_seconds) as client:
                response = await client.get(
                    "https://www.okx.com/api/v5/market/ticker",
                    params={"instId": instrument},
                    headers={"User-Agent": "APEX-Paper-Feed/1.0"},
                )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise PaperFeedError("provider_network_unavailable") from exc
        if not response.is_success:
            raise PaperFeedError("provider_http_error")
        try:
            payload = response.json()
            rows = payload.get("data") or []
            if payload.get("code") != "0" or not rows:
                raise PaperFeedError("provider_empty_quote")
            item = rows[0]
            bid = float(item["bidPx"])
            ask = float(item["askPx"])
            bid_size = float(item["bidSz"])
            ask_size = float(item["askSz"])
            provider_timestamp = datetime.fromtimestamp(int(item["ts"]) / 1000, tz=timezone.utc)
        except PaperFeedError:
            raise
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise PaperFeedError("provider_invalid_quote") from exc
        if bid <= 0 or ask <= 0 or ask < bid:
            raise PaperFeedError("provider_crossed_or_invalid_quote")
        available = min(bid_size, ask_size)
        if available <= 0:
            raise PaperFeedError("provider_liquidity_unavailable")
        identity = "|".join(
            [instrument, item["ts"], f"{bid:.12g}", f"{ask:.12g}", f"{available:.12g}"]
        )
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        return PaperProviderQuote(
            symbol=symbol.strip().upper(),
            bid=bid,
            ask=ask,
            available_quantity=available,
            timestamp=provider_timestamp,
            provider=self.provider_name,
            source="okx_public_real_best_bid_ask",
            event_id=f"okx_{digest[:48]}",
        )


class PaperMarketFeedService:
    def __init__(
        self,
        database: DatabaseManager,
        oms: PaperOmsService,
        provider: OkxPublicPaperQuoteProvider | None = None,
    ) -> None:
        self.database = database
        self.oms = oms
        self.provider = provider or OkxPublicPaperQuoteProvider()
        self.worker_id = f"paper-feed-{uuid4().hex[:16]}"

    @staticmethod
    def _now_dt() -> datetime:
        return datetime.now(timezone.utc)

    def _now(self) -> str:
        return self._now_dt().isoformat()

    @staticmethod
    def _subscription_from_row(row) -> PaperFeedSubscription:
        return PaperFeedSubscription(
            symbol=row["symbol"],
            market=MarketType(row["market"]),
            provider=row["provider"],
            enabled=bool(row["enabled"]),
            poll_interval_seconds=int(row["poll_interval_seconds"]),
            next_poll_at=row["next_poll_at"],
            last_attempt_at=row["last_attempt_at"],
            last_success_at=row["last_success_at"],
            last_provider_timestamp=row["last_provider_timestamp"],
            last_event_id=row["last_event_id"],
            consecutive_failures=int(row["consecutive_failures"] or 0),
            last_error_code=row["last_error_code"],
            updated_at=row["updated_at"],
            is_real_market_quote=True,
            live_routed=False,
        )

    def upsert_subscription(
        self,
        user_id: int,
        request: PaperFeedSubscriptionUpsertRequest,
    ) -> PaperFeedSubscription:
        control = self.oms.get_control(user_id)
        if not control.paper_trading_enabled or control.kill_switch_engaged:
            raise PaperFeedError("paper_mode_must_be_armed_before_feed_subscription")
        if request.market != MarketType.crypto:
            raise PaperFeedError("paper_feed_market_not_supported")
        symbol = request.symbol.upper()
        now = self._now()
        with self.database.connection() as conn:
            conn.execute(
                """
                INSERT INTO paper_feed_subscriptions (
                    user_id, symbol, market, provider, enabled, poll_interval_seconds,
                    next_poll_at, last_attempt_at, last_success_at,
                    last_provider_timestamp, last_event_id, consecutive_failures,
                    last_error_code, lease_owner, lease_until, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, symbol) DO UPDATE SET
                    market = excluded.market,
                    provider = excluded.provider,
                    enabled = excluded.enabled,
                    poll_interval_seconds = excluded.poll_interval_seconds,
                    next_poll_at = excluded.next_poll_at,
                    consecutive_failures = 0,
                    last_error_code = NULL,
                    lease_owner = NULL,
                    lease_until = NULL,
                    updated_at = excluded.updated_at
                """,
                (
                    user_id,
                    symbol,
                    request.market.value,
                    self.provider.provider_name,
                    1,
                    request.poll_interval_seconds,
                    now,
                    None,
                    None,
                    None,
                    None,
                    0,
                    None,
                    None,
                    None,
                    now,
                    now,
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM paper_feed_subscriptions WHERE user_id = ? AND symbol = ?",
                (user_id, symbol),
            ).fetchone()
        return self._subscription_from_row(row)

    def disable_subscription(self, user_id: int, symbol: str) -> PaperFeedSubscription:
        now = self._now()
        with self.database.connection() as conn:
            row = conn.execute(
                "SELECT symbol FROM paper_feed_subscriptions WHERE user_id = ? AND symbol = ?",
                (user_id, symbol.upper()),
            ).fetchone()
            if row is None:
                raise PaperFeedError("paper_feed_subscription_not_found")
            conn.execute(
                "UPDATE paper_feed_subscriptions SET enabled = 0, lease_owner = NULL, "
                "lease_until = NULL, updated_at = ? WHERE user_id = ? AND symbol = ?",
                (now, user_id, symbol.upper()),
            )
            conn.commit()
            result = conn.execute(
                "SELECT * FROM paper_feed_subscriptions WHERE user_id = ? AND symbol = ?",
                (user_id, symbol.upper()),
            ).fetchone()
        return self._subscription_from_row(result)

    def list_subscriptions(self, user_id: int) -> PaperFeedSubscriptionListResponse:
        with self.database.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM paper_feed_subscriptions WHERE user_id = ? ORDER BY symbol",
                (user_id,),
            ).fetchall()
        items = [self._subscription_from_row(row) for row in rows]
        return PaperFeedSubscriptionListResponse(items=items, count=len(items))

    def status(self, user_id: int) -> PaperFeedStatus:
        control = self.oms.get_control(user_id)
        now = self._now()
        with self.database.connection() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS subscription_count,
                       SUM(CASE WHEN enabled = 1 AND next_poll_at <= ? THEN 1 ELSE 0 END) AS due_count,
                       MAX(last_success_at) AS latest_success_at
                FROM paper_feed_subscriptions WHERE user_id = ?
                """,
                (now, user_id),
            ).fetchone()
            error_row = conn.execute(
                "SELECT last_error_code FROM paper_feed_subscriptions "
                "WHERE user_id = ? AND last_error_code IS NOT NULL "
                "ORDER BY last_attempt_at DESC LIMIT 1",
                (user_id,),
            ).fetchone()
        return PaperFeedStatus(
            automated_feed_enabled=control.automated_feed_enabled,
            paper_trading_enabled=control.paper_trading_enabled,
            kill_switch_engaged=control.kill_switch_engaged,
            worker_enabled=settings.paper_feed_worker_enabled,
            subscription_count=int(row["subscription_count"] or 0),
            due_subscription_count=int(row["due_count"] or 0),
            latest_success_at=row["latest_success_at"],
            latest_error_code=error_row["last_error_code"] if error_row else None,
            live_execution_enabled=settings.enable_live_execution,
        )

    def _get_subscription_row(self, user_id: int, symbol: str):
        with self.database.connection() as conn:
            row = conn.execute(
                "SELECT * FROM paper_feed_subscriptions "
                "WHERE user_id = ? AND symbol = ? AND enabled = 1",
                (user_id, symbol.upper()),
            ).fetchone()
        if row is None:
            raise PaperFeedError("paper_feed_subscription_not_found")
        return row

    def _record_success(self, user_id: int, symbol: str, quote: PaperProviderQuote) -> None:
        now_dt = self._now_dt()
        row = self._get_subscription_row(user_id, symbol)
        next_poll = now_dt + timedelta(seconds=int(row["poll_interval_seconds"]))
        with self.database.connection() as conn:
            conn.execute(
                """
                UPDATE paper_feed_subscriptions
                SET last_attempt_at = ?, last_success_at = ?, last_provider_timestamp = ?,
                    last_event_id = ?, consecutive_failures = 0, last_error_code = NULL,
                    next_poll_at = ?, lease_owner = NULL, lease_until = NULL, updated_at = ?
                WHERE user_id = ? AND symbol = ?
                """,
                (
                    now_dt.isoformat(),
                    now_dt.isoformat(),
                    quote.timestamp.isoformat(),
                    quote.event_id,
                    next_poll.isoformat(),
                    now_dt.isoformat(),
                    user_id,
                    symbol.upper(),
                ),
            )
            conn.commit()

    def _record_failure(self, user_id: int, symbol: str, code: str) -> None:
        now_dt = self._now_dt()
        with self.database.connection() as conn:
            row = conn.execute(
                "SELECT consecutive_failures, poll_interval_seconds FROM paper_feed_subscriptions "
                "WHERE user_id = ? AND symbol = ?",
                (user_id, symbol.upper()),
            ).fetchone()
            if row is None:
                return
            failures = int(row["consecutive_failures"] or 0) + 1
            base = int(row["poll_interval_seconds"])
            backoff = min(300, max(base, base * (2 ** min(failures, 5))))
            conn.execute(
                """
                UPDATE paper_feed_subscriptions
                SET last_attempt_at = ?, consecutive_failures = ?, last_error_code = ?,
                    next_poll_at = ?, lease_owner = NULL, lease_until = NULL, updated_at = ?
                WHERE user_id = ? AND symbol = ?
                """,
                (
                    now_dt.isoformat(),
                    failures,
                    code[:100],
                    (now_dt + timedelta(seconds=backoff)).isoformat(),
                    now_dt.isoformat(),
                    user_id,
                    symbol.upper(),
                ),
            )
            conn.commit()

    async def sync_subscription(self, user_id: int, symbol: str) -> PaperFeedSyncItem:
        row = self._get_subscription_row(user_id, symbol)
        control = self.oms.get_control(user_id)
        if (
            not control.paper_trading_enabled
            or control.kill_switch_engaged
            or not control.automated_feed_enabled
        ):
            code = "automated_paper_feed_not_armed"
            self._record_failure(user_id, symbol, code)
            return PaperFeedSyncItem(
                symbol=symbol.upper(), ok=False, provider=row["provider"], error_code=code
            )
        try:
            quote = await self.provider.fetch(symbol.upper())
            result = self.oms.process_tick(
                user_id,
                PaperMarketTickRequest(
                    symbol=quote.symbol,
                    bid=quote.bid,
                    ask=quote.ask,
                    available_quantity=quote.available_quantity,
                    timestamp=quote.timestamp,
                    source=quote.source,
                    event_id=quote.event_id,
                ),
            )
            self._record_success(user_id, symbol, quote)
            return PaperFeedSyncItem(
                symbol=quote.symbol,
                ok=True,
                provider=quote.provider,
                event_id=quote.event_id,
                duplicate_tick=result.duplicate_tick,
                affected_orders=result.count,
                bid=quote.bid,
                ask=quote.ask,
                provider_timestamp=quote.timestamp.isoformat(),
                is_real_market_quote=True,
                live_routed=False,
            )
        except PaperFeedError as exc:
            code = exc.code
        except PaperOmsError as exc:
            code = exc.code
        except Exception:
            code = "paper_feed_internal_error"
        self._record_failure(user_id, symbol, code)
        return PaperFeedSyncItem(
            symbol=symbol.upper(), ok=False, provider=row["provider"], error_code=code
        )

    async def sync_user(self, user_id: int, request: PaperFeedSyncRequest) -> PaperFeedSyncResponse:
        subscriptions = self.list_subscriptions(user_id).items
        enabled = [item for item in subscriptions if item.enabled]
        if request.symbols:
            requested = set(request.symbols)
            enabled = [item for item in enabled if item.symbol in requested]
        items = [await self.sync_subscription(user_id, item.symbol) for item in enabled]
        success = sum(1 for item in items if item.ok)
        return PaperFeedSyncResponse(
            items=items,
            count=len(items),
            success_count=success,
            failure_count=len(items) - success,
            live_execution_enabled=settings.enable_live_execution,
        )

    def _claim_due(self, limit: int) -> list[tuple[int, str]]:
        now_dt = self._now_dt()
        now = now_dt.isoformat()
        lease_until = (now_dt + timedelta(seconds=30)).isoformat()
        with self.database.connection() as conn:
            sql = """
                SELECT s.user_id, s.symbol
                FROM paper_feed_subscriptions s
                JOIN paper_execution_controls c ON c.user_id = s.user_id
                WHERE s.enabled = 1
                  AND c.paper_trading_enabled = 1
                  AND c.kill_switch_engaged = 0
                  AND c.automated_feed_enabled = 1
                  AND s.next_poll_at <= ?
                  AND (s.lease_until IS NULL OR s.lease_until < ?)
                ORDER BY s.next_poll_at, s.user_id, s.symbol
                LIMIT ?
            """
            if self.database.backend == "postgresql":
                sql += " FOR UPDATE OF s SKIP LOCKED"
            rows = conn.execute(sql, (now, now, max(1, min(limit, 100)))).fetchall()
            claimed = []
            for row in rows:
                conn.execute(
                    "UPDATE paper_feed_subscriptions SET lease_owner = ?, lease_until = ? "
                    "WHERE user_id = ? AND symbol = ?",
                    (self.worker_id, lease_until, row["user_id"], row["symbol"]),
                )
                claimed.append((int(row["user_id"]), str(row["symbol"])))
            conn.commit()
        return claimed

    async def run_once(self) -> int:
        claimed = self._claim_due(settings.paper_feed_worker_batch_size)
        for user_id, symbol in claimed:
            await self.sync_subscription(user_id, symbol)
        return len(claimed)

    async def run_forever(self) -> None:
        while True:
            try:
                await self.run_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                # Worker errors are isolated; per-subscription errors are stored sanitized.
                pass
            await asyncio.sleep(max(1.0, settings.paper_feed_worker_sweep_seconds))
