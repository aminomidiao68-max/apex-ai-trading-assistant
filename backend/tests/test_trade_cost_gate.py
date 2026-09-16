"""Tests for the v3.20 trade-cost/geometry gate and its wiring.

Audit 2026-09-16: tight stops (0.05-0.3% of price) made round-trip fees cost
0.3-3.7R per trade — the dominant post-fee loss source. The gate rejects such
geometry deterministically in BOTH the live strict engine and the backtests.
"""
from __future__ import annotations

import inspect
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services import trade_cost_gate as tcg


# ------------------------------------------------------------------ gate unit
def test_tight_stop_btc_plan_fails_fee_rule():
    # real audit sample: entry 77321.7, sl 77252.1 → risk 0.09% → fee ≈ 1.11R
    out = tcg.evaluate(77321.7, 77252.1, 77461.0, "long", fee_pct=0.05)
    assert out["applicable"] and not out["passed"]
    assert out["fee_r"] > 1.0
    assert any("کارمزد" in r for r in out["reasons_fa"])


def test_healthy_stop_passes():
    # 1% risk on BTC: fee_r ≈ 0.1R, tp at 2R → net_rr ≈ 1.9
    out = tcg.evaluate(100000.0, 99000.0, 102000.0, "long", fee_pct=0.05)
    assert out["applicable"] and out["passed"], out["reasons_fa"]
    assert out["fee_r"] < 0.15 and out["net_rr"] > 1.5


def test_stop_inside_atr_noise_band_fails():
    # risk 0.5% would pass the fee rule, but ATR=3000 → floor = 0.35*3000 = 1050
    out = tcg.evaluate(100000.0, 99500.0, 101500.0, "long", fee_pct=0.05, atr=3000.0)
    assert out["applicable"] and not out["passed"]
    assert any("ATR" in r for r in out["reasons_fa"])
    # same plan with a proportionate ATR passes
    out2 = tcg.evaluate(100000.0, 99500.0, 101500.0, "long", fee_pct=0.05, atr=900.0)
    assert out2["passed"], out2["reasons_fa"]


def test_net_rr_floor_blocks_fee_eaten_targets():
    # gross RR 2.0 but risk 0.15% → fee_r ≈ 0.67 → net_rr ≈ 1.33 < 1.5
    out = tcg.evaluate(100000.0, 99850.0, 100300.0, "long", fee_pct=0.05)
    assert not out["passed"]
    assert out["net_rr"] < 1.5


def test_short_direction_geometry():
    out = tcg.evaluate(100000.0, 101000.0, 98000.0, "short", fee_pct=0.05)
    assert out["applicable"] and out["passed"], out["reasons_fa"]
    bad = tcg.evaluate(100000.0, 99000.0, None, "short", fee_pct=0.05)  # wrong side
    assert not bad["applicable"]  # invalid geometry → pass-through, not our job


def test_missing_plan_is_pass_through():
    for entry, sl in ((None, None), (0, 0), (100.0, None), ("x", 99.0)):
        out = tcg.evaluate(entry, sl, None, "long")
        assert not out["applicable"] and out["passed"]


def test_atr14_helper():
    candles = [{"t": i, "h": 102.0, "l": 98.0, "c": 100.0} for i in range(20)]
    assert abs(tcg.atr14(candles) - 4.0) < 1e-9
    assert tcg.atr14(candles[:5]) is None


# ------------------------------------------------------------- live wiring
def test_strict_engine_has_trade_cost_hard_gate():
    from app.services import strict_decision_engine as sde

    src = inspect.getsource(sde.apply_strict_decision)
    assert 'evaluate_trade_cost(' in src
    assert '_gate(\n            "trade_cost"' in src or '"trade_cost"' in src
    sig = inspect.signature(sde.apply_strict_decision)
    assert "report" in sig.parameters


def test_backtest_services_and_endpoints_wire_cost_gate():
    from app.services import prime_backtest_service as pbs
    from app.services import strategy_backtest_service as sbs
    from app import main as app_main

    assert "cost_gate" in inspect.signature(sbs.run).parameters
    assert "cost_gate" in inspect.signature(pbs.run).parameters
    for fn_name in ("backtest_prime_setups", "backtest_classic_strategies"):
        fn = getattr(app_main, fn_name)
        assert "cost_gate" in inspect.signature(fn).parameters
        src = inspect.getsource(fn)
        assert "cost_gate=cost_gate" in src
        assert "|{cost_gate}" in src  # cache keyed by the flag
