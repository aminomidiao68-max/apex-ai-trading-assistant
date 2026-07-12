from __future__ import annotations

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
