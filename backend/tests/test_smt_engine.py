"""Unit tests for the deterministic SMT divergence engine."""
from __future__ import annotations

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services import smt_engine


# --------------------------------------------------------------------- helpers
def make_series(turns: list[float], bars_per_leg: int = 8, start_t: float = 1_700_000_000.0, dt: float = 60.0, wick: float = 0.05) -> list[dict]:
    """Zigzag candle series through the given turning prices (equal wicks)."""
    closes: list[float] = [turns[0]]
    for a, b in zip(turns, turns[1:]):
        for j in range(1, bars_per_leg + 1):
            closes.append(a + (b - a) * j / bars_per_leg)
    items = []
    t = start_t
    prev = closes[0]
    for c in closes:
        items.append({
            "t": t,
            "o": prev,
            "h": c + wick,
            "l": c - wick,
            "c": c,
            "v": 10.0,
        })
        prev = c
        t += dt
    return items


A_TURNS = [100.0, 110.0, 95.0, 115.0, 92.0, 118.0, 90.0]   # HH highs + LL lows
B_TURNS = [100.0, 110.0, 95.0, 108.0, 97.0, 112.0, 93.0]   # fails HH, refuses LL


def test_align_series_inner_join_on_timestamp():
    a = make_series([100, 105, 100])
    b = make_series([50, 52, 50], start_t=1_700_000_000.0 + 120)  # shifted: only partial overlap
    ja, jb = smt_engine.align_series(a, b)
    assert len(ja) == len(jb)
    assert all(x["t"] == y["t"] for x, y in zip(ja, jb))
    assert len(ja) < len(a)


def test_align_series_empty_inputs():
    a = make_series([100, 105, 100])
    assert smt_engine.align_series([], a) == ([], [])
    assert smt_engine.align_series(a, []) == ([], [])


def test_correlation_identical_series_is_one():
    a = make_series(A_TURNS)
    r = smt_engine.returns_correlation(a, a)
    assert r is not None and abs(r - 1.0) < 1e-9


def test_correlation_none_when_flat():
    flat = [{"t": float(i), "o": 100.0, "h": 100.0, "l": 100.0, "c": 100.0, "v": 1.0} for i in range(40)]
    noisy = make_series([100, 105, 98, 103], bars_per_leg=10)
    assert smt_engine.returns_correlation(flat, noisy) is None
    assert smt_engine.returns_correlation(flat[:5], flat[:5]) is None  # too short


def test_detects_bearish_smt_on_higher_high_mismatch():
    a = make_series(A_TURNS)
    b = make_series(B_TURNS)
    out = smt_engine.detect_smt(a, b, "BTCUSDT", "ETHUSDT")
    assert out["available"] is True
    assert out["aligned_candles"] == len(a)
    bearish = [d for d in out["divergences"] if d["kind"] == "smt_bearish"]
    assert bearish, f"expected a bearish SMT, got {out['divergences']}"
    row = bearish[0]
    assert row["side"] == "high"
    assert row["strong"] == "BTCUSDT"   # printed the higher high
    assert row["weak"] == "ETHUSDT"     # failed to follow
    assert row["strong_levels"]["new"] > row["strong_levels"]["prev"]
    assert row["weak_levels"]["new"] < row["weak_levels"]["prev"]


def test_detects_bullish_smt_on_lower_low_refusal():
    a = make_series(A_TURNS)
    b = make_series(B_TURNS)
    out = smt_engine.detect_smt(a, b, "BTCUSDT", "ETHUSDT")
    bullish = [d for d in out["divergences"] if d["kind"] == "smt_bullish"]
    assert bullish, f"expected a bullish SMT, got {out['divergences']}"
    row = bullish[0]
    assert row["side"] == "low"
    assert row["strong"] == "ETHUSDT"   # refused the lower low
    assert row["weak"] == "BTCUSDT"
    assert row["weak_levels"]["new"] < row["weak_levels"]["prev"]
    assert row["strong_levels"]["new"] > row["strong_levels"]["prev"]


def test_no_divergence_when_series_move_together():
    a = make_series(A_TURNS)
    out = smt_engine.detect_smt(a, list(a), "BTCUSDT", "BTCUSDT2")
    assert out["available"] is True
    assert out["divergences"] == []
    assert out["score"] == 0
    assert out["correlation"] is not None and out["correlation"] > 0.99
    assert out["correlation_reliable"] is True


def test_score_bounds_and_reliability_flag():
    a = make_series(A_TURNS)
    b = make_series(B_TURNS)
    out = smt_engine.detect_smt(a, b, "A", "B")
    assert -6 <= out["score"] <= 6
    corr = out["correlation"]
    assert out["correlation_reliable"] == bool(corr is not None and abs(corr) >= smt_engine.MIN_CORRELATION)


def test_insufficient_data_reports_unavailable():
    short = make_series([100, 105], bars_per_leg=4)
    out = smt_engine.detect_smt(short, list(short), "A", "B")
    assert out["available"] is False
    assert out["reason"] == "insufficient_aligned_candles"
    assert smt_engine.detect_smt([], [], "A", "B")["available"] is False


def test_summary_fa_mentions_pair_and_is_persian():
    a = make_series(A_TURNS)
    b = make_series(B_TURNS)
    out = smt_engine.detect_smt(a, b, "BTCUSDT", "ETHUSDT")
    summary = out["summary_fa"]
    assert isinstance(summary, str) and summary
    assert "ETHUSDT" in summary
    assert "SMT" in summary


def test_detection_is_deterministic():
    a = make_series(A_TURNS)
    b = make_series(B_TURNS)
    first = smt_engine.detect_smt(a, b, "A", "B")
    second = smt_engine.detect_smt(a, b, "A", "B")
    assert first == second
