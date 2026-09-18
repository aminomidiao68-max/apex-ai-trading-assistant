"""v3.27 trade-craft gates: stop placement & entry proximity (real WR killers)."""
from datetime import datetime, timezone

from app.services.precision_window import atr_value
from app.services.strict_decision_engine import apply_strict_decision
from tests.test_zero_error_v326 import _candles, _report

NOW = datetime(2026, 9, 16, 13, 0, tzinfo=timezone.utc)


def _strict(report, candles=None):
    return apply_strict_decision(report, candles or _candles(), "crypto", "4h", now_utc=NOW)


def _failed(report, candles=None):
    return _strict(report, candles)["decision"]["failed_gates"]


def test_stop_parked_inside_swing_is_rejected():
    cs = _candles()
    swing_low = min(x["l"] for x in cs[-20:])
    close = cs[-1]["c"]
    atr = atr_value(cs)
    rep = _report(levels={"entry": close, "sl": swing_low + 0.5 * atr, "tp": close + 3 * atr},
                  tp1=close + 2 * atr)
    assert "stop_placement" in _failed(rep, cs)


def test_absurd_wide_stop_is_rejected():
    cs = _candles()
    swing_low = min(x["l"] for x in cs[-20:])
    close = cs[-1]["c"]
    atr = atr_value(cs)
    rep = _report(levels={"entry": close, "sl": swing_low - 6 * atr, "tp": close + 20 * atr},
                  tp1=close + 2 * atr)
    assert "stop_placement" in _failed(rep, cs)


def test_chased_entry_is_rejected():
    cs = _candles()
    swing_low = min(x["l"] for x in cs[-20:])
    close = cs[-1]["c"]
    atr = atr_value(cs)
    rep = _report(levels={"entry": close + 2.5 * atr, "sl": swing_low - 1 * atr,
                          "tp": close + 6 * atr}, tp1=close + 3 * atr)
    assert "entry_proximity" in _failed(rep, cs)


def test_craftsound_plan_passes_both_gates():
    cs = _candles(step=0.15, back=0.12, wick=0.15)  # gentle trend with pullbacks
    swing_low = min(x["l"] for x in cs[-20:])
    close = cs[-1]["c"]
    atr = atr_value(cs)
    rep = _report(levels={"entry": close, "sl": swing_low - 0.5 * atr, "tp": close + 3 * atr},
                  tp1=close + 2 * atr, rr=3.5)
    failed = _failed(rep, cs)
    assert "stop_placement" not in failed and "entry_proximity" not in failed


def test_baseline_without_levels_still_evaluates():
    dec = _strict(_report())
    assert "stop_placement" not in dec["decision"]["failed_gates"]
    assert "entry_proximity" not in dec["decision"]["failed_gates"]
