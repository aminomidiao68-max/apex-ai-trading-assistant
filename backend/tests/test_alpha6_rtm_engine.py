"""Alpha-6: RTM engine — Quasimodo / FTR / flag-MPL / compression / supply-demand
/ liquidity map. Synthetic-candle tests with DIRECTIONAL regression guards:
a bullish scenario must never emit bearish signals and vice versa (the
double_bottom sign-bug lesson)."""
import json

from app.services import rtm_engine


def C(o, h, l, c, t=0.0, v=100.0):
    return {"t": t, "o": o, "h": h, "l": l, "c": c, "v": v}


def pad(n, base=100.0, t0=1_700_000_000.0, step=900.0):
    out = []
    for i in range(n):
        o = base + (0.1 if i % 2 else -0.1)
        out.append(C(o, o + 0.3, o - 0.3, o + (0.05 if i % 2 else -0.05), t=t0 + len(out) * step))
    return out


def with_t(items, t0=1_700_000_000.0, step=900.0):
    for i, it in enumerate(items):
        it["t"] = t0 + i * step
    return items


# --------------------------------------------------------------------------- QML
def _bear_qml_candles():
    items = []
    items += [C(90 + i * 1.4, 90.6 + i * 1.4, 89.8 + i * 1.4, 90.3 + i * 1.4) for i in range(6)]
    items.append(C(98.0, 100.0, 97.8, 98.5))            # 6: H1 swing high
    items.append(C(97.5, 97.9, 96.8, 97.0))             # 7
    items.append(C(96.8, 97.0, 96.0, 96.2))             # 8
    items.append(C(95.8, 95.9, 95.0, 95.4))             # 9: swing low 95.0
    items.append(C(95.8, 96.8, 95.6, 96.5))             # 10
    items.append(C(96.6, 99.4, 96.2, 99.0))             # 11
    items.append(C(99.0, 105.2, 98.9, 100.0))           # 12: H2 sweep 105.2
    items.append(C(99.5, 99.8, 97.5, 97.8))             # 13
    items.append(C(97.5, 97.8, 96.0, 96.3))             # 14
    items.append(C(96.0, 96.2, 94.2, 94.5))             # 15: close < 95 → QML confirmed
    items += [C(94.2, 94.8, 93.6, 94.0) for _ in range(19)]
    return with_t(items)


def test_bearish_qml_detected_and_never_bullish():
    s = rtm_engine.summarize(_bear_qml_candles(), {"bias": "bearish"})
    assert s["available"] is True
    bears = [z for z in s["qml"] if z["kind"] == "qml_bear" and not z["mitigated"]]
    assert bears, "sweep-high + low-break must produce an unmitigated bearish QML"
    assert abs(bears[0]["price"] - 105.2) < 0.01
    assert all(z["kind"] != "qml_bull" for z in s["qml"]), "directional guard"


def _bull_qml_candles():
    items = []
    items += [C(100 - i * 1.4, 100.2 - i * 1.4, 99.4 - i * 1.4, 99.7 - i * 1.4) for i in range(6)]
    items.append(C(92.0, 92.2, 90.0, 91.5))             # 6: L1 swing low 90.0
    items.append(C(92.5, 93.2, 92.3, 93.0))             # 7
    items.append(C(93.2, 94.0, 93.0, 93.8))             # 8
    items.append(C(94.2, 95.0, 94.1, 94.6))             # 9: swing high 95.0
    items.append(C(94.2, 94.4, 93.2, 93.5))             # 10
    items.append(C(93.4, 93.8, 90.6, 91.0))             # 11
    items.append(C(91.0, 91.1, 84.8, 90.0))             # 12: L2 sweep 84.8
    items.append(C(90.5, 92.8, 90.2, 92.5))             # 13
    items.append(C(92.8, 94.2, 92.6, 94.0))             # 14
    items.append(C(94.2, 96.4, 94.0, 95.8))             # 15: close > 95 → confirmed
    items += [C(95.8, 96.6, 95.6, 96.2) for _ in range(19)]
    return with_t(items)


def test_bullish_qml_is_exact_mirror():
    s = rtm_engine.summarize(_bull_qml_candles(), {"bias": "bullish"})
    bulls = [z for z in s["qml"] if z["kind"] == "qml_bull" and not z["mitigated"]]
    assert bulls and abs(bulls[0]["price"] - 84.8) < 0.01
    assert all(z["kind"] != "qml_bear" for z in s["qml"]), "directional guard"


# --------------------------------------------------------------------------- FTR
def test_ftr_bull_zone_when_price_never_returns():
    items = pad(12, base=100.0)
    items.append(C(100.1, 100.3, 99.6, 99.8))           # origin (bearish)
    items.append(C(99.8, 103.2, 99.7, 103.0))           # impulse +3.2
    for i in range(16):
        o = 103.0 + i * 0.12
        items.append(C(o, o + 0.3, o - 0.05, o + 0.1))  # lows stay > 100.3
    s = rtm_engine.summarize(with_t(items), {"bias": "bullish"})
    bulls = [z for z in s["ftr"] if z["kind"] == "ftr_bull" and not z["mitigated"]]
    assert bulls, "impulse origin never revisited → FTR must be active"
    assert bulls[0]["top"] == 100.3 and bulls[0]["strength"] >= 2.0
    assert all(z["kind"] != "ftr_bear" for z in s["ftr"]), "directional guard"


