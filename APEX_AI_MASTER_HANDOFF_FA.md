# APEX AI Trading Assistant — Master Project Handoff

> **سند مرجع جامع برای بازیابی کامل Context پروژه و ادامه کار بدون نیاز به این گفتگو**  
> نسخه سند: `1.0`  
> وضعیت Baseline زنده در زمان ثبت اولیه: `3.0.0-rc1`؛ Candidate فعلی: `3.4.0-paper-alpha3`  
> تاریخ Snapshot: `2026-07-14`  
> زبان مرجع: فارسی؛ نام فیلدها، مسیرها و قراردادهای کد انگلیسی باقی مانده‌اند.

---

## 0) روش استفاده از این فایل در گفتگوی آینده

اگر گفتگوی فعلی از بین رفت، این فایل را به Agent بعدی بده و بگو:

> «این سند Master Handoff پروژه APEX است. آن را به‌عنوان Context معتبر بخوان، سپس فقط وضعیت Remote/Live را سریع Verify کن و بدون بازکشف معماری یا تکرار کارهای انجام‌شده، پروژه را از بخش Next Steps ادامه بده.»

Agent بعدی باید:

1. این سند را کامل بخواند.
2. `origin/main` و Live `/health` و `/ready` را Verify کند.
3. Remote GitHub را منبع حقیقت بداند؛ Git metadata محلی Arena ممکن است عقب برگردد.
4. قبل از هر تغییر، اصول غیرقابل‌مذاکره بخش 2 را حفظ کند.
5. هیچ Secret، Token، Password، Connection String یا API Key درخواست یا چاپ نکند.
6. Live Execution را بدون دستور کاملاً صریح و یک Gate مستقل فعال نکند.
7. هیچ سود، Win Rate، دقت یا احتمال موفقیت را تضمین نکند.

این فایل **هیچ Secret واقعی** ندارد. تمام Secretهای واقعی فقط در Secret Store سرویس‌ها قرار دارند.

---

## 1) شناسنامه و وضعیت نهایی پروژه

| مورد | مقدار |
|---|---|
| نام | APEX AI Trading Assistant / APEX Omega Pro |
| نوع محصول | دستیار معاملاتی Mobile-first برای Crypto و Forex |
| Android | Kotlin + Jetpack Compose |
| Backend | FastAPI + Python |
| Production DB | PostgreSQL 16 |
| Local/Test DB | SQLite |
| نسخه زنده | `3.0.0-rc1` |
| Android versionCode | `66` |
| GitHub Repo | https://github.com/aminomidiao68-max/apex-ai-trading-assistant |
| GitHub branch مرجع | `main` |
| Current main SHA | `961851e66511b125db03d4345c3a44519757ea4e` |
| Render API | https://apex-ai-trading-assistant.onrender.com |
| OpenAPI | https://apex-ai-trading-assistant.onrender.com/openapi.json |
| Swagger | https://apex-ai-trading-assistant.onrender.com/docs |
| وضعیت Release | Release Candidate نهایی؛ GA/Live Trading هنوز جداست |
| Live Execution | `false`؛ عمداً خاموش |
| External AI | پیش‌فرض خاموش |
| AI Provider فعلی | `deterministic` |
| Forex Order Flow | پروکسی شفاف با `is_real=false` |

### Live Snapshot تأییدشده

`GET /health`:

```json
{
  "status": "ok",
  "app": "Apex AI Trading API",
  "version": "3.0.0-rc1",
  "env": "production"
}
```

`GET /ready`:

```json
{
  "status": "ready",
  "database": {
    "connected": true,
    "backend": "postgresql",
    "persistent": true,
    "migration_current": true,
    "production_database_ready": true
  },
  "live_execution_enabled": false
}
```

`GET /api/v1/ai/status`:

- `selected_provider=deterministic`
- `external_ai_enabled=false`
- `deterministic_fallback_ready=true`
- `deterministic_core_can_be_overridden=false`
- OpenAI-compatible و Gemini در معماری موجودند ولی Key/Provider خارجی فعال نیست.

`GET /api/v1/system/readiness` در Snapshot نهایی:

- `overall_status=partial`
- `ready_count=10`
- `warning_count=5`
- `missing_count=0`
- علت پنج Warning فقط Broker Connectorهای اختیاری و خاموش است.
- APP_ENV، Firebase، TwelveData، Finnhub، AI deterministic، PostgreSQL، Backup Policy، Rate Limit و Live-Execution-off همگی Ready گزارش شده‌اند.

### وضعیت Connectorها

همه در `dry-run` و بدون Credential اجرایی هستند:

- Binance Futures: خاموش/بدون Credential
- Bybit: خاموش/بدون Credential
- OANDA: خاموش/بدون Credential
- MT5: Foundation-only؛ Bridge واقعی تکمیل نشده
- cTrader: Foundation-only؛ Routing واقعی تکمیل نشده

---

## 2) تصمیم‌ها و اصول غیرقابل‌مذاکره کاربر

کاربر صریحاً خواست حداکثر توان و سخت‌گیری روی پروژه گذاشته شود و موتور ICT/SMC، Order Flow، Signal، Risk، Chart، Setups، Backtest و AI حرفه‌ای و محافظه‌کارانه شوند.

سه انتخاب معماری قطعی کاربر:

1. **AI Provider-agnostic**؛ قابل اتصال به OpenAI، Gemini یا مدل سازگار دیگر؛ تصمیم اصلی Deterministic و قابل تست بماند.
2. **Forex Order Flow فقط پروکسی شفاف**؛ هرگز CVD واقعی جعلی برای Forex تولید نشود؛ `is_real=false`.
3. **تحویل مرحله‌ای با Test Gate**؛ Alphaها و RC فقط پس از Backend/Android/Live Gate بسته شوند.

اصول ثابت:

- Default همیشه `NO_TRADE` است.
- AI اجازه Override تصمیم Deterministic را ندارد.
- هیچ Probability بدون Calibration به‌عنوان احتمال واقعی معرفی نمی‌شود.
- Label فعلی احتمال: `model_estimate_not_calibrated`.
- هر تصمیم باید Evidence، Negative Evidence، Hard Gates و Invalidation داشته باشد.
- در نبود داده حیاتی، سیستم باید Refuse یا Watch/No-Trade کند، نه اینکه داده بسازد.
- هیچ Plan Line برای Setup ردشده باقی نمی‌ماند.
- هیچ Order Flow پروکسی به‌عنوان Real Exchange Flow معرفی نمی‌شود.
- هیچ بک‌تست یا Walk-forward تضمین عملکرد آینده نیست.
- Live Execution و Broker Routeها تا یک پروژه مستقل Approval/Testnet/Legal/Risk Gate خاموش می‌مانند.
- Secretها نباید وارد Git، Log، API Response، Artifact یا این سند شوند.

---

## 3) معماری کلان فعلی

### Android

- Kotlin `1.9.24`
- Jetpack Compose
- Android Gradle Plugin `8.7.3`
- Gradle Wrapper `8.9`
- JDK `17`
- compileSdk/targetSdk `35`
- minSdk `26`
- Retrofit `2.11.0`
- OkHttp `4.12.0`
- Gson converter
- Firebase Messaging foundation
- Stable committed debug signing key برای نصب Update روی نسخه Debug
- Release base URL: Render production URL
- هر Request Android دارای `X-Request-ID` UUID است.

### Backend

- Python 3.12 در CI/Container
- FastAPI `0.116.1`
- Pydantic `2.11.7`
- Uvicorn `0.35.0`
- HTTPX `0.28.1`
- Psycopg `3.2.9` با binary و pool extras
- PostgreSQL 16 در Production
- SQLite local/test fallback
- WebSocket برای Market snapshot
- Deterministic engines برای Signal/Risk/Decision/Backtest
- Optional external AI explanation adapters

### Production

- Render Web Service
- Render PostgreSQL با نام منطقی `apex-ai-postgres`
- Database name: `apex_ai`
- PostgreSQL major: `16`
- `DATABASE_URL` از Secret/Render اتصال داده شده؛ مقدار آن نباید نمایش داده شود.
- Health check path: `/ready`
- Auto-deploy از GitHub `main`
- Render Device Token استفاده‌شده برای Provision پس از پایان Revoke و حذف شده است.
- GitHub OAuth Tokenهای Device Flow نیز پس از هر Push حذف شده‌اند.

### Data Flow خلاصه

```text
Market Provider(s)
  -> normalized Candle model
  -> data quality + market regime
  -> deterministic SMC/ICT engine
  -> real crypto order flow / honest forex proxy
  -> strict decision hard gates
  -> setup lifecycle state machine
  -> portfolio risk gate
  -> evidence packet
  -> deterministic or verified external AI explanation
  -> Android Explainability/Chart/Setup/Risk UI
```

---

## 4) روند ساخت از صفر تا RC1

### 4.1 شروع پروژه — 2026-07-01

اولین Commit:

- `5a0bace828259bc9707ccb2a8caad5bfe708cea5`
- `Initial APEX AI final delivery`

بنیان اولیه شامل Android، Backend، Auth، Market UI، Signal/Risk/Backtest/Journal foundation و GitHub Actions بود. در روزهای بعد Build Android، Theme، Firebase config و provider fallbackها تعمیر شدند.

### 4.2 Premium UI و Mobile foundation — 2026-07-03 تا 2026-07-05

- Premium bilingual polish
- Neon splash/dashboard redesign
- Phase 2 premium visual redesign
- Portrait splash asset
- Render WebSocket support
- Text-field visibility fixes
- Dashboard compile fixes
- Luxury polish برای Signals/Analytics/Backtest/Readiness
- 1m timeframe در Signal/Chart/Backtest

### 4.3 فازهای 1 تا 18 محصول — 2026-07-05

فازها به‌ترتیب:

1. Signal Engine Pro + selectable timeframe
2. Persian Signal polish
3. Institutional Signal panel
4. Backtest Pro Lab + Analytics Board
5. Trade Journal Pro + Performance Intelligence
6. Smart Alerts Pro + Market Focus Board
7. Broker Execution Pro + Risk Command Center
8. AI Strategy Lab + Elite Scanner Board
9. Portfolio Command + Multi-Asset Board
10. Mission Control UI
11. Elite Portfolio Flow + Capital Allocation
12. Quant Ops Center + Advanced Decision Matrix
13. Prime AI Cockpit + Executive Signal Radar
14. Institutional Overview Grid + Tactical Response Board
15. Supreme Control Layer + Global Market Pulse
16. Institutional AI Matrix + Final Executive Layer
17. Ultimate Decision Stack + Omni Market Command
18. Final Premium Unification + Production Candidate

پس از Phase 18 چند Build-rescue و Compose compile fix انجام شد تا Screenها دوباره compile-safe شوند.

### 4.4 Firebase، Liquidity Timing و Dashboard stabilization

- Firebase JSON env support برای Real Push foundation
- Liquidity timing box
- Tehran/UTC toggle
- Dashboard state/remember fixes
- Clean Dashboard rewrite
- Navigation callbacks و News screen wiring

### 4.5 News integration stabilization

Finnhub integration چند بار به‌دلیل Route placement، import order، invalid key و fallback رفتار ناپایدار داشت. تعمیرات نهایی:

- `/api/v1/news/*` با prefix درست
- Async Finnhub wiring
- invalid-key detection
- Persian fallback
- sanitized provider errors
- no raw URL/API key in response/log

### 4.6 Phase C — تکامل SMC/ICT

#### Phase C اولیه

- BOS
- CHoCH
- Order Block
- FVG
- Breaker
- Inducement/Liquidity
- Endpoint `/api/v1/analysis/smc`
- Android Chart Analysis UI

#### v2

- Killzones
- Liquidity
- Order flow proxy foundation
- AI narrative اولیه
- Candlestick Canvas
- Symbol/Timeframe selector
- Dashboard live AI card

#### v3

- Visible-range scaling
- Dedup liquidity
- RR
- HTF bias
- Premium/Discount
- Signal scan endpoint
- TradingView-style chart

#### v4

- Setup classifier
- BOS/CHoCH/Liquidity/Breaker/FVG/ORB
- Entry zone
- TP1/TP2/TP3
- Invalidation
- MTF alignment
- News block
- Volume spike
- Plan lines

#### v6/v7 Ultra

