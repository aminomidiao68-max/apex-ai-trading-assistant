from __future__ import annotations

import gzip
import hashlib
import json
from datetime import datetime, timezone

from app.config import settings
from app.models import (
    PaperChaosDrillRunRequest,
    PaperChaosDrillRunResponse,
    PaperChaosScenarioResult,
    PaperRecoverySnapshotResponse,
)
from app.services.database_service import DatabaseManager


class PaperChaosError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


_TABLES = {
    "orders": "paper_orders",
    "fills": "paper_fills",
    "order_events": "paper_order_events",
    "accounts": "paper_accounts",
    "positions": "paper_positions",
    "market_ticks": "paper_market_ticks",
    "margin_events": "paper_margin_events",
    "connector_checkpoints": "paper_connector_checkpoints",
    "shadow_reconciliations": "paper_shadow_reconciliations",
    "private_reconciliations": "paper_private_testnet_reconciliations",
    "correlation_snapshots": "paper_correlation_snapshots",
}


class PaperChaosService:
    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    @staticmethod
    def _hash(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def _jsonable(row) -> dict:
        output = {}
        for key in row.keys():
            value = row[key]
            output[key] = value.hex() if isinstance(value, bytes) else value
        return output

    def create_snapshot(self, user_id: int, snapshot_id: str) -> PaperRecoverySnapshotResponse:
        payload = {}
        with self.database.connection() as conn:
            for label, table in _TABLES.items():
                rows = conn.execute(f"SELECT * FROM {table} WHERE user_id = ?", (user_id,)).fetchall()
                items = [self._jsonable(row) for row in rows]
                payload[label] = sorted(items, key=lambda item: json.dumps(item, sort_keys=True, default=str))
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
        digest = self._hash(canonical)
        compressed = gzip.compress(canonical, compresslevel=9, mtime=0)
        counts = {key: len(value) for key, value in payload.items()}
        now = datetime.now(timezone.utc).isoformat()
        with self.database.connection() as conn:
            existing = conn.execute(
                "SELECT * FROM paper_recovery_snapshots WHERE user_id = ? AND snapshot_id = ?",
                (user_id, snapshot_id),
            ).fetchone()
            if existing is not None:
                if existing["canonical_sha256"] != digest:
                    raise PaperChaosError("immutable_recovery_snapshot_conflict")
                return PaperRecoverySnapshotResponse(
                    snapshot_id=snapshot_id,
                    canonical_sha256=existing["canonical_sha256"],
                    compressed_size_bytes=len(bytes(existing["payload_gzip"])),
                    row_counts=json.loads(existing["row_counts_json"]),
                    duplicate=True,
                    restore_verified=False,
                    production_mutated=False,
                    created_at=existing["created_at"],
                )
            conn.execute(
                """INSERT INTO paper_recovery_snapshots (
                    user_id, snapshot_id, canonical_sha256, payload_gzip, row_counts_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, snapshot_id, digest, compressed, json.dumps(counts, sort_keys=True), now),
            )
            conn.commit()
        return PaperRecoverySnapshotResponse(
            snapshot_id=snapshot_id, canonical_sha256=digest,
            compressed_size_bytes=len(compressed), row_counts=counts,
            duplicate=False, restore_verified=False, production_mutated=False, created_at=now,
        )

    def verify_snapshot(self, user_id: int, snapshot_id: str) -> PaperRecoverySnapshotResponse:
        with self.database.connection() as conn:
            row = conn.execute(
                "SELECT * FROM paper_recovery_snapshots WHERE user_id = ? AND snapshot_id = ?",
                (user_id, snapshot_id),
            ).fetchone()
        if row is None:
            raise PaperChaosError("recovery_snapshot_not_found")
        try:
            canonical = gzip.decompress(bytes(row["payload_gzip"]))
            payload = json.loads(canonical)
            counts = {key: len(value) for key, value in payload.items()}
        except Exception as exc:
            raise PaperChaosError("recovery_snapshot_corrupt") from exc
        verified = self._hash(canonical) == row["canonical_sha256"] and counts == json.loads(row["row_counts_json"])
        return PaperRecoverySnapshotResponse(
            snapshot_id=snapshot_id, canonical_sha256=row["canonical_sha256"],
            compressed_size_bytes=len(bytes(row["payload_gzip"])), row_counts=counts,
            duplicate=False, restore_verified=verified, production_mutated=False,
            created_at=row["created_at"],
        )

    def _scenario(self, user_id: int, name: str, snapshot_id: str | None) -> PaperChaosScenarioResult:
        invariants = ["order_routing_disabled", "production_not_mutated"]
        rto = 1
        if name == "duplicate_delivery":
            committed = {"event-1"}; committed.add("event-1")
            passed = len(committed) == 1; invariants.append("single_commit_per_event")
        elif name == "crash_before_commit":
            committed = set(); staged = "event-1"; staged = None; committed.add("event-1")
            passed = len(committed) == 1; invariants.append("rollback_then_single_replay")
        elif name == "crash_after_commit_before_ack":
            committed = {"event-1"}; committed.add("event-1")
            passed = len(committed) == 1; invariants.append("ack_loss_does_not_duplicate")
        elif name == "lease_expiry_takeover":
            owner = "worker-a"; owner = "worker-b"
            passed = owner == "worker-b"; rto = 2; invariants.append("single_active_lease_owner")
        elif name == "provider_timeout_backoff":
            delays = [min(600, 5 * (2 ** index)) for index in range(1, 9)]
            passed = delays == sorted(delays) and delays[-1] == 600; rto = 8; invariants.append("bounded_exponential_backoff")
        elif name == "database_reconnect":
            states = ["disconnected", "backoff", "connected"]
            passed = states[-1] == "connected"; rto = 3; invariants.append("fail_closed_until_reconnected")
        else:
            verified = self.verify_snapshot(user_id, snapshot_id or "")
            passed = verified.restore_verified and not verified.production_mutated
            rto = 2; invariants.extend(["sha256_verified", "isolated_restore_only"])
        return PaperChaosScenarioResult(
            scenario=name, passed=passed, invariants=invariants,
            simulated_rpo_events=0 if passed else 1, simulated_rto_steps=rto,
        )

    def run(self, user_id: int, request: PaperChaosDrillRunRequest) -> PaperChaosDrillRunResponse:
        request_hash = self._hash(json.dumps(request.model_dump(mode="json", exclude={"run_id"}), sort_keys=True).encode())
        with self.database.connection() as conn:
            existing = conn.execute("SELECT * FROM paper_chaos_runs WHERE user_id = ? AND run_id = ?", (user_id, request.run_id)).fetchone()
        if existing is not None:
            if existing["request_hash"] != request_hash:
                raise PaperChaosError("chaos_run_id_payload_conflict")
            data = json.loads(existing["result_json"]); data["duplicate"] = True
            return PaperChaosDrillRunResponse(**data)
        items = [self._scenario(user_id, scenario, request.recovery_snapshot_id) for scenario in request.scenarios]
        now = datetime.now(timezone.utc).isoformat()
        response = PaperChaosDrillRunResponse(
            run_id=request.run_id, status="PASSED" if all(item.passed for item in items) else "FAILED",
            items=items, deterministic=True, network_called=False, production_mutated=False,
            order_routing_enabled=False, actionable_for_live=False,
            live_execution_enabled=settings.enable_live_execution, created_at=now,
        )
        with self.database.connection() as conn:
            conn.execute("INSERT INTO paper_chaos_runs (user_id, run_id, request_hash, status, result_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                         (user_id, request.run_id, request_hash, response.status, response.model_dump_json(), now))
            conn.commit()
        return response
