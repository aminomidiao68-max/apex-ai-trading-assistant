"""v3.31 ANTI-STOP-HUNT: stops placed beyond liquidity pools + wick-depth buffer.

User-reported failure mode: setup direction was right, but the stop was wicked
out and price then went to TP. Fix: SL sits beyond the deepest equal-low/high
pool and the 20-bar swing, with a buffer of max(0.35xATR, 0.6x p90 adverse
wick). The strict gate independently requires max(0.25xATR, 0.5x p90 wick).
"""
from app.services import smc_engine
from app.services.precision_window import atr_value
from tests.test_zero_error_v326 import _candles, _report, _strict


def test_harden_pushes_long_stop_below_liquidity_pool():
    cs = [dict(c) for c in _candles()]
    entry = cs[-1]["c"]
    atr = smc_engine._atr(cs)
    pool = min(x["l"] for x in cs[-20:]) - 0.05 * atr
    # create an equal-low pool (two touches within tolerance) below the swing
    cs[-2]["l"] = pool
    cs[-4]["l"] = pool * 1.0004
    naive_sl = min(x["l"] for x in cs[-20:]) + 0.3 * atr  # parked inside noise
    hardened = smc_engine._harden_stop(cs, atr, "long", entry, naive_sl)
    assert hardened < naive_sl                     # never tightens
    assert hardened <= pool - 0.34 * atr           # beyond the pool + buffer


def test_harden_pushes_short_stop_above_swing_with_buffer():
    cs = _candles()
    entry = cs[-1]["c"]
    atr = smc_engine._atr(cs)
    swing_high = max(x["h"] for x in cs[-20:])
    naive_sl = entry + 0.2 * atr
    hardened = smc_engine._harden_stop(cs, atr, "short", entry, naive_sl)
    assert hardened > naive_sl
    assert hardened >= max(naive_sl, swing_high) + 0.34 * atr


def test_harden_is_widen_only_and_respects_entry():
    cs = _candles()
    entry = cs[-1]["c"]
    atr = smc_engine._atr(cs)
    deep_sl = entry - 3.0 * atr
    hardened = smc_engine._harden_stop(cs, atr, "long", entry, deep_sl)
    assert hardened <= deep_sl and hardened < entry
    # degenerate inputs are returned untouched
    assert smc_engine._harden_stop(cs, 0.0, "long", entry, deep_sl) == deep_sl
    assert smc_engine._harden_stop(cs[:5], atr, "long", entry, deep_sl) == deep_sl


def test_wick_depth_p90_measures_real_wicks():
    cs = _candles(wick=0.15)
    d = smc_engine._wick_depth_p90(cs, "long", n=30)
    assert d >= 0.14  # synthetic lower wicks are exactly 0.15


def test_gate_rejects_stop_without_hunt_buffer():
    cs = _candles(step=0.15, back=0.12, wick=0.15)
    swing_low = min(x["l"] for x in cs[-20:])
    close = cs[-1]["c"]
    atr = smc_engine._atr(cs)
    tight = _report(levels={"entry": close, "sl": swing_low - 0.05 * atr,
                            "tp": close + 3 * atr}, tp1=close + 2 * atr, rr=3.5)
    dec = _strict(tight, cs)["decision"]
    assert "stop_placement" in dec["failed_gates"]
    sound = _report(levels={"entry": close, "sl": swing_low - 0.5 * atr,
                            "tp": close + 3 * atr}, tp1=close + 2 * atr, rr=3.5)
    dec2 = _strict(sound, cs)["decision"]
    assert "stop_placement" not in dec2["failed_gates"]
    gate = [g for g in dec2["gates"] if g["name"] == "stop_placement"][0]
    assert gate["actual"]["hunt_buffer_required"] > 0


def test_gate_rejects_short_stop_without_hunt_buffer():
    cs = _candles(step=0.15, back=0.12, wick=0.15)
    swing_high = max(x["h"] for x in cs[-20:])
    close = cs[-1]["c"]
    atr = smc_engine._atr(cs)
    tight = _report(direction="short", htf_bias="bearish",
                    levels={"entry": close, "sl": swing_high + 0.05 * atr,
                            "tp": close - 3 * atr}, tp1=close - 2 * atr, rr=3.5)
    assert "stop_placement" in _strict(tight, cs)["decision"]["failed_gates"]
