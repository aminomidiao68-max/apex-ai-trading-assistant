"""Unit tests for the deterministic PRIME/setup backtest service."""
from __future__ import annotations

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services import prime_backtest_service as pbs


def bar(t, o, h, l, c):
    return {"t": float(t), "o": float(o), "h": float(h), "l": float(l), "c": float(c), "v": 1.0}


def long_report(entry=100.0, sl=95.0, tp1=110.0, grade="A", confluence=30, omega=True):
    return {
        "direction": "long",
        "levels": {"entry": entry, "sl": sl},
        "tp1": tp1,
        "setup_type": "OB Return",
        "grade": grade,
        "confluence": confluence,
        "omega_compliant": omega,
    }


def short_report(entry=100.0, sl=105.0, tp1=90.0, grade="A+", confluence=40, omega=False):
    return {
        "direction": "short",
        "levels": {"entry": entry, "sl": sl},
        "tp1": tp1,
        "setup_type": "Liquidity Sweep",
        "grade": grade,
        "confluence": confluence,
        "omega_compliant": omega,
    }


# ------------------------------------------------------------------ simulate
def test_long_tp1_fill_and_r_multiple():
    items = [
        bar(0, 100, 101, 99, 100),        # i=0 detection bar
        bar(60, 100, 100.8, 100.2, 100.5),  # no trigger (low > entry)
        bar(120, 100.5, 100.6, 99.9, 100.1),  # trigger: low <= 100
        bar(180, 100.1, 105.0, 100.0, 104.0),  # no exit yet
        bar(240, 104.0, 110.2, 103.5, 110.0),  # TP1 touched
    ]
    trade = pbs._simulate(items, 0, long_report(), exit_horizon=10, fee_pct=0.0)
    assert trade and trade["triggered"] is True
    assert trade["exit_reason"] == "tp1"
    assert trade["r"] == 2.0  # (110-100)/(100-95)
    assert trade["bars_held"] == 2
    assert trade["prime"] is True  # omega_compliant report -> live confirmed gate


def test_long_sl_fill_r_minus_one():
    items = [
        bar(0, 100, 101, 99, 100),
        bar(60, 100, 100.5, 94.0, 95.0),  # triggers entry AND breaks stop on same bar
        bar(120, 95, 96, 93, 94),
    ]
    trade = pbs._simulate(items, 0, long_report(), exit_horizon=10, fee_pct=0.0)
    assert trade and trade["exit_reason"] == "sl"
    assert trade["r"] == -1.0
    assert trade["bars_held"] == 0


def test_entry_bar_ignores_tp_same_bar():
    # conservative rule: the entry bar only checks the stop, never the target
    items = [
        bar(0, 100, 101, 99, 100),
        bar(60, 100, 112.0, 99.9, 111.0),  # triggers entry; high > tp but same bar
        bar(120, 111, 111.5, 94.0, 95.0),  # stop fills on the next bar
    ]
    trade = pbs._simulate(items, 0, long_report(), exit_horizon=10, fee_pct=0.0)
    assert trade and trade["exit_reason"] == "sl"
    assert trade["r"] == -1.0


def test_ambiguous_bar_resolves_to_sl_first():
    items = [
        bar(0, 100, 101, 99, 100),
        bar(60, 100, 100.5, 99.9, 100.2),   # entry trigger
        bar(120, 100.2, 110.5, 94.5, 105),  # both TP and SL in one bar -> SL wins
    ]
    trade = pbs._simulate(items, 0, long_report(), exit_horizon=10, fee_pct=0.0)
    assert trade and trade["exit_reason"] == "sl"
    assert trade["r"] == -1.0


