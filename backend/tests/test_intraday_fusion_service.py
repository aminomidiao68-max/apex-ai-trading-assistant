from app.services.intraday_fusion_service import IntradayFusionService


def frame(tf, side, status, real=True, pressure=None, quality=90, regime="trending"):
    direction = side
    return {
        "timeframe": tf,
        "report": {
            "direction": direction,
            "bias": "bullish" if side == "long" else "bearish" if side == "short" else "neutral",
            "confluence": 80,
            "invalidation": 99 if side == "long" else 101 if side == "short" else None,
            "levels": {"entry": 100, "sl": 99, "tp1": 102},
            "data_quality": {"score": quality},
            "market_regime": {"name": regime},
            "decision": {
                "side": side,
                "status": status,
                "orderflow": {
                    "is_real": real,
                    "pressure": pressure or ("buy" if side == "long" else "sell" if side == "short" else "neutral"),
                },
            },
        },
    }


def test_precision_fusion_requires_all_causal_gates():
    service = IntradayFusionService()
    frames = [
        frame("5m", "long", "actionable"),
        frame("15m", "long", "watch"),
        frame("1h", "long", "actionable"),
        frame("4h", "long", "actionable"),
    ]
    result = service.fuse("BTCUSDT", "crypto", frames)
    assert result["status"] == "ACTIONABLE_CANDIDATE"
    assert result["action_label"] == "LONG"
    assert result["side"] == "long"
    assert not result["failed_gates"]
    assert result["probability_is_calibrated"] is False
    assert result["ai_override_allowed"] is False
    assert result["actionable_for_live"] is False


def test_context_or_trigger_conflict_forces_no_trade_or_watch():
    service = IntradayFusionService()
    conflict = [
        frame("5m", "short", "actionable"),
        frame("15m", "long", "watch"),
        frame("1h", "long", "actionable"),
        frame("4h", "short", "actionable"),
    ]
    result = service.fuse("BTCUSDT", "crypto", conflict)
    assert result["status"] == "NO_TRADE"
    assert result["action_label"] == "NO_TRADE"
    assert "context_consensus" in result["failed_gates"]
    assert result["levels"] is None


def test_crypto_requires_real_flow_but_forex_proxy_is_honest():
    service = IntradayFusionService()
    frames = [
        frame("5m", "long", "actionable", real=False),
        frame("15m", "long", "watch", real=False),
        frame("1h", "long", "actionable", real=False),
        frame("4h", "long", "actionable", real=False),
    ]
    crypto = service.fuse("BTCUSDT", "crypto", frames)
    assert crypto["status"] == "WATCH"
    assert "crypto_real_flow" in crypto["failed_gates"]
    forex = service.fuse("XAUUSD", "forex", frames)
    assert forex["status"] == "ACTIONABLE_CANDIDATE"
    assert all(item["is_real"] is False for item in forex["orderflow_evidence"])
