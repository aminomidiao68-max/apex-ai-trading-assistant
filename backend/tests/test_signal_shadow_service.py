from app.services.database_service import DatabaseManager, LATEST_SCHEMA_VERSION
from app.services.signal_shadow_service import SignalShadowService


def test_shadow_capture_never_routes_and_panel_is_insufficient(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "shadow.db"))
    service = SignalShadowService(db)
    no_trade = service.capture(1, {
        "symbol": "BTCUSDT", "market": "crypto", "status": "NO_TRADE",
        "side": "flat", "failed_gates": ["context_consensus"],
        "actionable_for_live": False,
    })
    candidate = service.capture(1, {
        "symbol": "BTCUSDT", "market": "crypto", "status": "ACTIONABLE_CANDIDATE",
        "side": "long", "failed_gates": [], "levels": {"entry": 100, "sl": 99, "tp1": 102},
        "actionable_for_live": False,
    })
    assert no_trade.outcome_status == "NOT_APPLICABLE"
    assert candidate.outcome_status == "PENDING"
    assert no_trade.order_routed is False and candidate.actionable_for_live is False
    assert len(candidate.evidence_sha256) == 64
    panel = service.panel(1, minimum_required_resolved=30)
    assert panel.total_observations == 2
    assert panel.no_trade_count == 1
    assert panel.candidate_count == 1
    assert panel.pending_outcomes == 1
    assert panel.resolved_outcomes == 0
    assert panel.status == "INSUFFICIENT_EVIDENCE"
    assert panel.precision_claimed is False
    assert panel.live_execution_enabled is False
    assert service.panel(2).total_observations == 0
    assert db.schema_version() == LATEST_SCHEMA_VERSION == 16
