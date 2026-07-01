from datetime import datetime, timedelta, timezone
import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models import Candle, MarketType, OrderFlowData, RiskSettings, SignalRequest, TradeStats
from app.services.signal_engine import SignalEngine


now = datetime.now(timezone.utc)
base = 100.0
candles = []
for i in range(30):
    o = base + i * 0.4
    c = o + 0.25
    h = c + 0.4
    l = o - 0.3
    candles.append(
        Candle(
            timestamp=now - timedelta(minutes=(30 - i) * 15),
            open=round(o, 4),
            high=round(h, 4),
            low=round(l, 4),
            close=round(c, 4),
            volume=1000 + i * 10,
        )
    )

request = SignalRequest(
    symbol="BTCUSDT",
    market=MarketType.crypto,
    timeframe="15m",
    candles=candles,
    order_flow=OrderFlowData(
        delta_volume=12000,
        open_interest_change_pct=1.5,
        funding_rate=-0.01,
        aggressive_buy_ratio=0.61,
        aggressive_sell_ratio=0.39,
    ),
    risk_settings=RiskSettings(account_balance=5000, risk_per_trade_pct=1.0),
    trade_stats=TradeStats(trades_today=1, consecutive_losses=0, daily_loss_pct=0.5, open_positions=0),
    now_utc=now,
)

response = SignalEngine().analyze(request)
print(json.dumps(response.model_dump(), indent=2, default=str))
