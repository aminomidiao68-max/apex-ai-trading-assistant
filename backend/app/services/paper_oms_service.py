from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

from app.config import settings
from app.models import (
    MarketType,
    PaperExecutionControl,
    PaperExecutionControlUpdateRequest,
    PaperFill,
    PaperMarketTickRequest,
    PaperOrder,
    PaperOrderCreateRequest,
    PaperOrderEvent,
    PaperOrderListResponse,
    PaperPortfolio,
    PaperPosition,
    PaperReconciliationResponse,
)
from app.services.database_service import DatabaseManager


_OPEN_STATUSES = {"accepted", "working", "partially_filled"}
_TERMINAL_STATUSES = {"filled", "canceled", "rejected", "expired"}


class PaperOmsError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class PaperOmsService:
    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _request_hash(self, request: PaperOrderCreateRequest) -> str:
        raw = json.dumps(
            request.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _payload_hash(self, payload: dict) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _ensure_control(self, conn, user_id: int) -> None:
        row = conn.execute(
            "SELECT user_id FROM paper_execution_controls WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            conn.execute(
                """
                INSERT INTO paper_execution_controls (
                    user_id, paper_trading_enabled, kill_switch_engaged,
                    max_open_orders, max_order_notional, default_fee_bps,
                    default_slippage_bps, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, 0, 1, 5, 10_000.0, 4.0, 1.0, self._now()),
            )
            conn.commit()

    def _ensure_account(self, conn, user_id: int) -> None:
        row = conn.execute(
            "SELECT user_id FROM paper_accounts WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            now = self._now()
            today = datetime.now(timezone.utc).date().isoformat()
            initial_cash = 100_000.0
            conn.execute(
                """
                INSERT INTO paper_accounts (
                    user_id, initial_cash, cash_balance, realized_pnl, total_fees,
                    peak_equity, daily_start_equity, trading_day, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, initial_cash, initial_cash, 0.0, 0.0, initial_cash, initial_cash, today, now),
            )
            conn.commit()

    def get_control(self, user_id: int) -> PaperExecutionControl:
        with self.database.connection() as conn:
            self._ensure_control(conn, user_id)
            self._ensure_account(conn, user_id)
            row = conn.execute(
                "SELECT * FROM paper_execution_controls WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return PaperExecutionControl(
            paper_trading_enabled=bool(row["paper_trading_enabled"]),
            kill_switch_engaged=bool(row["kill_switch_engaged"]),
            max_open_orders=int(row["max_open_orders"]),
            max_order_notional=float(row["max_order_notional"]),
            default_fee_bps=float(row["default_fee_bps"]),
            default_slippage_bps=float(row["default_slippage_bps"]),
            max_daily_drawdown_pct=float(row["max_daily_drawdown_pct"]),
            updated_at=row["updated_at"],
            live_execution_enabled=settings.enable_live_execution,
        )

    def update_control(
        self,
        user_id: int,
        request: PaperExecutionControlUpdateRequest,
    ) -> PaperExecutionControl:
        now = self._now()
        with self.database.connection() as conn:
            self._ensure_control(conn, user_id)
            conn.execute(
                """
                UPDATE paper_execution_controls
                SET paper_trading_enabled = ?, kill_switch_engaged = ?,
                    max_open_orders = ?, max_order_notional = ?,
                    default_fee_bps = ?, default_slippage_bps = ?,
                    max_daily_drawdown_pct = ?, updated_at = ?
                WHERE user_id = ?
                """,
                (
                    1 if request.paper_trading_enabled else 0,
                    1 if request.kill_switch_engaged else 0,
                    request.max_open_orders,
                    request.max_order_notional,
                    request.default_fee_bps,
                    request.default_slippage_bps,
                    request.max_daily_drawdown_pct,
                    now,
                    user_id,
                ),
            )
            if request.kill_switch_engaged or not request.paper_trading_enabled:
                rows = conn.execute(
                    "SELECT order_id, status FROM paper_orders WHERE user_id = ? AND status IN (?, ?, ?)",
                    (user_id, "accepted", "working", "partially_filled"),
                ).fetchall()
                for row in rows:
                    conn.execute(
                        "UPDATE paper_orders SET status = ?, updated_at = ?, terminal_at = ? WHERE order_id = ?",
                        ("canceled", now, now, row["order_id"]),
                    )
                    self._append_event(
                        conn,
                        user_id,
                        row["order_id"],
                        "kill_switch_cancel",
                        row["status"],
                        "canceled",
                        "paper_kill_switch_engaged",
                        {"kill_switch": True},
                    )
            conn.commit()
        return self.get_control(user_id)

    def _append_event(
        self,
        conn,
        user_id: int,
        order_id: str,
        event_type: str,
        from_status: str | None,
        to_status: str,
        reason: str,
        payload: dict,
    ) -> None:
        row = conn.execute(
            "SELECT COALESCE(MAX(sequence), 0) AS sequence FROM paper_order_events WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        sequence = int(row["sequence"] or 0) + 1
        conn.execute(
            """
            INSERT INTO paper_order_events (
                event_id, order_id, user_id, sequence, event_type,
                from_status, to_status, reason, payload_hash, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uuid4().hex,
                order_id,
                user_id,
                sequence,
                event_type,
                from_status,
                to_status,
                reason,
                self._payload_hash(payload),
                self._now(),
            ),
        )

    def submit(self, user_id: int, request: PaperOrderCreateRequest) -> PaperOrder:
        request_hash = self._request_hash(request)
        now = self._now()
        with self.database.connection() as conn:
            self._ensure_control(conn, user_id)
            control_sql = "SELECT * FROM paper_execution_controls WHERE user_id = ?"
            if self.database.backend == "postgresql":
                control_sql += " FOR UPDATE"
            control = conn.execute(control_sql, (user_id,)).fetchone()
            existing = conn.execute(
                "SELECT order_id, request_hash FROM paper_orders WHERE user_id = ? AND idempotency_key = ?",
                (user_id, request.idempotency_key),
            ).fetchone()
            if existing is not None:
                if existing["request_hash"] != request_hash:
                    raise PaperOmsError("idempotency_key_payload_conflict")
                return self._get_order_with_conn(conn, user_id, existing["order_id"])

            if not bool(control["paper_trading_enabled"]):
                raise PaperOmsError("paper_trading_disabled")
            if bool(control["kill_switch_engaged"]):
                raise PaperOmsError("paper_kill_switch_engaged")
            if not request.risk_approved:
                raise PaperOmsError("risk_approval_required")
            if request.signal_score < 75.0:
                raise PaperOmsError("signal_score_below_paper_execution_threshold")
            open_count = conn.execute(
                "SELECT COUNT(*) AS count FROM paper_orders WHERE user_id = ? AND status IN (?, ?, ?)",
                (user_id, "accepted", "working", "partially_filled"),
            ).fetchone()
            if int(open_count["count"] or 0) >= int(control["max_open_orders"]):
                raise PaperOmsError("max_open_paper_orders_reached")
            reference = request.reference_ask if request.side == "buy" else request.reference_bid
            notional = request.quantity * reference
            if notional > float(control["max_order_notional"]):
                raise PaperOmsError("paper_order_notional_limit_exceeded")

            order_id = uuid4().hex
            fee_bps = request.fee_bps if request.fee_bps is not None else float(control["default_fee_bps"])
            conn.execute(
                """
                INSERT INTO paper_orders (
                    order_id, user_id, idempotency_key, request_hash, symbol, market,
                    side, order_type, quantity, limit_price, time_in_force, status,
                    filled_quantity, average_fill_price, total_fees,
                    reference_bid, reference_ask, max_slippage_bps, fee_bps,
                    signal_score, risk_approved, strategy_id, setup_id,
                    created_at, updated_at, terminal_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    user_id,
                    request.idempotency_key,
                    request_hash,
                    request.symbol.upper(),
                    request.market.value,
                    request.side,
                    request.order_type,
                    request.quantity,
                    request.limit_price,
                    request.time_in_force,
                    "accepted",
                    0.0,
                    None,
                    0.0,
                    request.reference_bid,
                    request.reference_ask,
                    request.max_slippage_bps,
                    fee_bps,
                    request.signal_score,
                    1,
                    request.strategy_id,
                    request.setup_id,
                    now,
                    now,
                    None,
                ),
            )
            self._append_event(
                conn,
                user_id,
                order_id,
                "order_accepted",
                None,
                "accepted",
                "paper_risk_and_control_gates_passed",
                {"request_hash": request_hash, "live_routed": False},
            )
            conn.execute(
                "UPDATE paper_orders SET status = ?, updated_at = ? WHERE order_id = ?",
                ("working", now, order_id),
            )
            self._append_event(
                conn,
                user_id,
                order_id,
                "order_working",
                "accepted",
                "working",
                "paper_order_entered_simulation_book",
                {},
            )
            tick = PaperMarketTickRequest(
                symbol=request.symbol,
                bid=request.reference_bid,
                ask=request.reference_ask,
                available_quantity=request.available_quantity or request.quantity,
                timestamp=datetime.now(timezone.utc),
                source="paper_submit_reference_quote",
            )
            self._process_order_tick(conn, user_id, order_id, tick)
            conn.commit()
            return self._get_order_with_conn(conn, user_id, order_id)

    def _apply_position_fill(
        self,
        conn,
        user_id: int,
        symbol: str,
        market: str,
        side: str,
        quantity: float,
        price: float,
        fee: float,
    ) -> None:
        self._ensure_account(conn, user_id)
        row = conn.execute(
            "SELECT * FROM paper_positions WHERE user_id = ? AND symbol = ?",
            (user_id, symbol),
        ).fetchone()
        old_quantity = float(row["quantity"] if row else 0.0)
        old_average = float(row["average_entry_price"] or 0.0) if row else 0.0
        signed_fill = quantity if side == "buy" else -quantity
        new_quantity = old_quantity + signed_fill
        realized = 0.0
        if old_quantity == 0.0 or old_quantity * signed_fill > 0:
            total_abs = abs(old_quantity) + abs(signed_fill)
            new_average = (
                (old_average * abs(old_quantity) + price * abs(signed_fill)) / total_abs
                if total_abs > 0
                else None
            )
        else:
            closed_quantity = min(abs(old_quantity), abs(signed_fill))
            direction = 1.0 if old_quantity > 0 else -1.0
            realized = closed_quantity * (price - old_average) * direction
            if abs(new_quantity) <= 1e-12:
                new_quantity = 0.0
                new_average = None
            elif old_quantity * new_quantity > 0:
                new_average = old_average
            else:
                new_average = price
        now = self._now()
        old_realized = float(row["realized_pnl"] if row else 0.0)
        old_fees = float(row["total_fees"] if row else 0.0)
        if row is None:
            conn.execute(
                """
                INSERT INTO paper_positions (
                    user_id, symbol, market, quantity, average_entry_price,
                    mark_price, realized_pnl, total_fees, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    symbol,
                    market,
                    new_quantity,
                    new_average,
                    price,
                    realized,
                    fee,
                    now,
                ),
            )
        else:
            conn.execute(
                """
                UPDATE paper_positions
                SET quantity = ?, average_entry_price = ?, mark_price = ?,
                    realized_pnl = ?, total_fees = ?, updated_at = ?
                WHERE user_id = ? AND symbol = ?
                """,
                (
                    new_quantity,
                    new_average,
                    price,
                    old_realized + realized,
                    old_fees + fee,
                    now,
                    user_id,
                    symbol,
                ),
            )
        conn.execute(
            """
            UPDATE paper_accounts
            SET cash_balance = cash_balance + ? - ?,
                realized_pnl = realized_pnl + ?,
                total_fees = total_fees + ?, updated_at = ?
            WHERE user_id = ?
            """,
            (realized, fee, realized, fee, now, user_id),
        )

    def _process_order_tick(self, conn, user_id: int, order_id: str, tick: PaperMarketTickRequest) -> None:
        order_sql = "SELECT * FROM paper_orders WHERE user_id = ? AND order_id = ?"
        if self.database.backend == "postgresql":
            order_sql += " FOR UPDATE"
        row = conn.execute(order_sql, (user_id, order_id)).fetchone()
        if row is None or row["status"] not in _OPEN_STATUSES:
            return
        remaining = float(row["quantity"]) - float(row["filled_quantity"])
        if remaining <= 1e-12:
            return
        side = row["side"]
        order_type = row["order_type"]
        limit_price = row["limit_price"]
        marketable = order_type == "market" or (
            side == "buy" and tick.ask <= float(limit_price)
        ) or (
            side == "sell" and tick.bid >= float(limit_price)
        )
        if not marketable:
            if row["time_in_force"] in {"IOC", "FOK"}:
                self._cancel_with_conn(conn, user_id, order_id, "time_in_force_not_marketable")
            return
        if row["time_in_force"] == "FOK" and tick.available_quantity + 1e-12 < remaining:
            self._cancel_with_conn(conn, user_id, order_id, "fok_liquidity_insufficient")
            return
        fill_quantity = min(remaining, tick.available_quantity)
        slippage = float(row["max_slippage_bps"]) / 10_000.0
        if side == "buy":
            price = tick.ask * (1.0 + slippage)
            if order_type == "limit":
                price = min(price, float(limit_price))
        else:
            price = tick.bid * (1.0 - slippage)
            if order_type == "limit":
                price = max(price, float(limit_price))
        fee = fill_quantity * price * float(row["fee_bps"]) / 10_000.0
        old_filled = float(row["filled_quantity"])
        new_filled = old_filled + fill_quantity
        old_average = float(row["average_fill_price"] or 0.0)
        new_average = (
            (old_average * old_filled + price * fill_quantity) / new_filled
            if new_filled > 0
            else None
        )
        filled = new_filled >= float(row["quantity"]) - 1e-12
        new_status = "filled" if filled else "partially_filled"
        now = self._now()
        conn.execute(
            """
            INSERT INTO paper_fills (
                fill_id, order_id, user_id, quantity, price, fee_amount,
                liquidity, source, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uuid4().hex,
                order_id,
                user_id,
                fill_quantity,
                price,
                fee,
                "simulated_taker" if order_type == "market" else "simulated_limit",
                tick.source,
                now,
            ),
        )
        self._apply_position_fill(
            conn,
            user_id,
            row["symbol"],
            row["market"],
            side,
            fill_quantity,
            price,
            fee,
        )
        conn.execute(
            """
            UPDATE paper_orders
            SET status = ?, filled_quantity = ?, average_fill_price = ?,
                total_fees = total_fees + ?, updated_at = ?, terminal_at = ?
            WHERE order_id = ?
            """,
            (
                new_status,
                new_filled,
                new_average,
                fee,
                now,
                now if filled else None,
                order_id,
            ),
        )
        self._append_event(
            conn,
            user_id,
            order_id,
            "order_filled" if filled else "order_partially_filled",
            row["status"],
            new_status,
            "conservative_paper_fill",
            {
                "quantity": fill_quantity,
                "price": round(price, 12),
                "fee": round(fee, 12),
                "source": tick.source,
            },
        )
        if not filled and row["time_in_force"] == "IOC":
            self._cancel_with_conn(conn, user_id, order_id, "ioc_remainder_canceled")

    def process_tick(self, user_id: int, tick: PaperMarketTickRequest) -> PaperOrderListResponse:
        with self.database.connection() as conn:
            self._ensure_control(conn, user_id)
            control_sql = "SELECT * FROM paper_execution_controls WHERE user_id = ?"
            if self.database.backend == "postgresql":
                control_sql += " FOR UPDATE"
            control = conn.execute(control_sql, (user_id,)).fetchone()
            if not bool(control["paper_trading_enabled"]) or bool(control["kill_switch_engaged"]):
                raise PaperOmsError("paper_execution_not_armed")
            rows = conn.execute(
                "SELECT order_id FROM paper_orders WHERE user_id = ? AND symbol = ? AND status IN (?, ?, ?)",
                (user_id, tick.symbol.upper(), "accepted", "working", "partially_filled"),
            ).fetchall()
            for row in rows:
                self._process_order_tick(conn, user_id, row["order_id"], tick)
            conn.commit()
            order_ids = [row["order_id"] for row in rows]
        self.mark_portfolio(user_id, tick)
        items = [self.get(user_id, order_id) for order_id in order_ids]
        return PaperOrderListResponse(items=items, count=len(items))

    def get_portfolio(self, user_id: int) -> PaperPortfolio:
        with self.database.connection() as conn:
            self._ensure_control(conn, user_id)
            self._ensure_account(conn, user_id)
            account = conn.execute(
                "SELECT * FROM paper_accounts WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            rows = conn.execute(
                "SELECT * FROM paper_positions WHERE user_id = ? ORDER BY symbol",
                (user_id,),
            ).fetchall()
            positions = []
            unrealized_total = 0.0
            for row in rows:
                quantity = float(row["quantity"])
                average = float(row["average_entry_price"] or 0.0)
                mark = float(row["mark_price"] or average)
                unrealized = quantity * (mark - average) if quantity else 0.0
                unrealized_total += unrealized
                positions.append(
                    PaperPosition(
                        symbol=row["symbol"],
                        market=MarketType(row["market"]),
                        quantity=quantity,
                        average_entry_price=row["average_entry_price"],
                        mark_price=row["mark_price"],
                        realized_pnl=float(row["realized_pnl"]),
                        unrealized_pnl=unrealized,
                        total_fees=float(row["total_fees"]),
                        notional=abs(quantity * mark),
                        updated_at=row["updated_at"],
                    )
                )
            equity = float(account["cash_balance"]) + unrealized_total
            today = datetime.now(timezone.utc).date().isoformat()
            daily_start = float(account["daily_start_equity"])
            if account["trading_day"] != today:
                daily_start = equity
                conn.execute(
                    "UPDATE paper_accounts SET daily_start_equity = ?, trading_day = ? WHERE user_id = ?",
                    (daily_start, today, user_id),
                )
            peak = max(float(account["peak_equity"]), equity)
            conn.execute(
                "UPDATE paper_accounts SET peak_equity = ?, updated_at = ? WHERE user_id = ?",
                (peak, self._now(), user_id),
            )
            conn.commit()
            control = conn.execute(
                "SELECT kill_switch_engaged FROM paper_execution_controls WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        daily_drawdown = (
            max(0.0, (daily_start - equity) / daily_start * 100.0)
            if daily_start > 0
            else 0.0
        )
        return PaperPortfolio(
            initial_cash=float(account["initial_cash"]),
            cash_balance=float(account["cash_balance"]),
            equity=equity,
            peak_equity=peak,
            realized_pnl=float(account["realized_pnl"]),
            unrealized_pnl=unrealized_total,
            total_fees=float(account["total_fees"]),
            daily_drawdown_pct=daily_drawdown,
            kill_switch_engaged=bool(control["kill_switch_engaged"]),
            live_execution_enabled=settings.enable_live_execution,
            positions=positions,
            updated_at=self._now(),
        )

    def mark_portfolio(self, user_id: int, tick: PaperMarketTickRequest) -> PaperPortfolio:
        mark = (tick.bid + tick.ask) / 2.0
        with self.database.connection() as conn:
            self._ensure_account(conn, user_id)
            conn.execute(
                "UPDATE paper_positions SET mark_price = ?, updated_at = ? WHERE user_id = ? AND symbol = ?",
                (mark, self._now(), user_id, tick.symbol.upper()),
            )
            conn.commit()
        portfolio = self.get_portfolio(user_id)
        control = self.get_control(user_id)
        if (
            control.paper_trading_enabled
            and not control.kill_switch_engaged
            and portfolio.daily_drawdown_pct >= control.max_daily_drawdown_pct
        ):
            self.update_control(
                user_id,
                PaperExecutionControlUpdateRequest(
                    paper_trading_enabled=True,
                    kill_switch_engaged=True,
                    max_open_orders=control.max_open_orders,
                    max_order_notional=control.max_order_notional,
                    default_fee_bps=control.default_fee_bps,
                    default_slippage_bps=control.default_slippage_bps,
                    max_daily_drawdown_pct=control.max_daily_drawdown_pct,
                    acknowledgement="I_UNDERSTAND_PAPER_ONLY",
                ),
            )
            portfolio = self.get_portfolio(user_id)
        return portfolio

    def _cancel_with_conn(self, conn, user_id: int, order_id: str, reason: str) -> None:
        row = conn.execute(
            "SELECT status FROM paper_orders WHERE user_id = ? AND order_id = ?",
            (user_id, order_id),
        ).fetchone()
        if row is None:
            raise PaperOmsError("paper_order_not_found")
        if row["status"] in _TERMINAL_STATUSES:
            raise PaperOmsError("paper_order_already_terminal")
        now = self._now()
        conn.execute(
            "UPDATE paper_orders SET status = ?, updated_at = ?, terminal_at = ? WHERE order_id = ?",
            ("canceled", now, now, order_id),
        )
        self._append_event(
            conn,
            user_id,
            order_id,
            "order_canceled",
            row["status"],
            "canceled",
            reason,
            {},
        )

    def cancel(self, user_id: int, order_id: str) -> PaperOrder:
        with self.database.connection() as conn:
            self._cancel_with_conn(conn, user_id, order_id, "user_requested_cancel")
            conn.commit()
            return self._get_order_with_conn(conn, user_id, order_id)

    def get(self, user_id: int, order_id: str) -> PaperOrder:
        with self.database.connection() as conn:
            return self._get_order_with_conn(conn, user_id, order_id)

    def list(self, user_id: int, limit: int = 100) -> PaperOrderListResponse:
        with self.database.connection() as conn:
            rows = conn.execute(
                "SELECT order_id FROM paper_orders WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, max(1, min(limit, 500))),
            ).fetchall()
            items = [self._get_order_with_conn(conn, user_id, row["order_id"]) for row in rows]
        return PaperOrderListResponse(items=items, count=len(items))

    def _get_order_with_conn(self, conn, user_id: int, order_id: str) -> PaperOrder:
        row = conn.execute(
            "SELECT * FROM paper_orders WHERE user_id = ? AND order_id = ?",
            (user_id, order_id),
        ).fetchone()
        if row is None:
            raise PaperOmsError("paper_order_not_found")
        fill_rows = conn.execute(
            "SELECT * FROM paper_fills WHERE user_id = ? AND order_id = ? ORDER BY created_at, fill_id",
            (user_id, order_id),
        ).fetchall()
        event_rows = conn.execute(
            "SELECT * FROM paper_order_events WHERE user_id = ? AND order_id = ? ORDER BY sequence",
            (user_id, order_id),
        ).fetchall()
        quantity = float(row["quantity"])
        filled = float(row["filled_quantity"])
        return PaperOrder(
            order_id=row["order_id"],
            idempotency_key=row["idempotency_key"],
            symbol=row["symbol"],
            market=MarketType(row["market"]),
            side=row["side"],
            order_type=row["order_type"],
            quantity=quantity,
            limit_price=row["limit_price"],
            time_in_force=row["time_in_force"],
            status=row["status"],
            filled_quantity=filled,
            remaining_quantity=max(0.0, quantity - filled),
            average_fill_price=row["average_fill_price"],
            total_fees=float(row["total_fees"]),
            reference_bid=float(row["reference_bid"]),
            reference_ask=float(row["reference_ask"]),
            max_slippage_bps=float(row["max_slippage_bps"]),
            signal_score=float(row["signal_score"]),
            risk_approved=bool(row["risk_approved"]),
            strategy_id=row["strategy_id"],
            setup_id=row["setup_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            terminal_at=row["terminal_at"],
            live_routed=False,
            fills=[
                PaperFill(
                    fill_id=item["fill_id"],
                    order_id=item["order_id"],
                    quantity=float(item["quantity"]),
                    price=float(item["price"]),
                    fee_amount=float(item["fee_amount"]),
                    liquidity=item["liquidity"],
                    source=item["source"],
                    created_at=item["created_at"],
                )
                for item in fill_rows
            ],
            events=[
                PaperOrderEvent(
                    event_id=item["event_id"],
                    order_id=item["order_id"],
                    sequence=int(item["sequence"]),
                    event_type=item["event_type"],
                    from_status=item["from_status"],
                    to_status=item["to_status"],
                    reason=item["reason"],
                    payload_hash=item["payload_hash"],
                    created_at=item["created_at"],
                )
                for item in event_rows
            ],
        )

    def reconcile(self, user_id: int, order_id: str) -> PaperReconciliationResponse:
        order = self.get(user_id, order_id)
        fill_quantity = sum(item.quantity for item in order.fills)
        fees = sum(item.fee_amount for item in order.fills)
        weighted = sum(item.quantity * item.price for item in order.fills)
        average = weighted / fill_quantity if fill_quantity > 0 else None
        quantity_match = abs(fill_quantity - order.filled_quantity) <= 1e-8
        fees_match = abs(fees - order.total_fees) <= 1e-8
        average_match = (
            average is None and order.average_fill_price is None
        ) or (
            average is not None
            and order.average_fill_price is not None
            and abs(average - order.average_fill_price) <= 1e-8
        )
        sequences = [item.sequence for item in order.events]
        sequence_valid = sequences == list(range(1, len(sequences) + 1))
        terminal_valid = (
            order.status not in _TERMINAL_STATUSES
            and order.terminal_at is None
        ) or (
            order.status in _TERMINAL_STATUSES
            and order.terminal_at is not None
        )
        issues = []
        if not quantity_match:
            issues.append("filled_quantity_mismatch")
        if not fees_match:
            issues.append("fee_total_mismatch")
        if not average_match:
            issues.append("average_fill_price_mismatch")
        if not sequence_valid:
            issues.append("event_sequence_invalid")
        if not terminal_valid:
            issues.append("terminal_state_timestamp_invalid")
        return PaperReconciliationResponse(
            order_id=order_id,
            consistent=not issues,
            filled_quantity_matches=quantity_match,
            average_price_matches=average_match,
            fees_match=fees_match,
            event_sequence_valid=sequence_valid,
            terminal_state_valid=terminal_valid,
            issues=issues,
            live_execution_enabled=settings.enable_live_execution,
        )
