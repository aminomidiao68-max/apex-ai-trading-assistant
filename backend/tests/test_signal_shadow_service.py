from datetime import datetime, timedelta, timezone

import pytest

from app.services.database_service import DatabaseManager, LATEST_SCHEMA_VERSION
from app.services.signal_shadow_service import SignalShadowError, SignalShadowService


def _move_capture_to_past(db, observation_id: str, minutes: int = 60) -> float:
    captured = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    with db.connection() as conn:
        conn.execute(
            "UPDATE signal_shadow_observations SET captured_at=? WHERE observation_id=?",
            (captured.isoformat(), observation_id),
        )
        conn.commit()
    return captured.timestamp()


def _candidate(*, max_bars: int = 3, target_key: str = "tp") -> dict:
    levels = {"entry": 100, "sl": 99, target_key: 102}
    return {
        "symbol": "BTCUSDT",
        "market": "crypto",
        "status": "ACTIONABLE_CANDIDATE",
        "side": "long",
        "failed_gates": [],
        "levels": levels,
        "resolution_timeframe": "5m",
        "max_resolution_bars": max_bars,
        "frames": [
            {"timeframe": "1h", "regime": "trending"},
            {"timeframe": "4h", "regime": "trending"},
        ],
        "actionable_for_live": False,
    }


def test_shadow_capture_never_routes_and_panel_is_insufficient(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "shadow.db"))
    service = SignalShadowService(db)
    no_trade = service.capture(
        1,
        {
            "symbol": "BTCUSDT",
            "market": "crypto",
            "status": "NO_TRADE",
            "side": "flat",
            "failed_gates": ["context_consensus"],
            "actionable_for_live": False,
        },
    )
    # Real SMC payloads expose the first target as levels.tp. The capture
    # contract must not silently lose a valid candidate by requiring tp1.
    candidate = service.capture(1, _candidate(target_key="tp"))
    assert no_trade.outcome_status == "NOT_APPLICABLE"
    assert candidate.outcome_status == "PENDING"
    assert candidate.target_price == 102
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
    assert service.should_capture(1, "BTCUSDT", 900) is False
    assert service.should_capture(1, "ETHUSDT", 900) is True
    pending = service.pending_contexts(1)
    assert [item["observation_id"] for item in pending] == [candidate.observation_id]

    captured_ts = _move_capture_to_past(db, candidate.observation_id)
    resolved = service.resolve(
        1,
        candidate.observation_id,
        [{"t": captured_ts + 60, "o": 100, "h": 102.2, "l": 98.8, "c": 101}],
    )
    assert resolved.outcome_status == "LOSS"  # stop-first when SL and TP touch together
    assert resolved.realized_rr == -1.0
    assert resolved.resolution_reason == "stop_hit"
    assert resolved.future_only_enforced is True
    assert resolved.completed_candles_only is True
    after = service.panel(1, minimum_required_resolved=30)
    assert after.pending_outcomes == 0 and after.resolved_outcomes == 1
    assert service.panel(2).total_observations == 0
    assert db.schema_version() == LATEST_SCHEMA_VERSION == 18


def test_shadow_diagnostics_verify_evidence_and_report_stale_blockers(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "diagnostics.db"))
    service = SignalShadowService(db)
    captured = service.capture(
        19,
        {
            "symbol": "XAUUSD",
            "market": "forex",
            "status": "NO_TRADE",
            "side": "flat",
            "failed_gates": ["frame_freshness", "context_regime"],
            "frames": [
                {"timeframe": "5m", "fresh": False, "regime": "choppy"},
                {"timeframe": "15m", "fresh": False, "regime": "choppy"},
                {"timeframe": "1h", "fresh": False, "regime": "choppy"},
                {"timeframe": "4h", "fresh": False, "regime": "balanced"},
            ],
        },
    )
    diagnostics = service.diagnostics(19)
    assert diagnostics.total_observations == 1
    assert diagnostics.observations_analyzed == 1
    assert diagnostics.evidence_integrity_failures == 0
    assert diagnostics.status_counts == {"NO_TRADE": 1}
    assert diagnostics.failed_gate_counts["frame_freshness"] == 1
    assert diagnostics.context_regime_counts == {"balanced": 1, "choppy": 1}
    assert diagnostics.stale_frame_observations == 1
    assert diagnostics.all_frames_stale_observations == 1
    assert diagnostics.leading_failed_gates == ["context_regime", "frame_freshness"]
    assert diagnostics.threshold_relaxation_allowed is False
    assert diagnostics.actionable_for_live is False

    with db.connection() as conn:
        conn.execute(
            "UPDATE signal_shadow_observations SET evidence_json=? WHERE observation_id=?",
            ("{}", captured.observation_id),
        )
        conn.commit()
    failed = service.diagnostics(19)
    assert failed.evidence_integrity_failures == 1
    assert failed.observations_analyzed == 0


