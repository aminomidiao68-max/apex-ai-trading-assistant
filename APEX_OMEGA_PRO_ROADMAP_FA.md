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

## ⏳ GA Paper Alpha 2 — Portfolio Equity Ledger

- paper cash/equity account
- signed positions و weighted average entry
- position netting و direction flip
- realized/unrealized PnL
- fee ledger و mark-to-market
- peak/daily-start equity
- automatic daily-drawdown kill switch
- PostgreSQL schema v6
- Android Equity/Position dashboard

## ⏳ GA Paper Alpha 3 — Automated Real Quote Feed

- Opt-in per-user Crypto subscription
- real public OKX best bid/ask with explicit source label
- conservative available-liquidity size
- stale/future/crossed quote rejection
- deterministic Tick Event ID and payload conflict detection
- retry-safe duplicate Tick processing without duplicate fills
- PostgreSQL schema v7 market-tick ledger
- database lease for multi-worker polling
- sanitized error backoff
- Android Feed status/subscribe/sync controls
- Forex automated feed intentionally excluded until equivalent real bid/ask source exists
- live_routed=false و Live Execution خاموش

## ⏳ GA Paper Alpha 4 — Margin, Funding & Liquidation

- controlled leverage and margin-utilization gate
- isolated and conservative cross margin
- initial/maintenance/free margin metrics
- partial-close margin release and direction-flip reallocation
- signed idempotent funding ledger
- estimated liquidation price
- conservative bid/ask liquidation with fee/slippage
- automatic kill switch after liquidation
- PostgreSQL schema v8 margin event ledger
- Android leverage/margin dashboard
- exchange-specific tiers, ADL and insurance fund remain future work
- live_routed=false و Live Execution خاموش

## ⏳ GA Paper Alpha 5 — Recovery, Concentration & Testnet Shadow

- Binance/Bybit public Testnet connectivity probes
- latency and server-clock offset diagnostics
- durable connector checkpoints and exponential backoff
- user-scoped idempotent shadow reconciliation
- provider verification explicitly false for user snapshots
- full order/fill/event/position/account ledger audit
- symbol, structural risk-group and directional concentration gates
- fill-time recheck for working orders
- Android checkpoint/audit dashboard
- authenticated private Testnet reconciliation remains future work
- live_routed=false و Live Execution خاموش

## ⏳ GA Paper Alpha 6 — Statistical Correlation & Private Testnet Read-Only

- immutable stored-dataset correlation snapshots
- aligned log returns, deterministic winsorization and shrinkage
- canonical matrix/cluster SHA-256
- statistical cluster concentration at submit and fill
- structural proxy remains explicit fallback
- encrypted Binance/Bybit Testnet API key + secret slots
- signed private GET probes only
- no Place/Cancel and no Testnet/Live order routing
- PostgreSQL schema v10
- Android secure Testnet secret entry

## ⏳ GA Paper Alpha 7 — Authenticated Testnet Read-Only Reconciliation

- signed private GET for Binance/Bybit Testnet orders and fills
- provider-authenticated read-only snapshots
- external client-ID to Paper order-ID reconciliation
- persistent reconciliation ledger
- deterministic offline recovery/backoff drill
- no Place/Cancel and no Testnet/Live routing
- PostgreSQL schema v11

## ⏳ GA Paper Alpha 8 — Deterministic Chaos & Recovery
- immutable gzip/SHA paper-ledger snapshots
- isolated restore verification
- seven deterministic crash/retry/lease/backoff scenarios
- simulated event-RPO and step-RTO
- production chaos disabled
- separate Render staging blueprint
- no order routing and Live disabled

## ⏳ GA Paper Alpha 9 — Testnet Place/Cancel Safety
- independent disabled-by-default testnet flag and kill switch
- staging-only signed Place/Cancel
- symbol/notional/open-order limits
- idempotency and unknown-state fail closed
- encrypted user-scoped credentials
- production and live routing disabled

## ⏳ Operational Alpha 10 — Drift & SLO Gates
- immutable dataset PSI/KS/volatility drift
- stable/watch/blocked gates
- persisted drift runs
- API latency/error SLO snapshots
- no probability or live authorization claims

## ⏳ Operational Alpha 11 — Promotion Panel
- three consecutive stable drift windows
- within-SLO and database-readiness gates
- persisted idempotent panel
- never authorizes Testnet or Live

## ⏳ Release Alpha 12 — Supply Chain Security
- strict dependency audit with zero known vulnerabilities
- Bandit static security gate
- Python/Android CycloneDX SBOM
- canonical OpenAPI fingerprint
- honest debug APK provenance
- no production signing claim

## ⏳ Release Alpha 13 — Play App Signing Gate
- manual approved signed-AAB workflow
- temporary upload-keystore materialization
- release unit/lint/bundle and strict signature verify
- fail closed without secrets
- no signed artifact claim before key provisioning

## ⏳ Signal Intelligence Alpha 14 — Intraday Fusion
- causal 5m/15m triggers with 1h/4h context
- precision-first nine hard gates
- real crypto flow requirement
- honest Forex proxy
- no AI override or live authorization
