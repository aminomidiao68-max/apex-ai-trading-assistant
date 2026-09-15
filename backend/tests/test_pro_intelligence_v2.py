"""Tests for the v3.12 pro-intelligence upgrade.

Covers: indicator_pack_v2, strategy_pack_v2, ICT engine v2 additions
(market structure / OTE / killzones / inversion FVG / breakers), footprint
summary, compact AI context, PRIME strategy-conflict gating, dossier
sections and the /api/v1/analysis/smc integration. Fully offline.
"""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

_TEST_DB_DIR = tempfile.mkdtemp(prefix="apex-v2-tests-")
os.environ.setdefault("DATABASE_PATH", os.path.join(_TEST_DB_DIR, "v2.db"))
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SEED_DEMO_USER", "false")

from fastapi.testclient import TestClient

import app.main as main
from app.services import ict_engine, indicator_pack_v2, strategy_pack_v2
from app.services.microstructure_service import build_compact_context_text, summarize_footprint

client = TestClient(main.app, raise_server_exceptions=True)


# ------------------------------------------------------------------ fixtures
def flat_items(n=70, base=100.0, noise=0.3):
    items = []
    for i in range(n):
        o = base + (0.1 if i % 2 else -0.1)
        c = base + (-0.05 if i % 2 else 0.05)
        items.append({"t": 1_700_000_000.0 + i * 900.0, "o": o, "h": max(o, c) + noise,
                      "l": min(o, c) - noise, "c": c, "v": 1000.0 + i})
    return items


def trend_items(n=120, base=100.0, drift=0.35):
    """Uptrend with rhythmic pullbacks and varied wicks so fractal swings form
    (uniform wicks create equal highs/lows that strict fractals reject)."""
    items = []
    price = base
    for i in range(n):
        pull = -0.9 if (i % 9) in (5, 6, 7) else 0.0
        jitter = ((i * 37) % 7 - 3) / 100.0
        o = price
        c = max(1.0, price + drift + pull + jitter)
        wick = 0.05 + ((i * 53) % 9) / 100.0
        items.append({"t": 1_700_000_000.0 + i * 900.0, "o": o, "h": max(o, c) + wick,
                      "l": min(o, c) - wick, "c": c, "v": 1000.0 + (i % 7) * 10})
        price = c
    return items


def compact_micro_fixture():
    return {
        "is_real": True, "source": "okx", "confidence": 0.9, "timeframe": "15m",
        "window_trades": 500, "covered_seconds": 900, "full_coverage": True,
        "flow": {"delta": 0.25, "pressure": "buy", "cvd": 12.0, "absorption": False,
                 "climax": False, "cvd_divergence": "bullish"},
        "vp": {"poc": 101.0, "vah": 102.0, "val": 100.0, "hvn": [101.0], "lvn": [103.0],
               "shape": "D", "shape_note": "balanced"},
        "footprint": {"candles_covered": 6, "last_delta": 5.0, "last_poc": 101.2,
                      "stacked_buy": 4, "stacked_sell": 0, "unfinished_high": True,
                      "unfinished_low": False,
                      "summary": {"available": True, "poc_migration": "rising",
                                  "delta_price_divergence": None, "stacked_bias": "buy",
                                  "delta_trend": "accelerating_buy", "unfinished_bias": "up"}},
        "l2": {"mid": 101.0, "spread_bps": 0.8, "imbalance_top25": 0.3,
               "bid_wall": {"price": 100.5, "ratio": 3.2}, "ask_wall": {"price": 102.5, "ratio": 2.1}},
        "filters": {"net_bias": "bullish", "score": 0.6, "signals": ["delta:buy"]},
    }


