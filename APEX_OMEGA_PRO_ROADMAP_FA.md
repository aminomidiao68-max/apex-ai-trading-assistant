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

## ✅ Alpha 5 — AI & Explainability (Completed)

- Provider-agnostic adapter برای OpenAI-compatible، Gemini و endpoint سفارشی
- Evidence Packet با Evidence ID، منبع و برچسب `is_real`
- Evidence و Negative Evidence اجباری
- critic/verifier برای رد Citation، عدد، Probability و Invalidation ساختگی
- deterministic fallback قطعی و دوزبانه
- refusal در نبود داده حیاتی
- External AI به‌صورت opt-in با Timeout، Cache و Circuit Breaker
- Probability بدون Calibration با برچسب `model_estimate_not_calibrated`
- AI فقط توضیح می‌دهد و قادر به تغییر تصمیم یا مجوز اجرا نیست

## ⏳ RC1 — Mobile & Production Gate (Implementation Complete; Release Gate Pending)

- decision/evidence panels و strict plan visualization
- PostgreSQL 16 persistence با Connection Pool و Migration
- SQLite local/test fallback و Legacy Upgrade
- Request ID، Structured Monitoring و Metrics
- Auth/AI/Heavy/Default Rate Limiting
- Backup/Restore با Manifest و SHA-256
- Password Hash upgrade و Session Token hashing
- Render Blueprint database binding
- Android APK provenance manifest
- SQLite Regression و PostgreSQL integration tests
- پذیرش نهایی فقط پس از Backend/Android CI و `/ready` زنده

## ⏳ GA Quant Alpha 1 — Evidence & Calibration Lab

- Versioned Dataset Manifest و SHA-256
- Point-in-time / survivorship / independent-holdout attestations
- Circular block-bootstrap expectancy interval
- Sign-flip test و multiple-testing Bonferroni control
- Benchmark outperformance interval
- Purged walk-forward + embargo contract
- Monte Carlo drawdown distribution
- Simulated risk-of-ruin با برچسب غیرکالیبره
- Brier Score، Brier Skill، ECE، MCE، Log Loss و Reliability bins
- Calibration ID فقط پس از Gate مستقل holdout
- خروجی فقط `RESEARCH_CANDIDATE`؛ هرگز Live authorization نیست

## ⏳ GA Data Alpha 1 — Historical Data Pipeline

- Provider-agnostic historical adapters
- OKX paginated USDT-SWAP history
- TwelveData bounded time-series
- Yahoo range-limit fail-fast
- finalized-candle-only
- UTC normalization، dedup و gap diagnostics
- Canonical SHA-256 و immutable Dataset Version
- PostgreSQL schema v2 و Gzip candle registry
- User-scoped dataset isolation
- authenticated collect/list/manifest API
- Real OKX smoke بدون ادعای Holdout یا Edge

## ⏳ GA Research Alpha 1 — Stored Backtest & Purged Walk-forward

- user-scoped stored dataset execution
- fixed configuration fingerprint و freeze-time gate
- retrospective result هرگز Holdout نیست
- train-only parameter selection
- embargo >= lookahead
- non-overlapping OOS windows
- sparse OOS return/source-index mapping
- fold fingerprint و deterministic rerun
- Quant Evidence فقط روی Activated OOS trades
- zero-edge null benchmark با limitation صریح
- Live authorization همیشه false

## ⏳ GA Robustness Alpha 1 — Market Baseline & CSCV/PBO

- same-window always-long baseline in comparable R units
- strategy-panel contract
- contiguous block partition
- combinatorially symmetric cross-validation
- IS-only strategy selection
- selected-strategy OOS rank
- Probability of Backtest Overfitting estimate
- minimum panel/observation/combination gates
- deterministic panel fingerprint
- stable-panel و data-mined-panel tests
- final holdout همچنان اجباری و Live خاموش

## ⏳ GA Validation Alpha 1 — Automated Panel & Final Holdout

- automated parameter-grid panel
- immutable experiment ID/version
- PostgreSQL schema v3 research lock
- development/embargo/final-holdout partition
- holdout not consumed when PBO fails
- one selected configuration evaluated once
- PSR و Deflated Sharpe diagnostics
- expected maximum Sharpe multiple-trial threshold
- final holdout quant/baseline gates
- stored idempotent result و conflict detection
- Live authorization همیشه false

## ⏳ GA BYOK Alpha 1 — Encrypted Provider Settings

- Android Secure API Vault UI
- AES-256-GCM server-side encryption
- PostgreSQL schema v4 user secret table
- Groq/OpenAI/TwelveData/Finnhub/NewsAPI/OANDA slots
- no plaintext storage یا read-back
- user-scoped runtime provider routing
- user-scoped AI cache namespace
- personalized Finnhub/NewsAPI headlines
- OANDA Practice test و Live execution خاموش

## ⏳ GA Paper Alpha 1 — Paper OMS & Execution Safety

- default-disabled paper mode و engaged kill switch
- user-scoped order/fill/event ledger
- idempotency key + request hash
- accepted/working/partial/filled/canceled states
- conservative bid/ask/slippage/fee fills
- GTC/IOC/FOK
- partial fills و weighted average
- PostgreSQL FOR UPDATE concurrency guards
- kill-switch mass cancellation
- reconciliation diagnostics
- Android Paper Command UI
- live_routed=false
