"""Tests for the v3.22 SL-projection rescue (trade_cost_gate.project_plan).

Projection widens the *protective* stop to the cost/noise floor when the
structural stop is too tight; the structural SL remains the invalidation
reference. It never invents reward: the plan must still clear net RR >= 1.5
against its own target, and widening is capped at 4x.
"""
from __future__ import annotations

import inspect
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services import trade_cost_gate as tcg


def test_far_target_plan_is_rescued():
    out = tcg.project_plan(100000.0, 99900.0, 101500.0, "long", atr=1000.0)
    assert out["projected"] and out["viable"]
    # floor = max(fee-floor 0.0005*201500/0.3=335.8, atr-floor 350) = 350
    assert abs(out["risk"] - 350.0) < 1e-6
    assert abs(out["sl"] - 99650.0) < 1e-6
    assert out["net_rr"] >= 1.5 and out["fee_r"] <= 0.30


def test_tight_target_plan_stays_rejected():
    # real audit sample: entry 77321.7 sl 77252.1 tp 77461 → hopeless geometry
    out = tcg.project_plan(77321.7, 77252.1, 77461.0, "long")
    assert out["projected"] and not out["viable"]
    assert any("RR خالص" in r for r in out["reasons_fa"])


def test_widening_capped_at_four_times():
    # risk 10, floor would need 335.8 → >4x → not rescuable at all
    out = tcg.project_plan(100000.0, 99990.0, 101500.0, "long")
    assert not out["projected"] and not out["viable"]
    assert any("نجات ممکن نیست" in r for r in out["reasons_fa"])


def test_no_projection_needed_when_stop_already_wide():
    out = tcg.project_plan(100000.0, 99000.0, 102000.0, "long", atr=1000.0)
    assert not out["projected"] and not out["viable"]  # viable=False: nothing to project
    assert any("لازم نیست" in r for r in out["reasons_fa"])


def test_missing_target_uses_tp2r_default():
    out = tcg.project_plan(100000.0, 99900.0, None, "long", atr=1000.0)
    assert out["projected"] and out["viable"]
    assert abs(out["net_rr"] - (2.0 - out["fee_r"])) < 1e-6


def test_short_direction_projects_stop_upward():
    out = tcg.project_plan(100000.0, 100100.0, 98500.0, "short", atr=1000.0)
    assert out["projected"] and out["viable"]
    assert out["sl"] > 100000.0
    assert abs(out["sl"] - (100000.0 + 350.0)) < 1e-6


def test_atr_floor_dominates_when_fee_floor_small():
    # maker-tier fee makes the fee floor (1.35) smaller than the ATR floor (7.0)
    out = tcg.project_plan(1000.0, 998.0, 1030.0, "long", atr=20.0, fee_pct=0.02)
    assert out["projected"] and out["viable"]
    assert abs(out["risk"] - 7.0) < 1e-6  # 0.35 * 20
    assert abs(out["floor_risk"] - 7.0) < 1e-6


# ------------------------------------------------------------------ wiring
def test_strict_engine_rejects_but_explains_rescue_geometry():
    from app.services.strict_decision_engine import apply_strict_decision

    candles = [{"t": float(i * 60), "o": 100.0, "h": 101.0, "l": 99.0, "c": 100.0, "v": 10.0}
               for i in range(80)]
    report = {
        "direction": "long", "grade": "A", "confluence": 80, "probability": 80,
        "rr": 3.0, "setup_type": "OB Return", "atr": 0.2,
        "levels": {"entry": 100.0, "sl": 99.9},  # 0.1% structural stop — too tight
        "tp1": 103.0, "plan_lines": [{"kind": "entry", "price": 100.0}],
        "invalidation": 99.9,
    }
    dec = apply_strict_decision(report, candles, "crypto", "4h")
    gates = {g["name"]: g for g in dec["decision"]["gates"]}
    tc = gates["trade_cost"]
    # v3.22 measured verdict: projection adds no expectancy → gate still fails
    assert not tc["passed"]
    assert tc["actual"]["rescue_possible"] is True  # geometry WOULD be rescuable
    assert tc["actual"]["rescue_reason_fa"]
    # the gate's own failure reason comes first, projection detail second
    assert "کارمزد" in tc["actual"]["rescue_reason_fa"][0]
    proj = dec["decision"]["trade_cost"]["projection"]
    assert proj["viable"] and proj["sl"] < 99.9  # informational rescue detail
    assert dec["decision"]["status"] != "actionable"


def test_backtests_and_endpoints_wire_sl_project():
    from app.services import prime_backtest_service as pbs
    from app.services import strategy_backtest_service as sbs
    from app import main as app_main

    assert "sl_project" in inspect.signature(sbs.run).parameters
    assert "sl_project" in inspect.signature(pbs.run).parameters
    for fn_name in ("backtest_prime_setups", "backtest_classic_strategies"):
        fn = getattr(app_main, fn_name)
        sig = inspect.signature(fn)
        assert "sl_project" in sig.parameters
        assert sig.parameters["sl_project"].default.default is False  # off by default (measured: no edge)
        src = inspect.getsource(fn)
        assert "sl_project=sl_project" in src and "|{sl_project}" in src
