"""v3.25 WEEKLY-GRADE: scarcity + maximum-strictness tests (fully deterministic)."""
from datetime import datetime, timezone

from app.services.intraday_fusion_service import IntradayFusionService
from app.services.precision_window import in_killzone, week_key
from app.services.strict_decision_engine import apply_strict_decision

NOW = datetime(2026, 9, 16, 13, 0, tzinfo=timezone.utc)   # Wednesday, London/NY overlap
OFF = datetime(2026, 9, 16, 3, 0, tzinfo=timezone.utc)    # Asian dead zone


def _candles(n=120, mode="trend"):
    out = []
    price = 100.0
    for i in range(n):
        o = price
        if mode == "trend":
            c = price + (0.4 if i % 3 else -0.2)
        elif mode == "chop":
            c = price + (0.4 if i % 2 else -0.4)
        else:  # dead
            c = price + (0.001 if i % 2 else -0.001)
        h = max(o, c) + (0.15 if mode != "dead" else 0.002)
        l = min(o, c) - (0.15 if mode != "dead" else 0.002)
        out.append({"t": float(i * 900), "o": o, "h": h, "l": l, "c": c, "v": 1200.0 + i})
        price = c
    return out


def _doji_tail(candles):
    candles = [dict(item) for item in candles]
    last = candles[-1]
    mid = (last["h"] + last["l"]) / 2
    last.update(o=mid, c=mid)  # doji: no body, no confirmation
    return candles


def _report(**over):
    base = {
        "direction": "long", "grade": "A+", "confluence": 88, "probability": 88,
        "rr": 3.6, "mtf_aligned": True, "htf_bias": "bullish",
        "setup_type": "پولبک BOS به ناحیه OTE", "events": [],
        "news_blocked": False, "invalidation": 98.0,
        "plan_lines": [{"kind": "entry", "price": 100.0}],
        "confluence_factors": [
            {"name": "HTF alignment", "points": 12}, {"name": "BOS structure", "points": 10},
            {"name": "OTE entry", "points": 8}, {"name": "liquidity sweep", "points": 9},
        ],
        "orderflow": {},
    }
    base.update(over)
    return base


def _strict(report, candles=None, flow=None, timeframe="4h", now=NOW):
    return apply_strict_decision(report, candles or _candles(), "crypto", timeframe,
                                 orderflow_snapshot=flow, now_utc=now)


def _gates(dec):
    return {g["name"]: g for g in dec["decision"]["gates"]}


def _frame(tf, side, status, quality=92, regime="trending"):
    return {
        "timeframe": tf,
        "report": {
            "direction": side, "bias": "bullish" if side == "long" else "bearish",
            "confluence": 88, "invalidation": 99, "levels": {"entry": 100, "sl": 99, "tp": 103},
            "tp1": 102, "data_quality": {"score": quality},
            "frame_freshness": {"fresh": True, "age_seconds": 30},
            "market_regime": {"name": regime},
            "decision": {"side": side, "status": status,
                         "orderflow": {"is_real": True, "pressure": "buy" if side == "long" else "sell"}},
        },
    }


def _fusion_frames(**over):
    frames = [_frame("5m", "long", "actionable"), _frame("15m", "long", "watch"),
              _frame("1h", "long", "actionable"), _frame("4h", "long", "actionable"),
              _frame("1d", "long", "actionable")]
    for tf, patch in over.items():
        item = next(f for f in frames if f["timeframe"] == tf)
        item["report"].update(patch)
    return frames


# ------------------------------------------------------------------ windows
def test_killzone_is_london_ny_overlap_only():
    assert in_killzone(datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc))
    assert in_killzone(datetime(2026, 9, 16, 14, 0, tzinfo=timezone.utc))
    assert in_killzone(datetime(2026, 9, 16, 16, 59, tzinfo=timezone.utc))
    assert not in_killzone(datetime(2026, 9, 16, 8, 30, tzinfo=timezone.utc))  # v3.26: London AM retired
    assert not in_killzone(datetime(2026, 9, 16, 3, 0, tzinfo=timezone.utc))
    assert not in_killzone(datetime(2026, 9, 16, 11, 0, tzinfo=timezone.utc))
    assert not in_killzone(datetime(2026, 9, 16, 17, 0, tzinfo=timezone.utc))
    assert not in_killzone(datetime(2026, 9, 16, 21, 0, tzinfo=timezone.utc))
    assert week_key(NOW).startswith("2026-W")


