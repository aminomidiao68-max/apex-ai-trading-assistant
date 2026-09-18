"""v3.29 SELF-CALIBRATING HONESTY: empirical calibration, span gate, Wilson CI."""
from datetime import datetime, timedelta, timezone

from app.services.database_service import DatabaseManager
from app.services.signal_shadow_service import SignalShadowService

BASE = datetime(2026, 9, 1, 13, 0, tzinfo=timezone.utc)


def _seed(db, svc, wins, losses, span_days, prob=85):
    total = wins + losses
    for i in range(total):
        obs = svc.capture(0, {
            "symbol": "BTCUSDT", "market": "crypto", "status": "ACTIONABLE_CANDIDATE",
            "side": "long", "failed_gates": [], "levels": {"entry": 100, "sl": 99, "tp": 103},
            "resolution_timeframe": "5m", "max_resolution_bars": 3,
            "frames": [{"timeframe": "15m",
                        "report": {"probability": prob, "rr": 3.6,
                                   "decision": {"status": "actionable"}}}],
            "actionable_for_live": False,
        })
        day = (i * span_days) // max(1, total - 1)
        with db.connection() as conn:
            conn.execute(
                "UPDATE signal_shadow_observations SET outcome_status=?, activated=1, captured_at=? "
                "WHERE observation_id=?",
                ("WIN" if i < wins else "LOSS", (BASE + timedelta(days=day)).isoformat(),
                 obs.observation_id),
            )
            conn.commit()


def _svc(tmp_path, name="cal.db"):
    db = DatabaseManager(db_path=str(tmp_path / name))
    return db, SignalShadowService(db)


def test_inactive_cohort_passes_without_claiming(tmp_path):
    _, svc = _svc(tmp_path)
    info = svc.empirical_edge_report(85, 3.5)
    assert info["active"] is False and info["ok"] is True
    assert info["reason"] == "cohort_too_small_honest_passthrough"


def test_active_healthy_cohort_passes_on_bucket(tmp_path):
    db, svc = _svc(tmp_path)
    _seed(db, svc, 20, 10, span_days=10)
    info = svc.empirical_edge_report(85, 3.5)
    assert info["active"] is True and info["ok"] is True
    assert info["source"] == "bucket_85" and info["n"] == 30
    assert info["win_rate"] == round(20 / 30, 4)
    assert info["required_win_rate"] == round(1.2 / 4.5, 4)


def test_active_losing_cohort_vetoes(tmp_path):
    db, svc = _svc(tmp_path)
    _seed(db, svc, 6, 24, span_days=10)
    info = svc.empirical_edge_report(85, 3.5)
    assert info["active"] is True and info["ok"] is False
    assert info["reason"] == "empirical_edge_unproven"


def test_expired_outcomes_never_count_as_winloss(tmp_path):
    db, svc = _svc(tmp_path)
    _seed(db, svc, 2, 1, span_days=3)
    obs = svc.capture(0, {
        "symbol": "BTCUSDT", "market": "crypto", "status": "ACTIONABLE_CANDIDATE",
        "side": "long", "failed_gates": [], "levels": {"entry": 100, "sl": 99, "tp": 103},
        "resolution_timeframe": "5m", "max_resolution_bars": 3, "frames": [],
        "actionable_for_live": False,
    })
    with db.connection() as conn:
        conn.execute(
            "UPDATE signal_shadow_observations SET outcome_status='EXPIRED_ACTIVE', activated=1 "
            "WHERE observation_id=?", (obs.observation_id,),
        )
        conn.commit()
    stats = svc.cohort_stats()
    assert stats["win_loss_n"] == 3


def test_fusion_veto_and_passthrough(tmp_path):
    from app.services.intraday_fusion_service import IntradayFusionService
    from tests.test_weekly_grade_v325 import _fusion_frames

    def frames():
        fr = _fusion_frames()
        fr[0]["report"]["probability"] = 85
        fr[0]["report"]["rr"] = 3.6
        return fr

    now = datetime(2026, 9, 16, 13, 0, tzinfo=timezone.utc)
    db_bad, bad = _svc(tmp_path, "bad.db")
    _seed(db_bad, bad, 6, 24, span_days=10)
    res = IntradayFusionService().fuse("BTCUSDT", "crypto", frames(), now_utc=now,
                                       calibrator=bad)
    assert res["status"] != "ACTIONABLE_CANDIDATE"
    assert "calibrated_expectancy" in res["failed_gates"]

    db_ok, good = _svc(tmp_path, "good.db")
    _seed(db_ok, good, 20, 10, span_days=10)
    res2 = IntradayFusionService().fuse("BTCUSDT", "crypto", frames(), now_utc=now,
                                         calibrator=good)
    assert "calibrated_expectancy" not in res2["failed_gates"]


def test_panel_span_gate_and_confidence_interval(tmp_path):
    db, svc = _svc(tmp_path, "panel.db")
    _seed(db, svc, 20, 10, span_days=2)   # 30 resolved but crammed in 2 days
    panel = svc.panel(0)
    assert panel.resolved_current_engine >= 30
    assert panel.research_ready_current_engine is False      # span too short
    assert panel.cohort_span_days_current_engine == 2.0
    assert panel.win_rate_ci_low is not None
    assert panel.win_rate_ci_low <= 20 / 30 <= panel.win_rate_ci_high

    db2, svc2 = _svc(tmp_path, "panel2.db")
    _seed(db2, svc2, 20, 10, span_days=10)
    panel2 = svc2.panel(0)
    assert panel2.research_ready_current_engine is True
    assert panel2.cohort_wins_current_engine == 20
    assert panel2.cohort_losses_current_engine == 10


def test_wilson_ci_edges():
    assert SignalShadowService.wilson_ci(0, 0) == (None, None)
    low, high = SignalShadowService.wilson_ci(30, 30)
    assert low > 0.85 and high == 1.0
    low2, high2 = SignalShadowService.wilson_ci(15, 30)
    assert low2 < 0.5 < high2
