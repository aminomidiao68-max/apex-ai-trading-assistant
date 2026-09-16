"""Fee-parameter regression tests — honest post-fee backtests (v3.19.1).

The audit of 2026-09-16 found the backtest endpoints never exposed the
services' ``fee_pct`` support, so every published number was fee-free.
These tests lock the fix: fee math at the service layer AND the ``fee``
query parameter on both endpoints.
"""
from __future__ import annotations

import inspect
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services import prime_backtest_service as pbs
from app.services import strategy_backtest_service as sbs


def bar(t, o, h, l, c):
    return {"t": float(t), "o": float(o), "h": float(h), "l": float(l), "c": float(c), "v": 1.0}


LONG_ITEMS = [
    bar(0, 100, 101, 99, 100),
    bar(60, 100, 100.8, 100.2, 100.5),
    bar(120, 100.5, 100.6, 99.9, 100.1),   # triggers long entry at 100
    bar(180, 100.1, 105.0, 100.0, 104.0),
    bar(240, 104.0, 110.2, 103.5, 110.0),  # TP1 at 110
]

LONG_REPORT = {
    "direction": "long",
    "levels": {"entry": 100.0, "sl": 95.0},
    "tp1": 110.0,
    "setup_type": "OB Return",
    "grade": "A",
    "confluence": 30,
    "omega_compliant": True,
}


def test_prime_simulate_fee_reduces_r_by_exact_notional_cost():
    free = pbs._simulate(LONG_ITEMS, 0, LONG_REPORT, exit_horizon=10, fee_pct=0.0)
    fee = pbs._simulate(LONG_ITEMS, 0, LONG_REPORT, exit_horizon=10, fee_pct=0.05)
    assert free and fee and free["triggered"] and fee["triggered"]
    # entry 100, exit 110, risk 5 → cost = 0.0005*(100+110)/5 = 0.021R per side-pair
    expected = (0.05 / 100.0) * (100.0 + 110.0) / 5.0
    assert abs((free["r"] - fee["r"]) - expected) < 2e-3  # r is rounded to 3 decimals
    assert fee["r"] < free["r"]


def test_strategy_pack_simulate_plan_fee_reduces_r():
    free = sbs._simulate_plan(LONG_ITEMS, 0, "long", 100.0, 95.0, 110.0,
                              exit_horizon=10, fee_pct=0.0)
    fee = sbs._simulate_plan(LONG_ITEMS, 0, "long", 100.0, 95.0, 110.0,
                             exit_horizon=10, fee_pct=0.05)
    assert free and fee
    expected = (0.05 / 100.0) * (100.0 + 110.0) / 5.0
    assert abs((free["r"] - fee["r"]) - expected) < 1e-9
    assert fee["r"] < free["r"]


def test_backtest_endpoints_expose_fee_query_param():
    from app import main as app_main

    for fn_name in ("backtest_prime_setups", "backtest_classic_strategies"):
        fn = getattr(app_main, fn_name)
        sig = inspect.signature(fn)
        assert "fee" in sig.parameters, f"{fn_name} lost its fee parameter"
        src = inspect.getsource(fn)
        assert "fee_pct=fee" in src, f"{fn_name} does not forward fee to the service"
        assert "|{fee}" in src, f"{fn_name} must key its cache by fee"