# ---------------------------------------------------------- indicator pack v2
def test_indicator_pack_v2_deterministic_and_complete():
    items = trend_items(240)
    pack1 = indicator_pack_v2.compute_all(items)
    pack2 = indicator_pack_v2.compute_all(items)
    assert pack1 == pack2  # strict determinism
    assert pack1["available"] is True
    for key in ("roc", "trix", "kst", "force_index", "elder_ray", "chaikin",
                "ultimate_osc", "aroon", "donchian", "keltner", "ttm_squeeze",
                "pvt", "ad_line", "vwap", "awesome", "hull", "fractals",
                "choppiness", "pivots", "zscore", "linreg_momentum"):
        assert key in pack1, key
    summary = indicator_pack_v2.summarize(pack1)
    v = summary["votes"]
    assert v["bullish"] + v["bearish"] + v["neutral"] == v["total"] == 16
    assert -100 <= summary["net"] <= 100
    levels = summary["levels"]
    assert levels["donchian_upper"] >= levels["donchian_lower"]
    assert levels["vwap_up2"] >= levels["vwap"] >= levels["vwap_dn2"]
    assert levels["pivot_r1"] > levels["pivot"] > levels["pivot_s1"]
    ctx = indicator_pack_v2.build_context_text(pack1, summary)
    assert "رأی اندیکاتورهای پیشرفته" in ctx


def test_indicator_pack_v2_insufficient_data():
    pack = indicator_pack_v2.compute_all(trend_items(10))
    assert pack["available"] is False
    summary = indicator_pack_v2.summarize(pack)
    assert summary["available"] is False and summary["verdict"] == "no_data"
    assert indicator_pack_v2.build_context_text(pack, summary) == ""


def test_indicator_pack_v2_uptrend_votes_bullish():
    items = trend_items(240, drift=0.6)
    summary = indicator_pack_v2.summarize(indicator_pack_v2.compute_all(items))
    assert summary["votes"]["bullish"] > summary["votes"]["bearish"]
    assert summary["net"] > 0


# ---------------------------------------------------------- strategy pack v2
def test_strategy_pack_wyckoff_spring_detected():
    items = flat_items(70)
    # sweep candle: deep wick below the range, close back inside with strength
    items[68] = {"t": items[68]["t"], "o": 100.0, "h": 100.6, "l": 97.8, "c": 100.5, "v": 2200.0}
    scan = strategy_pack_v2.scan_all(items, "15m")
    assert scan["available"] is True
    spring = [r for r in scan["active"] if r["id"] == "wyckoff_spring"]
    assert spring, "spring must fire on a constructed sweep-and-reclaim"
    assert spring[0]["direction"] == "long"
    assert 0 <= spring[0]["quality"] <= 100
    assert spring[0]["stop"] < spring[0]["entry"] < spring[0]["target"]


def test_strategy_pack_turtle_breakout_detected():
    items = trend_items(80)
    last = items[-1]
    items[-1] = {**last, "c": last["c"] + 3.0, "h": last["h"] + 3.2}
    scan = strategy_pack_v2.scan_all(items, "15m")
    ids = {r["id"] for r in scan["active"]}
    assert "turtle_breakout" in ids


def test_strategy_pack_scan_integrity():
    # uptrend then a downtrend leg (valid OHLC throughout, varied wicks)
    items = trend_items(120)
    price = items[-1]["c"]
    for i in range(80):
        pull = 0.9 if (i % 9) in (5, 6, 7) else 0.0
        jitter = ((i * 41) % 7 - 3) / 100.0
        o = price
        c = max(1.0, price - 0.6 + pull + jitter)
        wick = 0.05 + ((i * 29) % 9) / 100.0
        items.append({"t": items[-1]["t"] + 900.0, "o": o, "h": max(o, c) + wick,
                      "l": min(o, c) - wick, "c": c, "v": 1100.0 + (i % 5) * 10})
        price = c
    scan = strategy_pack_v2.scan_all(items, "15m")
    seen = set()
    for r in scan["active"] + scan["forming"]:
        for key in ("id", "name_fa", "family", "direction", "status", "quality", "reason_fa"):
            assert key in r
        assert 0 <= r["quality"] <= 100
        if r["status"] == "active":
            assert r["direction"] in ("long", "short")
        key = (r["id"], r["direction"])
        assert key not in seen, f"duplicate {key}"
        seen.add(key)
    assert scan["net_direction"] in ("long", "short", "conflict", "none")
    assert 0 <= scan["agreement_pct"] <= 100
    ctx = strategy_pack_v2.build_context_text(scan)
    assert "استراتژی‌های کلاسیک" in ctx


