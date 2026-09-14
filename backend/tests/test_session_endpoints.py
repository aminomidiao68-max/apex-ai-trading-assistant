"""Integration tests for the new endpoints: SMT helper, proximity alerts, prime backtest.

Uses the same isolated-DB pattern as test_regressions.py. All network access is
monkeypatched — these tests are fully offline and deterministic.
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

_TEST_DB_DIR = tempfile.mkdtemp(prefix="apex-session-tests-")
os.environ.setdefault("DATABASE_PATH", os.path.join(_TEST_DB_DIR, "session.db"))
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SEED_DEMO_USER", "false")

from fastapi.testclient import TestClient

import app.main as main


client = TestClient(main.app, raise_server_exceptions=True)


# --------------------------------------------------------------------- helpers
def make_closes_zigzag(n: int = 220, base: float = 100.0) -> list[dict]:
    """Ascending normalized candles with rhythmic swings (structure for detectors)."""
    items = []
    price = base
    for i in range(n):
        drift = 0.12
        pull = -0.8 if (i % 14) in (10, 11, 12) else 0.0
        o = price
        c = max(1.0, price + drift + pull)
        items.append({
            "t": 1_700_000_000.0 + i * 900.0,
            "o": o,
            "h": max(o, c) + 0.25,
            "l": min(o, c) - 0.25,
            "c": c,
            "v": 100.0 + i,
        })
        price = c
    return items


FAKE_CANDLES = make_closes_zigzag()


async def fake_fetch_live_candles(symbol: str, market: str, timeframe: str):
    # shift the correlated leg slightly so SMT has two distinct real series
    if symbol.upper() != "BTCUSDT":
        shifted = []
        for i, row in enumerate(FAKE_CANDLES):
            bump = 0.5 if (i // 14) % 2 == 0 else -0.3
            shifted.append({**row, "c": row["c"] + bump, "h": row["h"] + bump, "l": row["l"] + bump, "o": row["o"] + bump})
        return shifted
    return list(FAKE_CANDLES)


async def fake_micro_none(symbol, market, timeframe, timeout_s=6.0, compact=True):
    return None


# ------------------------------------------------------------------ SMT helper
def test_smt_for_symbol_maps_canonical_pair(monkeypatch):
    monkeypatch.setattr(main, "fetch_live_candles", fake_fetch_live_candles)
    items_a = main._norm_candles(FAKE_CANDLES)
    out = asyncio.run(main._smt_for_symbol("BTCUSDT", "crypto", "15m", items_a))
    assert out is not None
    assert out["primary"] == "BTCUSDT"
    assert out["correlated"] == "ETHUSDT"
    assert out["available"] is True
    assert isinstance(out.get("divergences"), list)
    assert "summary_fa" in out


def test_smt_for_symbol_unknown_pair_returns_none():
    out = asyncio.run(main._smt_for_symbol("DOGEUSDT", "crypto", "15m", main._norm_candles(FAKE_CANDLES)))
    assert out is None
    out2 = asyncio.run(main._smt_for_symbol("BTCUSDT", "crypto", None, main._norm_candles(FAKE_CANDLES)))
    assert out2 is None


# --------------------------------------------------------------- proximity API
def test_proximity_endpoint_offline(monkeypatch):
    monkeypatch.setattr(main, "fetch_live_candles", fake_fetch_live_candles)
    monkeypatch.setattr(main, "get_micro_summary", fake_micro_none)
    response = client.get(
        "/api/v1/alerts/proximity",
        params={"symbol": "BTCUSDT", "timeframe": "15m"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "BTCUSDT"
    assert data["available"] is True
    assert data["price"] > 0
    assert isinstance(data["alerts"], list)
    assert isinstance(data["nearest"], list)
    for row in data["nearest"]:
        assert {"kind", "ref", "level_price", "distance_pct", "side", "in_range"} <= set(row)
    for alert in data["alerts"]:
        assert alert["in_range"] is True
        assert "message_fa" in alert and "BTCUSDT" in alert["message_fa"]


def test_proximity_endpoint_is_deterministic(monkeypatch):
    monkeypatch.setattr(main, "fetch_live_candles", fake_fetch_live_candles)
    monkeypatch.setattr(main, "get_micro_summary", fake_micro_none)
    first = client.get("/api/v1/alerts/proximity", params={"symbol": "BTCUSDT"}).json()
    second = client.get("/api/v1/alerts/proximity", params={"symbol": "BTCUSDT"}).json()
    assert first["nearest"] == second["nearest"]
    assert first["alerts"] == second["alerts"]


def test_proximity_evaluation_failure_is_safe(monkeypatch):
    async def boom(symbol, market, timeframe):
        raise RuntimeError("provider down")

    monkeypatch.setattr(main, "fetch_live_candles", boom)
    response = client.get("/api/v1/alerts/proximity", params={"symbol": "BTCUSDT"})
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is False
    assert data["alerts"] == [] and data["nearest"] == []


# ------------------------------------------------------------ backtest API
def test_backtest_prime_endpoint_offline(monkeypatch):
    deep = make_closes_zigzag(320)

    async def fake_deep(symbol, timeframe, max_candles=1200):
        return deep[:max_candles]

    monkeypatch.setattr(main.prime_backtest_service, "fetch_okx_deep_candles", fake_deep)
    response = client.get(
        "/api/v1/backtest/prime",
        params={"symbol": "BTCUSDT", "timeframe": "15m", "candles": 320, "force": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["data_source"] == "okx_history_candles"
    assert data["candles"] == 320
    assert "all" in data and "prime_proxy" in data
    assert data["disclaimer_fa"]
    assert data["settings"]["target"] == "tp1"


def test_backtest_prime_insufficient_history(monkeypatch):
    async def fake_deep(symbol, timeframe, max_candles=1200):
        return make_closes_zigzag(40)

    async def fake_live(symbol, market, timeframe):
        return make_closes_zigzag(40)

    monkeypatch.setattr(main.prime_backtest_service, "fetch_okx_deep_candles", fake_deep)
    monkeypatch.setattr(main, "fetch_live_candles", fake_live)
    response = client.get(
        "/api/v1/backtest/prime",
        params={"symbol": "BTCUSDT", "timeframe": "15m", "candles": 200, "force": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert data["required"] == 160


def test_backtest_prime_force_has_cooldown(monkeypatch):
    deep = make_closes_zigzag(320)
    calls = {"n": 0}

    async def fake_deep(symbol, timeframe, max_candles=1200):
        calls["n"] += 1
        return deep[:max_candles]

    monkeypatch.setattr(main.prime_backtest_service, "fetch_okx_deep_candles", fake_deep)
    params = {"symbol": "ETHUSDT", "timeframe": "15m", "candles": 320, "force": True}
    first = client.get("/api/v1/backtest/prime", params=params)
    assert first.status_code == 200 and first.json()["ok"] is True
    second = client.get("/api/v1/backtest/prime", params=params)
    body = second.json()
    assert body.get("refresh_cooldown") is True
    assert body.get("cached") is True
    assert calls["n"] == 1  # heavy replay ran only once


def test_backtest_prime_validates_candles_param():
    response = client.get("/api/v1/backtest/prime", params={"symbol": "BTCUSDT", "candles": 10})
    assert response.status_code == 422
    response = client.get("/api/v1/backtest/prime", params={"symbol": "BTCUSDT", "candles": 5000})
    assert response.status_code == 422
