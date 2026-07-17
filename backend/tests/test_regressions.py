from __future__ import annotations

import asyncio
import math
import os
import tempfile
from datetime import datetime, timedelta, timezone
from uuid import uuid4

# Set an isolated database before importing app.main and its singleton services.
_TEST_DB_DIR = tempfile.mkdtemp(prefix="apex-tests-")
os.environ["DATABASE_PATH"] = os.path.join(_TEST_DB_DIR, "regressions.db")
os.environ["APP_ENV"] = "test"
os.environ["SEED_DEMO_USER"] = "false"
os.environ.pop("CORS_ALLOWED_ORIGINS", None)

from fastapi.testclient import TestClient

import app.main as main
from app.models import Candle


client = TestClient(main.app, raise_server_exceptions=True)


def _candles(count: int = 190) -> list[Candle]:
    start = datetime(2026, 7, 10, tzinfo=timezone.utc)
    items = []
    for index in range(count):
        close = 100 + index * 0.08 + math.sin(index / 5) * 0.35
        open_price = close - 0.12 * math.sin(index)
        items.append(
            Candle(
                timestamp=start + timedelta(minutes=15 * index),
                open=open_price,
                high=max(open_price, close) + 0.4,
                low=min(open_price, close) - 0.4,
                close=close,
                volume=1000 + index * 5,
            )
        )
    return items


def _register() -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Regression User",
            "email": f"regression-{uuid4().hex}@example.com",
            "password": "StrongPass123!",
        },
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_signal_and_backtest_endpoints_no_longer_return_500(monkeypatch):
    candles = _candles()

    async def fake_fetch(symbol: str, market: str, timeframe: str):
        return candles

    monkeypatch.setattr(main, "fetch_live_candles", fake_fetch)
    auth = _register()

    analyze_payload = {
        "symbol": "BTCUSDT",
        "market": "crypto",
        "timeframe": "15m",
        "candles": [c.model_dump(mode="json") for c in candles[-60:]],
    }
    assert client.post("/api/v1/signals/analyze", json=analyze_payload, headers=auth).status_code == 200
    assert client.post(
        "/api/v1/signals/live-scan",
        json={"symbol": "BTCUSDT", "market": "crypto"},
        headers=auth,
    ).status_code == 200

    run_payload = {
        "symbol": "BTCUSDT",
        "market": "crypto",
        "window_size": 20,
        "lookahead_candles": 2,
        "score_threshold": 65,
        "max_signals": 5,
    }
    assert client.post("/api/v1/backtest/run", json=run_payload, headers=auth).status_code == 200

    sweep_payload = {
        "symbol": "BTCUSDT",
        "market": "crypto",
        "window_sizes": [20],
        "lookahead_options": [2],
        "score_thresholds": [65],
        "take_profit_indices": [0],
        "max_signals": 5,
        "max_results": 3,
    }
    assert client.post("/api/v1/backtest/sweep", json=sweep_payload, headers=auth).status_code == 200

    walk_payload = {
        "symbol": "BTCUSDT",
        "market": "crypto",
        "train_window": 40,
        "test_window": 10,
        "step_size": 5,
        "window_sizes": [20],
        "lookahead_options": [2],
        "score_thresholds": [65],
        "take_profit_indices": [0],
        "max_signals": 5,
        "max_steps": 1,
    }
    assert client.post("/api/v1/backtest/walk-forward", json=walk_payload, headers=auth).status_code == 200


def test_provider_errors_never_expose_api_keys(monkeypatch):
    async def failing_provider(*args, **kwargs):
        raise RuntimeError("https://provider.invalid/path?apikey=TOP_SECRET_VALUE")

    main._CANDLE_CACHE.clear()
    monkeypatch.setattr(main.market_data, "fetch_forex_candles", failing_provider)
    response = client.get(
        "/api/v1/analysis/smc",
        params={"symbol": "EURUSD", "market": "forex", "interval": "30m"},
    )
    assert response.status_code == 200
    body = response.text.lower()
    assert "top_secret_value" not in body
    assert "apikey=" not in body
    assert "provider_unavailable" in body


def test_setup_state_machine_lifecycle_and_cooldown():
    from datetime import datetime, timedelta, timezone
    from app.services.setup_state_engine import SetupStateEngine

    engine = SetupStateEngine()
    now = datetime(2026, 7, 13, 10, 0, tzinfo=timezone.utc)
    base = {
        "id": "BTCUSDT:15m:long:test",
        "symbol": "BTCUSDT",
        "market": "crypto",
        "timeframe": "15m",
        "status": "forming",
        "setup_type": "test",
        "direction": "long",
        "price": 110.0,
        "entry": 100.0,
        "entry_low": 99.0,
        "entry_high": 101.0,
        "stop_loss": 95.0,
        "invalidation": 95.0,
        "confluence": 50,
        "probability": 60,
        "rr": 2.2,
        "omega_compliant": False,
        "data_quality": {"score": 80},
        "decision": {"hard_gates_passed": 5, "hard_gates_total": 10, "expires_after_bars": 5},
    }
    first = engine.update([base], {"BTCUSDT:15m": 110.0}, now)
    assert len(first["forming"]) == 1

    armed = {**base, "decision": {**base["decision"], "hard_gates_passed": 8}}
    second = engine.update([armed], {"BTCUSDT:15m": 108.0}, now + timedelta(minutes=1))
    assert len(second["armed"]) == 1

    confirmed = {
        **armed,
        "status": "confirmed",
        "omega_compliant": True,
        "confluence": 75,
        "probability": 75,
        "decision": {**armed["decision"], "hard_gates_passed": 10},
    }
    third = engine.update([confirmed], {"BTCUSDT:15m": 108.0}, now + timedelta(minutes=2))
    assert len(third["confirmed"]) == 1

    triggered_candidate = {**confirmed, "price": 100.0}
    fourth = engine.update(
        [triggered_candidate], {"BTCUSDT:15m": 100.0}, now + timedelta(minutes=3)
    )
    assert len(fourth["triggered"]) == 1
    assert fourth["triggered"][0]["transition_reason"] == "price_entered_entry_zone"

    invalidated_candidate = {**confirmed, "price": 94.0}
    fifth = engine.update(
        [invalidated_candidate], {"BTCUSDT:15m": 94.0}, now + timedelta(minutes=4)
    )
    assert len(fifth["invalidated"]) == 1
    assert fifth["invalidated"][0]["cooldown_until"] is not None

    cooldown = engine.update([confirmed], {"BTCUSDT:15m": 110.0}, now + timedelta(minutes=5))
    assert len(cooldown["invalidated"]) == 1
    assert not cooldown["confirmed"]


