import os
import sys
from tempfile import NamedTemporaryFile
from datetime import datetime, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models import (
    DeviceTokenRegisterRequest,
    MarketType,
    ScoreBreakdown,
    SignalDirection,
    SignalResponse,
    TradeJournalCloseRequest,
    TradeJournalCreateRequest,
)
from app.services.storage_service import StorageService


tmp = NamedTemporaryFile(suffix=".db", delete=False)
storage = StorageService(db_path=tmp.name)

for symbol, score in [("BTCUSDT", 72.0), ("BTCUSDT", 68.0), ("ETHUSDT", 77.0)]:
    storage.save_signal(
        SignalResponse(
            symbol=symbol,
            market=MarketType.crypto,
            timeframe="15m",
            direction=SignalDirection.buy,
            score=score,
            confidence="medium",
            session_name="London",
            session_quality="high",
            news_blocked=False,
            entry_low=100.0,
            entry_high=101.0,
            stop_loss=98.0,
            take_profits=[103.0, 105.0, 108.0],
            risk_to_reward=3.0,
            score_breakdown=ScoreBreakdown(
                structure=20.0,
                smc=18.0,
                order_flow=12.0,
                session=8.0,
                news=10.0,
                indicators=9.0,
                total=score,
            ),
            reasons=["test"],
            risk_plan=None,
        )
    )

trade = storage.create_trade(
    TradeJournalCreateRequest(
        symbol="BTCUSDT",
        market=MarketType.crypto,
        direction=SignalDirection.buy,
        entry_price=100.0,
        stop_loss=98.0,
        take_profit=103.0,
        size=2.0,
        notes="analytics test",
    )
)
storage.close_trade(trade.id, TradeJournalCloseRequest(exit_price=103.0, pnl_amount=6.0, notes="tp"))
storage.register_device_token(1, DeviceTokenRegisterRequest(token="fcm_test_token_value_12345678901234567890", platform="android", device_name="Pixel"))
storage.log_notification_event(1, "Ping", "Body", "dry-run", 1)
report = storage.get_analytics_report()
print(report.model_dump())