- Close-confirmed BOS/CHoCH
- Structural-leg Fibonacci OTE 62–79%
- VWAP
- OB/FVG quality
- POI stacking
- Absorption/Climax
- CVD divergence foundation
- 20-factor confluence
- A+ تا F grade
- Watching setups
- 20-pair scanner
- Session killzone fixes
- Persian AI narrative

#### v8 Ultra

Indicator suite:

- RSI
- MACD
- Stochastic
- Bollinger Bands
- ADX
- CCI
- Williams %R
- MFI
- CMF
- PSAR
- Ichimoku
- EMA
- Pattern recognition
- Divergence

#### v8.1 و Chart overhaul

- Fix `plan_lines` UnboundLocalError
- Plan lines فقط برای Grade/Compliance معتبر
- TradingView-style chart
- KZ full-height
- Right price axis
- Volume pane
- OB/FVG/BRK boxes
- BOS/CHoCH arrows
- IDM labels
- Entry/Safe SL/TP pills
- Omega action chip
- Legend و collision fixes

### 4.7 نسخه‌های Stability قبل از Omega Pro

#### v2.1.6 — Stability & Security

- Signal/Backtest 500 fix
- Risk direction validation
- HTF alignment fix
- Bearer/OpenAPI security
- User-scoped data
- CORS allowlist
- Finnhub config cleanup
- Regression tests و Backend CI
- Android SDK 35 / Gradle 8.9
- Live execution خاموش

#### v2.1.7 — Universal Chart Stability

- Overlay index rebasing
- Visible-candle scaling
- Killzone/liquidity/label collision reduction
- Disable session overlay در 4h/1d
- Yahoo fallback
- TwelveData 429 circuit/stale cache
- Timeframe normalization
- Provider error sanitization
- Local HTF resampling
- 70/70 matrix validation

#### v2.1.8 — Simplified Professional Chart

- حذف شلوغی Chart
- حداکثر دو Killzone
- حداکثر Bull/Bear OB
- محدودکردن BOS/CHoCH/IDM
- فقط Entry/Safe SL/TP1 روی Chart اصلی
- FVG/Breaker/Fib در Detail باقی ماندند

#### v2.1.9 — Institutional Zones

- OB/FVG تا اولین revisit
- Bull/Bear prioritization
- یک Breaker مهم
- BSL/SSL و EQH/EQL
- Zone lifecycle/end_idx

#### v2.2.0 — Trading Setups Hub

- Bottom nav ساده‌تر
- Scanner روی 10 symbol × 7 timeframe = 70 ترکیب
- Confirmed/Forming/Invalidated sections
- Filter و deep-link به Chart
- Setup type واقعی؛ بدون synthetic signal

#### v2.2.1 — Network & Demo Resilience

- GET retry و exponential backoff
- Cold-start timeout
- Cache
- Demo-safe public analysis
- Expired-token logout
- Friendly sanitized network errors

#### v2.2.2 — Deep Stability Audit

- Dashboard public data بدون Auth dependency
- Demo-safe Journal/Analytics/Backtest
- Stable debug signing
- Setup refresh cooldown
- Security headers
- DB persistence warning
- GitHub Actions updates

#### v2.2.3 — Chart Visual Polish

- BSL/SSL/EQH/EQL dedup
- Legend LTR scroll
- Compact labels
- Scroll reset
- Collision filter
- Android ChartRenderPolicy tests

---

## 5) Omega Pro Alpha 1 — Strict Core

Commit:

- `90c50424de39262bd2751f7af4ce35341bfe3280`
- `feat: add Omega Pro strict quality, regime and decision core`

فایل‌ها:

- `backend/app/services/market_quality_engine.py`
- `backend/app/services/strict_decision_engine.py`
- `OMEGA_PRO_ALPHA1_REPORT_FA.md`
- `APEX_OMEGA_PRO_ROADMAP_FA.md`

### Data Quality

Score صفر تا 100 بر اساس:

- sample size
- OHLC integrity
- timestamp strictly increasing
- duplicate
- timeframe-aware gap
- outlier
- volume coverage
- market-aware volume semantics
- خروجی `tradable`

### Market Regime

- `trending`
- `balanced`
- `volatile`
- `compressed`
- `choppy`
- `risk_multiplier`

### Strict Decision

Action labels:

- `STRONG_LONG`
- `LONG`
- `STRONG_SHORT`
- `SHORT`
- `WATCH`
- `NO_TRADE`

Probability همیشه:

```text
probability_is_calibrated=false
probability_label=model_estimate_not_calibrated
```

Hard Gates پایه Alpha 1:

1. data_quality
2. data_integrity
3. direction
4. grade
5. confluence
6. estimated_probability
7. risk_reward
8. news_clear
9. htf_alignment
10. market_not_choppy
11. conflict_budget
12. trade_plan

در نسخه‌های بعد Gateهای Order Flow و Invalidation اضافه شدند.

نتیجه Alpha 1:

- 70 ترکیب Scan
- Confirmed سخت‌گیرانه: 2 در Snapshot آن مرحله
- Forming: 20
- Data Quality نمونه Confirmed: 100
- Backend regression آن مرحله: 10 تست

CI:

- Backend run `29230865205` — success
- Android run `29230865235` — success
- Artifact digest: `17067ec177f01f183dd743ab891817d4b444b2410df22f664a82895944698a41`

---

## 6) Omega Pro Alpha 2 — Real Order Flow

Commit:

- `73aa247a527c4687681aa36c78016b556d45e9e1`
- `feat: add real crypto order flow and honest forex proxy`

فایل اصلی:

- `backend/app/services/orderflow_service.py`

### کشف مهم Provider

Binance Futures از محیط اجرا HTTP 451 می‌داد، از جمله:

- `/fapi/v1/aggTrades`
- `/fapi/v1/depth`
- `/fapi/v1/openInterest`
- `/fapi/v1/premiumIndex`

بنابراین Real Crypto Order Flow به OKX USDT Perpetual Swap منتقل شد.

OKX endpoints:

- `/api/v5/market/trades?instId=BTC-USDT-SWAP&limit=500`
- `/api/v5/market/books?instId=BTC-USDT-SWAP&sz=50`
- `/api/v5/public/open-interest?instType=SWAP&instId=BTC-USDT-SWAP`
- `/api/v5/public/funding-rate?instId=BTC-USDT-SWAP`

### Crypto output

- `source=okx_swap_public`
- `is_real=true`
- confidence
- aggressive buy/sell
- delta
- exchange-specific real CVD
- depth imbalance
- spread bps
- bid/ask walls
- OI / OI USD / OI change
- funding
- large-trade imbalance
- absorption
- climax
- divergence
- cache 20 seconds

نمونه‌های ثبت‌شده BTC:

- 500 trade
- confidence حدود `0.98`
- یک Snapshot pressure sell و delta حدود `-0.2466`
- یک Snapshot pressure buy و delta حدود `0.2903`
- spread ثبت‌شده حدود `0.0159 bps`
- OI USD حدود `1.97B` در Snapshot همان زمان

این داده فقط Real Flow همان صرافی است، نه کل بازار Crypto.

### Forex output

- `source=forex_ohlcv_proxy`
- `is_real=false`
- proxy delta/CVD
- Depth/OI/Funding = `null`
- Disclaimer:

```text
Forex order flow proxy derived from OHLCV/tick-volume; not centralized bid/ask flow.
```

### Gateهای اضافه

- real_orderflow_available
- orderflow_alignment
- execution_spread
- depth_conflict
- funding_crowding (soft)
- orderflow_evidence (soft)

Crypto تا 1h بدون Real Order Flow Actionable نمی‌شود. Spread threshold برابر 8 bps است.

Android:

- REAL OF / PROXY OF badge
- depth
- spread
- OI
- funding
- confidence

CI:

- Backend `29239336456` — success
- Android `29239337159` — success
- Artifact digest: `3047084cc50f1ed539aa6611c75687d365b496f8797141db384ee99974d4d9af`

---

## 7) Omega Pro Alpha 3 — Setup State Machine

Commit اولیه مشکل‌دار:

- `bfe67d024bcf9a0b3f764b7e2ae14c9472ac8f92`
- `feat: add deterministic setup lifecycle state machine`

Repair commit:

- `ba83486f3d64289dadaf5c6eefbf78221d6292ac`
- `fix: restore Alpha 2 order flow and include Alpha 3 state engine`

فایل اصلی:

- `backend/app/services/setup_state_engine.py`

### Stateها

- `forming`
- `armed`
- `confirmed`
- `triggered`
- `invalidated`
- `expired`

Transition اصلی:

```text
FORMING -> ARMED -> CONFIRMED -> TRIGGERED
```

قواعد:

- Trigger: price وارد `entry_low..entry_high` شود.
- Long invalidation: price <= invalidation/SL
- Short invalidation: price >= invalidation/SL
- Strict gate lost before trigger => invalidated
- Expiry timeframe-aware با `expires_after_bars`
- Missing for two scans => expired
- Cooldown سه کندل بعد Invalidated/Expired
- Terminal retention برابر 48h
- Dedup key: `symbol:timeframe:direction:setup_type`

Lifecycle fields:

- lifecycle_state
- first_seen_at
- last_seen_at
- armed_at
- confirmed_at
- triggered_at
- terminated_at
- expires_at
- cooldown_until
- transition_reason
- scan_count
- missing_scans
- state_version

Scanner response:

- active
- forming
- armed
- confirmed
- triggered
- invalidated
- expired
- countهای مربوط
- `state_machine=v1`

Android tabs:

- Active
- Armed
- Forming
- Closed

### Incident مهم Alpha 3

Commit اولیه `bfe67d0` ناخواسته فایل‌های Alpha 2 را حذف کرده بود:

- `backend/app/services/orderflow_service.py`
- `OMEGA_PRO_ALPHA2_ORDERFLOW_REPORT_FA.md`

همچنین State Engine و گزارش Alpha 3 در Commit وارد نشده بودند و `android/gradlew` executable نبود.

نتیجه CI اولیه:

- Backend run `29243093060` failure
- خطا: `ModuleNotFoundError: No module named 'app.services.orderflow_service'`
- Android run `29243093063` failure
- exit 126 به‌علت gradlew permission

Repair:

- Restore فایل‌های Alpha 2
- Add State Engine/Report
- `chmod +x android/gradlew`
- Workflow نیز قبل Build `chmod +x gradlew` می‌زند.

CI Repair:

- Backend `29248261588` — success
- Android `29248261571` — success
- Artifact digest: `c01ebbe0cbeea3868654139addaa695c9a5412f343a5a2ca1e9ec4756467325d`

---

## 8) Alpha 4 — Portfolio Risk & Conservative Backtest

Commit:

- `1cfdf50b24e853b5114e5ab71438800eee4f8946`
- `feat: add Alpha 4 portfolio risk and conservative backtesting`

### Risk Engine

فایل:

- `backend/app/services/risk_engine.py`

از Position Size ساده به Policy Engine ارتقا یافت.

Risk hard gates فعلی:

1. direction
2. stop_geometry
3. daily_loss
4. trade_frequency
5. loss_streak
6. position_count
7. drawdown
8. execution_spread_known
9. execution_spread
10. execution_slippage
11. open_risk_budget
12. portfolio_heat
13. correlation_exposure
14. effective_stop

خروجی:

- base_risk_amount
- adjusted risk
- risk multiplier
- position size
- effective stop
- execution cost
- portfolio heat
- open-risk percentage
- correlated risk
- remaining risk budget
- drawdown multiplier
- volatility multiplier
- hard/failed gates

Drawdown:

- تا reduction threshold: multiplier=1
- بین reduction threshold و max drawdown: کاهش خطی
- در max drawdown: block کامل

Correlation:

- Explicit correlation اگر داده شود
- در نبود آن `structural_proxy`
- Forex currency exposure با base/quote vector
- Crypto/index/metals bucket proxy
- هرگز Proxy به‌عنوان Historical/Measured correlation معرفی نمی‌شود.

Spread/Slippage:

- Measured spread برای Strict approval لازم
- Slippage صریح یا policy default
- Effective stop شامل execution buffer
- extreme/abnormal volatility می‌تواند risk را کاهش دهد.

### Backtest Engine

فایل:

- `backend/app/services/backtest_service.py`

Execution model:

```text
conservative_ohlc_v2
```

قواعد:

- Signal فقط از candleهای بسته‌شده قبل از index ساخته می‌شود.
- Entry باید واقعاً trade شود؛ در غیر این صورت `no_entry`.
- Entry expiry بر حسب bar.
- Same-bar SL+TP => `stop_first` و Loss.
- Adverse stop gap با open بدتر محاسبه می‌شود.
- Favorable TP gap price improvement نمی‌گیرد.
- Overlapping trade پیش‌فرض ممنوع.
- Unclosed trade پیش‌فرض mark-to-market.
- Fee/Spread/Slippage/Funding از Gross R کم می‌شوند.
- Strictly increasing timestamp اجباری.

Trade result:

- activation time
- bars to entry
- exit reason
- gross R
- cost R
- fee R
- funding R
- net R

Summary:

- activated/no-entry
- gross/cost/net R
- expectancy
- profit factor
- max drawdown R
- assumptions
- `anti_lookahead_enforced=true`

Sweep:

- حداقل activated trades برای Ranking
- ranking بر Net R، expectancy، drawdown و sample size

Walk-forward:

- پارامتر فقط از Training
- Test خارج از نمونه

تست محلی آن مرحله: 18 passed.

Android:

- Portfolio Heat
- Correlated Risk
- Risk Budget
- DD/Vol multiplier
- Failed gates
- Gross/Cost/Net R
- Entry activation/no-entry
- Drawdown/fees/funding
- متن UI هیچ سود آینده را تضمین نمی‌کند.

CI:

- Backend `29323998299` — success
- Android `29323998382` — success
- Artifact digest: `480ec1506326d89321b52c698340cab7818e0161da1aa94c9f7961d988282e87`

---

## 9) Alpha 5 — Provider-Agnostic AI & Explainability

Commit:

- `7c98c893822c64af0df4d67a37f3415bcd2ad36e`
- `feat: add provider-agnostic verified AI explainability`

فایل:

- `backend/app/services/ai_explainability_service.py`

### اصل معماری

AI فقط Explanation Layer است. Deterministic Core تنها مرجع Action Label، Risk و Execution eligibility است.

Providerها:

- deterministic
- openai_compatible
- gemini

OpenAI-compatible adapter با Base URL می‌تواند OpenAI یا مدل سازگار دیگر را استفاده کند. External AI opt-in است و در Production فعلی خاموش است.

### Evidence Packet

- immutable deterministic action/status
- symbol/market/timeframe
- risk tier
- positive Evidence IDs
- negative Evidence IDs
- source
- `is_real`
- failed gates
- invalidation
- missing data
- probability calibration label

Negative Evidence اجباری است. اگر تعارض خاصی نباشد:

```text
N_RESIDUAL_UNCERTAINTY
```

اضافه می‌شود.

### Critic/Verifier

موارد ردشده:

- Unknown evidence ID
- Citation بدون source
- Action override
- Entry/SL/TP/position-size invention
- Number invention
- Probability/Win Rate درصدی بدون calibration
- Guaranteed/risk-free claim
- Direct buy/sell/execute command
- Invalidation mismatch
- Extra control fields
- Risk/confirmation without citation

اگر Provider fail/reject شود:

- Output خارجی نمایش داده نمی‌شود.
- Deterministic fallback فعال می‌شود.
- Raw provider error/API key/URL به Client نمی‌رسد.

Missing critical data => refusal قبل از provider call.

Reliability:

- timeout
- hash cache
- circuit breaker
- failure threshold/cooldown
- no redirect
- generic `provider_unavailable`

API:

- `GET /api/v1/ai/status`
- `POST /api/v1/ai/explain` (Bearer)

Android Explainability Panel:

- provider
- mode
- verified/refused
- deterministic label
- positive/negative evidence
- what would confirm
- invalidation
- calibration label
- deterministic core lock

تست آن مرحله: 28 passed.

CI:

- Backend `29327904604` — success
- Android `29327904619` — success
- Artifact digest: `1010b8384d2be5cfae4f04254832a0727fe04b181f3543836054e80f1226f4f8`

---

## 10) RC1 — Production & Release Candidate

Feature commit:

- `82ac9fcbe330a80c323766554ead3f39338d4a83`
- `feat: harden production infrastructure for RC1`

Repair commit نهایی:

- `961851e66511b125db03d4345c3a44519757ea4e`
- `fix: run PostgreSQL integration through Python module path`

### PostgreSQL

فایل:

- `backend/app/services/database_service.py`

ویژگی‌ها:

- SQLite/PostgreSQL adapter مشترک
- `DATABASE_URL` production
- `DATABASE_PATH` فقط local/test
- Psycopg connection pool
- `?` -> `%s` translation
- `RETURNING id`
- dict-row compatibility
- startup migration
- schema version check
- fail-closed readiness

Schema version فعلی: `1`

Tables:

- schema_migrations
- users
- sessions
- signals
- trades
- device_tokens
- notification_events

PostgreSQL:

- BIGSERIAL
- BIGINT user IDs
- idempotent `ADD COLUMN IF NOT EXISTS`
- indexes

SQLite:

- Legacy in-place upgrade
- integrity check
- local/test only

**توجه:** PostgreSQL Production در RC1 تازه Provision شد. داده تاریخی SQLite ephemeral به PostgreSQL منتقل نشد؛ Production DB از Schema جدید شروع شده است.

### Auth hardening

فایل:

- `backend/app/services/auth_service.py`

- Session token خام ذخیره نمی‌شود؛ SHA-256 digest ذخیره می‌شود.
- Password جدید PBKDF2-SHA256 با 310,000 iteration.
- Legacy password hash بعد Login موفق rehash می‌شود.
- DB constraint/error خام به Client نمی‌رسد.

### Production Guard

فایل:

- `backend/app/services/production_guard_service.py`

قابلیت‌ها:

- X-Request-ID
- X-Response-Time-Ms
- structured JSON HTTP logs
- route template، نه raw query
- client hash، نه IP خام
- request count
- 5xx count
- rate-limit count
- average/p95 latency
- body-size limit: 2 MiB
- generic 500 with request ID

Rate limits در دقیقه:

- Auth: 10
- AI: 20
- Heavy: 15
- Default: 120

Rate limiter فعلی In-process است. برای چند Replica باید Redis-backed state اضافه شود.

Security headers:

- HSTS production
- CSP
- X-Content-Type-Options
- X-Frame-Options
- Referrer-Policy
- Permissions-Policy
- no-store برای Auth/AI

### Health/Metrics

- `/health` public liveness
- `/ready` public readiness و fail-closed برای DB
- `/api/v1/system/health/deep` protected
- `/api/v1/system/metrics` protected

### Backup/Restore

- `backend/scripts/backup_database.py`
- `backend/scripts/restore_database.py`
- `backend/scripts/generate_release_manifest.py`
- `docs/rc_production_runbook_fa.md`

Backup:

- PostgreSQL custom pg_dump
- SQLite online backup
- manifest
- SHA-256
- retention cleanup

Restore:

- manifest/digest verify
- explicit `RESTORE_APEX_DATABASE`
- safety copy
- pg_restore exit-on-error

Backup ابزار آماده است ولی Scheduling خودکار هنوز باید با Render Cron/Provider backup policy مدیریت شود.

### Release provenance

Android CI فایل `release-manifest.json` را کنار APK می‌سازد:

- version
- source commit
- APK filename/size
- APK SHA-256
- safety flags
- required gates

Artifact نهایی:

- Name: `apex-ai-rc-debug-apk`
- Run: `29347527842`
- Artifact ID: `8316835416`
- Size: `25,803,719 bytes`
- GitHub Artifact archive digest:

```text
d7fa2d7d1a75d4f256c332e69433c56d993f76007be6a1d32fb7944befc11062
```

توجه: Digest بالا Digest آرشیو GitHub Artifact است؛ Digest خود APK داخل `release-manifest.json` همان Artifact قرار دارد.

### CI نهایی

Backend run:

- `29347527794`
- SQLite regression: success
- PostgreSQL 16 real integration: success
- Auth/Session/Journal/Migration roundtrip روی Postgres واقعی: success

Android run:

- `29347527842`
- Unit tests: success
- Lint: success
- assembleDebug: success
- Release manifest generation: success

Local suite قبل Push:

```text
38 passed, 1 skipped
```

Skipped test فقط Postgres local بود؛ همان test در GitHub CI با PostgreSQL 16 جداگانه success شد.

### Incident PostgreSQL CI

RC feature commit اولیه `82ac9fc`:

- Android success
- Backend SQLite success
- PostgreSQL step collection failure:

```text
ModuleNotFoundError: No module named 'app'
```

علت: اجرای single-file با `pytest` به‌جای `python -m pytest`.

Repair `961851e` فقط workflow را تغییر داد:

- `pytest -q` -> `python -m pytest -q`
- PostgreSQL integration سپس success شد.

### Incident Render Provision

کد RC Deploy شد ولی سرویس موجود Render تحت نام/Slug قبلی و خارج از Blueprint sync بود؛ ابتدا `/ready` چنین گزارش داد:

```json
{
  "status": "not_ready",
  "database": {
    "backend": "sqlite",
    "persistent": false,
    "production_database_ready": false
  }
}
```

این رفتار عمداً fail-closed بود. سپس با Render CLI رسمی Device Authorization:

- Service واقعی از روی slug `apex-ai-trading-assistant` شناسایی شد.
- PostgreSQL 16 با نام `apex-ai-postgres` ایجاد شد.
- Internal `DATABASE_URL` بدون چاپ/ذخیره به Service متصل شد.
- Health path `/ready` تنظیم شد.
- Commit `961851e` Deploy شد.
- `/ready` به 200/PostgreSQL/Persistent/Migration-current رسید.
- Render token بعد عملیات revoke و حذف شد.

---

## 10.5) Post-RC Quant Alpha 1 — Candidate جدید

پس از ارزیابی صادقانه پروژه، بزرگ‌ترین فاصله تا سطح حرفه‌ای‌تر «نبود لایه مستقل اثبات آماری» تشخیص داده شد. Candidate جدید `3.1.0-quant-alpha1` این موارد را اضافه می‌کند:

- `backend/app/services/quant_validation_service.py`
- `backend/scripts/build_dataset_manifest.py`
- `backend/tests/test_quant_validation_service.py`
- `OMEGA_PRO_QUANT_ALPHA1_REPORT_FA.md`
- Endpointهای محافظت‌شده `/api/v1/research/quant-validate` و `/api/v1/research/purged-split-plan`
- Dataset SHA-256/point-in-time/holdout contract
- Circular block bootstrap expectancy interval
- Sign-flip p-value و Bonferroni multiple-testing control
- Benchmark difference interval
- Purged walk-forward/embargo/fold-return matching
- Monte Carlo drawdown و simulated risk-of-ruin
- Brier/Brier Skill/ECE/MCE/Log Loss/Reliability bins
- Calibration ID فقط برای independent holdout واجد شرایط
- `actionable_for_live=false` در تمام پاسخ‌ها

Gate محلی Candidate:

```text
47 passed, 1 skipped
```

این مرحله هیچ Edge یا سودی را جعل نمی‌کند؛ بدون Dataset واقعی و Evidence کامل، فقط `REJECT` یا `INSUFFICIENT_EVIDENCE/WATCH` می‌دهد. بالاترین خروجی `RESEARCH_CANDIDATE` است و مجوز Live نیست.

## 10.6) Post-RC Data Alpha 1 — Historical Pipeline

Candidate `3.1.0-data-alpha1` لایه جمع‌آوری و Registry داده تاریخی را اضافه می‌کند:

- OKX paginated finalized USDT-SWAP candles
- TwelveData bounded time-series
- Yahoo fallback با range-limit fail-fast
- UTC canonicalization، duplicate/gap diagnostics
- Canonical SHA-256
- Immutable dataset ID/version
- PostgreSQL migration/schema v2
- User-scoped dataset isolation
- `quant_datasets` با Manifest و Gzip candles
- APIهای collect/list/manifest با Bearer
- Real OKX smoke: 2 pages، 200 raw، 167 accepted، duplicate/missing صفر
- `53 passed, 1 skipped` در Gate محلی

Dataset به‌صورت خودکار Holdout/Survivorship-controlled معرفی نمی‌شود و Collection هیچ ادعای Edge ندارد.

## 10.7) Post-RC Research Alpha 1 — Stored OOS Pipeline