def test_session_killzone_hard_gate():
    assert _gates(_strict(_report(), now=OFF))["session_killzone"]["passed"] is False
    assert _gates(_strict(_report(), now=NOW))["session_killzone"]["passed"] is True


# ------------------------------------------------- candle-state strictness
def test_confirmation_close_doji_rejected():
    dec = _strict(_report(), candles=_doji_tail(_candles()))
    assert "confirmation_close" in dec["decision"]["failed_gates"]


def test_trend_efficiency_chop_rejected():
    dec = _strict(_report(), candles=_candles(mode="chop"))
    assert "trend_efficiency" in dec["decision"]["failed_gates"]


def test_volatility_band_dead_market_rejected():
    dec = _strict(_report(), candles=_candles(mode="dead"))
    assert "volatility_band" in dec["decision"]["failed_gates"]


# ------------------------------------------------------ threshold strictness
def test_grade_a_no_longer_actionable():
    assert "grade" in _strict(_report(grade="A"))["decision"]["failed_gates"]


def test_htf_reversal_exception_is_retired():
    rep = _report(setup_type="sweep reversal", events=[{"kind": "CHoCH"}],
                  htf_bias="bearish", timeframe="1h")
    dec = _strict(rep, timeframe="1h")
    assert "htf_alignment" in dec["decision"]["failed_gates"]


def test_neutral_pressure_no_longer_passes():
    flow = {"source": "okx_swap_public", "is_real": True, "confidence": 0.9,
            "pressure": "neutral", "spread_bps": 1.0, "funding_rate": 0.0}
    assert "orderflow_alignment" in _strict(_report(), flow=flow, timeframe="1h")["decision"]["failed_gates"]


def test_spread_4bps_and_funding_0008_rejected():
    flow = {"source": "okx_swap_public", "is_real": True, "confidence": 0.9,
            "pressure": "buy", "spread_bps": 4.0, "funding_rate": 0.0008}
    failed = _strict(_report(), flow=flow, timeframe="1h")["decision"]["failed_gates"]
    assert "execution_spread" in failed and "funding_crowding" in failed


def test_real_flow_evidence_floor_is_060():
    flow = {"source": "okx_swap_public", "is_real": True, "confidence": 0.55,
            "pressure": "buy", "spread_bps": 1.0, "funding_rate": 0.0}
    assert "orderflow_evidence" in _strict(_report(), flow=flow, timeframe="1h")["decision"]["failed_gates"]


# ---------------------------------------------------- weekly scarcity governor
def test_fusion_context_must_be_trending():
    result = IntradayFusionService().fuse("BTCUSDT", "crypto",
                                          _fusion_frames(**{"1h": {"market_regime": {"name": "balanced"}}}),
                                          now_utc=NOW)
    assert "context_regime" in result["failed_gates"]


def test_fusion_trigger_unanimity_required():
    frames = _fusion_frames()
    frames[1]["report"]["direction"] = "short"
    frames[1]["report"]["decision"]["side"] = "short"
    frames[1]["report"]["decision"]["orderflow"]["pressure"] = "sell"
    result = IntradayFusionService().fuse("BTCUSDT", "crypto", frames, now_utc=NOW)
    assert "trigger_unanimity" in result["failed_gates"]


def test_full_stack_baseline_is_actionable_in_killzone():
    dec = _strict(_report())
    assert dec["decision"]["status"] == "actionable", dec["decision"]["failed_gates"]
    assert dec["decision"]["hard_gates_total"] >= 23  # v3.26: +evidence_diversity +target_reachability
    assert len(dec["decision"]["gates"]) >= 28