def test_active_candidate_has_terminal_horizon_expiry(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "active-expiry.db"))
    service = SignalShadowService(db)
    candidate = service.capture(7, _candidate(max_bars=3, target_key="tp1"))
    captured_ts = _move_capture_to_past(db, candidate.observation_id)
    candles = [
        {"t": captured_ts + 60 + index * 300, "o": 100, "h": 101, "l": 99.5, "c": 100.5}
        for index in range(3)
    ]
    resolved = service.resolve(7, candidate.observation_id, candles)
    assert resolved.outcome_status == "EXPIRED_ACTIVE"
    assert resolved.activated is True
    assert resolved.bars_observed == 3
    assert resolved.realized_rr == 0.5
    assert resolved.resolution_reason == "active_horizon_elapsed"
    assert resolved.resolution_close_price == 100.5
    assert service.pending_contexts(7) == []


def test_in_progress_and_pre_capture_candles_cannot_resolve(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "causal.db"))
    service = SignalShadowService(db)
    candidate = service.capture(3, _candidate(max_bars=1))
    captured_ts = datetime.fromisoformat(candidate.captured_at).timestamp()
    result = service.resolve(
        3,
        candidate.observation_id,
        [
            {"t": captured_ts - 600, "o": 100, "h": 103, "l": 98, "c": 101},
            {"t": captured_ts + 60, "o": 100, "h": 103, "l": 98, "c": 101},
        ],
    )
    assert result.outcome_status == "PENDING"
    assert result.bars_observed == 0


def test_no_entry_outcomes_cannot_satisfy_activated_research_gate(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "no-entry-research.db"))
    service = SignalShadowService(db)
    for _ in range(30):
        candidate = service.capture(12, _candidate(max_bars=1))
        captured_ts = _move_capture_to_past(db, candidate.observation_id, minutes=120)
        outcome = service.resolve(
            12,
            candidate.observation_id,
            [{"t": captured_ts + 60, "o": 99.5, "h": 99.8, "l": 99.2, "c": 99.6}],
        )
        assert outcome.outcome_status == "EXPIRED_NO_ENTRY"
    panel = service.research_panel(12)
    assert panel.terminal_outcomes == 30
    assert panel.activated_terminal_outcomes == 0
    assert panel.expired_no_entry == 30
    assert panel.status == "INSUFFICIENT_EVIDENCE"
    assert panel.precision_claimed is False
    assert panel.target_hit_rate_pct is None
    summary = service.panel(12)
    assert summary.resolved_outcomes == 30
    assert summary.activated_resolved_outcomes == 0
    assert summary.status == "INSUFFICIENT_EVIDENCE"


def test_research_panel_withholds_metrics_then_uses_wilson_and_integrity_gate(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "research.db"))
    service = SignalShadowService(db)
    empty = service.research_panel(11)
    assert empty.status == "INSUFFICIENT_EVIDENCE"
    assert empty.precision_claimed is False
    assert empty.target_hit_rate_pct is None
    assert len(empty.evidence_dataset_sha256) == 64

    observation_ids = []
    for index in range(30):
        candidate = service.capture(11, _candidate(max_bars=1))
        observation_ids.append(candidate.observation_id)
        captured_ts = _move_capture_to_past(db, candidate.observation_id, minutes=120)
        candle = (
            {"t": captured_ts + 60, "o": 100, "h": 102.2, "l": 99.5, "c": 101.5}
            if index % 2 == 0
            else {"t": captured_ts + 60, "o": 100, "h": 100.5, "l": 98.8, "c": 99.2}
        )
        service.resolve(11, candidate.observation_id, [candle])

    panel = service.research_panel(11)
    assert panel.status == "RESEARCH_READY"
    assert panel.terminal_outcomes == 30
    assert panel.activated_terminal_outcomes == 30
    assert panel.wins == 15 and panel.losses == 15
    assert panel.target_hit_rate_pct == 50.0
    assert panel.wilson_95_lower_pct < 50 < panel.wilson_95_upper_pct
    assert panel.average_realized_rr == 0.5
    assert panel.cumulative_realized_rr == 15.0
    assert panel.precision_claimed is True
    assert panel.probability_is_calibrated is False
    assert panel.actionable_for_live is False
    assert all(item.sample_eligible for item in panel.breakdowns)

    with db.connection() as conn:
        conn.execute(
            "UPDATE signal_shadow_observations SET evidence_json=? WHERE observation_id=?",
            ("{}", observation_ids[0]),
        )
        conn.commit()
    failed = service.research_panel(11)
    assert failed.status == "INTEGRITY_FAILED"
    assert failed.evidence_integrity_failures == 1
    assert failed.precision_claimed is False
    assert failed.target_hit_rate_pct is None
    assert failed.breakdowns == []


def test_invalid_candidate_geometry_is_rejected(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "invalid.db"))
    service = SignalShadowService(db)
    payload = _candidate()
    payload["levels"] = {"entry": 100, "sl": 101, "tp": 102}
    with pytest.raises(SignalShadowError, match="candidate_resolution_geometry_invalid"):
        service.capture(1, payload)
