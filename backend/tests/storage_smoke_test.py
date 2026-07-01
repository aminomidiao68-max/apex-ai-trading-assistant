import os
import sys
from tempfile import NamedTemporaryFile

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models import (
    MarketType,
    ScoreBreakdown,
    SignalDirection,
    SignalResponse,
    TradeJournalCloseRequest,
    TradeJournalCreateRequest,
)
from app.services.storage_service import StorageService


tmp = NamedTemporaryFile(suffix=".db", delete=False)
service = StorageService(db_path=tmp.name)

saved = service.save_signal(
    SignalResponse(
        symbol="BTCUSDT",
        market=MarketType.crypto,
        timeframe="15m",
        direction=SignalDirection.buy,
        score=80.0,
        confidence="high",
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
            smc=20.0,
            order_flow=12.0,
            session=8.0,
            news=10.0,
            indicators=10.0,
            total=80.0,
        ),
        reasons=["test"],
        risk_plan=None,
    )
)
print("SAVED_SIGNAL_ID:", saved.id)
print("HISTORY_COUNT:", len(service.list_signals(limit=10)))

trade = service.create_trade(
    TradeJournalCreateRequest(
        symbol="BTCUSDT",
        market=MarketType.crypto,
        direction=SignalDirection.buy,
        entry_price=100.0,
        stop_loss=98.0,
        take_profit=103.0,
        size=2.0,
        notes="from test",
    )
)
closed = service.close_trade(
    trade.id,
    TradeJournalCloseRequest(exit_price=103.0, pnl_amount=6.0, notes="tp hit"),
)
print("CLOSED_TRADE_STATUS:", closed.status)
print("TRADE_STATS:", service.get_trade_stats().model_dump())