def test_strategy_pack_insufficient_data():
    scan = strategy_pack_v2.scan_all(trend_items(20), "15m")
    assert scan["available"] is False
    assert strategy_pack_v2.build_context_text(scan) == ""


# ------------------------------------------------------------------- ICT v2
def test_ict_v2_market_structure_uptrend():
    items = trend_items(150, drift=0.6)
    ms = ict_engine.market_structure(items)
    assert ms["state"] in ("bullish", "bearish", "ranging", "unknown")
    assert ms["pattern"] in ("HH/HL", "LH/LL", "mixed", "unknown")
    assert ms["state"] == "bullish" and ms["pattern"] == "HH/HL"


def test_ict_v2_ote_zone_ordering():
    items = trend_items(150, drift=0.6)
    ote = ict_engine.ote_zone(items)
    assert ote["available"] is True
    assert ote["ote_top"] > ote["ote_bottom"]
    assert ote["ote_bottom"] >= ote["leg_low"] and ote["ote_top"] <= ote["leg_high"]


def test_ict_v2_killzone_fixed_times():
    wed_8 = datetime(2026, 9, 16, 8, 0, tzinfo=timezone.utc)
    kz = ict_engine.killzone_state(None, wed_8)
    assert kz["active"]["name"] == "london" and kz["quality"] == "high"
    late = datetime(2026, 9, 16, 23, 30, tzinfo=timezone.utc)
    assert ict_engine.killzone_state(None, late)["active"] is None
    sat = datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc)
    assert ict_engine.killzone_state(None, sat)["weekend"] is True


def test_ict_v2_inversion_and_summarize_keys():
    items = trend_items(150)
    fvgs = [{"top": 105.0, "bottom": 104.0, "side": "bullish", "index": 10}]
    states = ict_engine.fvg_states(fvgs, items)
    assert states and states[0]["state"] == "filled"  # trend blew through the gap
    inv = ict_engine.inversion_fvgs(states)
    assert inv and inv[0]["inverted_role"] == "resistance"
    summary = ict_engine.summarize(items, {"fvg": fvgs})
    for key in ("market_structure", "ote", "killzone", "inversion_fvg", "breakers"):
        assert key in summary, key
    assert summary["points_bull"] <= 15 and summary["points_bear"] <= 15


# --------------------------------------------------------- footprint summary
def test_footprint_summary_reads():
    fp = {
        "candles": [
            {"poc": 100.0 + i, "delta": 10.0, "high": 100.0 + i, "low": 99.0 + i, "partial": False,
             "unfinished": {"high": False, "low": False}} for i in range(5)
        ] + [{"poc": 105.0, "delta": 3.0, "high": 105.0, "low": 104.0, "partial": True,
              "unfinished": {"high": True, "low": False}}],
        "totals": {"delta_sum": 53.0, "max_stacked_buy": 5, "max_stacked_sell": 1},
    }
    s = summarize_footprint(fp, {"cvd_divergence": None})
    assert s["available"] is True
    assert s["poc_migration"] == "rising"
    assert s["stacked_bias"] == "buy"
    assert s["unfinished_bias"] == "up"
    assert s["delta_trend"] == "mixed"
    assert summarize_footprint({"candles": []})["available"] is False


def test_compact_context_text_real_numbers():
    text = build_compact_context_text(compact_micro_fixture())
    for token in ("POC=101", "جمع‌بندی فوت‌پرینت", "مهاجرت POC=rising", "دیوار خرید=100.5", "بایاس خالص=bullish"):
        assert token in text, token
    warn = build_compact_context_text({"is_real": False})
    assert "جعل نکن" in warn


# ------------------------------------------------------- PRIME gating + cards
def _prime_report(strategies=None):
    report = {
        "direction": "long", "setup_type": "BREAK+pullback", "grade": "A+",
        "confluence": 80, "probability": 70, "rr": 2.5,
        "microstructure": compact_micro_fixture(),
        "levels": {"entry": 100.0, "sl": 98.0}, "decision": {},
    }
    if strategies is not None:
        report["strategies_v2"] = strategies
    return report


