"""v3.26 ZERO-ERROR OBSESSION: zero-tolerance gates + self-learning loss veto."""
from datetime import datetime, timedelta, timezone

from app.services.precision_window import in_killzone
from app.services.strict_decision_engine import apply_strict_decision

NOW = datetime(2026, 9, 16, 13, 0, tzinfo=timezone.utc)  # inside London/NY overlap


def _loss_candidate():
    return {
        "symbol": "BTCUSDT", "market": "crypto", "status": "ACTIONABLE_CANDIDATE",
        "side": "long", "failed_gates": [], "levels": {"entry": 100, "sl": 99, "tp": 103},
        "resolution_timeframe": "5m", "max_resolution_bars": 3,
        "frames": [{"timeframe": "1h", "regime": "trending"}],
        "actionable_for_live": False,
    }


def _force_loss(db, observation_id, now):
    with db.connection() as conn:
        conn.execute(
            "UPDATE signal_shadow_observations SET outcome_status='LOSS', captured_at=? WHERE observation_id=?",
            (now.isoformat(), observation_id),
        )
        conn.commit()


def _candles(n=120, wick=0.15, step=0.4, back=0.2):
    out = []
    price = 100.0
    for i in range(n):
        o = price
        c = price + (step if i % 3 else -back)
        h = max(o, c) + wick
        l = min(o, c) - wick
        out.append({"t": float(i * 900), "o": o, "h": h, "l": l, "c": c, "v": 1200.0 + i})
        price = c
    return out


def _factors(k=4):
    names = ["HTF alignment", "BOS structure", "OTE entry", "liquidity sweep", "volume spike"]
    return [{"name": names[i], "points": 10} for i in range(k)]


def _report(**over):
    base = {
        "direction": "long", "grade": "A+", "confluence": 90, "probability": 90,
        "rr": 3.8, "mtf_aligned": True, "htf_bias": "bullish",
        "setup_type": "پولبک BOS به ناحیه OTE", "events": [],
        "news_blocked": False, "invalidation": 98.0,
        "plan_lines": [{"kind": "entry", "price": 100.0}],
        "confluence_factors": _factors(4), "orderflow": {},
    }
    base.update(over)
    return base


def _strict(report, candles=None, now=NOW, **kw):
    return apply_strict_decision(report, candles or _candles(), "crypto", "4h",
                                 now_utc=now, **kw)


def _gates(dec):
    return {g["name"]: g for g in dec["decision"]["gates"]}


def test_overlap_only_killzone():
    assert in_killzone(datetime(2026, 9, 16, 13, 0, tzinfo=timezone.utc))
    assert not in_killzone(datetime(2026, 9, 16, 9, 0, tzinfo=timezone.utc))


def test_any_negative_evidence_vetoes():
    rep = _report(confluence_factors=_factors(4) + [{"name": "doubt", "points": -0.5}])
    assert "conflict_budget" in _strict(rep)["decision"]["failed_gates"]


def test_evidence_diversity_minimum_four():
    assert "evidence_diversity" in _strict(_report(confluence_factors=_factors(3)))["decision"]["failed_gates"]
    assert _gates(_strict(_report(confluence_factors=_factors(4))))["evidence_diversity"]["passed"]


def test_confirmation_must_engulf_previous_high():
    candles = _candles()
    candles[-1]["c"] = candles[-2]["c"] + 0.10     # up but BELOW previous high (+0.15)
    candles[-1]["h"] = candles[-1]["c"] + 0.02
    candles[-1]["o"] = candles[-2]["c"] - 0.10
    candles[-1]["l"] = candles[-1]["o"] - 0.02
    assert "confirmation_close" in _strict(_report(), candles=candles)["decision"]["failed_gates"]


def test_confirmation_body_must_be_half_of_range():
    candles = _candles()
    o = candles[-2]["c"] + 0.01
    candles[-1].update(o=o, c=candles[-2]["h"] + 0.2, h=candles[-2]["h"] + 0.8, l=o - 0.05)
    # body 0.19+ vs range ~0.85 -> ratio < 0.5
    assert "confirmation_close" in _strict(_report(), candles=candles)["decision"]["failed_gates"]


def test_efficiency_floor_is_030():
    import math
    candles = []
    for i in range(118):  # smooth oscillation: huge path, tiny displacement
        c = 100 + 0.5 * math.sin(i)
        o = candles[-1]["c"] if candles else c - 0.01
        candles.append({"t": float(i * 900), "o": o, "h": max(o, c) + 0.05,
                        "l": min(o, c) - 0.05, "c": c, "v": 1200.0 + i})
    o1 = candles[-1]["c"]; c1 = o1 - 0.6
    candles.append({"t": 118 * 900.0, "o": o1, "h": o1 + 0.05, "l": c1 - 0.05, "c": c1, "v": 1300.0})
    o2 = c1; c2 = c1 + 0.9  # decisive engulfing confirmation inside a choppy market
    candles.append({"t": 119 * 900.0, "o": o2, "h": c2 + 0.05, "l": o2 - 0.05, "c": c2, "v": 1300.0})
    failed = _strict(_report(), candles=candles)["decision"]["failed_gates"]
    assert "trend_efficiency" in failed and "confirmation_close" not in failed