def test_trade_setup_scanner_covers_matrix_and_uses_cache(monkeypatch):
    candles = _candles(260)

    async def fake_fetch(symbol: str, market: str, timeframe: str):
        return candles

    async def fake_orderflow(symbol: str, market: str, items: list[dict]):
        if market == "crypto":
            return {
                "source": "okx_swap_public", "is_real": True, "confidence": 0.92,
                "pressure": "buy", "spread_bps": 1.0, "depth_imbalance": 0.1,
                "funding_rate": 0.0001,
            }
        return {
            "source": "forex_ohlcv_proxy", "is_real": False, "confidence": 0.42,
            "pressure": "buy", "spread_bps": None, "depth_imbalance": None,
        }

    monkeypatch.setattr(main, "fetch_live_candles", fake_fetch)
    monkeypatch.setattr(main.orderflow_service, "get_snapshot", fake_orderflow)
    main._SETUP_SCAN_CACHE["timestamp"] = 0.0
    main._SETUP_SCAN_CACHE["payload"] = None
    response = asyncio.run(main.scan_trade_setups(force=True))
    assert response["total_scanned"] == 70
    assert response["confirmed_count"] == len(response["confirmed"])
    assert response["forming_count"] == len(response["forming"])
    assert response["armed_count"] == len(response["armed"])
    assert response["triggered_count"] == len(response["triggered"])
    assert response["active_count"] == len(response["active"])
    assert all(item["lifecycle_state"] == "confirmed" for item in response["confirmed"])
    assert all(item["lifecycle_state"] == "forming" for item in response["forming"])
    assert all(item["lifecycle_state"] == "armed" for item in response["armed"])
    all_items = response["forming"] + response["armed"] + response["active"]
    assert all(item["setup_type"] not in ("", "-") for item in all_items)

    cached = asyncio.run(main.scan_trade_setups(force=False))
    assert cached["cached"] is True
    assert cached["total_scanned"] == 70
    cooldown = asyncio.run(main.scan_trade_setups(force=True))
    assert cooldown["cached"] is True
    assert cooldown["refresh_cooldown"] is True


def test_risk_direction_validation():
    settings = {
        "account_balance": 10000,
        "risk_per_trade_pct": 0.5,
        "max_daily_loss_pct": 3,
        "max_trades_per_day": 4,
        "max_consecutive_losses": 3,
        "max_open_positions": 2,
        "value_per_point": 1,
        "breakeven_rr": 1,
        "partial_tp_rr": [1, 2, 3],
    }
    invalid_cases = [
        {"entry_price": 100, "stop_loss": 101, "direction": "buy"},
        {"entry_price": 100, "stop_loss": 99, "direction": "sell"},
        {"entry_price": 100, "stop_loss": 99, "direction": "neutral"},
    ]
    for case in invalid_cases:
        response = client.post(
            "/api/v1/risk/plan",
            json={**case, "risk_settings": settings, "trade_stats": {}},
        )
        assert response.status_code == 200
        assert response.json()["is_trade_allowed"] is False
        assert response.json()["position_size_units"] == 0


def test_smc_htf_alignment_uses_trade_direction_and_range_does_not_clip(monkeypatch):
    import app.services.smc_engine as smc

    candles = [
        {
            "t": candle.timestamp.timestamp(),
            "o": candle.open,
            "h": candle.high,
            "l": candle.low,
            "c": candle.close,
            "v": candle.volume,
        }
        for candle in _candles(80)
    ]
    price = candles[-1]["c"]
    forced_long_setup = {
        "type": "continuation_fvg",
        "direction": smc.LONG,
        "entry": price,
        "entry_low": price - 0.1,
        "entry_high": price + 0.1,
        "sl": price - 1.0,
        "tp1": price + 1.3,
        "tp2": price + 2.4,
        "tp3": price + 3.8,
        "invalidation": price - 1.0,
        "ob_quality": 0,
        "fvg_quality": 5,
        "in_ote": False,
        "poi_count": 1,
        "poi_reasons": ["FVG"],
        "risk": 1.0,
        "rr": 2.4,
        "base_prob": 70,
        "vwap_above": True,
        "disp_strength": 5,
    }
    monkeypatch.setattr(smc, "_detect", lambda *args, **kwargs: forced_long_setup.copy())

    report = smc.analyze(candles, symbol="TEST", timeframe="15m", htf_bias="bearish")
    assert report["mtf_aligned"] is False
    assert not any(factor["name"] == "همراستایی با HTF" for factor in report["confluence_factors"])
    assert report["visible_range"]["low"] <= min(item["l"] for item in candles)
    assert report["visible_range"]["high"] >= max(item["h"] for item in candles)