# ---------------------------------------------------------------------- Flag/MPL
def test_flag_mpl_sweep_and_reclaim():
    items = pad(8, base=100.0)
    o = 100.0
    for _ in range(6):                                   # pole: +6.0
        items.append(C(o, o + 1.15, o - 0.05, o + 1.0))
        o += 1.0
    for i in range(12):                                  # tight 12-bar flag
        base = 106.0 + (0.1 if i % 2 else 0.0)
        items.append(C(base, base + 0.2, base - 0.2, base + 0.05))
    items.append(C(106.2, 106.4, 103.0, 106.3))          # deep stop-run below MPL, close back
    items += [C(106.4, 107.0, 106.2, 106.9) for _ in range(5)]
    s = rtm_engine.summarize(with_t(items), {"bias": "bullish"})
    flags = [f for f in s["flags"] if f["kind"] == "flag_bull"]
    assert flags, "pole + tight flag must be detected"
    assert abs(flags[0]["mpl"] - 105.7) < 0.35
    assert flags[0]["mpl_swept"] is True and flags[0]["sweep_reclaimed"] is True
    assert all(f["kind"] != "flag_bear" for f in s["flags"]), "directional guard"


# ------------------------------------------------------------------- Compression
def test_compression_bull_into_flat_highs():
    items = pad(6, base=96.0)
    items.append(C(99.0, 100.0, 98.8, 99.4))             # 6: H flat-1 @100.0
    items.append(C(98.6, 98.8, 97.4, 97.6))
    items.append(C(97.8, 98.0, 97.0, 97.3))              # 8: L 97.0
    items.append(C(97.6, 98.8, 97.4, 98.6))
    items.append(C(99.2, 100.05, 99.0, 99.5))            # 10: H flat-2 @100.05
    items.append(C(99.0, 99.3, 98.2, 98.4))
    items.append(C(98.2, 98.4, 97.8, 98.0))              # 12: L 97.8
    items.append(C(98.2, 98.8, 98.1, 98.6))
    items.append(C(98.6, 99.2, 98.5, 99.0))
    items.append(C(99.0, 99.5, 98.7, 99.2))
    items.append(C(99.0, 99.2, 98.4, 98.6))              # 16: L 98.4 (rising, shrinking)
    items += [C(99.3, 99.6, 99.0, 99.4) for _ in range(16)]
    s = rtm_engine.summarize(with_t(items), {"bias": "bullish"})
    comps = [z for z in s["compression"] if z["kind"] == "compression_bull"]
    assert comps, "rising shrinking lows into flat highs → bull compression"
    assert abs(comps[0]["target"] - 100.02) < 0.3
    assert all(z["kind"] != "compression_bear" for z in s["compression"]), "directional guard"


# ------------------------------------------------------------------ Supply/Demand
def _dbr_candles():
    items = [C(105.0, 105.3, 104.7, 105.1) for _ in range(20)]  # quiet ATR ~0.6
    items.append(C(105.0, 105.1, 103.9, 104.0))          # drop (approach < 0)
    items.append(C(104.0, 104.1, 102.9, 103.0))
    items.append(C(103.0, 103.1, 101.9, 102.0))
    items.append(C(102.0, 102.3, 101.7, 101.9))          # base bar 1 (tight)
    items.append(C(101.9, 102.2, 101.6, 102.05))         # base bar 2 (tight)
    items.append(C(102.05, 105.7, 102.0, 105.5))         # departure +3.45
    for i in range(8):
        o = 105.5 + i * 0.1
        items.append(C(o, o + 0.3, o - 0.1, o + 0.15))   # never returns
    return with_t(items)


def test_demand_dbr_zone_fresh_and_bullish_only():
    s = rtm_engine.summarize(_dbr_candles(), {"bias": "bullish"})
    dem = [z for z in s["supply_demand"] if z["kind"] == "DBR"]
    assert dem, "drop-base-rally must produce a demand zone"
    z = dem[0]
    assert z["side"] == "bullish" and z["fresh"] is True and z["strength"] >= 2.0
    assert z["bottom"] <= 102.0 <= z["top"]
    assert all(x["side"] == "bullish" for x in s["supply_demand"]), "directional guard"


def test_supply_rbd_zone_is_mirror():
    items = [C(100.0, 100.3, 99.7, 100.1) for _ in range(20)]  # quiet ATR ~0.6
    items.append(C(100.0, 101.1, 99.9, 101.0))           # rally (approach > 0)
    items.append(C(101.0, 102.1, 100.9, 102.0))
    items.append(C(102.0, 103.1, 101.9, 103.0))
    items.append(C(103.0, 103.4, 102.8, 103.1))          # base (tight)
    items.append(C(103.1, 103.5, 102.9, 103.0))
    items.append(C(103.0, 103.1, 99.4, 99.6))            # departure -3.4
    for i in range(8):
        o = 99.6 - i * 0.1
        items.append(C(o, o + 0.1, o - 0.3, o - 0.15))
    s = rtm_engine.summarize(with_t(items), {"bias": "bearish"})
    sup = [z for z in s["supply_demand"] if z["kind"] == "RBD"]
    assert sup and sup[0]["side"] == "bearish" and sup[0]["fresh"] is True
    assert all(x["side"] == "bearish" for x in s["supply_demand"]), "directional guard"


