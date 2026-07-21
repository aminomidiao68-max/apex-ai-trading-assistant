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
    assert db.schema_version() == LATEST_SCHEMA_VERSION == 20


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
    assert "USDCAD" in diagnostics.collection_universe
    assert "USDCHF" in diagnostics.collection_universe
    assert diagnostics.collection_interval_seconds == 900
    assert diagnostics.collector_max_concurrency == 3
    assert diagnostics.universe_policy == "pre_registered_data_quality_qualified"
    assert diagnostics.valid_non_all_stale_observations == 0
    assert diagnostics.observation_started_at is not None
    assert diagnostics.observation_latest_at is not None
    assert diagnostics.observation_span_days == 0.0
    assert diagnostics.scarcity_min_observations == 1000
    assert diagnostics.scarcity_min_span_days == 5.0
    assert diagnostics.scarcity_review_status == "COLLECTING_EVIDENCE"
    assert diagnostics.feasibility_audit_authorized is False
    assert diagnostics.candidate_rate_claimed is False
    assert diagnostics.threshold_change_authorized is False
    assert diagnostics.threshold_relaxation_allowed is False
    assert diagnostics.actionable_for_live is False

    status, authorized = service._scarcity_review(
        candidate_count=0,
        valid_observations=1000,
        span_days=5.0,
        integrity_failures=0,
        timestamps_complete=True,
        minimum_observations=1000,
        minimum_span_days=5.0,
    )
    assert status == "ELIGIBLE_FOR_FEASIBILITY_AUDIT" and authorized is True
    status, authorized = service._scarcity_review(
        candidate_count=1,
        valid_observations=1000,
        span_days=5.0,
        integrity_failures=0,
        timestamps_complete=True,
        minimum_observations=1000,
        minimum_span_days=5.0,
    )
    assert status == "CANDIDATES_OBSERVED" and authorized is False

    with db.connection() as conn:
        conn.execute(
            "UPDATE signal_shadow_observations SET evidence_json=? WHERE observation_id=?",
            ("{}", captured.observation_id),
        )
        conn.commit()
    failed = service.diagnostics(19)
    assert failed.evidence_integrity_failures == 1
    assert failed.observations_analyzed == 0