def test_fresh_signal_notification_is_callable_and_user_scoped(tmp_path):
    import sqlite3

    from app.models import (
        DeviceTokenRegisterRequest,
        MarketType,
        SignalDirection,
        SignalHistoryItem,
    )
    from app.services.notification_service import NotificationService
    from app.services.storage_service import StorageService

    storage = StorageService(db_path=str(tmp_path / "notifications.db"))
    storage.register_device_token(
        1, DeviceTokenRegisterRequest(token="user_one_device_token_1234567890")
    )
    storage.register_device_token(
        2, DeviceTokenRegisterRequest(token="user_two_device_token_1234567890")
    )
    signal = SignalHistoryItem(
        id=1,
        symbol="BTCUSDT",
        market=MarketType.crypto,
        timeframe="15m",
        direction=SignalDirection.buy,
        score=80,
        confidence="high",
        session_name="London",
        news_blocked=False,
        take_profits=[],
        setup_grade="A",
        execution_label="execution_ready",
        reasons=[],
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    NotificationService(storage).try_send_fresh_signal_alert(signal, user_id=1)

    with sqlite3.connect(storage.db_path) as connection:
        rows = connection.execute(
            "SELECT user_id FROM notification_events ORDER BY user_id"
        ).fetchall()
    assert rows == [(1,)]


def test_real_crypto_orderflow_and_honest_forex_proxy():
    from app.services.orderflow_service import analyze_okx_payloads, build_ohlcv_proxy

    trades = []
    for index in range(100):
        side = "buy" if index < 65 else "sell"
        trades.append({
            "side": side,
            "sz": "2" if side == "buy" else "1",
            "px": str(100 + index * 0.01),
            "ts": str(1_700_000_000_000 + index * 100),
        })
    depth = {
        "bids": [["100.00", "10", "0", "2"], ["99.99", "8", "0", "2"]],
        "asks": [["100.01", "5", "0", "2"], ["100.02", "4", "0", "2"]],
    }
    snapshot = analyze_okx_payloads(
        trades,
        depth,
        {"oi": "1000", "oiUsd": "1000000"},
        {"fundingRate": "0.0001"},
        previous_oi=(0.0, 990000.0),
    )
    assert snapshot["is_real"] is True
    assert snapshot["source"] == "okx_swap_public"
    assert snapshot["pressure"] == "buy"
    assert snapshot["delta"] > 0
    assert snapshot["depth_imbalance"] > 0
    assert snapshot["spread_bps"] < 2
    assert snapshot["open_interest_change_pct"] > 0

    candles = [
        {"t": item.timestamp.timestamp(), "o": item.open, "h": item.high,
         "l": item.low, "c": item.close, "v": item.volume}
        for item in _candles(80)
    ]
    proxy = build_ohlcv_proxy(candles, "forex_ohlcv_proxy", "forex")
    assert proxy["is_real"] is False
    assert proxy["source"] == "forex_ohlcv_proxy"
    assert "not centralized" in proxy["disclaimer"].lower()
    assert proxy["depth_imbalance"] is None


def test_market_quality_and_strict_decision_gates():
    from app.services.market_quality_engine import assess_data_quality, classify_market_regime
    from app.services.strict_decision_engine import apply_strict_decision

    candles_model = _candles(160)
    candles = [
        {
            "t": item.timestamp.timestamp(), "o": item.open, "h": item.high,
            "l": item.low, "c": item.close, "v": item.volume,
        }
        for item in candles_model
    ]
    quality = assess_data_quality(candles, "15m", "crypto")
    assert quality["score"] >= 95
    assert quality["tradable"] is True
    assert classify_market_regime(candles)["name"] in {
        "trending", "balanced", "volatile", "compressed", "choppy"
    }

    report = {
        "direction": "long",
        "grade": "A",
        "confluence": 82,
        "probability": 79,
        "rr": 2.5,
        "htf_bias": "bullish",
        "setup_type": "پولبک BOS به ناحیه OTE",
        "events": [{"kind": "BOS", "dir": "bullish"}],
        "news_blocked": False,
        "invalidation": 98.0,
        "plan_lines": [{"kind": "entry", "price": 100.0}],
        "overlay": {"lines": [{"kind": "entry", "price": 100.0}]},
        "confluence_factors": [
            {"name": "HTF alignment", "points": 12},
            {"name": "minor conflict", "points": -2},
        ],
        "orderflow": {},
        "ai": {},
        "omega_compliant": True,
    }
    real_flow = {
        "source": "okx_swap_public",
        "is_real": True,
        "confidence": 0.92,
        "pressure": "buy",
        "spread_bps": 1.2,
        "depth_imbalance": 0.12,
        "funding_rate": 0.0001,
    }
    strict = apply_strict_decision(
        report,
        candles,
        "crypto",
        "15m",
        orderflow_source="okx_swap_public",
        orderflow_confidence=0.92,
        orderflow_snapshot=real_flow,
    )
    assert strict["decision"]["status"] == "actionable"
    assert strict["omega_compliant"] is True
    assert strict["action_label"] == "STRONG_LONG"
    assert strict["decision"]["probability_is_calibrated"] is False
    assert strict["ai"]["provider"] == "deterministic"
    assert strict["ai"]["verified"] is True
    assert strict["ai"]["grounded"] is True
    assert strict["ai"]["deterministic_core_preserved"] is True
    assert strict["ai"]["probability_label"] == "model_estimate_not_calibrated"
    assert strict["ai"]["evidence_items"]
    assert strict["ai"]["negative_evidence"]

    weak = dict(report)
    weak["confluence"] = 45
    weak["probability"] = 55
    weak["plan_lines"] = [{"kind": "entry", "price": 100.0}]
    weak["overlay"] = {"lines": [{"kind": "entry", "price": 100.0}]}
    downgraded = apply_strict_decision(
        weak,
        candles,
        "crypto",
        "15m",
        orderflow_source="okx_swap_public",
        orderflow_confidence=0.92,
        orderflow_snapshot=real_flow,
    )
    assert downgraded["decision"]["status"] == "watch"
    assert downgraded["omega_compliant"] is False
    assert downgraded["plan_lines"] == []

    proxy_candidate = dict(report)
    proxy_candidate["plan_lines"] = [{"kind": "entry", "price": 100.0}]
    proxy_candidate["overlay"] = {"lines": [{"kind": "entry", "price": 100.0}]}
    proxy_result = apply_strict_decision(
        proxy_candidate,
        candles,
        "crypto",
        "15m",
        orderflow_source="crypto_ohlcv_fallback",
        orderflow_confidence=0.30,
        orderflow_snapshot={
            "source": "crypto_ohlcv_fallback",
            "is_real": False,
            "confidence": 0.30,
            "pressure": "buy",
        },
    )
    assert proxy_result["omega_compliant"] is False
    assert "real_orderflow_available" in proxy_result["decision"]["failed_gates"]


def test_chart_window_rebases_all_overlay_indices():
    items = [
        {"t": float(index), "o": 100.0, "h": 101.0, "l": 99.0, "c": 100.5, "v": 1.0}
        for index in range(260)
    ]
    report = {
        "events": [{"index": 210, "kind": "BOS"}],
        "order_blocks": [{"index": 20, "kind": "bullish"}],
        "fvg": [{"index": 220, "kind": "bullish"}],
        "breakers": [{"index": 30, "kind": "bearish"}],
        "inducements": [{"index": 230, "kind": "eqh"}],
        "killzones": [{"index": 200, "start_idx": 200, "end_idx": 220, "kind": "KZ"}],
        "overlay": {
            "lines": [],
            "labels": [{"index": 210, "kind": "BOS"}],
            "zones": [
                {"index": 200, "start_idx": 200, "end_idx": 220, "kind": "KZ"},
                {"index": 20, "kind": "OB"},
                {"index": 220, "kind": "FVG"},
            ],
        },
    }
    prepared = main._prepare_chart_report(report, items, max_candles=160)
    assert len(prepared["candles"]) == 160
    assert prepared["events"][0]["index"] == 110
    assert prepared["order_blocks"][0]["index"] == 0
    assert prepared["fvg"][0]["index"] == 120
    assert prepared["killzones"][0]["start_idx"] == 100
    assert prepared["killzones"][0]["end_idx"] == 120
    for collection in (
        prepared["events"], prepared["order_blocks"], prepared["fvg"],
        prepared["breakers"], prepared["inducements"], prepared["overlay"]["labels"],
        prepared["overlay"]["zones"],
    ):
        assert all(0 <= item["index"] < 160 for item in collection)
    assert len(prepared["killzones"]) <= 2
    assert all(item["kind"] in ("KZ", "OB", "FVG", "iFVG", "BRK") for item in prepared["overlay"]["zones"])
    assert len([item for item in prepared["overlay"]["zones"] if item["kind"] == "OB"]) <= 2
    assert len([item for item in prepared["overlay"]["zones"] if item["kind"] in ("FVG", "iFVG")]) <= 2
    assert len([item for item in prepared["overlay"]["zones"] if item["kind"] == "BRK"]) <= 1
    assert all(item.get("end_idx", 159) >= item["index"] for item in prepared["overlay"]["zones"] if item["kind"] != "KZ")


def test_timeframe_mapping_aggregation_and_high_tf_killzones():
    from app.services.market_data_service import MarketDataService
    from app.services.smc_engine import _sessions, _zone_return_index

    service = MarketDataService()
    assert service._normalize_twelvedata_interval("1d") == "1day"
    assert service._yahoo_interval("4h") == ("60m", "1y", 4 * 3600)
    source = _candles(16)
    aggregated = service.aggregate_candles(source, 4 * 15 * 60)
    assert len(aggregated) == 4
    assert aggregated[0].open == source[0].open
    assert aggregated[0].close == source[3].close
    assert aggregated[0].high == max(item.high for item in source[:4])
    assert aggregated[0].low == min(item.low for item in source[:4])

    raw = [
        {"t": item.timestamp.timestamp(), "o": item.open, "h": item.high,
         "l": item.low, "c": item.close, "v": item.volume}
        for item in _candles(260)
    ]
    assert _sessions(raw, "4h") == ([], [])
    zones, _ = _sessions(raw, "15m")
    assert len(zones) <= 6

    zone_candles = [
        {"h": 105.0, "l": 103.0},
        {"h": 104.0, "l": 102.0},
        {"h": 101.0, "l": 99.5},
        {"h": 100.0, "l": 98.0},
    ]
    assert _zone_return_index(
        zone_candles, start_index=0, top=101.0, bottom=99.0, search_from=1
    ) == 2


def test_user_data_isolation_delete_and_openapi_security():
    first = _register()
    second = _register()
    trade = {
        "symbol": "BTCUSDT",
        "market": "crypto",
        "direction": "buy",
        "entry_price": 100,
        "stop_loss": 99,
        "take_profit": 102,
        "size": 1,
        "notes": "isolation regression",
    }
    created = client.post("/api/v1/trades", json=trade, headers=first)
    assert created.status_code == 200
    trade_id = created.json()["id"]

    assert client.get("/api/v1/trades").status_code == 401
    second_items = client.get("/api/v1/trades", headers=second)
    assert second_items.status_code == 200
    assert second_items.json()["items"] == []
    assert client.post(
        f"/api/v1/trades/{trade_id}/close",
        json={"exit_price": 102},
        headers=second,
    ).status_code == 404
    assert client.delete(f"/api/v1/trades/{trade_id}", headers=first).status_code == 200

    openapi = client.get("/openapi.json").json()
    assert openapi["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"

    preflight = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert preflight.headers.get("access-control-allow-origin") is None

    health = client.get("/health")
    assert health.headers["x-content-type-options"] == "nosniff"
    assert health.headers["x-frame-options"] == "DENY"
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "invalid-password"},
    )
    assert login.headers["cache-control"] == "no-store"