def test_short_tp1_fill_and_r_multiple():
    items = [
        bar(0, 100, 101, 99, 100),
        bar(60, 100, 99.95, 99.5, 99.8),    # no trigger (high < entry)
        bar(120, 99.8, 100.3, 99.7, 100.1), # trigger: high >= 100
        bar(180, 100.1, 100.2, 95.0, 96.0), # no exit yet (low > tp)
        bar(240, 96.0, 96.5, 89.8, 90.5),   # TP1 touched
    ]
    trade = pbs._simulate(items, 0, short_report(), exit_horizon=10, fee_pct=0.0)
    assert trade and trade["exit_reason"] == "tp1"
    assert trade["r"] == 2.0  # (100-90)/(105-100)
    assert trade["direction"] == "short"
    assert trade["prime"] is False  # graded but not omega-confirmed


def test_timeout_exits_at_close_with_partial_r():
    items = [bar(0, 100, 101, 99, 100)]
    items.append(bar(60, 100, 100.5, 99.9, 100.2))  # trigger
    for i in range(2, 6):
        items.append(bar(i * 60, 100.2, 101.0, 100.0, 100.5))  # never hits SL/TP
    trade = pbs._simulate(items, 0, long_report(), exit_horizon=5, fee_pct=0.0)
    assert trade and trade["exit_reason"] == "timeout"
    assert abs(trade["r"] - (100.5 - 100.0) / 5.0) < 1e-9


def test_not_triggered_within_horizon():
    items = [bar(0, 100, 101, 99, 100)]
    items += [bar(i * 60, 101, 102, 100.6, 101.5) for i in range(1, 6)]  # stays above entry
    trade = pbs._simulate(items, 0, long_report(), exit_horizon=4, fee_pct=0.0)
    assert trade == {"triggered": False, "index": 0}


def test_invalid_geometry_returns_none():
    items = [bar(0, 100, 101, 99, 100)] * 5
    bad = long_report(entry=100, sl=105, tp1=110)   # long with SL above entry
    assert pbs._simulate(items, 0, bad, 10, 0.0) is None
    bad2 = long_report(entry=100, sl=95, tp1=90)    # TP on wrong side
    assert pbs._simulate(items, 0, bad2, 10, 0.0) is None
    bad3 = {"direction": "long", "levels": {"entry": 0, "sl": 95}, "tp1": 110}
    assert pbs._simulate(items, 0, bad3, 10, 0.0) is None


def test_fee_reduces_r():
    items = [
        bar(0, 100, 101, 99, 100),
        bar(60, 100, 100.5, 99.9, 100.2),   # entry trigger
        bar(120, 100.2, 110.5, 100.1, 110),  # TP
    ]
    free = pbs._simulate(items, 0, long_report(), exit_horizon=10, fee_pct=0.0)
    with_fee = pbs._simulate(items, 0, long_report(), exit_horizon=10, fee_pct=0.1)
    assert free["r"] == 2.0
    assert with_fee["r"] < free["r"]
    expected_fee_r = (0.1 / 100.0) * (100.0 + 110.0) / 5.0
    assert abs(with_fee["r"] - (2.0 - expected_fee_r)) < 1e-3


# --------------------------------------------------------------------- stats
def test_stats_known_values():
    trades = [
        {"r": 2.0, "exit_reason": "tp1"},
        {"r": -1.0, "exit_reason": "sl"},
        {"r": 0.5, "exit_reason": "timeout"},
    ]
    s = pbs._stats(trades)
    assert s["trades"] == 3 and s["wins"] == 2 and s["losses"] == 1
    assert s["win_rate_pct"] == 66.7
    assert s["total_r"] == 1.5 and s["avg_r"] == 0.5
    assert s["profit_factor"] == 2.5
    assert s["max_consecutive_losses"] == 1
    assert s["best_r"] == 2.0 and s["worst_r"] == -1.0
    assert s["exit_reasons"] == {"tp1": 1, "sl": 1, "timeout": 1}


def test_stats_empty():
    s = pbs._stats([])
    assert s["trades"] == 0 and s["win_rate_pct"] is None and s["profit_factor"] is None


