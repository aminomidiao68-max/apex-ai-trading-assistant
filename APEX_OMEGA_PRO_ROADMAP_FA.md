# نقشه ارتقای APEX Omega Pro v3

## اصول غیرقابل مذاکره

- حالت پیش‌فرض: NO TRADE
- هیچ Probability بدون Calibration، احتمال واقعی نامیده نمی‌شود.
- هیچ CVD فارکس، واقعی معرفی نمی‌شود؛ منبع آن PROXY خواهد بود.
- هر سیگنال باید Evidence، Negative Evidence، Hard Gates و Invalidation داشته باشد.
- Live Execution تا پایان تمام Gateها خاموش می‌ماند.
- هر فاز باید Backend Test، Android Test، Lint، Build و Live Matrix را پاس کند.

## ✅ Alpha 1 — Strict Core (Completed)

- Data Quality Engine
- Market Regime Engine
- Strict Decision Engine
- Strict Omega با ۱۲ Hard Gate
- No-Trade default
- Grounded AI decision contract

## ✅ Alpha 2 — Real Order Flow (Completed)

- Binance AggTrades delta
- Order Book imbalance و spread
- Open Interest و Funding
- Cache و source confidence
- Forex honest proxy بدون ادعای CVD واقعی

## ✅ Alpha 3 — Signal & Setup State Machine (Completed)

- forming → armed → confirmed → triggered → invalidated → expired
- deduplication و cooldown
- expiration by bars/timeframe
- strict setup classifier و conflict budget

## ✅ Alpha 4 — Risk & Backtest (Completed)

- Portfolio heat، drawdown، correlation و open-risk budget
- volatility/spread/slippage adjustments
- conservative intrabar execution با سیاست `stop_first`
- fees، funding و entry activation/expiry
- جلوگیری پیش‌فرض از معاملات هم‌پوشان
- Mark-to-market برای معاملات بسته‌نشده
- anti-look-ahead tests و الزام timestamps صعودی
- گزارش Gross/Cost/Net R و Max Drawdown

## Alpha 5 — AI & Explainability

- Provider-agnostic adapter
- Evidence-grounded prompt contract
- critic/verifier layer
- deterministic fallback
- refusal to invent missing data

## RC — Chart, Mobile & Production Gate

- decision/evidence panels
- strict plan visualization
- PostgreSQL persistence
- monitoring، rate limit، backup و release candidate tests
