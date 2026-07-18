from __future__ import annotations

import pytest

from app.models import PaperChaosDrillRunRequest
from app.services.database_service import DatabaseManager, LATEST_SCHEMA_VERSION
from app.services.paper_chaos_service import PaperChaosError, PaperChaosService


def test_recovery_snapshot_is_immutable_compressed_and_verified(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "chaos.db")); service = PaperChaosService(db)
    first = service.create_snapshot(1, "recovery-snapshot-0001")
    second = service.create_snapshot(1, "recovery-snapshot-0001")
    verified = service.verify_snapshot(1, "recovery-snapshot-0001")
    assert len(first.canonical_sha256) == 64
    assert first.compressed_size_bytes > 0
    assert first.production_mutated is False
    assert second.duplicate is True
    assert verified.restore_verified is True
    assert verified.production_mutated is False
    assert db.schema_version() == LATEST_SCHEMA_VERSION == 14


def test_chaos_drill_all_scenarios_is_deterministic_idempotent_and_route_free(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "drill.db")); service = PaperChaosService(db)
    service.create_snapshot(1, "recovery-snapshot-0002")
    request = PaperChaosDrillRunRequest(
        run_id="chaos-drill-run-0001",
        scenarios=[
            "duplicate_delivery", "crash_before_commit", "crash_after_commit_before_ack",
            "lease_expiry_takeover", "provider_timeout_backoff", "database_reconnect",
            "restore_checksum",
        ],
        recovery_snapshot_id="recovery-snapshot-0002",
    )
    first = service.run(1, request); second = service.run(1, request)
    assert first.status == "PASSED"
    assert all(item.passed for item in first.items)
    assert all(item.simulated_rpo_events == 0 for item in first.items)
    assert first.network_called is False
    assert first.production_mutated is False
    assert first.order_routing_enabled is False
    assert first.actionable_for_live is False
    assert second.duplicate is True
    with pytest.raises(PaperChaosError, match="chaos_run_id_payload_conflict"):
        service.run(1, request.model_copy(update={"scenarios": ["database_reconnect"]}))


def test_snapshot_conflict_and_user_isolation(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "isolation.db")); service = PaperChaosService(db)
    service.create_snapshot(1, "recovery-snapshot-0003")
    with db.connection() as conn:
        conn.execute("INSERT INTO paper_accounts (user_id, initial_cash, cash_balance, realized_pnl, total_fees, peak_equity, daily_start_equity, trading_day, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (1, 100, 100, 0, 0, 100, 100, "2026-01-01", "now")); conn.commit()
    with pytest.raises(PaperChaosError, match="immutable_recovery_snapshot_conflict"):
        service.create_snapshot(1, "recovery-snapshot-0003")
    with pytest.raises(PaperChaosError, match="recovery_snapshot_not_found"):
        service.verify_snapshot(2, "recovery-snapshot-0003")
