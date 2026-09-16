"""Tests for the v3.21 scale-out exit model (save 50% at +1R, breakeven stop).

Conservative-fill invariants that MUST hold:
  - SL wins any ambiguous bar in phase 1; breakeven wins any ambiguous bar
    in phase 2; phase 2 starts on the bar AFTER the +1R fill.
"""
from __future__ import annotations

import inspect
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.scale_exit import simulate_scale
from app.services import strategy_backtest_service as sbs


def bar(t, o, h, l, c):
    return {"t": float(t), "o": float(o), "h": float(h), "l": float(l), "c": float(c), "v": 1.0}


# long plan: entry 100, sl 95 (risk 5), target 110 (2R). i=0 detection, i=1 trigger.
def items_long(*tail):
    return [bar(0, 100, 101, 99.5, 100), bar(60, 100.2, 100.6, 99.8, 100.2), *tail]


def sim(tail, **kw):
    defaults = dict(entry_index=1, direction="long", entry=100.0, sl=95.0,
                    target=110.0, exit_horizon=10, fee_pct=0.0)
    defaults.update(kw)
    return simulate_scale(items_long(*tail), **defaults)


def test_full_sl_loss_costs_exactly_minus_one_r():
    out = sim([bar(120, 100, 100.5, 94.0, 94.5)])
    assert out["exit_reason"] == "sl" and out["r"] == -1.0
    assert out["legs"] == [{"price": 95.0, "weight": 1.0, "r": -1.0}]


def test_sl_beats_leg1_on_the_same_bar():
    out = sim([bar(120, 100, 106.0, 94.0, 105.0)])  # both +1R and SL touched
    assert out["exit_reason"] == "sl" and out["r"] == -1.0


def test_leg1_then_target_full_win():
    out = sim([bar(120, 100.2, 105.2, 100.1, 105.0),   # +1R touched (105)
               bar(180, 105.0, 110.5, 104.0, 110.0)])  # target touched
    assert out["exit_reason"] == "scale_target"
    assert abs(out["r"] - (0.5 * 1.0 + 0.5 * 2.0)) < 1e-9
    assert len(out["legs"]) == 2 and out["legs"][0]["price"] == 105.0


def test_leg1_then_breakeven_is_a_small_win():
    out = sim([bar(120, 100.2, 105.2, 100.1, 105.0),   # +1R
               bar(180, 104.0, 104.5, 99.5, 100.0)])   # back to entry, never target
    assert out["exit_reason"] == "scale_be"
    assert abs(out["r"] - 0.5) < 1e-9  # +0.5R net, fee-free case


def test_breakeven_beats_target_on_the_same_bar():
    out = sim([bar(120, 100.2, 105.2, 100.1, 105.0),
               bar(180, 100.0, 110.5, 99.5, 108.0)])   # both BE and target touched
    assert out["exit_reason"] == "scale_be"
    assert abs(out["r"] - 0.5) < 1e-9


def test_phase2_does_not_start_on_the_leg1_bar():
    # leg1 bar ALSO dips below entry intra-bar; phase 2 must wait for the next bar.
    out = sim([bar(120, 100.2, 105.2, 99.9, 105.0),    # +1R and BE on same bar
               bar(180, 101.0, 101.5, 100.5, 101.0)])  # quiet; horizon ends here
    assert out["exit_reason"] == "scale_timeout"
    assert abs(out["r"] - (0.5 * 1.0 + 0.5 * 0.2)) < 1e-9  # rest closed at 101 → +0.2R


def test_phase1_timeout_closes_everything_at_close():
    out = sim([bar(120, 100.2, 101.0, 100.0, 100.8),
               bar(180, 100.8, 101.2, 100.4, 99.0)])
    assert out["exit_reason"] == "timeout"
    assert abs(out["r"] - ((99.0 - 100.0) / 5.0)) < 1e-9


def test_target_below_1r_uses_target_as_first_leg():
    out = sim([bar(120, 100.2, 102.8, 100.1, 102.5),   # touches 102.5 (=target=+0.5R)
               bar(180, 102.5, 103.0, 102.0, 102.6)], target=102.5)
    assert out["exit_reason"] in ("scale_target", "scale_timeout")
    assert out["r"] > 0
    assert out["legs"][0]["r"] == 0.5  # leg1 capped at target_r=0.5


def test_fee_math_is_exact():
    out = sim([bar(120, 100.2, 105.2, 100.1, 105.0),
               bar(180, 105.0, 110.5, 104.0, 110.0)], fee_pct=0.05)
    fee = (0.05 / 100.0) * (0.5 * (100 + 105) + 0.5 * (100 + 110)) / 5.0
    assert abs(out["r"] - (1.5 - fee)) < 1e-3  # r rounded to 3 decimals


def test_short_direction_mirror():
    items = [bar(0, 100, 100.5, 99, 100), bar(60, 99.8, 100.2, 99.4, 99.8),
             bar(120, 99.8, 99.9, 94.8, 95.0),   # short +1R = 95
             bar(180, 95.0, 95.5, 89.5, 90.0)]   # target 90
    out = simulate_scale(items, 1, "short", 100.0, 105.0, 90.0, 10, 0.0)
    assert out["exit_reason"] == "scale_target"
    assert abs(out["r"] - (0.5 * 1.0 + 0.5 * 2.0)) < 1e-9


# ------------------------------------------------------------------- wiring
def test_simulate_plan_scale_model_returns_legs():
    items = items_long(bar(120, 100.2, 105.2, 100.1, 105.0),
                       bar(180, 105.0, 110.5, 104.0, 110.0))
    row = sbs._simulate_plan(items, 0, "long", 100.0, 95.0, 110.0,
                             exit_horizon=10, fee_pct=0.0, exit_model="scale_1r_be")
    assert row and row["triggered"] and row["exit_reason"] == "scale_target"
    assert row["legs"] and abs(row["r"] - 1.5) < 1e-9
    single = sbs._simulate_plan(items, 0, "long", 100.0, 95.0, 110.0,
                                exit_horizon=10, fee_pct=0.0)
    assert single["exit_reason"] in ("tp", "tp_2r") and abs(single["r"] - 2.0) < 1e-9


def test_endpoints_expose_exit_model_defaulting_to_scale():
    from app import main as app_main

    for fn_name in ("backtest_prime_setups", "backtest_classic_strategies"):
        fn = getattr(app_main, fn_name)
        sig = inspect.signature(fn)
        assert "exit_model" in sig.parameters
        assert sig.parameters["exit_model"].default.default == "scale_1r_be"
        src = inspect.getsource(fn)
        assert "exit_model=exit_model" in src and "|{exit_model}" in src


def test_strict_engine_publishes_exit_management_advice():
    from app.services import strict_decision_engine as sde

    src = inspect.getsource(sde.apply_strict_decision)
    assert '"exit_management"' in src and "scale_50pct_at_1r_then_breakeven" in src