def test_feasibility_panel_is_gated_and_aggregates_when_authorized(tmp_path, monkeypatch):
    from types import SimpleNamespace

    db = DatabaseManager(db_path=str(tmp_path / "feasibility.db"))
    service = SignalShadowService(db)
    packets = [
        {
            "symbol": "EURUSD",
            "market": "forex",
            "status": "NO_TRADE",
            "side": "flat",
            "failed_gates": ["gate_a", "gate_b"],
            "gates": [
                {"name": "gate_a", "passed": False},
                {"name": "gate_b", "passed": False},
            ],
            "frames": [{"fresh": True}] * 4,
        },
        {
            "symbol": "USDCHF",
            "market": "forex",
            "status": "WATCH",
            "side": "flat",
            "failed_gates": ["gate_a"],
            "gates": [
                {"name": "gate_a", "passed": False},
                {"name": "gate_b", "passed": True},
            ],
            "frames": [{"fresh": True}] * 4,
        },
        {
            "symbol": "USDCAD",
            "market": "forex",
            "status": "WATCH",
            "side": "flat",
            "failed_gates": [],
            "gates": [
                {"name": "gate_a", "passed": True},
                {"name": "gate_b", "passed": True},
            ],
            "frames": [{"fresh": True}] * 4,
        },
    ]
    for packet in packets:
        service.capture(27, packet)
    withheld = service.feasibility_panel(27)
    assert withheld.status == "NOT_ELIGIBLE"
    assert withheld.audit_metrics_available is False
    assert withheld.failed_gate_counts == {}
    assert withheld.threshold_change_authorized is False

    monkeypatch.setattr(
        service,
        "diagnostics",
        lambda _user_id: SimpleNamespace(
            total_observations=3,
            valid_non_all_stale_observations=1000,
            observation_span_days=5.0,
            scarcity_min_observations=1000,
            scarcity_min_span_days=5.0,
            status_counts={"NO_TRADE": 1, "WATCH": 2},
            evidence_integrity_failures=0,
            feasibility_audit_authorized=True,
        ),
    )
    available = service.feasibility_panel(27)
    assert available.status == "AVAILABLE"
    assert available.audit_metrics_available is True
    assert available.minimum_failed_gates_observed == 0
    assert available.zero_failed_gate_observations == 1
    assert available.failure_cardinality_counts == {"0": 1, "1": 1, "2": 1}
    assert available.failed_gate_counts == {"gate_a": 2, "gate_b": 1}
    assert available.passed_gate_counts == {"gate_a": 1, "gate_b": 2}
    assert available.single_gate_near_miss_counts == {"gate_a": 1}
    assert available.top_cofailure_pairs == {"gate_a|gate_b": 1}
    assert available.feasibility_audit_authorized is True
    assert available.candidate_rate_claimed is False
    assert available.threshold_change_authorized is False
    assert available.actionable_for_live is False


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
    assert empty.bootstrap_average_rr_95_lower is None
    assert empty.profit_factor_rr is None
    assert empty.dependence_aware_metrics_available is False
    assert empty.chronological_stability_status == "WITHHELD_INSUFFICIENT_SAMPLE"
    assert empty.chronological_folds == []
    assert empty.worst_fold_average_rr is None
    assert empty.final_holdout_used is False
    assert len(empty.evidence_dataset_sha256) == 64
    with pytest.raises(SignalShadowError, match="shadow_research_not_ready"):
        service.lock_research_snapshot(11)

    observation_ids = []
    for index in range(60):
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
    assert panel.terminal_outcomes == 60
    assert panel.activated_terminal_outcomes == 60
    assert panel.wins == 30 and panel.losses == 30
    assert panel.target_hit_rate_pct == 50.0
    assert panel.wilson_95_lower_pct < 50 < panel.wilson_95_upper_pct
    assert panel.average_realized_rr == 0.5
    assert panel.cumulative_realized_rr == 30.0
    assert panel.profit_factor_rr == 2.0
    assert panel.average_win_rr == 2.0
    assert panel.average_nonwin_rr == -1.0
    assert panel.active_expiry_rate_pct == 0.0
    assert panel.no_entry_rate_pct == 0.0
    assert panel.max_consecutive_nonwins == 1
    assert panel.bootstrap_average_rr_95_lower <= 0.5
    assert panel.bootstrap_average_rr_95_upper >= 0.5
    assert panel.bootstrap_block_length == 8
    assert panel.bootstrap_replicates == 2000
    assert panel.dependence_aware_metrics_available is True
    assert panel.chronological_stability_status == "AVAILABLE"
    assert panel.chronological_minimum_activated == 60
    assert panel.chronological_fold_count == 3
    assert len(panel.chronological_folds) == 3
    assert all(fold.sample_count == 20 for fold in panel.chronological_folds)
    assert all(fold.average_realized_rr == 0.5 for fold in panel.chronological_folds)
    assert panel.worst_fold_average_rr == 0.5
    assert panel.positive_average_rr_folds == 3
    assert panel.all_folds_positive_average_rr is True
    assert panel.chronological_model_reselection_used is False
    assert panel.chronological_shuffle_used is False
    assert panel.final_holdout_used is False
    again = service.research_panel(11)
    assert again.bootstrap_average_rr_95_lower == panel.bootstrap_average_rr_95_lower
    assert again.bootstrap_average_rr_95_upper == panel.bootstrap_average_rr_95_upper
    assert panel.precision_claimed is True
    assert panel.probability_is_calibrated is False
    assert panel.actionable_for_live is False
    assert all(item.sample_eligible for item in panel.breakdowns)

    snapshot = service.lock_research_snapshot(11)
    assert snapshot.duplicate is False
    assert snapshot.immutable is True
    assert snapshot.dataset_sha256 == panel.evidence_dataset_sha256
    assert len(snapshot.result_sha256) == 64
    assert snapshot.terminal_outcomes == 60
    assert snapshot.activated_terminal_outcomes == 60
    assert snapshot.result.model_dump() == panel.model_dump()
    assert snapshot.manual_outcome_allowed is False
    assert snapshot.threshold_change_authorized is False
    assert snapshot.actionable_for_live is False
    duplicate = service.lock_research_snapshot(11)
    assert duplicate.snapshot_id == snapshot.snapshot_id
    assert duplicate.result_sha256 == snapshot.result_sha256
    assert duplicate.duplicate is True
    loaded = service.get_research_snapshot(11, snapshot.snapshot_id)
    assert loaded.snapshot_id == snapshot.snapshot_id
    assert loaded.duplicate is False
    with pytest.raises(SignalShadowError, match="shadow_research_snapshot_not_found"):
        service.get_research_snapshot(12, snapshot.snapshot_id)
    with db.connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) AS count FROM signal_shadow_research_snapshots WHERE user_id=?",
            (11,),
        ).fetchone()
    assert int(count["count"]) == 1

    holdout = service.lock_forward_holdout_plan(
        11,
        snapshot.snapshot_id,
        required_activated_outcomes=30,
    )
    assert holdout.status == "COLLECTING"
    assert holdout.future_candidates == 0
    assert holdout.future_activated_outcomes == 0
    assert holdout.holdout_dataset_sha256 is None
    assert holdout.ready_at is None
    assert holdout.immutable_cutoff is True
    assert holdout.holdout_metrics_exposed is False
    assert holdout.final_holdout_used is False
    duplicate_holdout = service.lock_forward_holdout_plan(11, snapshot.snapshot_id)
    assert duplicate_holdout.plan_id == holdout.plan_id
    assert duplicate_holdout.duplicate is True
    with pytest.raises(SignalShadowError, match="shadow_forward_holdout_plan_not_found"):
        service.get_forward_holdout_plan(12, holdout.plan_id)

    for index in range(30):
        candidate = service.capture(11, _candidate(max_bars=1))
        with db.connection() as conn:
            conn.execute(
                "UPDATE signal_shadow_observations SET outcome_status=?,realized_rr=?,"
                "activated=?,resolved_at=? WHERE observation_id=?",
                (
                    "WIN" if index % 2 == 0 else "LOSS",
                    2.0 if index % 2 == 0 else -1.0,
                    1,
                    datetime.now(timezone.utc).isoformat(),
                    candidate.observation_id,
                ),
            )
            conn.commit()
    ready_holdout = service.get_forward_holdout_plan(11, holdout.plan_id)
    assert ready_holdout.status == "READY"
    assert ready_holdout.future_candidates == 30
    assert ready_holdout.future_terminal_outcomes == 30
    assert ready_holdout.future_activated_outcomes == 30
    assert len(ready_holdout.holdout_dataset_sha256) == 64
    assert ready_holdout.ready_at is not None
    locked_holdout_sha = ready_holdout.holdout_dataset_sha256

    later_candidate = service.capture(11, _candidate(max_bars=1))
    with db.connection() as conn:
        conn.execute(
            "UPDATE signal_shadow_observations SET outcome_status='WIN',realized_rr=2,"
            "activated=1,resolved_at=? WHERE observation_id=?",
            (datetime.now(timezone.utc).isoformat(), later_candidate.observation_id),
        )
        conn.commit()
    still_locked = service.get_forward_holdout_plan(11, holdout.plan_id)
    assert still_locked.future_activated_outcomes == 31
    assert still_locked.holdout_dataset_sha256 == locked_holdout_sha
    assert still_locked.final_holdout_used is False
    with db.connection() as conn:
        plan_count = conn.execute(
            "SELECT COUNT(*) AS count FROM signal_shadow_forward_holdout_plans WHERE user_id=?",
            (11,),
        ).fetchone()
    assert int(plan_count["count"]) == 1

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
    assert failed.bootstrap_average_rr_95_lower is None
    assert failed.profit_factor_rr is None
    assert failed.dependence_aware_metrics_available is False
    assert failed.chronological_stability_status == "WITHHELD_INSUFFICIENT_SAMPLE"
    assert failed.chronological_folds == []
    assert failed.breakdowns == []

    with db.connection() as conn:
        conn.execute(
            "UPDATE signal_shadow_research_snapshots SET result_json=? WHERE snapshot_id=?",
            ("{}", snapshot.snapshot_id),
        )
        conn.commit()
    with pytest.raises(SignalShadowError, match="shadow_research_snapshot_integrity_failed"):
        service.get_research_snapshot(11, snapshot.snapshot_id)


def test_invalid_candidate_geometry_is_rejected(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "invalid.db"))
    service = SignalShadowService(db)
    payload = _candidate()
    payload["levels"] = {"entry": 100, "sl": 101, "tp": 102}
    with pytest.raises(SignalShadowError, match="candidate_resolution_geometry_invalid"):
        service.capture(1, payload)
