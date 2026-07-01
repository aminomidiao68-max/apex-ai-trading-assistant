# طراحی API

## Health
### `GET /health`
بررسی سلامت سرویس.

## Auth
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`

## Notifications
### `POST /api/v1/notifications/register-device`
ثبت device token برای push.

### `GET /api/v1/notifications/devices`
لیست device tokenهای ثبت‌شده کاربر.

### `POST /api/v1/notifications/test`
ایجاد test notification event.
> در نسخه فعلی به‌صورت dry-run/logging است تا credential واقعی FCM اضافه شود.

## Session
### `GET /api/v1/sessions/current`
خروجی:
- session_name
- market_quality
- session_score

## Analytics
### `GET /api/v1/analytics/summary`
خروجی:
- total_saved_signals
- buy_signals
- sell_signals
- neutral_signals
- average_signal_score
- recent_signals_24h
- top_signal_symbols[]
- trade_stats

### `GET /api/v1/analytics/report`
خروجی:
- summary
- signal_stats_by_symbol[]
- trade_performance_by_symbol[]
- recent_notification_events_7d

## Market Data
### `GET /api/v1/market/overview?symbols=BTCUSDT,ETHUSDT,EURUSD,GBPUSD,XAUUSD`

### `GET /api/v1/market/candles?symbol=BTCUSDT&market=crypto&interval=15m&limit=200`

### `WS /ws/market?symbol=BTCUSDT&market=crypto`
استریم ساده snapshot بازار هر چند ثانیه.

## Signals
### `POST /api/v1/signals/analyze`
تحلیل صرف بدون ذخیره در دیتابیس.

### `POST /api/v1/signals/analyze-and-save`
تحلیل + ذخیره نتیجه در دیتابیس.

### `POST /api/v1/signals/live-scan`
ورودی:
- symbol
- market
- timeframe
- risk_settings
- trade_stats
- client_timezone

### `GET /api/v1/signals/history?limit=30`
دریافت تاریخچه سیگنال‌ها.

## Backtest
### `POST /api/v1/backtest/run`

### `POST /api/v1/backtest/sweep`

### `POST /api/v1/backtest/walk-forward`
ارزیابی مرحله‌ای out-of-sample با train/test windows.

## Trades Journal
### `POST /api/v1/trades`
ثبت معامله جدید در ژورنال.

### `GET /api/v1/trades?limit=50`
لیست معاملات ذخیره‌شده.

### `GET /api/v1/trades/stats`
خلاصه:
- total_trades
- open_trades
- closed_trades
- wins
- losses
- win_rate
- net_pnl

### `POST /api/v1/trades/{trade_id}/close`
بستن معامله و ثبت exit / pnl.

## Execution
### `GET /api/v1/execution/status`
اکنون وضعیت foundation برای این کانکتورها را برمی‌گرداند:
- binance_futures
- bybit
- oanda
- mt5
- ctrader

### `GET /api/v1/execution/capabilities`
نمایش maturity، بازار هدف، route و نکات هر connector.

### `POST /api/v1/execution/preview`
پیش‌نمایش مسیر اجرای سفارش، payload نرمال‌شده و هشدارهای credential/risk.

### `POST /api/v1/execution/binance/order`
### `POST /api/v1/execution/bybit/order`
### `POST /api/v1/execution/mt5/order`
### `POST /api/v1/execution/ctrader/order`
### `POST /api/v1/execution/oanda/order`

## Risk Planning
### `POST /api/v1/risk/plan`
برای محاسبه اندازه پوزیشن و اعتبارسنجی limits.

## ملاحظات امنیتی
- اجرای زنده فقط وقتی `ENABLE_LIVE_EXECUTION=true` باشد مجاز است.
- بدون API credentials، اجرای واقعی انجام نمی‌شود.
- برای اجرای واقعی، score سیگنال باید از آستانه تعیین‌شده بیشتر باشد.
- قبل از هر order باید risk engine تأیید دهد.
- ورود به اپ قبل از دسترسی به محیط اصلی اجباری شده است.