def test_ai_explainability_endpoint_is_grounded_and_secret_safe():
    status = client.get("/api/v1/ai/status")
    assert status.status_code == 200
    body = status.json()
    assert body["deterministic_fallback_ready"] is True
    assert body["deterministic_core_can_be_overridden"] is False
    serialized_status = status.text.lower()
    assert "api_key" not in serialized_status
    assert "secret" not in serialized_status

    payload = {
        "symbol": "BTCUSDT",
        "market": "crypto",
        "timeframe": "15m",
        "deterministic_status": "watch",
        "deterministic_action_label": "WATCH",
        "side": "long",
        "risk_tier": "blocked",
        "evidence": [
            {
                "evidence_id": "E_STRUCTURE",
                "category": "structure",
                "statement": "Deterministic structure evidence is present.",
                "source": "strict_core",
                "polarity": "positive",
            }
        ],
        "negative_evidence": [
            {
                "evidence_id": "N_GATE",
                "category": "hard_gate",
                "statement": "A deterministic hard gate failed.",
                "source": "strict_core",
                "polarity": "negative",
            }
        ],
        "failed_gates": ["execution_spread"],
        "invalidation": "No active trade thesis; reassess after failed gates change.",
        "probability_estimate": 70,
        "probability_is_calibrated": False,
        "provider": "deterministic",
    }
    assert client.post("/api/v1/ai/explain", json=payload).status_code == 401
    response = client.post("/api/v1/ai/explain", json=payload, headers=_register())
    assert response.status_code == 200, response.text
    explanation = response.json()
    assert explanation["provider"] == "deterministic"
    assert explanation["mode"] == "deterministic"
    assert explanation["grounded"] is True
    assert explanation["verified"] is True
    assert explanation["deterministic_action_label"] == "WATCH"
    assert explanation["deterministic_core_preserved"] is True
    assert explanation["probability_is_calibrated"] is False
    assert explanation["probability_label"] == "model_estimate_not_calibrated"