Candidate `3.1.0-research-alpha1` Dataset Registry را به Backtest/Quant وصل می‌کند:

- Fixed config فقط با freeze time قبل Dataset، Holdout محسوب می‌شود.
- Retrospective run صریحاً `retrospective_not_holdout` است.
- Parameter selection فقط روی Train انجام می‌شود.
- Embargo حداقل برابر Lookahead و Test windows غیرهم‌پوشان‌اند.
- Sparse OOS trade return با Candle source index ثبت می‌شود.
- Fold/config/return fingerprint deterministic است.
- Quant Evidence فقط روی Activated OOS trades اجرا می‌شود.
- Zero-edge benchmark صرفاً Null baseline است.
- Local Gate: `57 passed, 1 skipped`.
- Live authorization در همه Responseها false است.

## 10.8) Post-RC Robustness Alpha 1 — Market Baseline & PBO

Candidate `3.1.0-robustness-alpha1` موارد زیر را اضافه می‌کند:

- same-window always-long benchmark در R units
- Strategy Panel با حداقل پنج Variant
- CSCV روی Blockهای زمانی پیوسته
- انتخاب Strategy فقط در IS
- OOS rank percentile برای Strategy منتخب
- PBO estimate و degradation
- Statusهای `HIGH_OVERFIT_RISK` و `ROBUSTNESS_CANDIDATE`
- Stable-panel test با PBO صفر
- Data-mined-panel test با PBO بالا
- Local Gate: `63 passed, 1 skipped`
- Low PBO نیز مجوز Live یا تضمین آینده نیست.

## 10.9) Post-RC Validation Alpha 1 — Automated Final Holdout

Candidate `3.2.0-validation-alpha1`:

- Parameter Panel را خودکار می‌سازد.
- Final Holdout را قبل از Panel با Experiment ID/version قفل می‌کند.
- PostgreSQL schema v3 نتیجه Experiment را immutable نگه می‌دارد.
- اگر Panel Robust نباشد، Holdout مصرف نمی‌شود.
- فقط یک Config منتخب Development یک‌بار روی Holdout اجرا می‌شود.
- PSR و Deflated Sharpe با multiple-trial expected maximum محاسبه می‌شوند.
- Final gates شامل expectancy CI، market baseline، multiple-testing و DSR هستند.
- اجرای تکراری همان Experiment نتیجه ذخیره‌شده را برمی‌گرداند.
- Local Gate: `71 passed, 1 skipped`.
- `FINAL_HOLDOUT_CANDIDATE` نیز Live authorization نیست.

## 10.10) Post-RC BYOK Alpha 1 — Secure API Vault

Candidate `3.3.0-byok-alpha1`:

- Android Settings دارای Secure API Vault برای Groq/OpenAI/TwelveData/Finnhub/NewsAPI/OANDA است.
- Keyها در Android Preferences ذخیره نمی‌شوند و پس از Save پاک می‌شوند.
- Backend از AES-256-GCM و Associated Data شامل user/provider/version استفاده می‌کند.
- Master Key فقط در Render Secret قرار می‌گیرد.
- PostgreSQL schema v4 جدول user-scoped ciphertext دارد.
- Raw secret read-back وجود ندارد.
- Save/Test/Delete و Status API وجود دارد.
- Groq/OpenAI user-scoped Explanation، TwelveData historical و Finnhub/NewsAPI personalized news را تغذیه می‌کنند.
- OANDA فقط Practice test است و Live خاموش می‌ماند.
- Local Gate: `77 passed, 1 skipped`.

## 10.11) Post-RC Paper Alpha 1 — Paper OMS

Candidate `3.4.0-paper-alpha1`:

- Paper mode پیش‌فرض خاموش و Kill Switch فعال است.
- Order/Fill/Event/Control ledger در PostgreSQL schema v5 ذخیره می‌شود.
- Idempotency key و request hash از Duplicate order جلوگیری می‌کند.
- Market/Limit، GTC/IOC/FOK و Partial Fill شبیه‌سازی می‌شوند.
- Fill برای Buy از Ask و Sell از Bid با adverse slippage/fee محاسبه می‌شود.
- PostgreSQL `FOR UPDATE` از double-fill و race جلوگیری می‌کند.
- Kill Switch تمام سفارش‌های باز را Cancel می‌کند.
- Reconciliation quantity/average/fee/event sequence را بررسی می‌کند.
- Android Broker دارای Paper Command، Arm/Kill، Submit، Cancel و Reconcile است.
- `live_routed=false` و `ENABLE_LIVE_EXECUTION=false` باقی می‌مانند.
- Local Gate: `85 passed, 1 skipped`.

## 10.12) Post-RC Paper Alpha 2 — Portfolio Ledger

Candidate `3.4.0-paper-alpha3`:

- PostgreSQL schema v6 با paper_accounts و paper_positions
- Cash/Equity/Peak Equity و Daily Start
- Signed quantity و weighted average entry
- Position netting، partial close و direction flip
- Realized/Unrealized PnL و Fee ledger
- Mark-to-market با Paper Tick
- Auto Kill Switch در عبور از Daily Drawdown
- Android Equity/Unrealized/DD/Position UI
- `live_routed=false`
- Local Gate: `87 passed, 1 skipped`

## 11) موتور Strict فعلی

Strict gate set فعلی شامل پایه Alpha 1 به‌اضافه Invalidation و Order Flow است:

- data_quality
- data_integrity
- direction
- grade
- confluence
- estimated_probability
- risk_reward
- news_clear
- htf_alignment
- market_not_choppy
- conflict_budget
- trade_plan
- invalidation
- real_orderflow_available
- orderflow_alignment
- execution_spread
- depth_conflict
- funding_crowding (soft)
- orderflow_evidence (soft)

Hard count بسته به Real Order Flow پویاست؛ alignment/spread/depth فقط وقتی flow real است Hard می‌شوند.

Thresholdهای مهم:

- Data Quality >= 78
- Grade: A+/A/B
- Confluence >= 65
- Estimated score >= 68؛ همچنان uncalibrated
- RR >= 2
- Spread <= 8 bps
- Conflict budget بر اساس Grade
- HTF alignment یا reversal exception
- choppy market block مگر confluence بسیار بالا

در `WATCH` یا `REJECT`:

- `risk_multiplier=0`
- plan lines حذف
- Action label Watch/No-Trade
- failed gates و no-trade reason ثبت

---

## 12) Android فعلی

### Main UX

- Persian-first bilingual style
- Premium/Neon theme
- Dashboard
- Setups Hub
- Risk Command Center
- Broker Preview
- Profile/Readiness
- Chart و Signals از Dashboard/Setup detail
- Backtest Lab
- Journal/Analytics
- News

### Chart

- TradingView-inspired Canvas
- Candles + volume
- right price axis
- live price tag
- killzones
- prioritized OB/FVG/Breaker boxes
- BOS/CHoCH
- IDM
- BSL/SSL/EQH/EQL
- Entry/Safe SL/TP lines فقط برای Strict Actionable
- visible-range scaling
- overlay rebasing
- collision control
- symbol/timeframe scroll/reset

### Setup UI

- Active/Armed/Forming/Closed
- Lifecycle badge
- transition reason
- scan count
- expiry/cooldown
- grade/confluence/RR
- entry/SL/TP
- deep-link to chart

### Risk UI

- base/adjusted risk
- position size
- effective stop
- portfolio heat
- correlated risk
- risk budget
- drawdown/volatility multipliers
- failed gates

### Backtest UI

- activated/no entry
- gross/cost/net R
- fees/funding
- max drawdown
- exit reason
- anti-lookahead badge
- execution model
- non-guarantee messaging

### AI Explainability UI

- deterministic action label
- provider/mode
- verified/refused
- evidence IDs
- negative evidence
- what would confirm
- invalidation
- probability not calibrated label
- deterministic core preserved lock

---

## 13) Backend سرویس‌ها و مسیرهای کلیدی

### Core files

- `backend/app/main.py` — FastAPI routes، middleware، scanner integration
- `backend/app/models.py` — تمام Pydantic contracts
- `backend/app/config.py` — env-based settings
- `backend/app/services/smc_engine.py` — SMC/ICT detection
- `backend/app/services/market_quality_engine.py` — quality/regime
- `backend/app/services/strict_decision_engine.py` — strict gates
- `backend/app/services/orderflow_service.py` — OKX real flow/Forex proxy
- `backend/app/services/setup_state_engine.py` — lifecycle
- `backend/app/services/risk_engine.py` — portfolio risk
- `backend/app/services/backtest_service.py` — conservative backtest
- `backend/app/services/ai_explainability_service.py` — adapters/verifier/fallback
- `backend/app/services/database_service.py` — SQLite/Postgres/migration/pool
- `backend/app/services/auth_service.py` — auth/session hashing
- `backend/app/services/storage_service.py` — journal/signals/analytics/notifications
- `backend/app/services/production_guard_service.py` — rate limit/monitoring/request ID
- `backend/app/services/readiness_service.py` — production checks
- `backend/app/services/market_data_service.py` — market providers/cache/fallback
- `backend/app/services/execution_engine.py` — preview/pretrade guard

### Connector files

- `binance_connector.py`
- `bybit_connector.py`
- `oanda_connector.py`
- `mt5_connector.py`
- `ctrader_connector.py`

همه Connectorها باید تا Approval مستقل در dry-run بمانند.

### Tests

- `backend/tests/test_regressions.py`
- `backend/tests/test_alpha4_risk_backtest.py`
- `backend/tests/test_alpha5_ai_explainability.py`
- `backend/tests/test_rc_production_gate.py`
- `backend/tests/test_postgres_integration.py`
- smoke tests برای Auth/Storage/Backtest/Sweep/Walk-forward/Execution/Notifications

### CI

- `.github/workflows/backend-tests.yml`
- `.github/workflows/android-apk-build.yml`

Backend CI PostgreSQL 16 service دارد. Android CI JDK17 + SDK35 را نصب می‌کند و Test/Lint/APK می‌سازد.

---

## 14) API Endpoint Catalog

### Health/System

- `GET /health` — public
- `GET /ready` — public
- `GET /api/v1/system/readiness` — public config summary
- `GET /api/v1/system/health/deep` — Bearer
- `GET /api/v1/system/metrics` — Bearer

### AI

- `GET /api/v1/ai/status` — public، secret-safe
- `POST /api/v1/ai/explain` — Bearer

