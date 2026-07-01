import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models import BacktestRunRequest, Candle, MarketType, RiskSettings
from app.services.backtest_service import BacktestService
from app.services.signal_engine import SignalEngine


now = datetime.now(timezone.utc)
candles = []
base = 100.0
for i in range(80):
    drift = i * 0.3
    open_price = base + drift
    close_price = open_price + (0.2 if i % 2 == 0 else 0.35)
    high_price = close_price + 0.45
    low_price = open_price - 0.35
    candles.append(
        Candle(
            timestamp=now - timedelta(minutes=(80 - i) * 15),
            open=round(open_price, 4),
            high=round(high_price, 4),
            low=round(low_price, 4),
            close=round(close_price, 4),
            volume=1000 + i * 20,
        )
    )

summary = BacktestService(SignalEngine()).run(
    BacktestRunRequest(
        symbol="BTCUSDT",
        market=MarketType.crypto,
        timeframe="15m",
        window_size=30,
        lookahead_candles=6,
        score_threshold=60,
        max_signals=10,
        take_profit_index=0,
        risk_settings=RiskSettings(account_balance=5000, risk_per_trade_pct=1.0),
    ),
    candles,
)
print(summary.model_dump())
