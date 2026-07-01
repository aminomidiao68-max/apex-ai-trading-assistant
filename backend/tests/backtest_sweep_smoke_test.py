import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models import BacktestSweepRequest, Candle, MarketType, RiskSettings
from app.services.backtest_service import BacktestService
from app.services.signal_engine import SignalEngine


now = datetime.now(timezone.utc)
candles = []
base = 100.0
for i in range(90):
    drift = i * 0.28
    open_price = base + drift
    close_price = open_price + (0.18 if i % 2 == 0 else 0.42)
    high_price = close_price + 0.55
    low_price = open_price - 0.3
    candles.append(
        Candle(
            timestamp=now - timedelta(minutes=(90 - i) * 15),
            open=round(open_price, 4),
            high=round(high_price, 4),
            low=round(low_price, 4),
            close=round(close_price, 4),
            volume=1200 + i * 12,
        )
    )

summary = BacktestService(SignalEngine()).run_sweep(
    BacktestSweepRequest(
        symbol="BTCUSDT",
        market=MarketType.crypto,
        timeframe="15m",
        window_sizes=[25, 30],
        lookahead_options=[5, 8],
        score_thresholds=[60, 65],
        take_profit_indices=[0, 1],
        max_signals=12,
        max_results=5,
        risk_settings=RiskSettings(account_balance=5000, risk_per_trade_pct=1.0),
    ),
    candles,
)
print(summary.model_dump())