def test_rc_health_readiness_metrics_and_request_id_contract(monkeypatch):
    supplied_request_id = "RC_Request_123456"
    health = client.get("/health", headers={"X-Request-ID": supplied_request_id})
    assert health.status_code == 200
    assert health.headers["x-request-id"] == supplied_request_id
    assert health.headers["x-content-type-options"] == "nosniff"
    assert health.headers["x-frame-options"] == "DENY"
    assert health.headers["content-security-policy"].startswith("default-src 'none'")
    assert int(health.headers["x-response-time-ms"]) >= 0
    assert health.json()["version"] == main.settings.app_version

    invalid = client.get("/health", headers={"X-Request-ID": "bad id"})
    assert invalid.headers["x-request-id"] != "bad id"
    assert " " not in invalid.headers["x-request-id"]

    ready = client.get("/ready")
    assert ready.status_code == 200
    ready_body = ready.json()
    assert ready_body["status"] == "ready"
    assert ready_body["database"]["connected"] is True
    assert ready_body["database"]["migration_current"] is True
    assert ready_body["live_execution_enabled"] is False

    assert client.get("/api/v1/system/health/deep").status_code == 401
    auth = _register()
    deep = client.get("/api/v1/system/health/deep", headers=auth)
    assert deep.status_code == 200
    assert deep.json()["database"]["connected"] is True
    assert deep.json()["live_execution_enabled"] is False
    metrics = client.get("/api/v1/system/metrics", headers=auth)
    assert metrics.status_code == 200
    assert metrics.json()["requests_total"] >= 1

    monkeypatch.setattr(main.settings, "max_request_body_bytes", 16)
    too_large = client.post(
        "/api/v1/auth/login",
        content=b"x" * 32,
        headers={"Content-Type": "application/json"},
    )
    assert too_large.status_code == 413
    assert "request_id" in too_large.json()

    monkeypatch.setattr(main.settings, "app_env", "production")
    production_ready = client.get("/ready")
    assert production_ready.status_code == 503
    assert production_ready.json()["database"]["production_database_ready"] is False


def test_rc_unhandled_errors_are_sanitized_and_traceable():
    path = "/_test/rc-sanitized-error"
    if not any(getattr(route, "path", None) == path for route in main.app.routes):
        def fail_with_secret():
            raise RuntimeError("https://provider.invalid?apikey=TOP_SECRET_VALUE")
        main.app.add_api_route(path, fail_with_secret, methods=["GET"])

    response = client.get(path)
    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error"
    assert response.json()["request_id"] == response.headers["x-request-id"]
    assert "TOP_SECRET_VALUE" not in response.text
    assert "apikey=" not in response.text.lower()


def test_quant_research_endpoints_are_authenticated_and_never_authorize_live():
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    returns = [0.5 if index % 2 == 0 else -0.4 for index in range(30)]
    payload = {
        "strategy_id": "api-research-test",
        "strategy_version": "v1",
        "dataset": {
            "dataset_id": "api-fixture",
            "version": "v1",
            "source": "test_fixture",
            "symbol": "BTCUSDT",
            "market": "crypto",
            "timeframe": "15m",
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(minutes=15 * 30)).isoformat(),
            "sample_count": 30,
            "source_sha256": "b" * 64,
            "is_point_in_time": True,
            "is_survivorship_bias_controlled": True,
            "is_independent_holdout": True,
            "data_quality_score": 100,
        },
        "returns_rr": returns,
        "timestamps": [
            (start + timedelta(minutes=15 * index)).isoformat() for index in range(30)
        ],
        "bootstrap_samples": 500,
        "monte_carlo_paths": 500,
        "random_seed": 9,
    }
    assert client.post("/api/v1/research/quant-validate", json=payload).status_code == 401
    auth = _register()
    response = client.post("/api/v1/research/quant-validate", json=payload, headers=auth)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "INSUFFICIENT_EVIDENCE"
    assert result["actionable_for_live"] is False
    assert result["deterministic_reproducible"] is True

    split = client.post(
        "/api/v1/research/purged-split-plan",
        json={
            "sample_count": 1000,
            "train_size": 300,
            "test_size": 100,
            "step_size": 100,
            "embargo_bars": 5,
            "max_folds": 3,
        },
        headers=auth,
    )
    assert split.status_code == 200
    assert split.json()["fold_count"] == 3
    assert split.json()["all_boundaries_purged"] is True


