import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models import Candle, MarketType, RiskSettings, WalkForwardRequest
from app.services.backtest_service import BacktestService
from app.services.signal_engine import SignalEngine


now = datetime.now(timezone.utc)
candles = []
base = 100.0
for i in range(170):
    drift = i * 0.22
    open_price = base + drift
    close_price = open_price + (0.18 if i % 2 == 0 else 0.32)
    high_price = close_price + 0.4
    low_price = open_price - 0.25
    candles.append(
        Candle(
            timestamp=now - timedelta(minutes=(170 - i) * 15),
            open=round(open_price, 4),
            high=round(high_price, 4),
            low=round(low_price, 4),
            close=round(close_price, 4),
            volume=1000 + i * 8,
        )
    )

summary = BacktestService(SignalEngine()).run_walk_forward(
    WalkForwardRequest(
        symbol="BTCUSDT",
        market=MarketType.crypto,
        timeframe="15m",
        train_window=80,
        test_window=30,
        step_size=20,
        window_sizes=[20, 30],
        lookahead_options=[5, 8],
        score_thresholds=[60, 65],
        take_profit_indices=[0, 1],
        max_signals=12,
        max_steps=3,
        risk_settings=RiskSettings(account_balance=5000, risk_per_trade_pct=1.0),
    ),
    candles,
)
print(summary.model_dump())
