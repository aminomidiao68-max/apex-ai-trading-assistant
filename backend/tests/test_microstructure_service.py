"""Tests for the real microstructure service (L2 / Footprint / VP / Order Flow)."""
from __future__ import annotations

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from app.services import microstructure_service as ms
from app.services.microstructure_service import (
    MicrostructureService,
    apply_filters,
    build_ai_context_text,
    compact_micro,
    compute_flow_metrics,
    compute_footprint,
    compute_l2,
    compute_volume_profile,
    detect_symbol_from_text,
    norm_timeframe,
    resolve_instrument,
)


# --------------------------------------------------------------------- helpers
def make_trades(count: int = 300, base: float = 100.0, tf_ms: int = 60_000, start_ts: float = 1_700_000_000_000):
    """Synthetic trade tape: gentle uptrend with alternating taker sides."""
    trades = []
    ts = start_ts
    price = base
    for i in range(count):
        side = "buy" if i % 5 < 3 else "sell"  # 60% aggressive buys
        price = base + i * 0.01 + (0.02 if side == "buy" else -0.01)
        trades.append({"ts": ts + i * (tf_ms // count), "px": round(price, 4), "sz": 1.0 + (i % 7) * 0.25, "side": side, "tradeId": str(10_000 + i)})
    return trades


def make_book():
    bids = [[round(100 - i * 0.1, 2), 5.0] for i in range(200)]
    asks = [[round(100.1 + i * 0.1, 2), 5.0] for i in range(200)]
    bids[3][1] = 80.0  # engineered bid wall
    asks[4][1] = 90.0  # engineered ask wall
    return {"ts": 1_700_000_000_000, "bids": bids, "asks": asks}


# ------------------------------------------------------------ mapping helpers
def test_norm_timeframe_variants():
    assert norm_timeframe("5min") == "5m"
    assert norm_timeframe("60min") == "1h"
    assert norm_timeframe("15m") == "15m"
    assert norm_timeframe(None) == "15m"
    assert norm_timeframe("weird") == "15m"


def test_resolve_instrument_gold_proxy_and_crypto():
    gold = resolve_instrument("XAUUSD", "forex")
    assert gold is not None
    assert gold["inst_id"] == "PAXG-USDT"
    assert gold["proxy_for"] == "XAUUSD"
    crypto = resolve_instrument("BTCUSDT", "crypto")
    assert crypto["inst_id"] == "BTC-USDT-SWAP"
    assert resolve_instrument("USDJPY", "forex") is None


def test_detect_symbol_from_text():
    assert detect_symbol_from_text("وضعیت BTC چطوره؟") == "BTCUSDT"
    assert detect_symbol_from_text("تحلیل طلا XAUUSD بده") == "XAUUSD"
    assert detect_symbol_from_text("سلام") == ""


# ---------------------------------------------------------------- volume profile
def test_volume_profile_poc_and_value_area():
    trades = []
    price = 100.0
    for i in range(600):
        if i < 400:
            px = 100.0 + (i % 10) * 0.01  # heavy cluster around 100
        else:
            px = 101.0 + (i % 5) * 0.01
        trades.append({"px": px, "sz": 1.0, "side": "buy" if i % 2 else "sell", "ts": 1_700_000_000_000 + i})
    vp = compute_volume_profile(trades)
    assert vp["is_real"] is True
    assert vp["poc"] is not None
    assert vp["val"] <= vp["poc"] <= vp["vah"]
    # POC must sit inside (or at the edge of) the dominant cluster around 100.
    assert abs(vp["poc"] - 100.05) < 0.2
    assert 60 <= vp["value_area_volume_pct"] <= 85
    assert len(vp["bins"]) >= 5


# -------------------------------------------------------------------- footprint
def test_footprint_delta_rows_and_engineered_imbalance():
    tf_sec = 60
    base_ts = 1_700_000_000_000
    trades = []
    # Candle bucket 0: 12 consecutive price levels (one bin apart) where buys
    # dominate 9:1 on every level -> stacked buy diagonals.
    for level in range(12):
        for i in range(3):
            trades.append({"ts": base_ts + level * 3 + i, "px": round(100.0 + level * 0.005, 6), "sz": 9.0, "side": "buy", "tradeId": f"b{level}_{i}"})
            trades.append({"ts": base_ts + level * 3 + i, "px": round(100.0 + level * 0.005, 6), "sz": 1.0, "side": "sell", "tradeId": f"s{level}_{i}"})
    # Candle bucket 1 (next minute): mirrored sell dominance.
    ts2 = base_ts + tf_sec * 1000
    for level in range(12):
        for i in range(3):
            trades.append({"ts": ts2 + level * 3 + i, "px": round(101.0 + level * 0.005, 6), "sz": 9.0, "side": "sell", "tradeId": f"sb{level}_{i}"})
            trades.append({"ts": ts2 + level * 3 + i, "px": round(101.0 + level * 0.005, 6), "sz": 1.0, "side": "buy", "tradeId": f"ss{level}_{i}"})

    fp = compute_footprint(trades, tf_sec)
    assert fp["is_real"] is True
    assert fp["totals"]["candles_covered"] == 2
    deltas = [c["delta"] for c in fp["candles"]]
    assert deltas[0] > 0 and deltas[1] < 0
    assert fp["totals"]["cvd"] == pytest.approx(sum(deltas), abs=1e-3)
    # Every candle: rows ascending in price and delta consistency.
    for candle in fp["candles"]:
        prices = [row["p"] for row in candle["rows"]]
        assert prices == sorted(prices)
        assert candle["delta"] == pytest.approx(sum(r["d"] for r in candle["rows"]), abs=1e-3)
        assert candle["trades"] == 72
    # Engineered 9x diagonal imbalances must be detected and stacked (>= 3 runs).
    assert fp["totals"]["max_stacked_buy"] >= 3
    assert fp["totals"]["max_stacked_sell"] >= 3


def test_footprint_time_ordering():
    trades = make_trades(count=120, tf_ms=3_600_000)
    fp = compute_footprint(trades, 3_600)
    for candle in fp["candles"]:
        if candle["trades"] >= 2:
            assert candle["first"] <= candle["last"]


# ----------------------------------------------------------------------- L2
def test_compute_l2_bands_walls_spread():
    l2 = compute_l2(make_book())
    assert l2["is_real"] is True
    assert l2["mid"] == pytest.approx((100 + 100.1) / 2, abs=0.01)
    assert l2["spread_bps"] == pytest.approx(0.1 / 100 * 10_000, rel=0.01)
    top5 = l2["bands"]["top5"]
    assert top5["bid_notional"] > 0 and top5["ask_notional"] > 0
    assert -1 <= top5["imbalance"] <= 1
    # Engineered walls (>= 6x median) must be found on both sides.
    assert any(w["x_median"] >= 6 for w in l2["walls"]["bids"])
    assert any(w["x_median"] >= 6 for w in l2["walls"]["asks"])
    assert set(l2["liquidity_within_pct"].keys()) == {"0.1", "0.25", "0.5"}


# --------------------------------------------------------------------- flow
def test_flow_metrics_delta_pressure():
    trades = make_trades(count=300)
    flow = compute_flow_metrics(trades)
    assert flow["is_real"] is True
    assert flow["delta"] > 0  # 60% aggressive buys
    assert flow["pressure"] == "buy"
    assert flow["trades"] == 300
    assert len(flow["cvd_curve"]) >= 1
    assert flow["window_end_ts"] >= flow["window_start_ts"]


# ------------------------------------------------------------------ filters
def test_apply_filters_bullish_scenario():
    trades = make_trades(count=300)
    flow = compute_flow_metrics(trades)
    vp = compute_volume_profile(trades)
    l2 = compute_l2(make_book())
    fp = compute_footprint(trades, 60)
    price = flow["last_price"]
    filters = apply_filters(price, flow, vp, l2, fp)
    assert filters["net_bias"] == "bullish"
    assert filters["score"] > 0.18
    names = {row["name"] for row in filters["rows"]}
    assert {"delta", "l2_imbalance_top25", "footprint_stacked", "vp_position", "cvd_divergence"} <= names


def test_apply_filters_bearish_scenario():
    sells = [{"ts": 1_700_000_000_000 + i, "px": 100 - i * 0.01, "sz": 5.0, "side": "sell", "tradeId": str(i)} for i in range(200)]
    flow = compute_flow_metrics(sells)
    assert flow["delta"] < -0.9
    assert flow["pressure"] == "sell"
    vp = compute_volume_profile(sells)
    l2 = compute_l2(make_book())
    fp = compute_footprint(sells, 60)
    filters = apply_filters(flow["last_price"], flow, vp, l2, fp)
    assert filters["net_bias"] in ("bearish", "neutral")
    assert filters["score"] < 0


# -------------------------------------------------------------------- views
def test_compact_micro_and_ai_context_real_payload():
    trades = make_trades(count=300)
    flow = compute_flow_metrics(trades)
    vp = compute_volume_profile(trades)
    l2 = compute_l2(make_book())
    fp = compute_footprint(trades, 60)
    payload = {
        "symbol": "XAUUSD",
        "timeframe": "15m",
        "source": "okx_public",
        "is_real": True,
        "confidence": 0.8,
        "instrument": {"inst_id": "PAXG-USDT", "inst_type": "SPOT", "proxy_for": "XAUUSD", "note": "proxy"},
        "window": {"start_ts": 1, "end_ts": 2, "covered_seconds": 900, "requested_seconds": 900, "full_coverage": True, "trades": 300},
        "order_flow": flow,
        "volume_profile": vp,
        "footprint": fp,
        "level2": l2,
        "filters": apply_filters(flow["last_price"], flow, vp, l2, fp),
        "cached": False,
        "cache_age_seconds": 0.0,
    }
    compact = compact_micro(payload)
    assert compact["is_real"] is True
    assert compact["vp"]["poc"] is not None
    assert "filters" in compact and compact["filters"]["net_bias"] == "bullish"

    text = build_ai_context_text(payload)
    assert "POC" in text
    assert "PAXG-USDT" in text
    assert "فیلترهای قطعی" in text


def test_ai_context_fallback_is_honest():
    fallback = {"is_real": False, "source": "ohlcv_kline_proxy"}
    text = build_ai_context_text(fallback)
    assert "در دسترس نیست" in text


# ------------------------------------------------------------------ service
def test_service_kline_fallback_for_fx_without_instrument():
    svc = MicrostructureService()
    payload = svc._kline_fallback("USDJPY", "forex", "15m", [], reason="no_real_instrument")
    assert payload["is_real"] is False
    assert payload["fallback_reason"] == "no_real_instrument"
    compact = compact_micro(payload)
    assert compact["is_real"] is False
    assert compact["filters"]["net_bias"] == "neutral"


# ---------------------------------------------------------------- endpoint
def test_microstructure_endpoint(monkeypatch):
    from fastapi.testclient import TestClient
    from app import main as main_module

    async def fake_get(symbol, market, timeframe, candles=None, compact=False):
        return {
            "is_real": True,
            "source": "okx_public",
            "confidence": 0.8,
            "timeframe": "15m",
            "filters": {"net_bias": "bullish", "score": 0.4, "rows": []},
        }

    monkeypatch.setattr(main_module.microstructure_service, "get_microstructure", fake_get)
    client = TestClient(main_module.app)
    response = client.get("/api/v1/microstructure/BTCUSDT", params={"timeframe": "15m", "compact": "true"})
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "BTCUSDT"
    assert body["microstructure"]["filters"]["net_bias"] == "bullish"


# ------------------------------------------------------- database fallback fix
def test_database_fallback_uses_local_sqlite_path(monkeypatch, tmp_path):
    from app.services import database_service as dbs

    real_migrate = dbs.DatabaseManager.migrate

    def fake_migrate(self):
        if self.backend == "postgresql":
            raise RuntimeError("pg down")
        return real_migrate(self)

    monkeypatch.setattr(dbs.DatabaseManager, "migrate", fake_migrate)
    manager = dbs.DatabaseManager(database_url="postgresql://user:pass@localhost:5432/apex")
    assert manager.backend == "sqlite"
    assert manager.sqlite_path is not None
    assert manager.sqlite_path.endswith("smartmoney.db")
    assert not manager.sqlite_path.startswith("postgresql")


# ------------------------------------------------------ reasoning strip (fa UI)
def test_strip_reasoning_blocks_removes_think_chain():
    from app.main import _strip_reasoning_blocks

    leaked = "<think>\nHere's a thinking process in English...\n</think>\n\n✨ تحلیل نهایی فارسی چارت"
    assert _strip_reasoning_blocks(leaked) == "✨ تحلیل نهایی فارسی چارت"
    assert _strip_reasoning_blocks("<think>truncated without close") == ""
    assert _strip_reasoning_blocks("پاسخ معمولی") == "پاسخ معمولی"
    assert _strip_reasoning_blocks(None) == ""


def test_ai_payload_extra_hides_reasoning_only_for_reasoning_models():
    from app.main import _ai_payload_extra

    assert _ai_payload_extra("qwen/qwen3.6-27b") == {"reasoning_format": "hidden"}
    assert _ai_payload_extra("openai/gpt-oss-120b") == {"reasoning_format": "hidden"}
    assert _ai_payload_extra("llama-3.3-70b-versatile") == {}
    assert _ai_payload_extra("meta-llama/llama-4-scout-17b-16e-instruct") == {}


# ------------------------------------------- self-adaptive Groq model selection
def test_model_options_groq_prefers_live_models(monkeypatch):
    import asyncio
    from app import main as main_module

    async def fake_live(api_key, base_url):
        return [
            "whisper-large-v3",
            "llama-3.1-8b-instant",
            "openai/gpt-oss-120b",
            "qwen/qwen3.6-27b",
            "qwen/qwen3.8-27b",
        ]

    monkeypatch.setattr(main_module, "_groq_available_models", fake_live)
    cand = {"api_key": "k", "base_url": "https://api.groq.com/openai/v1", "model": "", "is_groq": True}
    vision = asyncio.run(main_module._model_options_for(cand, kind="vision"))
    assert vision[0] == "qwen/qwen3.8-27b"
    assert all("gpt-oss" not in m for m in vision)  # text-only filtered out for vision
    chat = asyncio.run(main_module._model_options_for(cand, kind="chat"))
    assert chat[0] == "openai/gpt-oss-120b"
    assert "whisper-large-v3" not in chat


def test_model_options_fallback_when_discovery_empty(monkeypatch):
    import asyncio
    from app import main as main_module

    async def fake_live(api_key, base_url):
        return []

    monkeypatch.setattr(main_module, "_groq_available_models", fake_live)
    cand = {"api_key": "k", "base_url": "u", "model": "", "is_groq": True}
    vision = asyncio.run(main_module._model_options_for(cand, kind="vision"))
    assert vision == ["qwen/qwen3.8-27b", "qwen/qwen3.6-27b"]
    chat = asyncio.run(main_module._model_options_for(cand, kind="chat"))
    assert chat[0] == "openai/gpt-oss-120b"


def test_model_options_openai_uses_configured(monkeypatch):
    import asyncio
    from app import main as main_module

    cand = {"api_key": "k", "base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini", "is_groq": False}
    assert asyncio.run(main_module._model_options_for(cand, kind="vision")) == ["gpt-4o-mini"]


# ------------------------------------- fundamental upgrade: micro confluence etc
def _compact_fixture():
    return {
        "is_real": True,
        "full_coverage": True,
        "filters": {"net_bias": "bullish", "score": 0.5, "signals": ["delta:buy_pressure"]},
        "flow": {"cvd_divergence": "bullish", "pressure": "buy"},
        "footprint": {"stacked_buy": 3, "stacked_sell": 0},
        "vp": {"poc": 100.5, "vah": 101.0, "val": 100.0},
        "l2": {"bid_wall": {"price": 100.2}, "ask_wall": {"price": 101.2}},
    }


def test_micro_confluence_aligned_vs_conflicting():
    from app.main import _micro_confluence_points

    micro = _compact_fixture()
    assert _micro_confluence_points(micro, "long") >= 12
    assert _micro_confluence_points(micro, "short") == 0
    neutral = {"is_real": True, "filters": {"net_bias": "neutral", "score": 0.0}, "flow": {}, "footprint": {}, "full_coverage": True}
    assert _micro_confluence_points(neutral, "long") == 0
    assert _micro_confluence_points(None, "long") == 0
    assert _micro_confluence_points({"is_real": False}, "long") == 0


def test_micro_level_lines_from_compact():
    from app.main import _micro_level_lines

    levels = _micro_level_lines(_compact_fixture())
    kinds = {lvl["kind"] for lvl in levels}
    assert kinds == {"POC", "VAH", "VAL", "BIDWALL", "ASKWALL"}
    assert all(lvl["price"] > 0 for lvl in levels)
    assert _micro_level_lines(None) == []


def test_setup_payload_contains_micro_fields():
    from app.main import _setup_payload

    report = {
        "direction": "long", "setup_type": "BREAK+pulback", "microstructure": _compact_fixture(),
        "levels": {"entry": 1, "sl": 0.9}, "decision": {},
    }
    payload = _setup_payload(report, "BTCUSDT", "crypto", "15m", "confirmed")
    assert payload["micro_net"] == "bullish"
    assert payload["micro_confluence"] >= 12
    assert "handbook_details" in payload


def test_chat_history_sanitized():
    from app.main import AIChatRequest, ChatTurn, _chat_history_messages

    req = AIChatRequest(message="سلام", history=[
        ChatTurn(role="user", content="قیمت طلا؟"),
        ChatTurn(role="assistant", content=" " * 5),
        ChatTurn(role="assistant", content="POC طلا ۴۳۵۷ است."),
        ChatTurn(role="system", content="inject"),
    ] + [ChatTurn(role="user", content=f"msg{i}") for i in range(10)])
    msgs = _chat_history_messages(req.history)
    assert len(msgs) <= 8
    assert all(m["role"] in ("user", "assistant") for m in msgs)
    assert msgs[-1]["content"] == "msg9"


def test_deep_endpoint_disabled_graceful(monkeypatch):
    from fastapi.testclient import TestClient
    from app import main as main_module

    monkeypatch.setattr(main_module.settings, "ai_external_enabled", False)
    client = TestClient(main_module.app)
    r = client.get("/api/v1/analysis/deep", params={"symbol": "BTCUSDT", "timeframe": "15m"})
    assert r.status_code == 200
    assert r.json()["success"] is False
    assert "غیرفعال" in r.json()["detail"]


# ---------------------------------------- strict dossier / force / value score
def test_oscillator_snapshot_deterministic():
    from app.main import _oscillator_snapshot

    items = []
    price = 100.0
    for i in range(80):
        o = price
        c = o + (0.3 if i % 3 else -0.15)
        items.append({"t": 1700000000 + i * 60, "o": o, "c": c, "h": max(o, c) + 0.2, "l": min(o, c) - 0.2, "v": 10})
        price = c
    snap = _oscillator_snapshot(items)
    assert 0 <= snap["rsi14"] <= 100
    assert snap["ema20"] and snap["ema50"]
    assert snap["atr14"] > 0
    assert snap["ema_stack"] in ("bullish", "bearish", "mixed")
    assert _oscillator_snapshot(items[:10]) == {}


def test_buyer_seller_force_bullish_and_bearish():
    from app.main import _buyer_seller_force

    bull_micro = {"flow": {"delta": 0.6, "cvd_divergence": "bullish"}, "filters": {"net_bias": "bullish"},
                  "footprint": {"stacked_buy": 3, "stacked_sell": 0}, "l2": {"imbalance_top25": 0.4}}
    force = _buyer_seller_force({}, bull_micro)
    assert force["buyers_pct"] >= 70 and force["label"] == "buyers_dominant"
    assert abs(force["buyers_pct"] + force["sellers_pct"] - 100) < 0.01

    bear_micro = {"flow": {"delta": -0.7, "cvd_divergence": "bearish"}, "filters": {"net_bias": "bearish"},
                  "footprint": {"stacked_buy": 0, "stacked_sell": 4}, "l2": {"imbalance_top25": -0.5}}
    assert _buyer_seller_force({}, bear_micro)["buyers_pct"] <= 30


def test_liquidity_gaps_and_dossier():
    from app.main import build_market_dossier, _numbered_liquidity, _gap_list, _top_order_blocks

    report = {
        "bias": "bearish", "htf": {"bias": "bearish"}, "premium_zone": "premium",
        "price": 4350.0, "inducements": [{"kind": "eqh", "price": 4360.5, "dir": "sell"}],
        "fvg": [{"top": 4355.0, "bottom": 4352.0, "side": "bearish", "fresh": True}],
        "order_blocks": [{"top": 4358.0, "bottom": 4356.0, "side": "bearish", "quality": 7}],
        "events": [{"kind": "choch", "price": 4351.0}], "action_label": "NO_TRADE", "grade": "F",
        "direction": "neutral", "confluence": 30, "probability": 35, "rr": 0,
        "levels": {"entry": None, "sl": None}, "force": {"buyers_pct": 40, "sellers_pct": 60, "label": "sellers_dominant"},
    }
    micro = {"is_real": True, "vp": {"poc": 4357.0, "vah": 4359.0, "val": 4355.0}, "flow": {"delta": -0.2},
             "footprint": {"stacked_buy": 0, "stacked_sell": 2}, "l2": {"imbalance_top25": -0.2},
             "filters": {"net_bias": "bearish", "score": -0.3}, "timeframe": "15m",
             "instrument": {"inst_id": "PAXG-USDT"}, "window": {"trades": 500}}
    assert _numbered_liquidity(report)[0]["price"] == 4360.5
    assert _gap_list(report)[0]["top"] == 4355.0
    assert _top_order_blocks(report)[0]["quality"] == 7

    dossier = build_market_dossier(report, micro, [])
    for token in ("نقدینگی", "FVG", "خریدار=", "NO_TRADE", "اندیکاتورها", "4360.5", "4355"):
        assert token in dossier, token
    assert "اجازه ورود نداده" in dossier


def test_setup_value_score_and_prime():
    from app.main import _setup_payload

    report = {
        "direction": "long", "setup_type": "BREAK+pulback", "grade": "A+",
        "confluence": 80, "probability": 70, "rr": 2.5,
        "microstructure": _compact_fixture(),
        "levels": {"entry": 1, "sl": 0.9}, "decision": {},
    }
    payload = _setup_payload(report, "BTCUSDT", "crypto", "15m", "confirmed")
    assert payload["is_prime"] is True
    assert payload["value_score"] >= 70
    weak = _setup_payload({**report, "grade": "C", "confluence": 45, "rr": 1.0, "microstructure": {"is_real": False}},
                          "BTCUSDT", "crypto", "15m", "forming")
    assert weak["is_prime"] is False and weak["value_score"] < payload["value_score"]