def test_historical_pipeline_endpoints_are_authenticated_and_persist_manifest(monkeypatch):
    from app.services.historical_data_service import HistoricalFetchResult

    candles = _candles(40)
    start = candles[0].timestamp

    class FakeProvider:
        name = "fake"

        async def fetch(self, request):
            return HistoricalFetchResult(
                source="fake_http_provider",
                candles=candles,
                pages=2,
                raw_rows=len(candles),
            )

    monkeypatch.setitem(main.historical_data_service.providers, "okx", FakeProvider())
    dataset_id = f"http-history-{uuid4().hex}"
    payload = {
        "dataset_id": dataset_id,
        "version": "v1",
        "provider": "okx",
        "symbol": "BTCUSDT",
        "market": "crypto",
        "timeframe": "15m",
        "start_time": start.isoformat(),
        "end_time": (start + timedelta(days=2)).isoformat(),
        "max_candles": 100,
        "persist": True,
        "attest_point_in_time": True,
    }
    assert client.post("/api/v1/research/historical/collect", json=payload).status_code == 401
    auth = _register()
    collected = client.post(
        "/api/v1/research/historical/collect", json=payload, headers=auth
    )
    assert collected.status_code == 200, collected.text
    body = collected.json()
    assert body["stored"] is True
    assert body["accepted_rows"] == 40
    assert len(body["canonical_sha256"]) == 64

    listed = client.get("/api/v1/research/datasets", headers=auth)
    assert listed.status_code == 200
    assert any(item["dataset_ref"] == f"{dataset_id}:v1" for item in listed.json()["items"])
    manifest = client.get(
        f"/api/v1/research/datasets/{dataset_id}/v1", headers=auth
    )
    assert manifest.status_code == 200
    assert manifest.json()["stored_candle_count"] == 40


def test_stored_research_endpoints_are_authenticated_and_sanitize_missing_dataset():
    fixed_payload = {
        "dataset_id": "missing-research-dataset",
        "dataset_version": "v1",
        "configuration_id": "fixed-config",
    }
    assert client.post("/api/v1/research/stored-backtest", json=fixed_payload).status_code == 401
    auth = _register()
    fixed = client.post(
        "/api/v1/research/stored-backtest", json=fixed_payload, headers=auth
    )
    assert fixed.status_code == 404
    assert fixed.json()["detail"]["code"] == "historical_dataset_not_found"

    walk = client.post(
        "/api/v1/research/stored-walk-forward",
        json={
            "dataset_id": "missing-research-dataset",
            "dataset_version": "v1",
        },
        headers=auth,
    )
    assert walk.status_code == 404
    assert walk.json()["detail"]["code"] == "historical_dataset_not_found"


def test_strategy_panel_endpoint_is_authenticated_and_never_live_actionable():
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    n = 200
    payload = {
        "panel_id": "api-strategy-panel",
        "panel_version": "v1",
        "dataset": {
            "dataset_id": "api-panel-data",
            "version": "v1",
            "source": "test_fixture",
            "symbol": "BTCUSDT",
            "market": "crypto",
            "timeframe": "1h",
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(hours=n)).isoformat(),
            "sample_count": n,
            "source_sha256": "f" * 64,
            "is_point_in_time": True,
            "is_survivorship_bias_controlled": True,
            "data_quality_score": 100,
        },
        "strategies": [
            {
                "strategy_id": f"api-s-{index}",
                "strategy_version": "v1",
                "returns_rr": [
                    0.5 - index * 0.1 + (0.02 if row % 2 == 0 else -0.02)
                    for row in range(n)
                ],
            }
            for index in range(5)
        ],
        "timestamps": [
            (start + timedelta(hours=index)).isoformat() for index in range(n)
        ],
        "block_count": 8,
    }
    assert client.post(
        "/api/v1/research/strategy-panel/validate", json=payload
    ).status_code == 401
    response = client.post(
        "/api/v1/research/strategy-panel/validate",
        json=payload,
        headers=_register(),
    )
    assert response.status_code == 200, response.text
    assert response.json()["actionable_for_live"] is False
    assert response.json()["deterministic_reproducible"] is True


