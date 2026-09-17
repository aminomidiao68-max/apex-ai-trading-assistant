"""v3.24 ULTRA-STRICT tests: tightened omega + strict gates + real news blocking.

User directive: "no signal is better than a wrong signal" — every layer got
stricter. These tests lock the new thresholds so they cannot silently relax.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# ---------------------------------------------------------------- omega rules
def test_omega_thresholds_tightened():
    from app.services import smc_engine

    assert smc_engine.OMEGA_MIN_RR == 3.5
    assert smc_engine.OMEGA_MIN_CONF == 85
    assert smc_engine.OMEGA_MIN_PROB == 88
    assert smc_engine.OMEGA_MAX_DAILY_TRADES == 1
    assert smc_engine.OMEGA_MAX_WEEKLY_TRADES == 2
    f = smc_engine._omega_compliant
    assert f(85, 88, 3.5, True, True, True)[0] is True
    assert f(84, 88, 3.5, True, True, True)[0] is False   # conf floor
    assert f(85, 87, 3.5, True, True, True)[0] is False   # prob floor
    assert f(85, 88, 3.4, True, True, True)[0] is False   # rr floor
    assert f(85, 88, 3.5, False, True, True)[0] is False  # mtf
    assert f(85, 88, 3.5, True, False, True)[0] is False  # killzone
    assert f(85, 88, 3.5, True, True, False)[0] is False  # volume


# ------------------------------------------------------------- strict engine
def _candles(n=120):
    out = []
    price = 100.0
    for i in range(n):
        o = price
        c = price + (0.3 if i % 3 else -0.15)
        h = max(o, c) + 0.25
        l = min(o, c) - 0.25
        out.append({"t": float(i * 900), "o": o, "h": h, "l": l, "c": c, "v": 1200.0 + i})
        price = c
    return out


def _report(**over):
    base = {
        "direction": "long", "grade": "A+", "confluence": 85, "probability": 85,
        "rr": 3.0, "mtf_aligned": True, "htf_bias": "bullish",
        "setup_type": "پولبک BOS به ناحیه OTE", "events": [],
        "news_blocked": False, "invalidation": 98.0,
        "plan_lines": [{"kind": "entry", "price": 100.0}],
        "confluence_factors": [], "orderflow": {},
    }
    base.update(over)
    return base


NOW_UTC = __import__("datetime").datetime(2026, 9, 16, 13, 0,
                                          tzinfo=__import__("datetime").timezone.utc)  # Wed, in killzone


def _strict(report, candles=None, flow=None, timeframe="4h"):
    from app.services.strict_decision_engine import apply_strict_decision
    return apply_strict_decision(report, candles or _candles(), "crypto", timeframe,
                                 orderflow_snapshot=flow, now_utc=NOW_UTC)


def _gates(dec):
    return {g["name"]: g for g in dec["decision"]["gates"]}


def test_grade_b_no_longer_actionable():
    dec = _strict(_report(grade="B"))
    assert "grade" in dec["decision"]["failed_gates"]


def test_probability_floor_is_88():
    dec = _strict(_report(probability=87))
    g = _gates(dec)["estimated_probability"]
    assert not g["passed"] and g["required"] == ">=88"


def test_rr_floor_is_350():
    dec = _strict(_report(rr=3.4))
    g = _gates(dec)["risk_reward"]
    assert not g["passed"] and g["required"] == ">=3.5"


def test_confluence_floor_is_85():
    dec = _strict(_report(confluence=84))
    g = _gates(dec)["confluence"]
    assert not g["passed"] and g["required"] == ">=85"


def test_mtf_alignment_hard_gate():
    dec = _strict(_report(mtf_aligned=False))
    assert "mtf_alignment" in dec["decision"]["failed_gates"]
    ok = _strict(_report(mtf_aligned=True))
    assert _gates(ok)["mtf_alignment"]["passed"]


def test_footprint_confirmation_blocks_opposing_delta():
    flow = {"source": "okx_swap_public", "is_real": True, "confidence": 0.9,
            "pressure": "buy", "spread_bps": 1.0, "depth_imbalance": 0.0,
            "funding_rate": 0.0001,
            "micro": {"is_real": True, "delta": -0.40, "large_trade_imbalance": -0.10}}
    dec = _strict(_report(), flow=flow)
    assert "footprint_confirmation" in dec["decision"]["failed_gates"]
    # aligned delta passes
    flow2 = {**flow, "micro": {"is_real": True, "delta": 0.25, "large_trade_imbalance": 0.10}}
    assert _gates(_strict(_report(), flow=flow2))["footprint_confirmation"]["passed"]


def test_funding_crowding_is_hard_at_0010():
    flow = {"source": "okx_swap_public", "is_real": True, "confidence": 0.9,
            "pressure": "buy", "spread_bps": 1.0, "depth_imbalance": 0.0,
            "funding_rate": 0.0012}
    dec = _strict(_report(), flow=flow)
    assert "funding_crowding" in dec["decision"]["failed_gates"]


def test_spread_floor_is_5bps_and_depth_12pct():
    flow = {"source": "okx_swap_public", "is_real": True, "confidence": 0.9,
            "pressure": "buy", "spread_bps": 6.0, "depth_imbalance": -0.13,
            "funding_rate": 0.0001}
    failed = _strict(_report(), flow=flow)["decision"]["failed_gates"]
    assert "execution_spread" in failed and "depth_conflict" in failed


def test_conflict_budget_tightened():
    factors = [{"name": "c1", "points": -2.0}, {"name": "c2", "points": -2.0}]
    dec = _strict(_report(grade="A", confluence_factors=factors))  # 4.0 > 3.0 for A
    assert "conflict_budget" in dec["decision"]["failed_gates"]


# ---------------------------------------------------------------- news engine
def test_calendar_block_high_impact_window():
    from app.news_engine_v2 import evaluate_calendar_block

    now = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)
    cal = [{"event": "FOMC", "impact": "high", "country": "US",
            "time": "2026-09-17 12:15:00"}]
    block, medium = evaluate_calendar_block(cal, now)
    assert block["blocked"] and not medium
    assert block["block_until"] > int(now.timestamp())
    assert any("پراثر" in r for r in block["reasons"])


def test_calendar_block_windows_and_medium():
    from app.news_engine_v2 import evaluate_calendar_block

    now = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)
    # v3.26: 31 min before high impact is INSIDE the 90-min pre window
    b1, _ = evaluate_calendar_block(
        [{"event": "CPI", "impact": "high", "time": "2026-09-17 12:31:00"}], now)
    assert b1["blocked"]
    # 91 min before high impact → outside
    b3, _ = evaluate_calendar_block(
        [{"event": "CPI", "impact": "high", "time": "2026-09-17 13:31:00"}], now)
    assert not b3["blocked"]
    # v3.26: medium nearby BLOCKS as well
    b2, m2 = evaluate_calendar_block(
        [{"event": "PMI", "impact": "medium", "time": "2026-09-17 12:05:00"}], now)
    assert b2["blocked"] and m2


def test_calendar_parses_epoch_and_iso_and_fails_closed_count():
    from app.news_engine_v2 import evaluate_calendar_block

    now = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)
    ts_ms = int(datetime(2026, 9, 17, 12, 10, tzinfo=timezone.utc).timestamp() * 1000)
    b, _ = evaluate_calendar_block([{"event": "NFP", "impact": "high", "time": ts_ms}], now)
    assert b["blocked"]
    b2, _ = evaluate_calendar_block([{"event": "?", "impact": "high", "time": "garbage"}], now)
    assert not b2["blocked"] and any("fail-closed" in r for r in b2["reasons"])
