# گزارش APEX Omega Pro v3 Alpha 2 — Real Order Flow

## Crypto Real Order Flow

منبع: OKX USDT Perpetual Swap Public APIs

- ۵۰۰ معامله اخیر و Aggressive Buy/Sell؛
- Delta و CVD واقعی همان صرافی؛
- Order Book تا ۵۰ Level؛
- Depth Imbalance و Spread Bps؛
- Bid/Ask Wall و Wall Strength؛
- Open Interest و تغییر OI بین Snapshotها؛
- Funding Rate؛
- Large Trade Imbalance؛
- Absorption، Climax و Delta/Price Divergence؛
- Cache بیست‌ثانیه‌ای برای هر Symbol.

این داده واقعی یک صرافی متمرکز است و به‌عنوان جریان کل بازار معرفی نمی‌شود.

## Forex Honest Proxy

- Candle pressure؛
- Close Location؛
- Tick/Relative Volume؛
- Proxy Delta و Proxy CVD؛
- Volume Spike، Absorption و Climax Proxy؛
- `is_real=false` و `source=forex_ohlcv_proxy`؛
- Depth، Funding و OI برابر Null؛
- Disclaimer صریح مبنی بر متمرکزنبودن فارکس.

## Gateهای جدید

- Real Order Flow برای Crypto در تایم‌فریم 1m تا 1h اجباری؛
- Order Flow Alignment؛
- Spread حداکثر ۸ bps؛
- عدم Depth Imbalance شدید خلاف جهت؛
- Funding Crowding به‌عنوان Gate نرم؛
- Confidence منبع Order Flow.

## آزمون واقعی BTCUSDT

- Source: `okx_swap_public`
- Real: true
- Confidence: 0.98
- Sample Trades: 500
- Spread: 0.0159 bps در Snapshot آزمون
- Open Interest USD: حدود 1.97B در Snapshot آزمون
- Cache Snapshot دوم: موفق

## تست

- Backend Regression: 11 passed
- Pure parser test برای Trades/Depth/OI/Funding
- Forex Proxy honesty test
- Crypto fallback strict gate test