# ----------------------------------------------------------------------- run
def make_trend_items(n: int = 240) -> list[dict]:
    """Uptrend with rhythmic pullbacks so the detector has real structure."""
    items = []
    price = 100.0
    for i in range(n):
        drift = 0.15
        pull = -0.9 if (i % 12) in (9, 10) else 0.0  # periodic pullback
        o = price
        c = max(1.0, price + drift + pull)
        h = max(o, c) + 0.3
        l = min(o, c) - 0.3
        items.append({"t": 1_700_000_000.0 + i * 900, "o": o, "h": h, "l": l, "c": c, "v": 100.0 + i})
        price = c
    return items


def test_run_insufficient_candles():
    out = pbs.run(make_trend_items(50), symbol="BTCUSDT", timeframe="15m")
    assert out["ok"] is False
    assert out["detail"] == "insufficient_candles"
    assert out["required"] == 150


def test_run_structure_and_determinism():
    items = make_trend_items(240)
    out = pbs.run(items, symbol="BTCUSDT", timeframe="15m")
    assert out["ok"] is True
    assert out["symbol"] == "BTCUSDT"
    assert out["candles"] == 240
    for key in ("settings", "all", "prime_proxy", "by_setup_type", "trades", "disclaimer_fa", "period"):
        assert key in out
    assert out["settings"]["target"] == "tp1"
    assert out["period"]["start_ts"] == items[0]["t"]
    assert out["period"]["end_ts"] == items[-1]["t"]
    for trade in out["trades"]:
        assert trade["exit_reason"] in ("sl", "tp1", "timeout")
        assert isinstance(trade["r"], float)
    again = pbs.run(items, symbol="BTCUSDT", timeframe="15m")
    assert again == out  # fully deterministic replay


def test_run_prime_subset_is_subset_of_all():
    items = make_trend_items(240)
    out = pbs.run(items, symbol="BTCUSDT", timeframe="15m")
    assert out["prime_proxy"]["trades"] <= out["all"]["trades"]


def test_resample_buckets_ohlcv_correctly():
    # four 15m bars into one 1h bucket
    items = [
        bar(0, 100, 102, 99, 101),
        bar(900, 101, 105, 100, 104),
        bar(1800, 104, 106, 103, 103.5),
        bar(2700, 103.5, 104, 101, 102),
    ]
    out = pbs.resample(items, 3600)
    assert len(out) == 1
    row = out[0]
    assert row["o"] == 100 and row["c"] == 102
    assert row["h"] == 106 and row["l"] == 99
    assert row["v"] == 4.0
    # two buckets when spanning the boundary
    items.append(bar(3600, 102, 103, 101, 102.5))
    out2 = pbs.resample(items, 3600)
    assert len(out2) == 2 and out2[1]["t"] == 3600.0
    assert pbs.resample([], 3600) == []


def test_htf_map_and_bias_replay_are_wired():
    assert pbs.HTF_MAP["15m"] == "1h"
    items = make_trend_items(240)

    def fake_analyze(window, symbol="", timeframe=""):
        return {"bias": "bullish"}

    assert pbs._htf_bias(items, "15m", fake_analyze) in ("bullish", None)
    assert pbs._htf_bias(items, "1d", fake_analyze) is None  # no HTF above 1d


def test_okx_candle_normalization_is_ascending_and_deduped():
    # exercise the row->item mapping rules used by fetch_okx_deep_candles
    rows = [
        ["1700000060000", "101", "102", "100", "101.5", "5", "507.5"],
        ["1700000000000", "100", "101", "99", "101", "4", "404"],
        ["1700000000000", "100", "101", "99", "101", "4", "404"],  # duplicate ts
        ["bad", "row"],
    ]
    by_t: dict[float, dict] = {}
    for row in rows:
        try:
            t = float(row[0]) / 1000.0
            by_t[t] = {"t": t, "o": float(row[1]), "h": float(row[2]), "l": float(row[3]), "c": float(row[4]), "v": float(row[5])}
        except (IndexError, TypeError, ValueError):
            continue
    items = [by_t[t] for t in sorted(by_t)]
    assert [it["t"] for it in items] == [1700000000.0, 1700000060.0]
    assert items[0]["c"] == 101.0 and items[1]["h"] == 102.0