### Auth

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me` — Bearer
- `POST /api/v1/auth/logout` — Bearer

### Notifications

- `POST /api/v1/notifications/register-device` — Bearer
- `GET /api/v1/notifications/devices` — Bearer
- `POST /api/v1/notifications/test` — Bearer

### Session/News

- `GET /api/v1/sessions/current`
- `GET /api/v1/news/health`
- `GET /api/v1/news/brief`
- `GET /api/v1/news/mock`

### Market/Analysis

- `GET /api/v1/market/overview`
- `GET /api/v1/market/candles`
- `GET /api/v1/analysis/smc`
- `GET /api/v1/signals/scan`
- `GET /api/v1/setups/scan`
- `GET /api/v1/orderflow/{symbol}`
- `WS /ws/market`

### Signal

- `POST /api/v1/signals/analyze` — Bearer
- `POST /api/v1/signals/analyze-and-save` — Bearer
- `POST /api/v1/signals/live-scan` — Bearer
- `GET /api/v1/signals/history` — Bearer

### Risk/Backtest

- `POST /api/v1/risk/plan`
- `POST /api/v1/backtest/run` — Bearer
- `POST /api/v1/backtest/sweep` — Bearer
- `POST /api/v1/backtest/walk-forward` — Bearer

### Analytics/Journal

- `GET /api/v1/analytics/summary` — Bearer
- `GET /api/v1/analytics/report` — Bearer
- `POST /api/v1/trades` — Bearer
- `GET /api/v1/trades` — Bearer
- `GET /api/v1/trades/stats` — Bearer
- `POST /api/v1/trades/{trade_id}/close` — Bearer
- `DELETE /api/v1/trades/{trade_id}` — Bearer

### Execution

- `GET /api/v1/execution/capabilities`
- `POST /api/v1/execution/preview`
- `GET /api/v1/execution/status`
- `POST /api/v1/execution/binance/order` — Bearer، blocked globally
- `POST /api/v1/execution/bybit/order` — Bearer، blocked globally
- `POST /api/v1/execution/oanda/order` — Bearer، blocked globally
- `POST /api/v1/execution/mt5/order` — Bearer، blocked globally
- `POST /api/v1/execution/ctrader/order` — Bearer، blocked globally

Live OpenAPI منبع دقیق schema است:

- https://apex-ai-trading-assistant.onrender.com/openapi.json

---

## 15) Environment Variables — فقط نام و کاربرد

### App

- `APP_NAME`
- `APP_ENV`
- `APP_VERSION`
- `DEFAULT_TIMEZONE`
- `CORS_ALLOWED_ORIGINS`
- `SEED_DEMO_USER`
- `SESSION_TTL_HOURS`

### Database

- `DATABASE_URL` — Production PostgreSQL secret
- `DATABASE_PATH` — Local/test SQLite only
- `DATABASE_POOL_MAX_SIZE`
- `DATABASE_CONNECT_TIMEOUT_SECONDS`
- `BACKUP_RETENTION_DAYS`

### Request Guard

- `RATE_LIMIT_ENABLED`
- `RATE_LIMIT_DEFAULT_PER_MINUTE`
- `RATE_LIMIT_AUTH_PER_MINUTE`
- `RATE_LIMIT_AI_PER_MINUTE`
- `RATE_LIMIT_HEAVY_PER_MINUTE`
- `TRUST_PROXY_HEADERS`
- `MAX_REQUEST_BODY_BYTES`

### Market/News

- `TWELVEDATA_API_KEY`
- `FINNHUB_API_KEY`

### AI

- `AI_PROVIDER`
- `AI_EXTERNAL_ENABLED`
- `AI_OPENAI_BASE_URL`
- `AI_OPENAI_API_KEY`
- `AI_OPENAI_MODEL`
- `AI_GEMINI_BASE_URL`
- `AI_GEMINI_API_KEY`
- `AI_GEMINI_MODEL`
- `AI_TIMEOUT_SECONDS`
- `AI_CACHE_TTL_SECONDS`
- `AI_CIRCUIT_FAILURE_THRESHOLD`
- `AI_CIRCUIT_COOLDOWN_SECONDS`

### Execution/Brokers

- `ENABLE_LIVE_EXECUTION`
- `BINANCE_API_KEY`
- `BINANCE_API_SECRET`
- `BINANCE_FUTURES_BASE_URL`
- `BYBIT_API_KEY`
- `BYBIT_API_SECRET`
- `BYBIT_BASE_URL`
- `OANDA_API_TOKEN`
- `OANDA_ACCOUNT_ID`
- `OANDA_BASE_URL`
- `MT5_SERVER`
- `MT5_LOGIN`
- `MT5_PASSWORD`
- `CTRADER_CLIENT_ID`
- `CTRADER_CLIENT_SECRET`
- `CTRADER_ACCESS_TOKEN`
- `CTRADER_BASE_URL`

### Firebase

- `FIREBASE_PROJECT_ID`
- `FIREBASE_SERVICE_ACCOUNT_JSON`

قانون: مقدار هیچ‌کدام از Key/Token/Password/Connection Stringها نباید در Prompt، Git، Log یا سند قرار گیرد.

---

## 16) Build، Test و Run

### Backend local

```bash
git clone https://github.com/aminomidiao68-max/apex-ai-trading-assistant.git
cd apex-ai-trading-assistant/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m compileall -q app tests scripts
python -m pytest -q
uvicorn app.main:app --reload
```

Local expected:

```text
38 passed, 1 skipped
```

PostgreSQL test locally فقط وقتی `DATABASE_URL` واقعی Test DB وجود دارد اجرا می‌شود.

### Android local

نیازها:

- JDK 17
- Android SDK 35
- Build Tools 35

```bash
cd android
chmod +x gradlew
./gradlew --no-daemon --max-workers=2 testDebugUnitTest lintDebug assembleDebug --stacktrace
```

### Docker

`backend/Dockerfile`:

- Python 3.12 slim
- non-root user
- postgresql-client
- scripts included
- `/ready` healthcheck
- proxy headers

### Backup

```bash
cd backend
python scripts/backup_database.py --output-dir /secure/backups --retention-days 14
```

### Restore

```bash
python scripts/restore_database.py BACKUP_FILE --confirm RESTORE_APEX_DATABASE
```

Restore فقط در maintenance window و پس از backup جدید.

---

## 17) نکات عملیاتی Arena/GitHub/Render

### Arena Git metadata issue

در این محیط فایل‌ها بین Turnها حفظ می‌شوند ولی `.git` ممکن است به HEAD قدیمی برگردد. پیامد:

- `git status` ممکن است تغییرات Alphaهای قبلی را دوباره Modified نشان دهد.
- Remote GitHub منبع حقیقت است.
- برای Push، Commit و Push باید در **یک Tool Call** انجام شوند.
- قبل Push: `git fetch origin main`.
- اگر local history diverged شد، فقط فایل‌های مرحله جاری را روی `origin/main` restore/commit کنید.
- هرگز Force Push نکنید.

### GitHub OAuth

- Device Flow رسمی استفاده شد.
- Codeها 10–15 دقیقه اعتبار داشتند و گاهی expired می‌شدند.
- Access Token فقط همان Tool Call استفاده و سپس حذف می‌شد.
- هیچ Token نباید در Workspace باقی بماند.

### Render OAuth/Provision

- Render CLI official device grant استفاده شد.
- اولین parser سرویس را به‌دلیل نام متفاوت پیدا نکرد؛ Token revoke شد و هیچ تغییری انجام نشد.
- بار دوم Slug واقعی `apex-ai-trading-assistant` استفاده شد.
- DB ایجاد، env متصل، deploy verify و token revoke شد.

### Local Android audit limitations

Local Sandbox ابتدا:

- JDK 11 داشت؛ پروژه JDK 17 می‌خواست.
- Maven TLS با JDK11 fail شد.
- JDK17 موقت دانلود شد.
- Gradle 2GB heap با memory sandbox kill شد.
- Android SDK محلی نبود.
- نصب موقت SDK به space limit خورد.

اینها خطای کد نبودند؛ GitHub CI استاندارد JDK17/SDK35 تمام Android Gateها را با موفقیت اجرا کرد.

---

## 18) مشکلات مهمی که نباید دوباره کشف شوند

1. Binance Futures public order-flow endpoints از محیط موردنظر HTTP 451 دادند؛ Real Order Flow فعلی OKX است.
2. Forex centralized tape ندارد؛ فقط proxy با `is_real=false`.
3. Alpha 3 commit اولیه orderflow را حذف کرده بود؛ Repair `ba83486` canonical است.
4. `android/gradlew` executable و workflow chmod هر دو لازم‌اند.
5. Backend single-test CI باید با `python -m pytest` اجرا شود تا `app` import شود.
6. Existing Render service ابتدا Blueprint-managed نبود؛ PostgreSQL دستی با CLI رسمی متصل شد.
7. `/ready` عمداً Production SQLite را 503 می‌کند.
8. Probability هنوز calibrated نیست؛ score را Real Probability صدا نزنید.
9. Backtest intrabar ambiguity باید stop-first بماند.
10. External AI هیچ‌وقت تصمیم یا execution را تغییر نمی‌دهد.
11. Plan lines برای Watch/Reject حذف می‌شوند.
12. Provider raw errors ممکن است Key/URL داشته باشند؛ همیشه sanitized fallback.
13. `PROJECT_DOCUMENTATION.py` در Commit `fe24062` یک سند تاریخی و قبل از Alpha4/5/RC است؛ بعضی بخش‌های آن مثل SQLite-current/JWT/قدیمی بودن version منبع حقیقت فعلی نیستند. این Master Handoff و Source فعلی بر آن مقدم‌اند.

---

## 19) Known limitations و کارهای آینده

پروژه در RC1 کامل است، اما موارد زیر برای GA/Scale یا Live Trading جداگانه‌اند:

### پیش از GA عمومی

- Soak test چندروزه Render/PostgreSQL
- Scheduled backup automation و Restore drill واقعی
- Alerting خارجی برای 5xx/latency/DB health
- Privacy/Terms/Store compliance review
- Signed release keystore/AAB و Play Console pipeline
- Crash reporting/ANR monitoring
- End-to-end Android device tests
- DB plan/retention/capacity monitoring

### Scale

- Redis-backed distributed rate limiting برای چند Replica
- Distributed cache/lock برای Scanner و AI cache
- Structured logs به observability backend
- Metrics export به Prometheus/OpenTelemetry
- Background jobs/queue برای scanner/notification/backup

### Probability Calibration

- Dataset versioning
- walk-forward/out-of-sample labels
- reliability curve/Brier score
- calibration ID
- فقط پس از آن `probability_is_calibrated=true`

### External AI

- Key و Provider فقط در Secret Store
- default همچنان deterministic
- هزینه/latency budgets
- provider evaluation set
- verifier bypass ممنوع

### Brokers/Live Execution — پروژه مستقل

- Testnet/paper trading طولانی
- Idempotency keys
- order reconciliation
- partial fill handling
- exchange precision/min-notional
- kill switch
- max daily loss server-side
- legal/compliance review
- explicit user approval
- فقط بعد از این مراحل `ENABLE_LIVE_EXECUTION=true`

تا آن زمان هیچ Agent نباید Live Execution را فعال کند.

---

## 20) Definition of Done فعلی

Alpha 1 تا Alpha 5 و RC1 بسته شده‌اند چون:

- Strict deterministic core موجود است.
- Real crypto order flow و honest Forex proxy موجود است.
- Setup lifecycle موجود است.
- Portfolio risk و conservative backtest موجود است.
- Provider-agnostic verified AI explanation موجود است.
- PostgreSQL production persistent است.
- Backend SQLite + PostgreSQL CI سبز است.
- Android Unit/Lint/APK CI سبز است.
- Render `/ready=200` و migration current است.
- Release manifest تولید می‌شود.
- Live execution خاموش است.

---

## 21) Quick Recovery Checklist برای Agent بعدی

```text
[ ] Read this file completely
[ ] Verify GitHub main == 961851e66511b125db03d4345c3a44519757ea4e or inspect newer commits
[ ] Verify /health version
[ ] Verify /ready backend=postgresql, persistent=true, migration_current=true
[ ] Verify latest Backend and Android Actions are green
[ ] Never use local Git metadata as sole truth in Arena
[ ] Never request/print secrets
[ ] Keep NO_TRADE default
[ ] Keep Forex is_real=false
[ ] Keep probability uncalibrated label
[ ] Keep AI unable to override deterministic core
[ ] Keep live execution disabled
[ ] Add tests before every push
[ ] Push fast-forward only; never force
```

اگر Remote بعداً از SHA این سند جلوتر بود، Commitهای جدید را بررسی و این سند را Update کنید؛ کورکورانه Reset به SHA قدیمی نکنید.

---

## 22) اسناد موجود در Repo

- `APEX_AI_BUILD_DOCUMENTATION.json` — AI-readable historical/current build metadata
- `APEX_OMEGA_PRO_ROADMAP_FA.md`
- `OMEGA_PRO_ALPHA1_REPORT_FA.md`
- `OMEGA_PRO_ALPHA2_ORDERFLOW_REPORT_FA.md`
- `OMEGA_PRO_ALPHA3_STATE_MACHINE_REPORT_FA.md`
- `OMEGA_PRO_ALPHA4_RISK_BACKTEST_REPORT_FA.md`
- `OMEGA_PRO_ALPHA5_AI_EXPLAINABILITY_REPORT_FA.md`
- `OMEGA_PRO_RC1_PRODUCTION_REPORT_FA.md`
- `docs/rc_production_runbook_fa.md`
- `PROJECT_DOCUMENTATION.py` — historical handoff before later Alphas/RC; see warning above
- این فایل: `APEX_AI_MASTER_HANDOFF_FA.md` — منبع Context جامع فعلی

---

## 23) تاریخچه کامل Commitها

در Appendix زیر تمام 133 Commit موجود در GitHub تا Snapshot این سند، از قدیمی به جدید، ثبت می‌شوند. برای خوانایی، فقط خط اول Message آمده؛ SHA کامل و URL حفظ شده است.

| # | تاریخ UTC | SHA | پیام Commit |
|---:|---|---|---|
| 1 | `2026-07-01T07:13:39Z` | [`5a0bace8`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/5a0bace828259bc9707ccb2a8caad5bfe708cea5) | Initial APEX AI final delivery |
| 2 | `2026-07-01T19:56:21Z` | [`3b93d627`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/3b93d627ee9f8f23fcad5510619cf96fa3015fd7) | Fix Android APK GitHub Actions workflow |
| 3 | `2026-07-02T05:29:27Z` | [`243910e3`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/243910e39eb6e2e79e5184901652027f580e876a) | Add firebase google-services config |
| 4 | `2026-07-02T05:52:47Z` | [`51d1a88e`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/51d1a88e4b0b3809a549acb5b8ebaa3570d9d1ed) | Add material components dependency for Android theme |
| 5 | `2026-07-02T05:56:39Z` | [`226432a3`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/226432a313862fdc64aa55d4cce66120382e6f7f) | Add material components dependency for Android theme |
| 6 | `2026-07-02T06:39:13Z` | [`2ac2d2b9`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/2ac2d2b959391f696a57d066563bf7f37d3ebc79) | Fix Android theme and chart compose return |
| 7 | `2026-07-02T08:13:39Z` | [`61b1ce0f`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/61b1ce0fc30176989b50d0d5bd8b8106db5b7536) | Update android-apk-build.yml |
| 8 | `2026-07-02T08:15:43Z` | [`af553459`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/af5534599b40a9c4d42e1e8a9e7502123b628149) | Update android-apk-build.yml |
| 9 | `2026-07-02T11:51:30Z` | [`230e22a5`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/230e22a5fb880931b5ec7c5d7fbde681325f8805) | Add Bybit fallback for crypto market data |
| 10 | `2026-07-02T23:13:05Z` | [`22b1605e`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/22b1605e98668b8fcb2f6158bfe7e86587a8d863) | Set Bybit default base URL to production public endpoint |
| 11 | `2026-07-02T23:36:12Z` | [`ad520eba`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/ad520eba6695741d9605a7ba4ac18c6c74cca711) | Use OKX as crypto fallback provider |
| 12 | `2026-07-03T13:58:47Z` | [`647816a0`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/647816a09ff1f814545a5990115677729e9edd3c) | APEX AI premium bilingual polish |
| 13 | `2026-07-03T16:52:21Z` | [`718775d7`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/718775d78b8d5c4935b3a35b248456c0cc7c9dbc) | Fix Compose weight import build error |
| 14 | `2026-07-03T18:18:52Z` | [`b245a481`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/b245a481e75e2568bfba4ecf350a324bc95df5fc) | Make premium visual changes clearly visible |
| 15 | `2026-07-03T18:56:53Z` | [`60a8c150`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/60a8c150bed5412406ec2a85a7bea2c3d143f3e6) | Add neon premium splash and dashboard redesign |
| 16 | `2026-07-03T20:07:09Z` | [`65adc8dc`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/65adc8dcd891ca7a21af318a523fbaeef9aa254b) | Phase 2 premium visual redesign |
| 17 | `2026-07-03T20:28:27Z` | [`ab19e24e`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/ab19e24edc1b0a785f73c766dc096afb34a58de2) | Replace splash image with final portrait |
| 18 | `2026-07-03T21:24:46Z` | [`e23e94c3`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/e23e94c3f013030f8989c3a0ac7b202f8665b74b) | Enable backend websocket support on Render |
| 19 | `2026-07-03T21:44:02Z` | [`dbce56e6`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/dbce56e68e95f5c772cac384533581c9ffb03963) | Force text field visibility fix |
| 20 | `2026-07-04T04:41:29Z` | [`88e828aa`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/88e828aaa5fa3f727b1fce69c422c931955b02c6) | Force text field visibility fix |
| 21 | `2026-07-04T06:19:13Z` | [`920333d4`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/920333d4abce8b9601fd2f74f47ce21d4508c2db) | Fix auth 403 fallback and final text polish |
| 22 | `2026-07-04T07:43:22Z` | [`50f51061`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/50f51061c82b98af6da43c7b73a28f63cf193696) | Fix dashboard StreamChip build error |
| 23 | `2026-07-04T08:49:24Z` | [`2aef3785`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/2aef37851c722f6652b9a7cb60f15f8a75288647) | Final luxury polish for signals analytics backtest readiness |
| 24 | `2026-07-04T14:25:56Z` | [`7535a501`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/7535a5011f42c53d2ef7125fbe39a6aced2f988c) | Final micro polish for language and luxury UI |
| 25 | `2026-07-05T10:18:52Z` | [`d60f2d5b`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/d60f2d5bb18cc0ad7901c7d8533dcb87ce6ca9db) | Add 1m timeframe to signals chart and backtest |
| 26 | `2026-07-05T10:30:26Z` | [`2e658b0c`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/2e658b0c3020d0059fdad7005257496ba9daaab3) | Add 1m timeframe to signals chart and backtest |
| 27 | `2026-07-05T12:51:05Z` | [`1f5ccd0f`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/1f5ccd0fee3d4e9ae741e5c0804a5babf7fddbd7) | Fix timeframe button build issue |
| 28 | `2026-07-05T13:25:53Z` | [`482c34ea`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/482c34eae6758a13d149bc1df401e5e408db4389) | Fix backend models for AI Engine Pro Phase 1 |
| 29 | `2026-07-05T13:32:02Z` | [`3bad3823`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/3bad38232f7a71b0cf47d264153edc99b918f8d4) | AI Signal Engine Pro Phase 1 + selectable timeframe |
| 30 | `2026-07-05T13:52:01Z` | [`c4fb07ee`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/c4fb07eef36ed860e3ecfecee2e63a363b3558c5) | AI Signal Engine Pro Phase 1 + selectable timeframe |
| 31 | `2026-07-05T16:49:06Z` | [`5514757b`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/5514757bf1a69dddce76b90c176d44b29598b516) | AI Signal Engine Pro Phase 2 + Persian signal polish |
| 32 | `2026-07-05T17:55:49Z` | [`58edb326`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/58edb326e092690ade8df796e8cf455d93b86c63) | Signal Intelligence Pro Phase 3 + institutional signal panel |
| 33 | `2026-07-05T19:14:54Z` | [`a5328fe6`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/a5328fe69dc0ec89fcf03cf9804cb9cac8d7147e) | Phase 4 Backtest Pro Lab + Analytics Board |
| 34 | `2026-07-05T19:26:18Z` | [`592a248a`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/592a248a1227689474476886d0345345355356a4) | Phase 5 Trade Journal Pro + Performance Intelligence |
| 35 | `2026-07-05T19:45:19Z` | [`7068937c`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/7068937c5cd7e321bb4b9c66fce4bb8f158bf493) | Phase 6 Smart Alerts Pro + Market Focus Board |
| 36 | `2026-07-05T19:56:56Z` | [`cda92aec`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/cda92aec9cd7817165759e2d40ca7d43d291a53b) | Phase 7 Broker Execution Pro + Risk Command Center |
| 37 | `2026-07-05T20:16:36Z` | [`4bf8ae55`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/4bf8ae55c199f385ef890bba2d78b5b1e2c7b29c) | Phase 8 AI Strategy Lab + Elite Scanner Board |
| 38 | `2026-07-05T20:29:09Z` | [`f29b4310`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/f29b43106d98a21233bb721cff2d7b7729c9ecd9) | Phase 9 Portfolio Command + Multi-Asset Intelligence Board |
| 39 | `2026-07-05T20:41:48Z` | [`4367e094`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/4367e0947504298f5ff910032e222080011f550a) | Phase 10 Mission Control UI + Executive Overview Board |
| 40 | `2026-07-05T20:53:11Z` | [`c5de39d6`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/c5de39d67782411d1bff71cb8a1c38665108bf2b) | Phase 11 Elite Portfolio Flow + Capital Allocation Board |
| 41 | `2026-07-05T21:00:34Z` | [`f4ba6946`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/f4ba69467d697865c8b296e79bc987e019b28614) | Phase 12 Quant Ops Center + Advanced Decision Matrix |
| 42 | `2026-07-05T21:10:09Z` | [`cac0ee8e`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/cac0ee8e0650ab47e9f926a72bdd3d34c3793f87) | Phase 13 Prime AI Cockpit + Executive Signal Radar |
| 43 | `2026-07-05T21:17:35Z` | [`5f70c1c3`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/5f70c1c312e07aaa8dfe216c2db7c9028c4b6982) | Phase 14 Institutional Overview Grid + Tactical Response Board |
| 44 | `2026-07-05T21:29:35Z` | [`6932164b`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/6932164bdced6d34d6c14e0b4031aa1de426d1cd) | Phase 15 Supreme Control Layer + Global Market Pulse |
| 45 | `2026-07-05T22:10:43Z` | [`2ad48061`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/2ad480610ea94943086553a99e6c1af2d8c20044) | Phase 16 Institutional AI Matrix + Final Executive Layer |
| 46 | `2026-07-05T22:21:42Z` | [`c8aefe1b`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/c8aefe1b5c5fd2f71073337529dbbf261e06c947) | Phase 17 Ultimate Decision Stack + Omni Market Command |
| 47 | `2026-07-05T22:27:14Z` | [`73a8e88d`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/73a8e88d086ad756d456edfd72cdb5906b47e98c) | Phase 18 Final Premium Unification + Production Candidate |
| 48 | `2026-07-05T23:15:03Z` | [`8d0b4fb9`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/8d0b4fb96724803a46b87d6846ba5da2f2e91246) | Build rescue hotfix: restore compile-safe screens |
| 49 | `2026-07-06T17:45:13Z` | [`7dde69b8`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/7dde69b8e7c49419d2d5593a4767aa2911ab59b7) | Build rescue hotfix: restore compile-safe screens |
| 50 | `2026-07-06T18:01:43Z` | [`108d0316`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/108d03161ff5232e09abdeca85fd79074ef600f6) | Build rescue hotfix: restore compile-safe screens |
| 51 | `2026-07-06T18:49:49Z` | [`5e02bc78`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/5e02bc781f1ef81d7fb0f56254d042a6d1386cca) | Hotfix compile error in JournalScreen |
| 52 | `2026-07-06T20:37:52Z` | [`1d145e02`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/1d145e0222615057ef64a797e14f715d61b473af) | Final stabilization P1 Persian polish |
| 53 | `2026-07-07T04:25:57Z` | [`f0127ff3`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/f0127ff3d58ef4aa24a354f6ce00356ddaf8f33b) | Final stabilization P1 Persian polish |
| 54 | `2026-07-07T07:21:35Z` | [`4d0387fc`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/4d0387fcc42f77b8c7af60dcaf964e7e5e3843f3) | Hotfix remove invalid Compose weight imports |
| 55 | `2026-07-07T08:36:10Z` | [`c2231ec5`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/c2231ec51e628b3f78e9b1621bcfdd63adb665d9) | Enable Firebase JSON env support for real push |
| 56 | `2026-07-09T08:13:20Z` | [`40517d12`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/40517d12002da08a3b74750b4033ed381043ed59) | Add liquidity timing box with Tehran UTC toggle |
| 57 | `2026-07-09T09:49:33Z` | [`995f028d`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/995f028dcdd87711ed88ea094e4bacc90f3e66a3) | Hotfix dashboard liquidity compile errors |
| 58 | `2026-07-09T12:16:37Z` | [`51dda02c`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/51dda02ca1085936e58adf08efb8b29349f4aca1) | Fix dashboard liquidity remember and state compile |
| 59 | `2026-07-09T21:33:49Z` | [`44e43aea`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/44e43aeabab47e23894b30f8fd0aad98574a76f5) | Fix missing liquidityFilter declaration before aiSummary |
| 60 | `2026-07-10T08:51:57Z` | [`256e2689`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/256e26891022172c959596ff2ae6a30b7bd32ff1) | Fix liquidity filter timezone parameter |
| 61 | `2026-07-10T10:57:39Z` | [`af4fe405`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/af4fe40547b562f95abe86f100af6b60de170a12) | Clean rewrite DashboardScreen, liquidity filter + TZ toggle, compile safe |
| 62 | `2026-07-10T11:06:15Z` | [`73891296`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/738912963e4b720e9013581cdaa579b1c0394fc9) | Bulletproof DashboardScreen: support both callback names, fix BorderStroke, remove remember outside composable |
| 63 | `2026-07-10T11:26:16Z` | [`3bb94728`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/3bb9472813ea2f593c0720c98be32c7fe288e523) | Final DashboardScreen: file-level OptIn, all callback names (incl. onOpenAnalytics) |
| 64 | `2026-07-10T11:35:49Z` | [`de1e6c4d`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/de1e6c4de7792294bc95e9c129f07d8169437c08) | Final DashboardScreen: clean syntax, all callback names, file-level OptIn |
| 65 | `2026-07-10T14:49:40Z` | [`54daff52`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/54daff52a1ee5faeb8789ae3be0bd8a3a767634b) | Wire NewsScreen into navigation, add onOpenNews callback |
| 66 | `2026-07-10T14:58:45Z` | [`ae81191b`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/ae81191b4e313b449567ea71a3b394b5ddb3466e) | Fix: move news route inside NavHost, remove unused tabIndicatorOffset |
| 67 | `2026-07-10T22:05:53Z` | [`ee95772d`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/ee95772dc924ea544c2c863e9ba38ccd82554ea7) | Fix news router: self-contained, graceful imports, wire early |
| 68 | `2026-07-11T04:42:06Z` | [`08f8a844`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/08f8a8440388a5232af8fc0826dd2d5e574340cc) | Fix news: register /api/news/* directly in main.py |
| 69 | `2026-07-11T05:14:23Z` | [`7bedfc6f`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/7bedfc6f994015d82cb5f505edd9820fdba4680b) | Fix: place news endpoints definitely AFTER app=FastAPI() |
| 70 | `2026-07-11T05:21:56Z` | [`a6feee75`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/a6feee75cb757a94aed3f7cf814b45fb920a8eb9) | Fix: move news endpoints right after app=FastAPI definition |
| 71 | `2026-07-11T05:45:58Z` | [`f736627d`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/f736627d6caa569856e10d99dfb26120b6ab9b55) | Fix news paths: /api/v1/news/* on backend + v1/news/brief on Android |
| 72 | `2026-07-11T06:02:51Z` | [`74a6cc5e`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/74a6cc5e3e1f0206696fa75b777512d2971c6265) | Trigger deploy: v1 news endpoints |
| 73 | `2026-07-11T07:52:01Z` | [`283a1466`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/283a146608b51104da90244a8528ee069c5d22da) | Move /api/v1/news/* to end of main.py (post all init) |
| 74 | `2026-07-11T08:06:00Z` | [`20cfefd2`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/20cfefd29a4c24d8a345eabe8fa0d8f942483580) | Cleanup + force deploy |
| 75 | `2026-07-11T08:30:21Z` | [`f703712d`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/f703712d8e895bedd117393d603d31a1609c2b1e) | Wire news endpoints via existing news_engine router to bypass build cache |
| 76 | `2026-07-11T09:52:52Z` | [`8c8c58e6`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/8c8c58e65b83901f7de43933b75c73dc5a0f7ed4) | Add news endpoints adjacent to working /api/v1/news/mock route |
| 77 | `2026-07-11T10:25:17Z` | [`baa30dc9`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/baa30dc91e9e3828adc1a9de6433b653d7481fb6) | Force rebuild with news endpoints |
| 78 | `2026-07-11T11:33:21Z` | [`74f16765`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/74f16765d1bbb10b714ac25807e9b586bef9af53) | Fix: place __future__ import at top of main.py; news endpoints now register correctly on startup |
| 79 | `2026-07-11T12:26:11Z` | [`1854d536`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/1854d536f9f2cba15aa6cb126978f2e6db651fa7) | Fix: define readiness_checks before finnhub entry in readiness_service (unblocks boot) |
| 80 | `2026-07-11T12:33:46Z` | [`d63f123e`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/d63f123e95add8da913ae8b0959c2be40cc44986) | Fix: proper readiness_checks init in readiness_service; reset __future__ import order |
| 81 | `2026-07-11T13:46:16Z` | [`a367b613`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/a367b613fbc50b6dea2d897f38d7258a1dc6b7e6) | Fix: release API base URL points to real Render backend; async Finnhub news wired |
| 82 | `2026-07-11T14:41:08Z` | [`af9a195e`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/af9a195e70d4ba3865b11a930b687fac0d951adc) | Phase C: SMC engine (BOS/CHoCH/OB/FVG/Breaker/Inducement) + /api/v1/analysis/smc endpoint |
| 83 | `2026-07-11T15:41:30Z` | [`cf9942cb`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/cf9942cbdddd5a56ca2f48389a968d9e2fa154da) | Phase C UI: SMC chart analysis screen (BOS/CHoCH/OB/FVG/Brk/Liq) |
| 84 | `2026-07-11T16:26:26Z` | [`43af4f6b`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/43af4f6bd29b6531bf2ecd0e7690c89875562b65) | Fix: re-add ChartScreen.kt with SMC analysis UI |
| 85 | `2026-07-11T16:41:09Z` | [`8d846cc5`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/8d846cc5d71c095949a89f6a9b626b8e97e7609c) | Fix: Kotlin compile errors (SerializedName import, ApiService/Repo closing braces) |
| 86 | `2026-07-11T16:50:40Z` | [`e9b94a91`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/e9b94a91ae6b793d528fb70615fe08ece8b73a1e) | Fix: move Repository.getSmcAnalysis inside class, correct Retrofit path prefix (api/v1/...), deduplicate SMC endpoint |
| 87 | `2026-07-11T17:20:32Z` | [`49293082`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/492930823e7fac4ec340ab625e69de9dea462891) | Phase C v2: Pro SMC engine (killzones/liquidity/orderflow/AI narrative), candlestick chart canvas, symbol+TF selectors, live AI card on Dashboard, Persian news fallback |
| 88 | `2026-07-11T17:25:36Z` | [`3a538e79`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/3a538e791fc73c4c411c0b04502332f1c0f69600) | Fix: Kotlin compile (duplicate @Composable, ElevatedCard border param, replace float/int stateOf) |
| 89 | `2026-07-11T17:46:00Z` | [`57515f7f`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/57515f7faccfda1eee6dd59a3ca385f28d528fa7) | Fix: detect Finnhub invalid-key errors and fall back to Persian calendar |
| 90 | `2026-07-11T17:49:51Z` | [`13fa20ce`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/13fa20ceca7ddac2d5c4b76605a9d49cc1b06420) | Fix: harden news Finnhub failure detection; always fall back to Persian calendar when live data unavailable |
| 91 | `2026-07-11T17:57:44Z` | [`51a964e3`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/51a964e3ad93581aac42033bdf71b3ffc68ff8c1) | Fix: Finnhub 401/error propagation so Persian fallback activates when key invalid |
| 92 | `2026-07-11T18:39:38Z` | [`e8b81376`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/e8b81376ef48f3321753774f6ceaf35234af464d) | Phase C v3: Pro SMC engine v3 (visible-range scaling, dedup liquidity, RR, HTF bias, premium/discount), /signals/scan endpoint, TradingView-style chart (KZ full-height, OB extend, BOS/CHoCH labels), Persian-l10n charts, AI signal board on Signals page |
| 93 | `2026-07-11T18:44:45Z` | [`c576fbc7`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/c576fbc767ddb370ebfa47e196b35a5db7c97df5) | Fix: Kotlin errors (min/max shadowing, paint variable shadow, remember import) |
| 94 | `2026-07-11T18:49:31Z` | [`8f8ed4f4`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/8f8ed4f4683e53e6b910dfefb7bc014dcab62ab6) | Tweak: tighten direction assignment, widen OB retest window |
| 95 | `2026-07-11T19:10:39Z` | [`0dc16d39`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/0dc16d3986fcd7193cc3e99f8e59324121eef9c2) | Phase C v4: setup classifier v4 (BOS/CHoCH/liq/breaker/FVG/ORB), probability 0-100, full trade plan (entry zone/TP1-3/invalidation), entry/SL/TP lines on chart, plan_lines overlay, news block flag, MTF alignment, volume spike, watchlist expansion, 0-100 confluence, 12 watchlist pairs, dashboard AI card upgrade |
| 96 | `2026-07-11T20:23:59Z` | [`620eaecb`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/620eaecbf89226f2a5665d6f7d8ae413ac2340f1) | Phase C v6 Ultra SMC: ICT-grade engine (BOS/CHoCH w/ close confirm, structural leg Fib OTE 62-79%, VWAP, OB/FVG quality, POI stacking, absorption/climax/CVD divergence, 20-factor confluence, A+ to F grading, watching setups, 20-pair scanner, session killzone timestamp fix, Persian AI narrative v2, chart fib/VWAP lines, grade badges |
| 97 | `2026-07-11T20:46:21Z` | [`5c24d5b9`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/5c24d5b994d1d6f535914c4e2b05d5003198cbcc) | Phase C v7: fix Fib OTE legs, OB mitigation tolerance, deep retracement entries, bull/bearish side mapping fix, grade tuning, Android UI: VWAP/fib lines, grade badges, absorption/climax chips, KZ colors, watching setups, 20-pair scanner |
| 98 | `2026-07-11T20:48:54Z` | [`c4ae3213`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/c4ae3213dea8d58e7ea58a47624fb3723b714a53) | fix: add setupType camelCase to scan signal output for Android compat |
| 99 | `2026-07-12T04:17:20Z` | [`8e84b6f3`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/8e84b6f3e414e67411c3ef6162847505f2c2b10a) | Phase C v8 Ultra: pro indicator suite (RSI/MACD/Stoch/BB/ADX/CCI/Williams/MFI/CMF/PSAR/Ichimoku/EMA/Pats/Div) |
| 100 | `2026-07-12T04:48:02Z` | [`e0831791`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/e0831791570b6c154316bf81baa5b2f2090eb57d) | Omega-100 Rule: enforce RR>=2, conf>=40, prob>=60 for actionable signals; omega_compliant flag, action_label (STRONG_BUY/BUY/CONSIDER/WAIT), full omega rule metadata; hide non-compliant signals, filter scanner; Android model updates for omega fields |
| 101 | `2026-07-12T05:17:00Z` | [`814bf04f`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/814bf04f3cb75b751f00c7594bc4f85ceef2f803) | Fix chart rendering: hide plan lines for F-grade signals, label positions fixed (left/right alternate), KZ labels above chart, BOS/CHoCH labels at event circles not left edge, split chip rows to prevent overlap, two-line header chips, fix note text ('watching' label for weak setups), adjust chart margins |
| 102 | `2026-07-12T05:50:32Z` | [`b8ff97a0`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/b8ff97a0bb33f823f64f9917d2171a965cb6c700) | v8.1 Fixes: |
| 103 | `2026-07-12T05:53:15Z` | [`2fb19876`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/2fb19876f5675140cf6da095e78f0aaa0c0edf04) | Fix direction for F-grade signals (force NEUTRAL to prevent bias mismatch in UI) |
| 104 | `2026-07-12T05:56:19Z` | [`eccd6ffb`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/eccd6ffb14491453f554d3bf19987e2a853e5e9e) | Fix direction for F-grade: always neutral, action_label AVOID |
| 105 | `2026-07-12T06:08:31Z` | [`9d8f38ec`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/9d8f38ecc576b047474e3f20364954e7b793a93c) | Fix Kotlin compile error: android.graphics.Rect properties are fields not methods |
| 106 | `2026-07-12T06:13:40Z` | [`97fd5c1f`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/97fd5c1fd84d2a092755053fd0d5eb5d53f5a963) | Fix critical bug: watching-loop overwrote 'direction' variable causing F-grade signals to show short/long instead of neutral |
| 107 | `2026-07-12T06:22:16Z` | [`ef6bf96b`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/ef6bf96ba8cc56b4513a652289f07846db3a9c41) | Retrigger CI build |
| 108 | `2026-07-12T06:35:33Z` | [`95e7b38d`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/95e7b38d661c34d1da9cfe1a1a650c680df667f3) | Fix Kotlin Rect API: width()/height() are methods (), top/bottom are fields |
| 109 | `2026-07-12T06:47:06Z` | [`069b9913`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/069b99136af2d7f80a8cdba076a0cafd8a1e42be) | Increase HTTP timeouts, add UA + Connection header, retry enabled |
| 110 | `2026-07-12T07:14:53Z` | [`7272f67a`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/7272f67a8fe241eea27dfde89151936444a6efaf) | TradingView-style chart redesign: TV colors, axis right panel, OB labels inside zones, BOS/CHoCH arrows, IDM dots, colored price-tag on axis, live signals scanner at bottom |
| 111 | `2026-07-12T07:18:57Z` | [`fae6ba22`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/fae6ba22add9207856a0c6a86f5aca34b653c5d1) | Fix SmcScanResponse.signals field access for chart live signals |
| 112 | `2026-07-12T07:23:23Z` | [`2dbc7859`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/2dbc7859f29f96342cc5e889e31bc9528d0fc2d2) | Restore AiSignalBoard composable used by SignalsScreen (was accidentally removed in rewrite) |
| 113 | `2026-07-12T08:54:24Z` | [`8e70274e`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/8e70274e2579686bffa5dfb68509e3e0094d1ef6) | Add comprehensive AI-readable build documentation in JSON format |
| 114 | `2026-07-12T13:03:54Z` | [`6d29b713`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/6d29b713681f6a4fc5882df01750c3c4b3a2c71f) | fix: stabilize non-broker APIs, auth, risk and Android build |
| 115 | `2026-07-12T13:35:35Z` | [`d7eaa37d`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/d7eaa37dc4897ff42cd12d744fa0fc83dc9f7baa) | ci: increase Gradle heap for clean Android builds |
| 116 | `2026-07-12T14:12:07Z` | [`8ff5f30a`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/8ff5f30a75d9d1f412453090b351ab356d28a0c9) | fix: stabilize charts across all symbols and timeframes |
| 117 | `2026-07-12T14:19:45Z` | [`6a582147`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/6a582147520b9b4b7ff6d77977d657da3b78efa2) | ci: replace deprecated Android setup action |
| 118 | `2026-07-12T14:29:31Z` | [`4616064b`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/4616064b44e4dd923c7c1abf001d755725c2451f) | ci: locate sdkmanager from Android SDK home |
| 119 | `2026-07-12T15:09:10Z` | [`ebe95550`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/ebe95550a1f83f8f04d825b7c9c10a7031c474b2) | feat: simplify chart overlays for clear price action |
| 120 | `2026-07-12T15:51:17Z` | [`acaf3e45`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/acaf3e45eeec9424555520cf35c2cf76d0f256e4) | feat: render prioritized institutional zones with lifecycle |
| 121 | `2026-07-12T19:18:02Z` | [`09f64575`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/09f64575fac7b782f0be1cd77ad62194ef9690a0) | feat: add cached trading setups hub and simplify navigation |
| 122 | `2026-07-13T04:00:15Z` | [`46251418`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/46251418e4ff8d0864c94bdef40a26f42acfaeb4) | fix: harden network retries, demo mode and expired sessions |
| 123 | `2026-07-13T04:58:15Z` | [`94207364`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/942073645a2bcf4eac4769e1ef37031f91865359) | fix: close remaining demo, dashboard, signing and security gaps |
| 124 | `2026-07-13T05:34:50Z` | [`5476426f`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/5476426ff7bc0b6f73ba9f8c42c5f3ecd9bcd9ac) | fix: polish chart labels, legend and rendering collisions |
| 125 | `2026-07-13T06:55:41Z` | [`90c50424`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/90c50424de39262bd2751f7af4ce35341bfe3280) | feat: add Omega Pro strict quality, regime and decision core |
| 126 | `2026-07-13T09:29:54Z` | [`73aa247a`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/73aa247a527c4687681aa36c78016b556d45e9e1) | feat: add real crypto order flow and honest forex proxy |
| 127 | `2026-07-13T10:32:11Z` | [`bfe67d02`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/bfe67d024bcf9a0b3f764b7e2ae14c9472ac8f92) | feat: add deterministic setup lifecycle state machine |
| 128 | `2026-07-13T12:00:54Z` | [`ba83486f`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/ba83486f3d64289dadaf5c6eefbf78221d6292ac) | fix: restore Alpha 2 order flow and include Alpha 3 state engine |
| 129 | `2026-07-14T04:42:58Z` | [`fe24062b`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/fe24062bc7547ba1c514f12334d32d809eb0ca13) | Add comprehensive project documentation in Python format for AI handoff |
| 130 | `2026-07-14T10:03:54Z` | [`1cfdf50b`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/1cfdf50b24e853b5114e5ab71438800eee4f8946) | feat: add Alpha 4 portfolio risk and conservative backtesting |
| 131 | `2026-07-14T11:09:26Z` | [`7c98c893`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/7c98c893822c64af0df4d67a37f3415bcd2ad36e) | feat: add provider-agnostic verified AI explainability |
| 132 | `2026-07-14T12:35:16Z` | [`82ac9fcb`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/82ac9fcbe330a80c323766554ead3f39338d4a83) | feat: harden production infrastructure for RC1 |
| 133 | `2026-07-14T15:56:21Z` | [`961851e6`](https://github.com/aminomidiao68-max/apex-ai-trading-assistant/commit/961851e66511b125db03d4345c3a44519757ea4e) | fix: run PostgreSQL integration through Python module path |

---

## 24) پایان سند / Canonical Resume Point

Canonical resume point در زمان تولید سند:

```text
GitHub main: 961851e66511b125db03d4345c3a44519757ea4e
Version: 3.0.0-rc1
Backend CI: success (SQLite + PostgreSQL 16)
Android CI: success (test + lint + APK + release manifest)
Render: ready
Database: PostgreSQL / persistent / migration current
AI: deterministic / verified fallback / external disabled
Live Execution: false
```

این سند Context پروژه را حفظ می‌کند، اما Secret Store، Database backup و Git repository همچنان باید جداگانه نگهداری شوند.

---

## Addendum — Paper Alpha 3 Automated Market Feed

```text
Version: 3.4.0-paper-alpha3
Schema: v7
Feed: opt-in, per-user, Crypto only
Provider: OKX public real best bid/ask
Tick processing: payload-hashed, idempotent and stale-quote guarded
Worker: database lease + sanitized exponential backoff
Android: feed status/subscription/manual sync controls
Live Execution: false
```

Paper Alpha 3 adds real public quote ingestion to the isolated Paper OMS. It does not turn simulated fills into broker fills and makes no performance claim. Forex remains excluded from automated feed until an equivalent real bid/ask source is available.

---

## Addendum — Paper Alpha 4 Margin/Funding/Liquidation

```text
Version: 3.4.0-paper-alpha4
Schema: v8
Margin modes: isolated / conservative cross
Funding: signed, event-idempotent, user-supplied rates labeled is_real_rate=false
Liquidation: conservative bid/ask + slippage + liquidation fee
Post-liquidation action: kill switch engaged and automated feed disabled
Live Execution: false
```

Paper Alpha 4 is an exchange-agnostic simulation. It does not implement complete exchange risk tiers, ADL, insurance funds or portfolio-margin rules and makes no profitability claim.

---

## Addendum — Paper Alpha 5 Recovery/Concentration/Testnet Shadow

```text
Version: 3.4.0-paper-alpha5
Schema: v9
Testnet probes: Binance Futures / Bybit public connectivity only
Authentication: false
Order routing: false
Shadow snapshots: provider_verified=false / actionable_for_live=false
Correlation source: structural_proxy (not statistical correlation)
Ledger audit: diagnostic only / repair_performed=false
Live Execution: false
```

Paper Alpha 5 adds durable public connectivity checkpoints, sanitized backoff, shadow-only reconciliation and deterministic concentration controls. Private authenticated Testnet order/fill reconciliation is still not implemented and no profitability claim is made.

---

## Addendum — Paper Alpha 6 Statistical Correlation / Private Testnet Read-Only

```text
Version: 3.4.0-paper-alpha6
Schema: v10
Correlation source: immutable stored datasets / aligned log returns
Stabilization: deterministic winsorization + n/(n+20) shrinkage
Private Testnet providers: Binance / Bybit
Private operations: signed GET only
Testnet order routing: false
Live Execution: false
```

Correlation snapshots are sample-dependent research/risk inputs, not proof of causality or future performance. Private Testnet Order/Fill reconciliation and any Place/Cancel operation remain outside this phase.

---

## Addendum — Paper Alpha 7 Private Testnet Read-Only

```text
Version: 3.4.0-paper-alpha7
Schema: v11
Private snapshot: provider authenticated / verified
Methods: signed GET only
Recovery drill: deterministic / offline
Testnet order routing: false
Live Execution: false
```

---
## Addendum — Paper Alpha 8 Chaos/DR
```text
Version: 3.4.0-paper-alpha8
Schema: v12
Production chaos: false
Staging: separate service/database blueprint
Production mutated: false
Order routing: false
Live Execution: false
```

---
## Addendum — Paper Alpha 9 Testnet Place/Cancel
```text
Version: 3.4.0-paper-alpha9
Schema: v13
Production Testnet flag: false
Staging Testnet flag: false until credentials/gates
Live Execution: false
```

---
## Addendum — Operational Alpha 10
```text
Version: 3.5.0-operational-alpha10
Schema: v14
Drift: PSI / KS / volatility ratio
SLO: P95 latency / server error rate
Testnet Execution: false
Live Execution: false
```

---
## Addendum — Operational Alpha 11
```text
Version: 3.5.0-operational-alpha11
Schema: v15
Promotion: 3x STABLE + WITHIN_SLO + DB ready
Testnet/Live authorization: false
```

---
## Addendum — Release Alpha 12
```text
Version: 3.6.0-release-alpha12
Dependency vulnerabilities: 0
SBOM: Python + Android CycloneDX
APK: debug / production_release_signed=false
Testnet/Live execution: false
```

---
## Addendum — Release Alpha 13
```text
Version: 3.6.0-release-alpha13
Target: Google Play AAB
Signing workflow: manual / environment-approved
Signed AAB available: false until owner provisions Upload Key
Live/Testnet: false
```

---
## Addendum — Signal Intelligence Alpha 14
```text
Version: 3.7.0-signal-alpha14
Frames: 5m/15m/1h/4h
Policy: precision-first / default NO_TRADE
AI override: false
Live authorization: false
```

---
## Addendum — Signal Shadow Alpha 15
```text
Version: 3.7.0-signal-alpha15
Schema: v16
Minimum resolved OOS outcomes: 30
Order routing: false
Precision claim: false
```

---
## Addendum — Signal Shadow Alpha 16
```text
Version: 3.7.0-signal-alpha16
Schema: v17
Outcome source: future server candles only
Intrabar: stop-first
Live authorization: false
```

---
## Addendum — Signal Shadow Alpha 17
```text
Version: 3.7.0-signal-alpha17
Staging worker: true / 900s
Production worker: false
Routing/Live: false
```

---
## Addendum — Signal Shadow Alpha 18
```text
Version: 3.7.0-signal-alpha18
Schedule: every 30 minutes
Endpoint: hidden / token protected / staging only
Production routing/live: false
```

---
## Addendum — Signal Research Alpha 19
```text
Version: 3.7.0-signal-alpha19
Schema: v18
Labels: future-only completed candles / stop-first / terminal horizon
Freshness: all 5m/15m/1h/4h latest closes <= 2.5x timeframe age
Research gate: >=30 terminal AND >=30 activated outcomes
Statistics: empirical target-hit rate + Wilson 95% CI + realized R
Integrity: canonical evidence SHA-256 must pass
Probability calibration claim: false
Threshold relaxation: false
Order routing / Live authorization: false
```

---
## Addendum — Signal Shadow Alpha 20
```text
Version: 3.7.0-signal-alpha20
Schema: v18 (unchanged)
GitHub schedule: automatic successes observed / cadence remains best-effort
Closed/stale market handling: fully stale frame sets are not persisted
Diagnostics: gate/regime/staleness/evidence-integrity counts
Cron observability: sanitized cycle + GitHub Job Summary
Research completion: automatic but requires real future market outcomes
Threshold relaxation: false
Order routing / Live authorization: false
```

---
## Addendum — Signal Shadow Alpha 21
```text
Version: 3.7.0-signal-alpha21
Schema: v18 (unchanged)
External wake: hidden / staging only / asynchronous 202
External token: independent / constant-time compare
Primary free scheduler: cron-job.org-compatible custom POST header
Capture due guard: 900 seconds
Concurrency: shared lock with worker/GitHub cycle
Production external wake: 404
Threshold relaxation / routing / Live authorization: false
```