def test_automated_final_holdout_endpoint_is_authenticated_and_sanitized():
    payload = {
        "experiment_id": "missing-dataset-experiment",
        "experiment_version": "v1",
        "dataset_id": "missing-automated-dataset",
        "dataset_version": "v1",
    }
    assert client.post(
        "/api/v1/research/automated-panel/final-holdout", json=payload
    ).status_code == 401
    response = client.post(
        "/api/v1/research/automated-panel/final-holdout",
        json=payload,
        headers=_register(),
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "historical_dataset_not_found"


def test_secure_byok_settings_never_return_raw_secrets(monkeypatch):
    import base64
    from app.services.provider_secret_service import ProviderSecretService

    vault = ProviderSecretService(
        main.storage.database,
        master_key=base64.urlsafe_b64encode(b"v" * 32).decode(),
    )
    monkeypatch.setattr(main, "provider_secret_service", vault)
    auth = _register()
    raw_secret = "never-return-this-provider-secret-123"

    initial = client.get("/api/v1/settings/providers", headers=auth)
    assert initial.status_code == 200
    assert initial.json()["vault_configured"] is True
    assert initial.json()["raw_secrets_returned"] is False

    saved = client.post(
        "/api/v1/settings/providers/groq",
        json={"api_key": raw_secret, "model": "test-model", "enabled": True},
        headers=auth,
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["configured"] is True
    assert raw_secret not in saved.text

    async def fake_probe(material):
        assert material.api_key == raw_secret
        return "connected"

    monkeypatch.setattr(vault, "_probe", fake_probe)
    tested = client.post("/api/v1/settings/providers/groq/test", headers=auth)
    assert tested.status_code == 200
    assert tested.json()["status"] == "connected"
    assert raw_secret not in tested.text

    listed = client.get("/api/v1/settings/providers", headers=auth)
    assert raw_secret not in listed.text
    assert next(
        item for item in listed.json()["providers"] if item["provider"] == "groq"
    )["last_test_status"] == "connected"

    personalized = client.get("/api/v1/news/personalized", headers=auth)
    assert personalized.status_code == 200
    assert personalized.json()["user_scoped"] is True
    assert raw_secret not in personalized.text

    deleted = client.delete("/api/v1/settings/providers/groq", headers=auth)
    assert deleted.status_code == 200
    assert raw_secret not in deleted.text


def test_paper_oms_api_is_user_scoped_idempotent_and_never_live_routed():
    assert client.get("/api/v1/paper/control").status_code == 401
    auth = _register()
    control = client.get("/api/v1/paper/control", headers=auth)
    assert control.status_code == 200
    assert control.json()["paper_trading_enabled"] is False
    assert control.json()["kill_switch_engaged"] is True

    armed = client.post(
        "/api/v1/paper/control",
        headers=auth,
        json={
            "paper_trading_enabled": True,
            "kill_switch_engaged": False,
            "acknowledgement": "I_UNDERSTAND_PAPER_ONLY",
        },
    )
    assert armed.status_code == 200
    key = f"paper-api-{uuid4().hex}"
    payload = {
        "idempotency_key": key,
        "symbol": "BTCUSDT",
        "market": "crypto",
        "side": "buy",
        "order_type": "market",
        "quantity": 1,
        "reference_bid": 99.9,
        "reference_ask": 100,
        "signal_score": 85,
        "risk_approved": True,
    }
    first = client.post("/api/v1/paper/orders", headers=auth, json=payload)
    second = client.post("/api/v1/paper/orders", headers=auth, json=payload)
    assert first.status_code == 200, first.text
    assert second.status_code == 200
    assert first.json()["order_id"] == second.json()["order_id"]
    assert first.json()["status"] == "filled"
    assert first.json()["live_routed"] is False

    portfolio = client.get("/api/v1/paper/portfolio", headers=auth)
    assert portfolio.status_code == 200
    assert portfolio.json()["live_execution_enabled"] is False
    assert portfolio.json()["positions"][0]["symbol"] == "BTCUSDT"

    reconciled = client.get(
        f"/api/v1/paper/orders/{first.json()['order_id']}/reconcile",
        headers=auth,
    )
    assert reconciled.status_code == 200
    assert reconciled.json()["consistent"] is True
    assert reconciled.json()["live_execution_enabled"] is False


def test_paper_automated_feed_api_is_opt_in_idempotent_and_never_live(monkeypatch):
    from app.services.paper_market_feed_service import PaperProviderQuote

    assert client.get("/api/v1/paper/feed/status").status_code == 401
    auth = _register()
    armed = client.post(
        "/api/v1/paper/control",
        headers=auth,
        json={
            "paper_trading_enabled": True,
            "kill_switch_engaged": False,
            "automated_feed_enabled": True,
            "max_tick_age_seconds": 30,
            "acknowledgement": "I_UNDERSTAND_PAPER_ONLY",
        },
    )
    assert armed.status_code == 200, armed.text
    assert armed.json()["automated_feed_enabled"] is True

    subscribed = client.post(
        "/api/v1/paper/feed/subscriptions",
        headers=auth,
        json={
            "symbol": "BTCUSDT",
            "market": "crypto",
            "poll_interval_seconds": 15,
            "acknowledgement": "I_UNDERSTAND_PAPER_ONLY",
        },
    )
    assert subscribed.status_code == 200, subscribed.text
    assert subscribed.json()["provider"] == "okx_public"
    assert subscribed.json()["is_real_market_quote"] is True
    assert subscribed.json()["live_routed"] is False

    class ApiFixtureProvider:
        provider_name = "okx_public"
        timestamp = datetime.now(timezone.utc)

        async def fetch(self, symbol):
            return PaperProviderQuote(
                symbol=symbol,
                bid=100.0,
                ask=100.1,
                available_quantity=5.0,
                timestamp=self.timestamp,
                provider="okx_public",
                source="okx_public_real_best_bid_ask",
                event_id=f"okx_{'a' * 48}",
            )

    monkeypatch.setattr(main.paper_market_feed_service, "provider", ApiFixtureProvider())
    first = client.post(
        "/api/v1/paper/feed/sync",
        headers=auth,
        json={"symbols": ["BTCUSDT"]},
    )
    second = client.post(
        "/api/v1/paper/feed/sync",
        headers=auth,
        json={"symbols": ["BTCUSDT"]},
    )
    assert first.status_code == 200, first.text
    assert first.json()["success_count"] == 1
    assert first.json()["items"][0]["duplicate_tick"] is False
    assert first.json()["items"][0]["live_routed"] is False
    assert second.status_code == 200
    assert second.json()["items"][0]["duplicate_tick"] is True

    status = client.get("/api/v1/paper/feed/status", headers=auth)
    assert status.status_code == 200
    assert status.json()["live_execution_enabled"] is False
    assert status.json()["subscription_count"] == 1


def test_paper_margin_funding_api_is_authenticated_idempotent_and_never_live():
    assert client.get("/api/v1/paper/margin/events").status_code == 401
    auth = _register()
    armed = client.post(
        "/api/v1/paper/control",
        headers=auth,
        json={
            "paper_trading_enabled": True,
            "kill_switch_engaged": False,
            "max_leverage": 10,
            "default_maintenance_margin_rate": 0.005,
            "liquidation_fee_bps": 20,
            "max_margin_utilization_pct": 70,
            "acknowledgement": "I_UNDERSTAND_PAPER_ONLY",
        },
    )
    assert armed.status_code == 200, armed.text
    order_key = f"margin-api-{uuid4().hex}"
    order = client.post(
        "/api/v1/paper/orders",
        headers=auth,
        json={
            "idempotency_key": order_key,
            "symbol": "BTCUSDT",
            "market": "crypto",
            "side": "buy",
            "order_type": "market",
            "quantity": 10,
            "reference_bid": 99.9,
            "reference_ask": 100,
            "leverage": 5,
            "margin_mode": "isolated",
            "signal_score": 85,
            "risk_approved": True,
        },
    )
    assert order.status_code == 200, order.text
    assert order.json()["leverage"] == 5
    assert order.json()["margin_mode"] == "isolated"

    portfolio = client.get("/api/v1/paper/portfolio", headers=auth)
    assert portfolio.status_code == 200
    assert portfolio.json()["used_margin"] > 0
    assert portfolio.json()["free_margin"] < portfolio.json()["equity"]
    assert portfolio.json()["liquidation_count"] == 0
    assert portfolio.json()["live_execution_enabled"] is False

    event_id = f"funding-api-{uuid4().hex}"
    funding_payload = {
        "event_id": event_id,
        "symbol": "BTCUSDT",
        "funding_rate": 0.001,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "api_user_supplied_fixture",
    }
    first = client.post(
        "/api/v1/paper/funding/settle",
        headers=auth,
        json=funding_payload,
    )
    second = client.post(
        "/api/v1/paper/funding/settle",
        headers=auth,
        json=funding_payload,
    )
    assert first.status_code == 200, first.text
    assert second.status_code == 200
    assert first.json()["duplicate"] is False
    assert second.json()["duplicate"] is True
    assert first.json()["event"]["is_real_rate"] is False
    assert first.json()["event"]["live_routed"] is False
    assert first.json()["live_execution_enabled"] is False

    events = client.get("/api/v1/paper/margin/events", headers=auth)
    assert events.status_code == 200
    assert events.json()["count"] == 1
    assert events.json()["items"][0]["event_type"] == "funding"


def test_paper_correlation_snapshot_endpoint_is_authenticated_and_fail_closed():
    payload = {
        "snapshot_id": "missing-correlation-snapshot-1",
        "datasets": [
            {"dataset_id": "missing-btc", "version": "v1"},
            {"dataset_id": "missing-eth", "version": "v1"},
        ],
        "minimum_observations": 60,
        "cluster_threshold": 0.7,
    }
    assert client.post(
        "/api/v1/paper/risk/correlation/snapshots", json=payload
    ).status_code == 401
    response = client.post(
        "/api/v1/paper/risk/correlation/snapshots",
        json=payload,
        headers=_register(),
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "historical_dataset_not_found"


def test_paper_recovery_audit_and_shadow_reconciliation_api_are_never_live():
    assert client.get("/api/v1/paper/audit").status_code == 401
    auth = _register()
    armed = client.post(
        "/api/v1/paper/control",
        headers=auth,
        json={
            "paper_trading_enabled": True,
            "kill_switch_engaged": False,
            "max_symbol_margin_pct": 100,
            "max_risk_group_margin_pct": 100,
            "max_directional_notional_multiple": 20,
            "acknowledgement": "I_UNDERSTAND_PAPER_ONLY",
        },
    )
    assert armed.status_code == 200, armed.text
    order = client.post(
        "/api/v1/paper/orders",
        headers=auth,
        json={
            "idempotency_key": f"recovery-api-{uuid4().hex}",
            "symbol": "BTCUSDT",
            "market": "crypto",
            "side": "buy",
            "quantity": 2,
            "reference_bid": 99.9,
            "reference_ask": 100,
            "available_quantity": 2,
            "leverage": 2,
            "signal_score": 85,
            "risk_approved": True,
        },
    )
    assert order.status_code == 200, order.text
    order_data = order.json()
    assert order_data["correlation_source"] == "structural_proxy"

    audit = client.get("/api/v1/paper/audit", headers=auth)
    assert audit.status_code == 200, audit.text
    assert audit.json()["consistent"] is True
    assert audit.json()["repair_performed"] is False
    assert audit.json()["actionable_for_live"] is False
    assert audit.json()["live_execution_enabled"] is False

    checkpoints = client.get("/api/v1/paper/testnet/checkpoints", headers=auth)
    assert checkpoints.status_code == 200
    assert checkpoints.json()["count"] == 2
    assert all(not item["authenticated"] for item in checkpoints.json()["items"])
    assert all(not item["order_routing_enabled"] for item in checkpoints.json()["items"])

    payload = {
        "run_id": f"shadow-api-run-{uuid4().hex}",
        "connector": "binance_futures_testnet",
        "snapshot_id": f"snapshot-{uuid4().hex}",
        "snapshot_timestamp": datetime.now(timezone.utc).isoformat(),
        "orders": [{
            "order_id": order_data["order_id"],
            "status": order_data["status"],
            "filled_quantity": order_data["filled_quantity"],
            "average_fill_price": order_data["average_fill_price"],
            "total_fees": order_data["total_fees"],
        }],
    }
    first = client.post(
        "/api/v1/paper/testnet/shadow-reconcile",
        headers=auth,
        json=payload,
    )
    second = client.post(
        "/api/v1/paper/testnet/shadow-reconcile",
        headers=auth,
        json=payload,
    )
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "CONSISTENT"
    assert first.json()["snapshot_verified_by_provider"] is False
    assert first.json()["actionable_for_live"] is False
    assert second.json()["duplicate"] is True
