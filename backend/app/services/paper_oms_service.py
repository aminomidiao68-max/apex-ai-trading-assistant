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
    PaperFundingSettlementRequest,
    PaperFundingSettlementResponse,
    PaperMarginEvent,
    PaperMarginEventListResponse,
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

    def _tick_identity(self, tick: PaperMarketTickRequest) -> tuple[str, str]:
        payload = tick.model_dump(mode="json", exclude={"event_id"})
        payload["symbol"] = tick.symbol.upper()
        payload_hash = self._payload_hash(payload)
        event_id = tick.event_id or f"tick_{payload_hash[:48]}"
        return event_id, payload_hash

    @staticmethod
    def _risk_group(symbol: str, market: MarketType | str) -> str:
        upper = symbol.upper().replace("-", "").replace("_", "")
        market_value = market.value if isinstance(market, MarketType) else str(market)
        if market_value == "crypto":
            if upper.startswith(("BTC", "ETH")):
                return "crypto_major_structural_proxy"
            if upper.startswith(("USDC", "USDT", "DAI")):
                return "crypto_stable_structural_proxy"
            return "crypto_alt_structural_proxy"
        if upper.startswith(("XAU", "XAG")):
            return "metals_usd_structural_proxy"
        if "USD" in upper:
            return "forex_usd_structural_proxy"
        if "EUR" in upper:
            return "forex_eur_structural_proxy"
        return "other_structural_proxy"

    def _resolve_correlation_group(
        self,
        conn,
        user_id: int,
        symbol: str,
        market: MarketType,
        snapshot_id: str | None,
    ) -> tuple[str, str, str | None]:
        if not snapshot_id:
            return self._risk_group(symbol, market), "structural_proxy", None
        row = conn.execute(
            "SELECT symbols_json, clusters_json FROM paper_correlation_snapshots "
            "WHERE user_id = ? AND snapshot_id = ?",
            (user_id, snapshot_id),
        ).fetchone()
        if row is None:
            raise PaperOmsError("correlation_snapshot_not_found")
        upper = symbol.upper()
        symbols = list(json.loads(row["symbols_json"]))
        if upper not in symbols:
            raise PaperOmsError("correlation_snapshot_symbol_not_found")
        clusters = list(json.loads(row["clusters_json"]))
        cluster_index = next(
            (index for index, cluster in enumerate(clusters) if upper in cluster),
            None,
        )
        if cluster_index is None:
            raise PaperOmsError("correlation_snapshot_cluster_invalid")
        digest = hashlib.sha256(snapshot_id.encode("utf-8")).hexdigest()[:12]
        return (
            f"statistical_cluster_{digest}_{cluster_index}",
            "stored_dataset_statistical",
            snapshot_id,
        )

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
            automated_feed_enabled=bool(row["automated_feed_enabled"]),
            max_open_orders=int(row["max_open_orders"]),
            max_order_notional=float(row["max_order_notional"]),
            default_fee_bps=float(row["default_fee_bps"]),
            default_slippage_bps=float(row["default_slippage_bps"]),
            max_daily_drawdown_pct=float(row["max_daily_drawdown_pct"]),
            max_tick_age_seconds=int(row["max_tick_age_seconds"]),
            max_leverage=float(row["max_leverage"]),
            default_maintenance_margin_rate=float(row["default_maintenance_margin_rate"]),
            liquidation_fee_bps=float(row["liquidation_fee_bps"]),
            max_margin_utilization_pct=float(row["max_margin_utilization_pct"]),
            max_symbol_margin_pct=float(row["max_symbol_margin_pct"]),
            max_risk_group_margin_pct=float(row["max_risk_group_margin_pct"]),
            max_directional_notional_multiple=float(row["max_directional_notional_multiple"]),
            updated_at=row["updated_at"],
            live_execution_enabled=settings.enable_live_execution,
        )

    def update_control(
        self,
        user_id: int,
        request: PaperExecutionControlUpdateRequest,
    ) -> PaperExecutionControl:
        if request.automated_feed_enabled and (
            not request.paper_trading_enabled or request.kill_switch_engaged
        ):
            raise PaperOmsError("automated_feed_requires_armed_paper_mode")
        now = self._now()
        with self.database.connection() as conn:
            self._ensure_control(conn, user_id)
            conn.execute(
                """
                UPDATE paper_execution_controls
                SET paper_trading_enabled = ?, kill_switch_engaged = ?,
                    automated_feed_enabled = ?, max_open_orders = ?, max_order_notional = ?,
                    default_fee_bps = ?, default_slippage_bps = ?,
                    max_daily_drawdown_pct = ?, max_tick_age_seconds = ?,
                    max_leverage = ?, default_maintenance_margin_rate = ?,
                    liquidation_fee_bps = ?, max_margin_utilization_pct = ?,
                    max_symbol_margin_pct = ?, max_risk_group_margin_pct = ?,
                    max_directional_notional_multiple = ?, updated_at = ?
                WHERE user_id = ?
                """,
                (
                    1 if request.paper_trading_enabled else 0,
                    1 if request.kill_switch_engaged else 0,
                    1 if request.automated_feed_enabled else 0,
                    request.max_open_orders,
                    request.max_order_notional,
                    request.default_fee_bps,
                    request.default_slippage_bps,
                    request.max_daily_drawdown_pct,
                    request.max_tick_age_seconds,
                    request.max_leverage,
                    request.default_maintenance_margin_rate,
                    request.liquidation_fee_bps,
                    request.max_margin_utilization_pct,
                    request.max_symbol_margin_pct,
                    request.max_risk_group_margin_pct,
                    request.max_directional_notional_multiple,
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

    @staticmethod
    def _liquidation_price(
        quantity: float,
        average_entry: float | None,
        initial_margin: float,
        maintenance_margin_rate: float,
        accumulated_funding: float,
        liquidation_fee_bps: float,
    ) -> float | None:
        if abs(quantity) <= 1e-12 or not average_entry or average_entry <= 0:
            return None
        collateral_per_unit = max(0.0, initial_margin - accumulated_funding) / abs(quantity)
        maintenance_per_unit = average_entry * maintenance_margin_rate
        liquidation_fee_per_unit = average_entry * liquidation_fee_bps / 10_000.0
        if quantity > 0:
            return max(
                0.0,
                average_entry - collateral_per_unit + maintenance_per_unit + liquidation_fee_per_unit,
            )
        return max(
            0.0,
            average_entry + collateral_per_unit - maintenance_per_unit - liquidation_fee_per_unit,
        )

    def _append_margin_event(
        self,
        conn,
        user_id: int,
        event_id: str,
        event_type: str,
        symbol: str,
        amount: float,
        funding_rate: float | None,
        mark_price: float | None,
        realized_pnl: float,
        source: str,
        is_real_rate: bool,
        payload_hash: str,
    ) -> None:
        conn.execute(
            """
            INSERT INTO paper_margin_events (
                event_id, user_id, event_type, symbol, amount, funding_rate,
                mark_price, realized_pnl, source, is_real_rate, payload_hash, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                user_id,
                event_type,
                symbol,
                amount,
                funding_rate,
                mark_price,
                realized_pnl,
                source,
                1 if is_real_rate else 0,
                payload_hash,
                self._now(),
            ),
        )

    def _engage_kill_switch_with_conn(self, conn, user_id: int, reason: str) -> None:
        now = self._now()
        conn.execute(
            """
            UPDATE paper_execution_controls
            SET kill_switch_engaged = 1, automated_feed_enabled = 0, updated_at = ?
            WHERE user_id = ?
            """,
            (now, user_id),
        )
        rows = conn.execute(
            "SELECT order_id, status FROM paper_orders "
            "WHERE user_id = ? AND status IN (?, ?, ?)",
            (user_id, "accepted", "working", "partially_filled"),
        ).fetchall()
        for row in rows:
            conn.execute(
                "UPDATE paper_orders SET status = ?, updated_at = ?, terminal_at = ? "
                "WHERE order_id = ?",
                ("canceled", now, now, row["order_id"]),
            )
            self._append_event(
                conn,
                user_id,
                row["order_id"],
                "kill_switch_cancel",
                row["status"],
                "canceled",
                reason,
                {"kill_switch": True},
            )

    def _evaluate_liquidations_with_conn(
        self,
        conn,
        user_id: int,
        tick: PaperMarketTickRequest,
        control,
    ) -> list[str]:
        rows = conn.execute(
            "SELECT * FROM paper_positions WHERE user_id = ? AND ABS(quantity) > 0.000000000001",
            (user_id,),
        ).fetchall()
        if not rows:
            return []
        account = conn.execute(
            "SELECT * FROM paper_accounts WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        total_unrealized = 0.0
        isolated_reserved = 0.0
        cross_requirement = 0.0
        cross_symbols: list[str] = []
        liquidate: set[str] = set()
        fee_rate = float(control["liquidation_fee_bps"]) / 10_000.0
        for row in rows:
            quantity = float(row["quantity"])
            average = float(row["average_entry_price"] or 0.0)
            mark = float(row["mark_price"] or average)
            unrealized = quantity * (mark - average)
            notional = abs(quantity * mark)
            maintenance = notional * float(row["maintenance_margin_rate"])
            close_fee = notional * fee_rate
            total_unrealized += unrealized
            if row["margin_mode"] == "isolated":
                isolated_equity = (
                    float(row["initial_margin"]) + unrealized - float(row["accumulated_funding"])
                )
                isolated_reserved += max(0.0, float(row["initial_margin"]))
                if isolated_equity <= maintenance + close_fee:
                    liquidate.add(str(row["symbol"]))
            else:
                cross_symbols.append(str(row["symbol"]))
                cross_requirement += maintenance + close_fee
        equity = float(account["cash_balance"]) + total_unrealized
        cross_collateral = equity - isolated_reserved
        if cross_symbols and cross_collateral <= cross_requirement:
            liquidate.update(cross_symbols)
        if not liquidate:
            return []

        liquidated = []
        for row in rows:
            symbol = str(row["symbol"])
            if symbol not in liquidate:
                continue
            quantity = float(row["quantity"])
            average = float(row["average_entry_price"] or 0.0)
            mark = float(row["mark_price"] or average)
            slippage = float(control["default_slippage_bps"]) / 10_000.0
            if symbol == tick.symbol.upper():
                exit_price = tick.bid * (1.0 - slippage) if quantity > 0 else tick.ask * (1.0 + slippage)
            else:
                exit_price = mark * (1.0 - slippage) if quantity > 0 else mark * (1.0 + slippage)
            realized = abs(quantity) * (exit_price - average) * (1.0 if quantity > 0 else -1.0)
            liquidation_fee = abs(quantity * exit_price) * fee_rate
            now = self._now()
            conn.execute(
                """
                UPDATE paper_positions
                SET quantity = 0.0, average_entry_price = NULL, mark_price = ?,
                    initial_margin = 0.0, position_status = 'liquidated',
                    liquidated_at = ?, realized_pnl = realized_pnl + ?,
                    total_fees = total_fees + ?, updated_at = ?
                WHERE user_id = ? AND symbol = ?
                """,
                (exit_price, now, realized, liquidation_fee, now, user_id, symbol),
            )
            conn.execute(
                """
                UPDATE paper_accounts
                SET cash_balance = cash_balance + ? - ?,
                    realized_pnl = realized_pnl + ?, total_fees = total_fees + ?,
                    liquidation_count = liquidation_count + 1, updated_at = ?
                WHERE user_id = ?
                """,
                (realized, liquidation_fee, realized, liquidation_fee, now, user_id),
            )
            liquidation_event_id = uuid4().hex
            payload = {
                "event_id": liquidation_event_id,
                "symbol": symbol,
                "quantity": quantity,
                "average_entry": average,
                "exit_price": exit_price,
                "margin_mode": row["margin_mode"],
                "source": tick.source,
            }
            self._append_margin_event(
                conn,
                user_id,
                liquidation_event_id,
                "liquidation",
                symbol,
                liquidation_fee,
                None,
                exit_price,
                realized,
                f"paper_liquidation:{tick.source}",
                False,
                self._payload_hash(payload),
            )
            liquidated.append(symbol)
        self._engage_kill_switch_with_conn(conn, user_id, "paper_margin_liquidation")
        return liquidated

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
            risk_group, correlation_source, correlation_snapshot_id = self._resolve_correlation_group(
                conn,
                user_id,
                request.symbol,
                request.market,
                request.correlation_snapshot_id,
            )
            notional = request.quantity * reference
            if notional > float(control["max_order_notional"]):
                raise PaperOmsError("paper_order_notional_limit_exceeded")
            self._ensure_account(conn, user_id)
            position = conn.execute(
                "SELECT * FROM paper_positions WHERE user_id = ? AND symbol = ?",
                (user_id, request.symbol.upper()),
            ).fetchone()
            old_quantity = float(position["quantity"] if position else 0.0)
            signed_request = request.quantity if request.side == "buy" else -request.quantity
            if old_quantity * signed_request > 0 and position is not None:
                if (
                    abs(float(position["leverage"]) - request.leverage) > 1e-9
                    or position["margin_mode"] != request.margin_mode
                ):
                    raise PaperOmsError("position_margin_configuration_conflict")
            if old_quantity == 0.0 or old_quantity * signed_request > 0:
                opening_quantity = request.quantity
            else:
                opening_quantity = max(0.0, request.quantity - abs(old_quantity))
            if opening_quantity > 0.0:
                if request.leverage > float(control["max_leverage"]):
                    raise PaperOmsError("paper_leverage_limit_exceeded")
                account = conn.execute(
                    "SELECT cash_balance FROM paper_accounts WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
                position_rows = conn.execute(
                    "SELECT symbol, risk_group, quantity, average_entry_price, mark_price, initial_margin "
                    "FROM paper_positions WHERE user_id = ?",
                    (user_id,),
                ).fetchall()
                current_used_margin = sum(float(item["initial_margin"] or 0.0) for item in position_rows)
                current_unrealized = sum(
                    float(item["quantity"])
                    * (
                        float(item["mark_price"] or item["average_entry_price"] or 0.0)
                        - float(item["average_entry_price"] or 0.0)
                    )
                    for item in position_rows
                )
                equity = float(account["cash_balance"]) + current_unrealized
                required_margin = opening_quantity * reference / request.leverage
                projected_margin = current_used_margin + required_margin
                allowed_margin = max(0.0, equity) * float(control["max_margin_utilization_pct"]) / 100.0
                if equity <= 0.0 or projected_margin > allowed_margin + 1e-9:
                    raise PaperOmsError("paper_margin_utilization_limit_exceeded")
                current_symbol_margin = sum(
                    float(item["initial_margin"] or 0.0)
                    for item in position_rows
                    if item["symbol"] == request.symbol.upper()
                )
                if current_symbol_margin + required_margin > equity * float(control["max_symbol_margin_pct"]) / 100.0 + 1e-9:
                    raise PaperOmsError("paper_symbol_margin_concentration_limit_exceeded")
                current_group_margin = sum(
                    float(item["initial_margin"] or 0.0)
                    for item in position_rows
                    if item["risk_group"] == risk_group
                )
                if current_group_margin + required_margin > equity * float(control["max_risk_group_margin_pct"]) / 100.0 + 1e-9:
                    raise PaperOmsError("paper_risk_group_concentration_limit_exceeded")
                candidate_direction = 1.0 if signed_request > 0 else -1.0
                directional_notional = sum(
                    abs(float(item["quantity"]) * float(item["mark_price"] or item["average_entry_price"] or 0.0))
                    for item in position_rows
                    if float(item["quantity"]) * candidate_direction > 0.0
                )
                projected_directional = directional_notional + opening_quantity * reference
                if projected_directional > equity * float(control["max_directional_notional_multiple"]) + 1e-9:
                    raise PaperOmsError("paper_directional_exposure_limit_exceeded")

            order_id = uuid4().hex
            fee_bps = request.fee_bps if request.fee_bps is not None else float(control["default_fee_bps"])
            conn.execute(
                """
                INSERT INTO paper_orders (
                    order_id, user_id, idempotency_key, request_hash, symbol, market,
                    side, order_type, quantity, limit_price, time_in_force, status,
                    filled_quantity, average_fill_price, total_fees,
                    reference_bid, reference_ask, max_slippage_bps, fee_bps,
                    leverage, margin_mode, maintenance_margin_rate, risk_group,
                    correlation_source, correlation_snapshot_id,
                    signal_score, risk_approved, strategy_id, setup_id,
                    created_at, updated_at, terminal_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    request.leverage,
                    request.margin_mode,
                    float(control["default_maintenance_margin_rate"]),
                    risk_group,
                    correlation_source,
                    correlation_snapshot_id,
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
        leverage: float,
        margin_mode: str,
        maintenance_margin_rate: float,
        liquidation_fee_bps: float,
        risk_group: str,
        correlation_source: str,
        correlation_snapshot_id: str | None,
    ) -> None:
        self._ensure_account(conn, user_id)
        row = conn.execute(
            "SELECT * FROM paper_positions WHERE user_id = ? AND symbol = ?",
            (user_id, symbol),
        ).fetchone()
        old_quantity = float(row["quantity"] if row else 0.0)
        old_average = float(row["average_entry_price"] or 0.0) if row else 0.0
        old_initial_margin = float(row["initial_margin"] if row else 0.0)
        old_funding = float(row["accumulated_funding"] if row else 0.0)
        signed_fill = quantity if side == "buy" else -quantity
        new_quantity = old_quantity + signed_fill
        realized = 0.0
        if old_quantity == 0.0 or old_quantity * signed_fill > 0:
            if row is not None and old_quantity != 0.0 and (
                abs(float(row["leverage"]) - leverage) > 1e-9
                or row["margin_mode"] != margin_mode
            ):
                raise PaperOmsError("position_margin_configuration_conflict")
            total_abs = abs(old_quantity) + abs(signed_fill)
            new_average = (
                (old_average * abs(old_quantity) + price * abs(signed_fill)) / total_abs
                if total_abs > 0
                else None
            )
            new_leverage = float(row["leverage"]) if row and old_quantity != 0.0 else leverage
            new_margin_mode = row["margin_mode"] if row and old_quantity != 0.0 else margin_mode
            new_maintenance_rate = (
                float(row["maintenance_margin_rate"])
                if row and old_quantity != 0.0
                else maintenance_margin_rate
            )
            new_initial_margin = old_initial_margin + abs(signed_fill * price) / new_leverage
            new_funding = old_funding
        else:
            closed_quantity = min(abs(old_quantity), abs(signed_fill))
            direction = 1.0 if old_quantity > 0 else -1.0
            realized = closed_quantity * (price - old_average) * direction
            if abs(new_quantity) <= 1e-12:
                new_quantity = 0.0
                new_average = None
                new_initial_margin = 0.0
                new_funding = 0.0
                new_leverage = leverage
                new_margin_mode = margin_mode
                new_maintenance_rate = maintenance_margin_rate
            elif old_quantity * new_quantity > 0:
                remaining_ratio = abs(new_quantity) / abs(old_quantity)
                new_average = old_average
                new_initial_margin = old_initial_margin * remaining_ratio
                new_funding = old_funding * remaining_ratio
                new_leverage = float(row["leverage"])
                new_margin_mode = row["margin_mode"]
                new_maintenance_rate = float(row["maintenance_margin_rate"])
            else:
                new_average = price
                new_initial_margin = abs(new_quantity * price) / leverage
                new_funding = 0.0
                new_leverage = leverage
                new_margin_mode = margin_mode
                new_maintenance_rate = maintenance_margin_rate
        preserve_existing_correlation = (
            row is not None and old_quantity != 0.0 and old_quantity * new_quantity > 0.0
        )
        new_risk_group = row["risk_group"] if preserve_existing_correlation else risk_group
        new_correlation_source = (
            row["correlation_source"] if preserve_existing_correlation else correlation_source
        )
        new_correlation_snapshot_id = (
            row["correlation_snapshot_id"]
            if preserve_existing_correlation
            else correlation_snapshot_id
        )
        liquidation_price = self._liquidation_price(
            new_quantity,
            new_average,
            new_initial_margin,
            new_maintenance_rate,
            new_funding,
            liquidation_fee_bps,
        )
        now = self._now()
        old_realized = float(row["realized_pnl"] if row else 0.0)
        old_fees = float(row["total_fees"] if row else 0.0)
        status = "open" if abs(new_quantity) > 1e-12 else "flat"
        if row is None:
            conn.execute(
                """
                INSERT INTO paper_positions (
                    user_id, symbol, market, quantity, average_entry_price,
                    mark_price, leverage, margin_mode, risk_group,
                    correlation_source, correlation_snapshot_id, initial_margin,
                    maintenance_margin_rate, liquidation_price, accumulated_funding,
                    position_status, liquidated_at, realized_pnl, total_fees, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    symbol,
                    market,
                    new_quantity,
                    new_average,
                    price,
                    new_leverage,
                    new_margin_mode,
                    new_risk_group,
                    new_correlation_source,
                    new_correlation_snapshot_id,
                    new_initial_margin,
                    new_maintenance_rate,
                    liquidation_price,
                    new_funding,
                    status,
                    None,
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
                    leverage = ?, margin_mode = ?, risk_group = ?,
                    correlation_source = ?, correlation_snapshot_id = ?, initial_margin = ?,
                    maintenance_margin_rate = ?, liquidation_price = ?,
                    accumulated_funding = ?, position_status = ?, liquidated_at = NULL,
                    realized_pnl = ?, total_fees = ?, updated_at = ?
                WHERE user_id = ? AND symbol = ?
                """,
                (
                    new_quantity,
                    new_average,
                    price,
                    new_leverage,
                    new_margin_mode,
                    new_risk_group,
                    new_correlation_source,
                    new_correlation_snapshot_id,
                    new_initial_margin,
                    new_maintenance_rate,
                    liquidation_price,
                    new_funding,
                    status,
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

    def _fill_margin_rejection_reason(
        self,
        conn,
        user_id: int,
        order_row,
        fill_quantity: float,
        fill_price: float,
        control,
    ) -> str | None:
        position = conn.execute(
            "SELECT * FROM paper_positions WHERE user_id = ? AND symbol = ?",
            (user_id, order_row["symbol"]),
        ).fetchone()
        old_quantity = float(position["quantity"] if position else 0.0)
        signed_fill = fill_quantity if order_row["side"] == "buy" else -fill_quantity
        if old_quantity * signed_fill > 0 and position is not None and (
            abs(float(position["leverage"]) - float(order_row["leverage"])) > 1e-9
            or position["margin_mode"] != order_row["margin_mode"]
        ):
            return "margin_configuration_changed_before_fill"
        if old_quantity == 0.0 or old_quantity * signed_fill > 0:
            opening_quantity = fill_quantity
        else:
            opening_quantity = max(0.0, fill_quantity - abs(old_quantity))
        if opening_quantity <= 0.0:
            return None
        if float(order_row["leverage"]) > float(control["max_leverage"]):
            return "leverage_limit_changed_before_fill"
        account = conn.execute(
            "SELECT cash_balance FROM paper_accounts WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        rows = conn.execute(
            "SELECT symbol, risk_group, quantity, average_entry_price, mark_price, initial_margin "
            "FROM paper_positions WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        used_margin = sum(float(item["initial_margin"] or 0.0) for item in rows)
        unrealized = sum(
            float(item["quantity"])
            * (
                float(item["mark_price"] or item["average_entry_price"] or 0.0)
                - float(item["average_entry_price"] or 0.0)
            )
            for item in rows
        )
        equity = float(account["cash_balance"]) + unrealized
        required = opening_quantity * fill_price / float(order_row["leverage"])
        allowed = max(0.0, equity) * float(control["max_margin_utilization_pct"]) / 100.0
        if equity <= 0.0 or used_margin + required > allowed + 1e-9:
            return "margin_utilization_changed_before_fill"
        symbol_margin = sum(
            float(item["initial_margin"] or 0.0)
            for item in rows
            if item["symbol"] == order_row["symbol"]
        )
        if symbol_margin + required > equity * float(control["max_symbol_margin_pct"]) / 100.0 + 1e-9:
            return "symbol_concentration_changed_before_fill"
        group_margin = sum(
            float(item["initial_margin"] or 0.0)
            for item in rows
            if item["risk_group"] == order_row["risk_group"]
        )
        if group_margin + required > equity * float(control["max_risk_group_margin_pct"]) / 100.0 + 1e-9:
            return "risk_group_concentration_changed_before_fill"
        direction = 1.0 if signed_fill > 0 else -1.0
        directional_notional = sum(
            abs(float(item["quantity"]) * float(item["mark_price"] or item["average_entry_price"] or 0.0))
            for item in rows
            if float(item["quantity"]) * direction > 0.0
        )
        if directional_notional + opening_quantity * fill_price > equity * float(control["max_directional_notional_multiple"]) + 1e-9:
            return "directional_exposure_changed_before_fill"
        return None

    def _process_order_tick(self, conn, user_id: int, order_id: str, tick: PaperMarketTickRequest) -> float:
        order_sql = "SELECT * FROM paper_orders WHERE user_id = ? AND order_id = ?"
        if self.database.backend == "postgresql":
            order_sql += " FOR UPDATE"
        row = conn.execute(order_sql, (user_id, order_id)).fetchone()
        if row is None or row["status"] not in _OPEN_STATUSES:
            return 0.0
        remaining = float(row["quantity"]) - float(row["filled_quantity"])
        if remaining <= 1e-12:
            return 0.0
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
            return 0.0
        if row["time_in_force"] == "FOK" and tick.available_quantity + 1e-12 < remaining:
            self._cancel_with_conn(conn, user_id, order_id, "fok_liquidity_insufficient")
            return 0.0
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
        control = conn.execute(
            "SELECT * FROM paper_execution_controls WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        margin_rejection = self._fill_margin_rejection_reason(
            conn,
            user_id,
            row,
            fill_quantity,
            price,
            control,
        )
        if margin_rejection:
            self._cancel_with_conn(conn, user_id, order_id, margin_rejection)
            return 0.0
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
            float(row["leverage"]),
            row["margin_mode"],
            float(row["maintenance_margin_rate"]),
            float(control["liquidation_fee_bps"]),
            row["risk_group"],
            row["correlation_source"],
            row["correlation_snapshot_id"],
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
        return fill_quantity

    def process_tick(self, user_id: int, tick: PaperMarketTickRequest) -> PaperOrderListResponse:
        event_id, payload_hash = self._tick_identity(tick)
        duplicate = False
        with self.database.connection() as conn:
            self._ensure_control(conn, user_id)
            control_sql = "SELECT * FROM paper_execution_controls WHERE user_id = ?"
            if self.database.backend == "postgresql":
                control_sql += " FOR UPDATE"
            control = conn.execute(control_sql, (user_id,)).fetchone()

            existing = conn.execute(
                "SELECT payload_hash, affected_order_ids_json FROM paper_market_ticks "
                "WHERE user_id = ? AND event_id = ?",
                (user_id, event_id),
            ).fetchone()
            if existing is not None:
                if existing["payload_hash"] != payload_hash:
                    raise PaperOmsError("tick_event_id_payload_conflict")
                order_ids = list(json.loads(existing["affected_order_ids_json"]))
                duplicate = True
            else:
                if not bool(control["paper_trading_enabled"]) or bool(control["kill_switch_engaged"]):
                    raise PaperOmsError("paper_execution_not_armed")
                now_dt = datetime.now(timezone.utc)
                tick_dt = tick.timestamp.astimezone(timezone.utc)
                age_seconds = (now_dt - tick_dt).total_seconds()
                if age_seconds > float(control["max_tick_age_seconds"]):
                    raise PaperOmsError("paper_tick_stale")
                if age_seconds < -5.0:
                    raise PaperOmsError("paper_tick_from_future")
                rows = conn.execute(
                    "SELECT order_id FROM paper_orders "
                    "WHERE user_id = ? AND symbol = ? AND status IN (?, ?, ?) "
                    "ORDER BY created_at, order_id",
                    (user_id, tick.symbol.upper(), "accepted", "working", "partially_filled"),
                ).fetchall()
                order_ids = [row["order_id"] for row in rows]
                remaining_liquidity = tick.available_quantity
                for order_id in order_ids:
                    if remaining_liquidity <= 1e-12:
                        break
                    order_tick = tick.model_copy(
                        update={"available_quantity": remaining_liquidity}
                    )
                    consumed = self._process_order_tick(conn, user_id, order_id, order_tick)
                    remaining_liquidity = max(0.0, remaining_liquidity - consumed)
                now = self._now()
                conn.execute(
                    "UPDATE paper_positions SET mark_price = ?, updated_at = ? "
                    "WHERE user_id = ? AND symbol = ?",
                    ((tick.bid + tick.ask) / 2.0, now, user_id, tick.symbol.upper()),
                )
                self._evaluate_liquidations_with_conn(conn, user_id, tick, control)
                conn.execute(
                    """
                    INSERT INTO paper_market_ticks (
                        tick_id, user_id, event_id, symbol, source, bid, ask,
                        available_quantity, provider_timestamp, payload_hash,
                        affected_order_ids_json, received_at, processed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        uuid4().hex,
                        user_id,
                        event_id,
                        tick.symbol.upper(),
                        tick.source,
                        tick.bid,
                        tick.ask,
                        tick.available_quantity,
                        tick_dt.isoformat(),
                        payload_hash,
                        json.dumps(order_ids, separators=(",", ":")),
                        now,
                        now,
                    ),
                )
                conn.commit()

        portfolio = self.get_portfolio(user_id)
        control_state = self.get_control(user_id)
        if (
            control_state.paper_trading_enabled
            and not control_state.kill_switch_engaged
            and portfolio.daily_drawdown_pct >= control_state.max_daily_drawdown_pct
        ):
            self.update_control(
                user_id,
                PaperExecutionControlUpdateRequest(
                    paper_trading_enabled=True,
                    kill_switch_engaged=True,
                    automated_feed_enabled=False,
                    max_open_orders=control_state.max_open_orders,
                    max_order_notional=control_state.max_order_notional,
                    default_fee_bps=control_state.default_fee_bps,
                    default_slippage_bps=control_state.default_slippage_bps,
                    max_daily_drawdown_pct=control_state.max_daily_drawdown_pct,
                    max_tick_age_seconds=control_state.max_tick_age_seconds,
                    max_leverage=control_state.max_leverage,
                    default_maintenance_margin_rate=control_state.default_maintenance_margin_rate,
                    liquidation_fee_bps=control_state.liquidation_fee_bps,
                    max_margin_utilization_pct=control_state.max_margin_utilization_pct,
                    max_symbol_margin_pct=control_state.max_symbol_margin_pct,
                    max_risk_group_margin_pct=control_state.max_risk_group_margin_pct,
                    max_directional_notional_multiple=control_state.max_directional_notional_multiple,
                    acknowledgement="I_UNDERSTAND_PAPER_ONLY",
                ),
            )
        items = [self.get(user_id, order_id) for order_id in order_ids]
        return PaperOrderListResponse(
            items=items,
            count=len(items),
            tick_event_id=event_id,
            duplicate_tick=duplicate,
        )

    def get_portfolio(self, user_id: int) -> PaperPortfolio:
        with self.database.connection() as conn:
            self._ensure_control(conn, user_id)
            self._ensure_account(conn, user_id)
            account = conn.execute(
                "SELECT * FROM paper_accounts WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            control = conn.execute(
                "SELECT * FROM paper_execution_controls WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            rows = conn.execute(
                "SELECT * FROM paper_positions WHERE user_id = ? ORDER BY symbol",
                (user_id,),
            ).fetchall()
            positions = []
            unrealized_total = 0.0
            used_margin = 0.0
            maintenance_total = 0.0
            for row in rows:
                quantity = float(row["quantity"])
                average = float(row["average_entry_price"] or 0.0)
                mark = float(row["mark_price"] or average)
                unrealized = quantity * (mark - average) if quantity else 0.0
                notional = abs(quantity * mark)
                initial_margin = float(row["initial_margin"] or 0.0) if quantity else 0.0
                maintenance = notional * float(row["maintenance_margin_rate"])
                funding = float(row["accumulated_funding"] or 0.0)
                unrealized_total += unrealized
                used_margin += initial_margin
                maintenance_total += maintenance
                if maintenance > 0 and row["margin_mode"] == "isolated":
                    margin_ratio = (initial_margin + unrealized - funding) / maintenance * 100.0
                else:
                    margin_ratio = None
                liquidation_price = row["liquidation_price"]
                if quantity and liquidation_price is None:
                    liquidation_price = self._liquidation_price(
                        quantity,
                        average,
                        initial_margin,
                        float(row["maintenance_margin_rate"]),
                        funding,
                        float(control["liquidation_fee_bps"]),
                    )
                positions.append(
                    PaperPosition(
                        symbol=row["symbol"],
                        market=MarketType(row["market"]),
                        quantity=quantity,
                        average_entry_price=row["average_entry_price"],
                        mark_price=row["mark_price"],
                        leverage=float(row["leverage"]),
                        margin_mode=row["margin_mode"],
                        risk_group=row["risk_group"],
                        correlation_source=row["correlation_source"],
                        correlation_snapshot_id=row["correlation_snapshot_id"],
                        initial_margin=initial_margin,
                        maintenance_margin=maintenance,
                        maintenance_margin_rate=float(row["maintenance_margin_rate"]),
                        margin_ratio_pct=margin_ratio,
                        liquidation_price=liquidation_price,
                        accumulated_funding=funding,
                        position_status=row["position_status"],
                        liquidated_at=row["liquidated_at"],
                        realized_pnl=float(row["realized_pnl"]),
                        unrealized_pnl=unrealized,
                        total_fees=float(row["total_fees"]),
                        notional=notional,
                        updated_at=row["updated_at"],
                    )
                )
            equity = float(account["cash_balance"]) + unrealized_total
            free_margin = equity - used_margin
            margin_utilization = (
                used_margin / equity * 100.0
                if equity > 0.0
                else (100.0 if used_margin > 0.0 else 0.0)
            )
            margin_level = equity / maintenance_total * 100.0 if maintenance_total > 0.0 else None
            for position in positions:
                if position.margin_mode == "cross" and position.quantity != 0.0:
                    position.margin_ratio_pct = margin_level
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
            total_funding=float(account["total_funding"]),
            used_margin=used_margin,
            maintenance_margin=maintenance_total,
            free_margin=free_margin,
            margin_utilization_pct=margin_utilization,
            margin_level_pct=margin_level,
            liquidation_count=int(account["liquidation_count"]),
            daily_drawdown_pct=daily_drawdown,
            kill_switch_engaged=bool(control["kill_switch_engaged"]),
            live_execution_enabled=settings.enable_live_execution,
            positions=positions,
            updated_at=self._now(),
        )

    def mark_portfolio(self, user_id: int, tick: PaperMarketTickRequest) -> PaperPortfolio:
        mark = (tick.bid + tick.ask) / 2.0
        with self.database.connection() as conn:
            self._ensure_control(conn, user_id)
            self._ensure_account(conn, user_id)
            control_row = conn.execute(
                "SELECT * FROM paper_execution_controls WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            tick_dt = tick.timestamp.astimezone(timezone.utc)
            age_seconds = (datetime.now(timezone.utc) - tick_dt).total_seconds()
            if age_seconds > float(control_row["max_tick_age_seconds"]):
                raise PaperOmsError("paper_tick_stale")
            if age_seconds < -5.0:
                raise PaperOmsError("paper_tick_from_future")
            conn.execute(
                "UPDATE paper_positions SET mark_price = ?, updated_at = ? WHERE user_id = ? AND symbol = ?",
                (mark, self._now(), user_id, tick.symbol.upper()),
            )
            self._evaluate_liquidations_with_conn(conn, user_id, tick, control_row)
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
                    automated_feed_enabled=False,
                    max_open_orders=control.max_open_orders,
                    max_order_notional=control.max_order_notional,
                    default_fee_bps=control.default_fee_bps,
                    default_slippage_bps=control.default_slippage_bps,
                    max_daily_drawdown_pct=control.max_daily_drawdown_pct,
                    max_tick_age_seconds=control.max_tick_age_seconds,
                    max_leverage=control.max_leverage,
                    default_maintenance_margin_rate=control.default_maintenance_margin_rate,
                    liquidation_fee_bps=control.liquidation_fee_bps,
                    max_margin_utilization_pct=control.max_margin_utilization_pct,
                    max_symbol_margin_pct=control.max_symbol_margin_pct,
                    max_risk_group_margin_pct=control.max_risk_group_margin_pct,
                    max_directional_notional_multiple=control.max_directional_notional_multiple,
                    acknowledgement="I_UNDERSTAND_PAPER_ONLY",
                ),
            )
            portfolio = self.get_portfolio(user_id)
        return portfolio

    def _margin_event_from_row(self, row) -> PaperMarginEvent:
        return PaperMarginEvent(
            event_id=row["event_id"],
            event_type=row["event_type"],
            symbol=row["symbol"],
            amount=float(row["amount"]),
            funding_rate=float(row["funding_rate"]) if row["funding_rate"] is not None else None,
            mark_price=float(row["mark_price"]) if row["mark_price"] is not None else None,
            realized_pnl=float(row["realized_pnl"]),
            source=row["source"],
            is_real_rate=bool(row["is_real_rate"]),
            payload_hash=row["payload_hash"],
            created_at=row["created_at"],
            live_routed=False,
        )

    def settle_funding(
        self,
        user_id: int,
        request: PaperFundingSettlementRequest,
    ) -> PaperFundingSettlementResponse:
        payload = request.model_dump(mode="json", exclude={"event_id"})
        payload["symbol"] = request.symbol.upper()
        payload_hash = self._payload_hash(payload)
        with self.database.connection() as conn:
            self._ensure_control(conn, user_id)
            self._ensure_account(conn, user_id)
            account_sql = "SELECT * FROM paper_accounts WHERE user_id = ?"
            if self.database.backend == "postgresql":
                account_sql += " FOR UPDATE"
            account = conn.execute(account_sql, (user_id,)).fetchone()
            existing = conn.execute(
                "SELECT * FROM paper_margin_events WHERE user_id = ? AND event_id = ?",
                (user_id, request.event_id),
            ).fetchone()
            if existing is not None:
                if existing["payload_hash"] != payload_hash:
                    raise PaperOmsError("funding_event_id_payload_conflict")
                return PaperFundingSettlementResponse(
                    event=self._margin_event_from_row(existing),
                    duplicate=True,
                    cash_balance=float(account["cash_balance"]),
                    total_funding=float(account["total_funding"]),
                    live_execution_enabled=settings.enable_live_execution,
                )
            economic_duplicate = conn.execute(
                "SELECT * FROM paper_margin_events "
                "WHERE user_id = ? AND event_type = 'funding' AND payload_hash = ?",
                (user_id, payload_hash),
            ).fetchone()
            if economic_duplicate is not None:
                return PaperFundingSettlementResponse(
                    event=self._margin_event_from_row(economic_duplicate),
                    duplicate=True,
                    cash_balance=float(account["cash_balance"]),
                    total_funding=float(account["total_funding"]),
                    live_execution_enabled=settings.enable_live_execution,
                )
            funding_time = request.timestamp.astimezone(timezone.utc)
            age_seconds = (datetime.now(timezone.utc) - funding_time).total_seconds()
            if age_seconds > 86_400:
                raise PaperOmsError("paper_funding_event_stale")
            if age_seconds < -300:
                raise PaperOmsError("paper_funding_event_from_future")
            position_sql = "SELECT * FROM paper_positions WHERE user_id = ? AND symbol = ?"
            if self.database.backend == "postgresql":
                position_sql += " FOR UPDATE"
            position = conn.execute(
                position_sql,
                (user_id, request.symbol.upper()),
            ).fetchone()
            if position is None or abs(float(position["quantity"])) <= 1e-12:
                raise PaperOmsError("paper_funding_position_not_open")
            quantity = float(position["quantity"])
            mark = float(position["mark_price"] or position["average_entry_price"] or 0.0)
            if mark <= 0.0:
                raise PaperOmsError("paper_funding_mark_unavailable")
            funding_amount = quantity * mark * request.funding_rate
            new_funding = float(position["accumulated_funding"]) + funding_amount
            control = conn.execute(
                "SELECT liquidation_fee_bps FROM paper_execution_controls WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            liquidation_price = self._liquidation_price(
                quantity,
                float(position["average_entry_price"] or 0.0),
                float(position["initial_margin"]),
                float(position["maintenance_margin_rate"]),
                new_funding,
                float(control["liquidation_fee_bps"]),
            )
            now = self._now()
            conn.execute(
                """
                UPDATE paper_positions
                SET accumulated_funding = ?, liquidation_price = ?, updated_at = ?
                WHERE user_id = ? AND symbol = ?
                """,
                (new_funding, liquidation_price, now, user_id, request.symbol.upper()),
            )
            conn.execute(
                """
                UPDATE paper_accounts
                SET cash_balance = cash_balance - ?, total_funding = total_funding + ?,
                    updated_at = ? WHERE user_id = ?
                """,
                (funding_amount, funding_amount, now, user_id),
            )
            self._append_margin_event(
                conn,
                user_id,
                request.event_id,
                "funding",
                request.symbol.upper(),
                funding_amount,
                request.funding_rate,
                mark,
                0.0,
                request.source,
                False,
                payload_hash,
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM paper_margin_events WHERE user_id = ? AND event_id = ?",
                (user_id, request.event_id),
            ).fetchone()
            updated_account = conn.execute(
                "SELECT cash_balance, total_funding FROM paper_accounts WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return PaperFundingSettlementResponse(
            event=self._margin_event_from_row(row),
            duplicate=False,
            cash_balance=float(updated_account["cash_balance"]),
            total_funding=float(updated_account["total_funding"]),
            live_execution_enabled=settings.enable_live_execution,
        )

    def list_margin_events(self, user_id: int, limit: int = 100) -> PaperMarginEventListResponse:
        with self.database.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM paper_margin_events WHERE user_id = ? "
                "ORDER BY created_at DESC LIMIT ?",
                (user_id, max(1, min(limit, 500))),
            ).fetchall()
        items = [self._margin_event_from_row(row) for row in rows]
        return PaperMarginEventListResponse(
            items=items,
            count=len(items),
            live_execution_enabled=settings.enable_live_execution,
        )

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
            leverage=float(row["leverage"]),
            margin_mode=row["margin_mode"],
            maintenance_margin_rate=float(row["maintenance_margin_rate"]),
            risk_group=row["risk_group"],
            correlation_source=row["correlation_source"],
            correlation_snapshot_id=row["correlation_snapshot_id"],
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