def test_setup_payload_strategy_conflict_blocks_prime():
    base = main._setup_payload(_prime_report(), "BTCUSDT", "crypto", "15m", "confirmed")
    assert base["is_prime"] is True  # micro fixture is strongly bullish
    conflicting = main._setup_payload(
        _prime_report({"available": True, "net_direction": "short", "agreement_pct": 70,
                       "counts": {"active": 3, "long": 0, "short": 3}, "active": []}),
        "BTCUSDT", "crypto", "15m", "confirmed")
    assert conflicting["is_prime"] is False
    assert conflicting["strategies_conflict"] is True
    assert conflicting["value_score"] < base["value_score"]
    aligned = main._setup_payload(
        _prime_report({"available": True, "net_direction": "long", "agreement_pct": 80,
                       "counts": {"active": 4, "long": 4, "short": 0},
                       "active": [{"name_fa": "اسپرینگ وایکاف", "direction": "long", "quality": 70}]}),
        "BTCUSDT", "crypto", "15m", "confirmed")
    assert aligned["is_prime"] is True
    assert aligned["value_score"] > base["value_score"]
    assert aligned["strategies_active"][0]["name_fa"] == "اسپرینگ وایکاف"


def test_dossier_includes_v2_sections():
    items = trend_items(160)
    report = {"bias": "bullish", "price": items[-1]["c"], "action_label": "NO_TRADE",
              "grade": "C", "direction": "neutral", "confluence": 30, "probability": 40,
              "rr": 0, "force": {"buyers_pct": 55, "sellers_pct": 45, "label": "متمایل به خریدار"},
              "ict": ict_engine.summarize(items, {"fvg": []}),
              "indicators_v2": None, "strategies_v2": None}
    pack = indicator_pack_v2.compute_all(items)
    report["indicators_v2"] = {"pack": pack, "summary": indicator_pack_v2.summarize(pack)}
    report["strategies_v2"] = strategy_pack_v2.scan_all(items, "15m")
    dossier = main.build_market_dossier(report, compact_micro_fixture(), items)
    assert "14) پک اندیکاتورهای پیشرفته v2" in dossier
    assert "15) پک استراتژی‌های کلاسیک v2" in dossier
    assert "OTE" in dossier and "کیلزون" in dossier
    assert "ساختار=" in dossier
    # compact micro must render real numbers, not dashes
    assert "POC=101" in dossier
    assert "جمع‌بندی فوت‌پرینت" in dossier


# --------------------------------------------------------------- integration
def test_smc_endpoint_includes_v2_packs(monkeypatch):
    items = trend_items(220)

    async def fake_fetch(symbol: str, market: str, timeframe: str):
        return items

    async def fake_orderflow(symbol: str, market: str, its: list[dict]):
        return {"source": "okx_swap_public", "is_real": True, "confidence": 0.9,
                "pressure": "buy", "spread_bps": 1.0, "depth_imbalance": 0.1, "funding_rate": 0.0001}

    async def fake_micro_none(*args, **kwargs):
        return None

    async def fake_news():
        return {"block": {"blocked": False}}

    async def fake_enrich(report, **kwargs):
        return report

    main._CANDLE_CACHE.clear()
    monkeypatch.setattr(main, "fetch_live_candles", fake_fetch)
    monkeypatch.setattr(main.orderflow_service, "get_snapshot", fake_orderflow)
    monkeypatch.setattr(main, "get_micro_summary", fake_micro_none)
    monkeypatch.setattr(main.ai_explainability_service, "enrich_report", fake_enrich)
    import app.news_engine_v2 as news_v2
    monkeypatch.setattr(news_v2, "build_news_brief", fake_news)

    resp = client.get("/api/v1/analysis/smc", params={"symbol": "BTCUSDT", "market": "crypto", "interval": "15m"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    ind = body.get("indicators_v2") or {}
    assert (ind.get("summary") or {}).get("available") is True
    strat = body.get("strategies_v2") or {}
    assert strat.get("available") is True
    assert strat["counts"]["active"] == len(strat["active"])
    ict = body.get("ict") or {}
    assert "market_structure" in ict and "ote" in ict and "killzone" in ict