# ------------------------------------------------------------- Liquidity map/DOL
def test_dol_targets_eqh_for_bullish_bias():
    items = pad(6, base=104.0)
    items.append(C(107.0, 110.0, 106.8, 107.5))          # EQH touch 1 @110.0
    items.append(C(107.0, 107.4, 105.5, 105.8))
    items.append(C(105.9, 106.2, 104.8, 105.0))          # swing low
    items.append(C(105.4, 106.6, 105.2, 106.4))
    items.append(C(106.8, 110.05, 106.6, 107.2))         # EQH touch 2 @110.05
    items.append(C(106.8, 107.0, 105.4, 105.6))
    items.append(C(105.6, 105.9, 104.9, 105.2))          # swing low
    items += [C(105.2, 105.8, 104.8, 105.4) for _ in range(18)]
    s = rtm_engine.summarize(with_t(items), {"bias": "bullish"})
    liq = s["liquidity"]
    assert any(p["kind"] == "eqh" for p in liq["pools"])
    dol = liq["dol"]
    assert dol and dol["side"] == "buy" and abs(dol["target"] - 110.0) < 0.5
    assert "نقدینگی" in dol["rationale_fa"]


# ------------------------------------------------------------------------ guards
def test_summarize_is_safe_on_thin_or_flat_data():
    assert rtm_engine.summarize(pad(20), {})["available"] is False
    assert rtm_engine.summarize([], {})["available"] is False
    flat = [C(100, 100, 100, 100) for _ in range(40)]
    out = rtm_engine.summarize(with_t(flat), {})
    assert out["available"] is False
    assert json.dumps(out)  # always serializable


def test_overlay_items_shape():
    s = rtm_engine.summarize(_bear_qml_candles(), {"bias": "bearish"})
    ov = rtm_engine.overlay_items(s)
    assert any(ln["kind"] == "QML" for ln in ov["lines"])
    assert rtm_engine.overlay_items(None) == {"lines": [], "zones": [], "labels": []}
    s2 = rtm_engine.summarize(_dbr_candles(), {"bias": "bullish"})
    ov2 = rtm_engine.overlay_items(s2)
    assert any(z["kind"] == "SD" and z["side"] == "bullish" for z in ov2["zones"])


# ------------------------------------------------------- AI evidence integration
def _report_with_rtm(side):
    return {
        "price": 105.0,
        "decision": {
            "status": "watch", "side": side, "action_label": "WATCH",
            "risk_tier": "reduced",
            "gates": [{"name": "data_quality", "passed": True, "actual": 99, "required": ">=78"}],
            "orderflow": {"source": "okx_swap_public", "is_real": True, "aligned": True,
                          "pressure": "buy", "confidence": 0.9},
        },
        "confluence_factors": [{"name": "ساختار صعودی", "points": 10}],
        "invalidation": 100.0,
        "rtm": {
            "available": True,
            "qml": [{"kind": "qml_bull", "price": 104.0, "mitigated": False, "distance_pct": -0.9}],
            "ftr": [], "flags": [], "compression": [],
            "supply_demand": [{"kind": "DBR", "side": "bullish", "fresh": True, "mitigated": False,
                               "price": 104.5, "top": 105.0, "bottom": 104.0,
                               "strength": 3.0, "distance_pct": -0.5}],
            "liquidity": {"pools": [], "dol": {"side": "buy", "kind": "eqh",
                                              "target": 110.0, "distance_pct": 4.8}},
        },
    }


def test_rtm_evidence_aligns_with_deterministic_side():
    from app.services.ai_explainability_service import build_evidence_request_from_report

    req = build_evidence_request_from_report(
        _report_with_rtm("long"), market="crypto", timeframe="1h")
    ids = {item.evidence_id for item in req.evidence}
    assert {"RTM_QML_BULLISH", "RTM_SD_DBR", "RTM_DOL"} <= ids
    assert all(item.category == "rtm" for item in req.evidence if item.evidence_id.startswith("RTM_"))
    blob = json.dumps([i.model_dump() for i in req.evidence], ensure_ascii=False).lower()
    assert "rtm_deterministic_engine" in blob


def test_rtm_evidence_conflicts_become_negative():
    from app.services.ai_explainability_service import build_evidence_request_from_report

    req = build_evidence_request_from_report(
        _report_with_rtm("short"), market="crypto", timeframe="1h")
    neg_ids = {item.evidence_id for item in req.negative_evidence}
    assert {"RTM_QML_BULLISH", "RTM_SD_DBR", "RTM_DOL"} <= neg_ids
    assert not any(item.evidence_id.startswith("RTM_") for item in req.evidence)
