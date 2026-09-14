"""Unit tests for the deterministic proximity alert service."""
from __future__ import annotations

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services import proximity_alert_service as pas


def make_items(closes: list[float], start_t: float = 1_700_000_000.0) -> list[dict]:
    items = []
    for i, c in enumerate(closes):
        items.append({"t": start_t + i * 60, "o": c, "h": c + 0.5, "l": c - 0.5, "c": c, "v": 1.0})
    return items


# ------------------------------------------------------------------- ATR
def test_atr_percent_known_values():
    # every bar: h-l = 1.0 and closes flat => TR = 1.0 => ATR% = 1/100*100 = 1%
    items = make_items([100.0] * 30)
    atr = pas.atr_percent(items)
    assert atr is not None and abs(atr - 1.0) < 1e-9


def test_atr_percent_insufficient_data():
    assert pas.atr_percent(make_items([100.0] * 5)) is None
    assert pas.atr_percent([]) is None


# ------------------------------------------------------------- evaluation
def test_evaluate_levels_thresholds_and_severity():
    price = 100.0
    atr_pct = 1.0  # warn = max(0.25, 0.5) = 0.5% ; crit = max(0.10, 0.25) = 0.25%
    levels = [
        {"kind": "liquidity", "price": 100.10, "label": "#1 eqh"},   # 0.10% -> critical
        {"kind": "poc", "price": 100.30, "label": "POC"},            # 0.30% -> warning
        {"kind": "fvg_edge", "price": 99.00, "label": "FVG کف"},      # 1.00% -> out of range, below
        {"kind": "l2_ask_wall", "price": 102.0, "label": "×8"},      # 2.00% -> out of range
    ]
    rows = pas.evaluate_levels(price, atr_pct, levels)
    assert len(rows) == 4
    assert rows[0]["ref"] == "#1 eqh" and rows[0]["severity"] == "critical" and rows[0]["in_range"]
    assert rows[1]["ref"] == "POC" and rows[1]["severity"] == "warning" and rows[1]["in_range"]
    by_ref = {row["ref"]: row for row in rows}
    assert by_ref["FVG کف"]["in_range"] is False and by_ref["FVG کف"]["side"] == "below"
    assert by_ref["×8"]["side"] == "above"
    # sorted by distance
    distances = [row["distance_pct"] for row in rows]
    assert distances == sorted(distances)


def test_evaluate_levels_floor_without_atr():
    rows = pas.evaluate_levels(100.0, None, [{"kind": "eqh", "price": 100.2, "label": "EQH"}])
    assert rows and rows[0]["in_range"] and rows[0]["severity"] == "warning"
    rows = pas.evaluate_levels(100.0, None, [{"kind": "eqh", "price": 100.05, "label": "EQH"}])
    assert rows and rows[0]["severity"] == "critical"


def test_evaluate_levels_dedups_same_kind_price():
    levels = [
        {"kind": "liquidity", "price": 100.1, "label": "#1"},
        {"kind": "liquidity", "price": 100.1, "label": "#2"},
    ]
    rows = pas.evaluate_levels(100.0, 1.0, levels)
    assert len(rows) == 1


def test_evaluate_levels_garbage_input_is_safe():
    assert pas.evaluate_levels(0, 1.0, [{"kind": "x", "price": 10}]) == []
    assert pas.evaluate_levels(100.0, 1.0, [{"kind": "x", "price": "bad"}]) == []
    assert pas.evaluate_levels(100.0, 1.0, []) == []


# ------------------------------------------------------------------ state
def _row(distance: float, in_range: bool, kind: str = "liquidity", price_lvl: float = 100.1) -> dict:
    return {
        "kind": kind,
        "ref": kind,
        "level_price": price_lvl,
        "distance_pct": distance,
        "side": "above",
        "severity": "critical" if in_range else None,
        "in_range": in_range,
        "threshold_pct": {"warning": 0.5, "critical": 0.25},
    }


def test_state_fires_once_and_needs_rearm():
    state = pas.ProximityAlertState(cooldown_s=600)
    near = [_row(0.1, True)]
    fired = state.filter_new("BTCUSDT", near, now=1000.0)
    assert len(fired) == 1
    assert state.filter_new("BTCUSDT", near, now=1100.0) == []  # in cooldown + disarmed
    # cooldown elapsed but the key is still disarmed (hysteresis: price never
    # moved away beyond REARM_FACTOR x warning) -> must NOT re-fire
    assert state.filter_new("BTCUSDT", near, now=1700.0) == []
def test_state_requires_rearm_after_firing():
    state = pas.ProximityAlertState(cooldown_s=60)
    near = [_row(0.1, True)]
    assert len(state.filter_new("BTCUSDT", near, now=0.0)) == 1
    # far but below rearm threshold (0.5*2=1.0) -> still disarmed
    assert state.filter_new("BTCUSDT", [_row(0.8, False)], now=1000.0) == []
    assert state.filter_new("BTCUSDT", near, now=1001.0) == []
    # beyond rearm threshold -> armed again
    assert state.filter_new("BTCUSDT", [_row(1.5, False)], now=1002.0) == []
    assert len(state.filter_new("BTCUSDT", near, now=1003.0)) == 1


def test_state_is_per_symbol_and_kind():
    state = pas.ProximityAlertState(cooldown_s=600)
    near = [_row(0.1, True)]
    assert len(state.filter_new("BTCUSDT", near, now=0.0)) == 1
    assert len(state.filter_new("ETHUSDT", near, now=0.0)) == 1
    other_kind = [_row(0.1, True, kind="l2_bid_wall")]
    assert len(state.filter_new("BTCUSDT", other_kind, now=0.0)) == 1


# ---------------------------------------------------------------- messages
def test_message_fa_contains_symbol_and_numbers():
    row = _row(0.123, True)
    row["level_price"] = 115432.5
    msg = pas.message_fa("BTCUSDT", row)
    assert "BTCUSDT" in msg
    assert "115432" in msg
    assert "🔴" in msg  # critical icon
    row2 = _row(0.4, True, kind="l2_ask_wall")
    row2["severity"] = "warning"
    assert "🟡" in pas.message_fa("X", row2)
    assert "دیوار فروش L2" in pas.message_fa("X", row2)


def test_evaluation_is_deterministic():
    levels = [{"kind": "poc", "price": 100.2, "label": "POC"}]
    assert pas.evaluate_levels(100.0, 1.0, levels) == pas.evaluate_levels(100.0, 1.0, levels)