def test_volatility_band_narrowed_for_crypto():
    assert "volatility_band" in _strict(_report(), candles=_candles(wick=3.0))["decision"]["failed_gates"]
    assert "volatility_band" in _strict(_report(), candles=_candles(wick=0.002, step=0.004, back=0.002))["decision"]["failed_gates"]


def test_target_must_be_reachable_within_3atr():
    rep = _report(levels={"entry": 100.0, "sl": 99.0, "tp": 130.0}, tp1=130.0)
    g = _gates(_strict(rep))["target_reachability"]
    assert not g["passed"]


def test_news_blackout_widened_and_medium_blocks():
    from app.news_engine_v2 import evaluate_calendar_block
    high = [{"impact": "high", "event": "CPI", "country": "US", "time": "2026-09-16 14:00:00"}]
    medium = [{"impact": "medium", "event": "PMI", "country": "US", "time": "2026-09-16 13:30:00"}]
    far = [{"impact": "high", "event": "CPI", "country": "US", "time": "2026-09-16 16:00:00"}]
    assert evaluate_calendar_block(high, NOW)[0]["blocked"] is True
    assert evaluate_calendar_block(medium, NOW)[0]["blocked"] is True
    assert evaluate_calendar_block(far, NOW)[0]["blocked"] is False


def test_loss_cooldown_vetoes_symbol_and_expires(tmp_path):
    from app.config import settings
    from app.services.database_service import DatabaseManager
    from app.services.signal_shadow_service import SignalShadowService

    db = DatabaseManager(db_path=str(tmp_path / "cool.db"))
    svc = SignalShadowService(db)
    obs = svc.capture(0, _loss_candidate())
    _force_loss(db, obs.observation_id, NOW)
    assert svc.symbol_in_loss_cooldown("BTCUSDT", NOW) is True
    assert svc.symbol_in_loss_cooldown("ETHUSDT", NOW) is False
    assert svc.symbol_in_loss_cooldown("BTCUSDT", NOW + timedelta(days=31)) is False
    with db.connection() as conn:
        conn.execute(
            "UPDATE signal_shadow_observations SET engine_version='other-engine' WHERE observation_id=?",
            (obs.observation_id,),
        )
        conn.commit()
    assert svc.symbol_in_loss_cooldown("BTCUSDT", NOW) is False  # only CURRENT engine teaches
    assert settings.engine_version  # cohort key is the live engine build


def test_fusion_blocks_symbol_in_loss_cooldown(tmp_path):
    from app.services.database_service import DatabaseManager
    from app.services.intraday_fusion_service import IntradayFusionService
    from app.services.signal_shadow_service import SignalShadowService

    db = DatabaseManager(db_path=str(tmp_path / "fusecool.db"))
    svc = SignalShadowService(db)
    obs = svc.capture(0, _loss_candidate())
    _force_loss(db, obs.observation_id, NOW)

    def frame(tf, status):
        return {"timeframe": tf, "report": {
            "direction": "long", "bias": "bullish", "confluence": 90, "invalidation": 99,
            "levels": {"entry": 100, "sl": 99, "tp": 103}, "tp1": 102,
            "data_quality": {"score": 95}, "frame_freshness": {"fresh": True, "age_seconds": 20},
            "market_regime": {"name": "trending"},
            "decision": {"side": "long", "status": status,
                         "orderflow": {"is_real": True, "pressure": "buy"}}}}
    frames = [frame("5m", "actionable"), frame("15m", "watch"),
              frame("1h", "actionable"), frame("4h", "actionable"),
              frame("1d", "actionable")]
    result = IntradayFusionService().fuse("BTCUSDT", "crypto", frames,
                                          now_utc=NOW, loss_guard=svc)
    assert result["status"] != "ACTIONABLE_CANDIDATE"
    assert "symbol_loss_cooldown" in result["failed_gates"]


def test_omega_zero_error_constants():
    from app.services import smc_engine
    assert (smc_engine.OMEGA_MIN_RR, smc_engine.OMEGA_MIN_CONF, smc_engine.OMEGA_MIN_PROB) == (3.5, 85, 88)
    assert smc_engine.OMEGA_MAX_DAILY_TRADES == -1 and smc_engine.OMEGA_MAX_WEEKLY_TRADES == -1


def test_zero_error_baseline_actionable_in_overlap():
    dec = _strict(_report())
    assert dec["decision"]["status"] == "actionable", dec["decision"]["failed_gates"]
    assert dec["decision"]["action_label"] == "STRONG_LONG"
