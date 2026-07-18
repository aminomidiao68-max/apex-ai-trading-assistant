from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings
from app.models import (
    PaperConnectorCheckpoint,
    PaperConnectorCheckpointListResponse,
    PaperLedgerAuditResponse,
    PaperShadowReconciliationRequest,
    PaperShadowReconciliationResponse,
)
from app.services.database_service import DatabaseManager


_CONNECTORS = {
    "binance_futures_testnet": "https://demo-fapi.binance.com/fapi/v1/time",
    "bybit_testnet": "https://api-testnet.bybit.com/v5/market/time",
}
_TERMINAL = {"filled", "canceled", "rejected", "expired"}
_OPEN = {"accepted", "working", "partially_filled"}


class PaperRecoveryError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class PaperRecoveryService:
    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    @staticmethod
    def _now_dt() -> datetime:
        return datetime.now(timezone.utc)

    def _now(self) -> str:
        return self._now_dt().isoformat()

    @staticmethod
    def _hash(payload: dict) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _ensure_checkpoint(self, conn, user_id: int, connector: str) -> None:
        now = self._now()
        conn.execute(
            """
            INSERT INTO paper_connector_checkpoints (
                user_id, connector, state, consecutive_failures, backoff_until,
                latency_ms, server_time_offset_ms, last_probe_at, last_success_at,
                last_error_code, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, connector) DO NOTHING
            """,
            (user_id, connector, "unknown", 0, None, None, None, None, None, None, now),
        )

    @staticmethod
    def _checkpoint_from_row(row) -> PaperConnectorCheckpoint:
        return PaperConnectorCheckpoint(
            connector=row["connector"],
            state=row["state"],
            public_connectivity_only=True,
            authenticated=False,
            order_routing_enabled=False,
            consecutive_failures=int(row["consecutive_failures"] or 0),
            backoff_until=row["backoff_until"],
            latency_ms=int(row["latency_ms"]) if row["latency_ms"] is not None else None,
            server_time_offset_ms=(
                int(row["server_time_offset_ms"])
                if row["server_time_offset_ms"] is not None
                else None
            ),
            last_probe_at=row["last_probe_at"],
            last_success_at=row["last_success_at"],
            last_error_code=row["last_error_code"],
            live_execution_enabled=settings.enable_live_execution,
        )

    def list_checkpoints(self, user_id: int) -> PaperConnectorCheckpointListResponse:
        with self.database.connection() as conn:
            for connector in _CONNECTORS:
                self._ensure_checkpoint(conn, user_id, connector)
            conn.commit()
            rows = conn.execute(
                "SELECT * FROM paper_connector_checkpoints WHERE user_id = ? ORDER BY connector",
                (user_id,),
            ).fetchall()
        items = [self._checkpoint_from_row(row) for row in rows]
        return PaperConnectorCheckpointListResponse(
            items=items,
            count=len(items),
            live_execution_enabled=settings.enable_live_execution,
        )

    async def probe_connector(
        self,
        user_id: int,
        connector: str,
        force: bool = False,
    ) -> PaperConnectorCheckpoint:
        if connector not in _CONNECTORS:
            raise PaperRecoveryError("paper_testnet_connector_not_supported")
        now_dt = self._now_dt()
        with self.database.connection() as conn:
            self._ensure_checkpoint(conn, user_id, connector)
            conn.commit()
            row = conn.execute(
                "SELECT * FROM paper_connector_checkpoints WHERE user_id = ? AND connector = ?",
                (user_id, connector),
            ).fetchone()
        if row["backoff_until"] and not force:
            backoff_until = datetime.fromisoformat(row["backoff_until"])
            if backoff_until > now_dt:
                return self._checkpoint_from_row(row)

        started = time.monotonic()
        error_code = None
        server_ms = None
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(
                    _CONNECTORS[connector],
                    headers={"User-Agent": "APEX-Paper-Testnet-Probe/1.0"},
                )
            if not response.is_success:
                error_code = "public_probe_http_error"
            else:
                data = response.json()
                if connector == "binance_futures_testnet":
                    server_ms = int(data["serverTime"])
                else:
                    if int(data.get("retCode", -1)) != 0:
                        raise ValueError("provider status")
                    result = data.get("result") or {}
                    raw_time = result.get("timeSecond")
                    server_ms = int(raw_time) * 1000 if raw_time else int(data["time"])
        except (httpx.TimeoutException, httpx.NetworkError):
            error_code = "public_probe_network_unavailable"
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            error_code = "public_probe_invalid_response"
        latency_ms = max(0, int((time.monotonic() - started) * 1000))
        now_dt = self._now_dt()
        now = now_dt.isoformat()
        with self.database.connection() as conn:
            current = conn.execute(
                "SELECT * FROM paper_connector_checkpoints WHERE user_id = ? AND connector = ?",
                (user_id, connector),
            ).fetchone()
            if error_code is None and server_ms is not None:
                offset = server_ms - int(now_dt.timestamp() * 1000)
                conn.execute(
                    """
                    UPDATE paper_connector_checkpoints
                    SET state = 'connected', consecutive_failures = 0, backoff_until = NULL,
                        latency_ms = ?, server_time_offset_ms = ?, last_probe_at = ?,
                        last_success_at = ?, last_error_code = NULL, updated_at = ?
                    WHERE user_id = ? AND connector = ?
                    """,
                    (latency_ms, offset, now, now, now, user_id, connector),
                )
            else:
                failures = int(current["consecutive_failures"] or 0) + 1
                backoff_seconds = min(600, 5 * (2 ** min(failures, 7)))
                conn.execute(
                    """
                    UPDATE paper_connector_checkpoints
                    SET state = 'backoff', consecutive_failures = ?, backoff_until = ?,
                        latency_ms = ?, last_probe_at = ?, last_error_code = ?, updated_at = ?
                    WHERE user_id = ? AND connector = ?
                    """,
                    (
                        failures,
                        (now_dt + timedelta(seconds=backoff_seconds)).isoformat(),
                        latency_ms,
                        now,
                        error_code or "public_probe_unknown_error",
                        now,
                        user_id,
                        connector,
                    ),
                )
            conn.commit()
            updated = conn.execute(
                "SELECT * FROM paper_connector_checkpoints WHERE user_id = ? AND connector = ?",
                (user_id, connector),
            ).fetchone()
        return self._checkpoint_from_row(updated)

    @staticmethod
    def _reconciliation_from_row(row, duplicate: bool) -> PaperShadowReconciliationResponse:
        return PaperShadowReconciliationResponse(
            run_id=row["run_id"],
            connector=row["connector"],
            snapshot_id=row["snapshot_id"],
            status=row["status"],
            matched_orders=int(row["matched_orders"]),
            mismatched_orders=int(row["mismatched_orders"]),
            missing_local_orders=int(row["missing_local_orders"]),
            missing_external_orders=int(row["missing_external_orders"]),
            issues=list(json.loads(row["issues_json"])),
            duplicate=duplicate,
            snapshot_verified_by_provider=False,
            public_connectivity_only=True,
            actionable_for_live=False,
            live_execution_enabled=settings.enable_live_execution,
            created_at=row["created_at"],
        )

    def reconcile_shadow_snapshot(
        self,
        user_id: int,
        request: PaperShadowReconciliationRequest,
    ) -> PaperShadowReconciliationResponse:
        payload = request.model_dump(mode="json", exclude={"run_id"})
        request_hash = self._hash(payload)
        snapshot_time = request.snapshot_timestamp.astimezone(timezone.utc)
        age = (self._now_dt() - snapshot_time).total_seconds()
        if age > 86_400:
            raise PaperRecoveryError("shadow_snapshot_stale")
        if age < -300:
            raise PaperRecoveryError("shadow_snapshot_from_future")
        with self.database.connection() as conn:
            existing = conn.execute(
                "SELECT * FROM paper_shadow_reconciliations WHERE user_id = ? AND run_id = ?",
                (user_id, request.run_id),
            ).fetchone()
            if existing is not None:
                if existing["request_hash"] != request_hash:
                    raise PaperRecoveryError("shadow_run_id_payload_conflict")
                return self._reconciliation_from_row(existing, duplicate=True)
            same_snapshot = conn.execute(
                "SELECT * FROM paper_shadow_reconciliations "
                "WHERE user_id = ? AND connector = ? AND snapshot_id = ?",
                (user_id, request.connector, request.snapshot_id),
            ).fetchone()
            if same_snapshot is not None:
                if same_snapshot["request_hash"] != request_hash:
                    raise PaperRecoveryError("shadow_snapshot_id_payload_conflict")
                return self._reconciliation_from_row(same_snapshot, duplicate=True)
            local_rows = conn.execute(
                "SELECT * FROM paper_orders WHERE user_id = ?",
                (user_id,),
            ).fetchall()
            local = {str(row["order_id"]): row for row in local_rows}
            external = {item.order_id: item for item in request.orders}
            matched = 0
            mismatched = 0
            missing_local = 0
            issues: list[str] = []
            for order_id, item in external.items():
                row = local.get(order_id)
                if row is None:
                    missing_local += 1
                    issues.append(f"external_order_missing_locally:{order_id}")
                    continue
                order_issues = []
                if row["status"] != item.status:
                    order_issues.append("status")
                if abs(float(row["filled_quantity"]) - item.filled_quantity) > 1e-8:
                    order_issues.append("filled_quantity")
                local_average = row["average_fill_price"]
                if (local_average is None) != (item.average_fill_price is None) or (
                    local_average is not None
                    and item.average_fill_price is not None
                    and abs(float(local_average) - item.average_fill_price) > 1e-8
                ):
                    order_issues.append("average_fill_price")
                if abs(float(row["total_fees"]) - item.total_fees) > 1e-8:
                    order_issues.append("fees")
                if order_issues:
                    mismatched += 1
                    issues.append(f"order_mismatch:{order_id}:{','.join(order_issues)}")
                else:
                    matched += 1
            missing_external_ids = [
                order_id
                for order_id, row in local.items()
                if row["status"] in _OPEN and order_id not in external
            ]
            for order_id in missing_external_ids:
                issues.append(f"open_local_order_missing_externally:{order_id}")
            missing_external = len(missing_external_ids)
            status = "EMPTY" if not request.orders and not local_rows else ("CONSISTENT" if not issues else "MISMATCH")
            now = self._now()
            conn.execute(
                """
                INSERT INTO paper_shadow_reconciliations (
                    user_id, run_id, connector, snapshot_id, request_hash, status,
                    matched_orders, mismatched_orders, missing_local_orders,
                    missing_external_orders, issues_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    request.run_id,
                    request.connector,
                    request.snapshot_id,
                    request_hash,
                    status,
                    matched,
                    mismatched,
                    missing_local,
                    missing_external,
                    json.dumps(issues[:200], separators=(",", ":")),
                    now,
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM paper_shadow_reconciliations WHERE user_id = ? AND run_id = ?",
                (user_id, request.run_id),
            ).fetchone()
        return self._reconciliation_from_row(row, duplicate=False)

    def audit_ledger(self, user_id: int) -> PaperLedgerAuditResponse:
        issues: list[str] = []
        with self.database.connection() as conn:
            orders = conn.execute(
                "SELECT * FROM paper_orders WHERE user_id = ? ORDER BY created_at, order_id",
                (user_id,),
            ).fetchall()
            fills = conn.execute(
                "SELECT f.*, o.side, o.symbol FROM paper_fills f "
                "JOIN paper_orders o ON o.order_id = f.order_id "
                "WHERE f.user_id = ? ORDER BY f.created_at, f.fill_id",
                (user_id,),
            ).fetchall()
            events = conn.execute(
                "SELECT * FROM paper_order_events WHERE user_id = ? ORDER BY order_id, sequence",
                (user_id,),
            ).fetchall()
            positions = conn.execute(
                "SELECT * FROM paper_positions WHERE user_id = ? ORDER BY symbol",
                (user_id,),
            ).fetchall()
            margin_events = conn.execute(
                "SELECT * FROM paper_margin_events WHERE user_id = ? ORDER BY created_at, event_id",
                (user_id,),
            ).fetchall()
            account = conn.execute(
                "SELECT * FROM paper_accounts WHERE user_id = ?",
                (user_id,),
            ).fetchone()

        fills_by_order: dict[str, list] = {}
        for fill in fills:
            fills_by_order.setdefault(str(fill["order_id"]), []).append(fill)
        events_by_order: dict[str, list] = {}
        for event in events:
            events_by_order.setdefault(str(event["order_id"]), []).append(event)
        for order in orders:
            order_id = str(order["order_id"])
            order_fills = fills_by_order.get(order_id, [])
            quantity = sum(float(item["quantity"]) for item in order_fills)
            fees = sum(float(item["fee_amount"]) for item in order_fills)
            weighted = sum(float(item["quantity"]) * float(item["price"]) for item in order_fills)
            average = weighted / quantity if quantity > 0 else None
            if abs(quantity - float(order["filled_quantity"])) > 1e-8:
                issues.append(f"order_fill_quantity_mismatch:{order_id}")
            if abs(fees - float(order["total_fees"])) > 1e-8:
                issues.append(f"order_fee_mismatch:{order_id}")
            if average is not None and (
                order["average_fill_price"] is None
                or abs(average - float(order["average_fill_price"])) > 1e-8
            ):
                issues.append(f"order_average_price_mismatch:{order_id}")
            order_events = events_by_order.get(order_id, [])
            sequences = [int(item["sequence"]) for item in order_events]
            if sequences != list(range(1, len(sequences) + 1)):
                issues.append(f"order_event_sequence_invalid:{order_id}")
            terminal_at = order["terminal_at"]
            if (order["status"] in _TERMINAL) != (terminal_at is not None):
                issues.append(f"order_terminal_timestamp_invalid:{order_id}")

        replay: dict[str, dict[str, float]] = {}
        timeline = []
        for fill in fills:
            timeline.append((fill["created_at"], "fill", fill))
        for event in margin_events:
            if event["event_type"] == "liquidation":
                timeline.append((event["created_at"], "liquidation", event))
        timeline.sort(key=lambda item: (item[0], item[1]))
        for _, kind, item in timeline:
            symbol = str(item["symbol"])
            state = replay.setdefault(symbol, {"quantity": 0.0, "average": 0.0, "realized": 0.0, "fees": 0.0})
            if kind == "liquidation":
                state["realized"] += float(item["realized_pnl"])
                state["fees"] += float(item["amount"])
                state["quantity"] = 0.0
                state["average"] = 0.0
                continue
            signed = float(item["quantity"]) if item["side"] == "buy" else -float(item["quantity"])
            old = state["quantity"]
            new = old + signed
            price = float(item["price"])
            if old == 0.0 or old * signed > 0.0:
                state["average"] = (
                    (state["average"] * abs(old) + price * abs(signed)) / (abs(old) + abs(signed))
                )
            else:
                closed = min(abs(old), abs(signed))
                state["realized"] += closed * (price - state["average"]) * (1.0 if old > 0 else -1.0)
                if abs(new) <= 1e-12:
                    new = 0.0
                    state["average"] = 0.0
                elif old * new < 0.0:
                    state["average"] = price
            state["quantity"] = new
            state["fees"] += float(item["fee_amount"])
        position_symbols = {str(item["symbol"]) for item in positions}
        for symbol in replay:
            if symbol not in position_symbols:
                issues.append(f"position_missing_for_fill_history:{symbol}")
        for position in positions:
            symbol = str(position["symbol"])
            state = replay.get(symbol, {"quantity": 0.0, "average": 0.0, "realized": 0.0, "fees": 0.0})
            if abs(state["quantity"] - float(position["quantity"])) > 1e-8:
                issues.append(f"position_quantity_mismatch:{symbol}")
            stored_average = float(position["average_entry_price"] or 0.0)
            if abs(state["quantity"]) > 1e-12 and abs(state["average"] - stored_average) > 1e-8:
                issues.append(f"position_average_entry_mismatch:{symbol}")
            if abs(state["realized"] - float(position["realized_pnl"])) > 1e-8:
                issues.append(f"position_realized_pnl_mismatch:{symbol}")
            if abs(state["fees"] - float(position["total_fees"])) > 1e-8:
                issues.append(f"position_fee_mismatch:{symbol}")

        if account is not None:
            position_realized = sum(float(item["realized_pnl"]) for item in positions)
            position_fees = sum(float(item["total_fees"]) for item in positions)
            funding = sum(
                float(item["amount"])
                for item in margin_events
                if item["event_type"] == "funding"
            )
            liquidation_count = sum(1 for item in margin_events if item["event_type"] == "liquidation")
            if abs(position_realized - float(account["realized_pnl"])) > 1e-8:
                issues.append("account_realized_pnl_mismatch")
            if abs(position_fees - float(account["total_fees"])) > 1e-8:
                issues.append("account_fee_mismatch")
            if abs(funding - float(account["total_funding"])) > 1e-8:
                issues.append("account_funding_mismatch")
            if liquidation_count != int(account["liquidation_count"]):
                issues.append("account_liquidation_count_mismatch")
            expected_cash = (
                float(account["initial_cash"])
                + float(account["realized_pnl"])
                - float(account["total_fees"])
                - float(account["total_funding"])
            )
            if abs(expected_cash - float(account["cash_balance"])) > 1e-7:
                issues.append("account_cash_identity_mismatch")
        return PaperLedgerAuditResponse(
            consistent=not issues,
            order_count=len(orders),
            fill_count=len(fills),
            event_count=len(events),
            position_count=len(positions),
            margin_event_count=len(margin_events),
            issues=issues[:200],
            repair_performed=False,
            actionable_for_live=False,
            live_execution_enabled=settings.enable_live_execution,
            audited_at=self._now(),
        )
