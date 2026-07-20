# سند جامع بازیابی و ادامه پروژه APEX AI Trading Assistant

> نوع سند: Living Recovery / Continuation Master
> تاریخ Snapshot: 2026-07-20
> منطقه زمانی مالک: Asia/Tehran
> وضعیت فعلی: Signal Shadow Alpha 21 — Free External Wake Failover
> هدف: ادامه امن پروژه در یک گفت‌وگوی جدید، حتی اگر کل تاریخچه چت از دست برود

---

## 1. روش استفاده از این سند در چت جدید

در صورت حذف یا گم‌شدن گفت‌وگو، این فایل را به Agent جدید بدهید و دقیقاً بنویسید:

```text
این سند وضعیت کامل پروژه APEX را ثبت کرده است.
ابتدا کل سند را بخوان، سپس Remote GitHub را منبع حقیقت قرار بده.
از Stage 1 در بخش «چهار مرحله باقی‌مانده» ادامه بده.
هیچ Threshold را برای تولید Candidate پایین نیاور.
Live/Testnet Execution را روشن نکن.
Signed AAB و انتشار را تا دستور صریح نهایی انجام نده.
هیچ Secret یا Token را از من درخواست نکن؛ از Vault/UI موجود استفاده کن.
```

منبع حقیقت کد:

```text
Repository:
https://github.com/aminomidiao68-max/apex-ai-trading-assistant

Branch:
main

Latest functional Alpha 21 commit:
477d960ecb7c5d272421db7ffd0a5c35e7fa0c75
```

آخرین Commitهای زیرساخت Cron قبل از Alpha 21:

```text
57e4abe058abdab495a603b8da821b1ba2599c3d
fix: add resilient shadow wake cadence

5e8d254334e30e0ca217610e4ad052a57fe91595
fix: add independent shadow heartbeat failover
```

Alpha 21 بعد از Commitهای بالا منتشر شده و HEAD اصلی مورد انتظار هنگام این Snapshot برابر `477d960...` است.

---

## 2. هدف واقعی پروژه

APEX یک دستیار تحلیل و پژوهش بازار برای Crypto و Forex/Gold است که باید:

- تصمیم Deterministic، قابل‌آزمون و قابل‌ممیزی داشته باشد؛
- به‌صورت پیش‌فرض `NO_TRADE` باشد؛
- فقط از داده معتبر و بدون Look-ahead استفاده کند؛
- Evidence و Negative Evidence را همراه تصمیم نگه دارد؛
- هیچ Probability کالیبره‌نشده را احتمال واقعی معرفی نکند؛
- AI را فقط برای توضیح Evidence استفاده کند، نه Override تصمیم؛
- Forex Order Flow را فقط به‌عنوان Proxy شفاف با `is_real=false` معرفی کند؛
- پیش از هر ادعای Precision، Outcomeهای Future-only واقعی جمع کند؛
- تا Gate مستقل، هیچ سفارش Testnet یا Live ارسال نکند.

این پروژه سود، Accuracy، Win Rate یا عملکرد آینده را تضمین نمی‌کند.

---

## 3. تصمیم‌های قطعی مالک پروژه

```text
Markets: Crypto + Forex/Gold
Policy: Precision-first
Horizon: Intraday
Trigger frames: 5m / 15m
Context frames: 1h / 4h
Default decision: NO_TRADE
```

معماری قطعی:

1. AI Provider-agnostic است؛ تصمیم اصلی Deterministic باقی می‌ماند.
2. Forex Order Flow فقط Proxy شفاف با `is_real=false` است.
3. تحویل مرحله‌ای و هر مرحله دارای Test Gate است.
4. Signed AAB و انتشار Play Store فقط با دستور صریح نهایی مالک انجام می‌شود.

برچسب Probability پیش‌فرض:

```text
model_estimate_not_calibrated
```

کنترل‌های دائمی:

```text
ai_override_allowed=false
probability_is_calibrated=false
actionable_for_live=false
ENABLE_TESTNET_EXECUTION=false
ENABLE_LIVE_EXECUTION=false
```

---

## 4. هشدار امنیتی غیرقابل‌مذاکره

هیچ‌یک از موارد زیر نباید در Chat، Git، Log، Screenshot یا Report قرار گیرد:

- API Key
- API Secret
- Password
- Database URL
- Render Token
- GitHub Token
- Cron Token
- Keystore Password
- Upload Key material

مالک قبلاً برخی API Keyهای واقعی را در گفت‌وگوی قدیمی ارسال کرده بود. همه افشاشده فرض شدند و Rotate آن‌ها توصیه شد. مقادیر قدیمی هرگز نباید بازتولید شوند.

Secretهای شناخته‌شده فقط با نام ثبت می‌شوند:

```text
USER_SECRET_MASTER_KEY
SHADOW_CRON_TOKEN                 # GitHub Repository Secret
SIGNAL_SHADOW_CRON_TOKEN          # Render Staging
SIGNAL_SHADOW_EXTERNAL_CRON_TOKEN # Render Staging + cron-job.org
ANDROID_UPLOAD_KEYSTORE_BASE64
ANDROID_UPLOAD_STORE_PASSWORD
ANDROID_UPLOAD_KEY_ALIAS
ANDROID_UPLOAD_KEY_PASSWORD
```

نکات Token خارجی:

- Token اولیه‌ی Cron خارجی به‌دلیل دیده‌شدن بخشی از آن در Screenshot افشاشده فرض شد.
- Token جدید Rotate و در Render و cron-job.org جایگزین شد.
- مقدار Token جدید در این سند یا Git ثبت نشده است.
- Endpoint بدون Token عمداً `401` می‌دهد.

---

## 5. محیط‌ها و URLها

### Production

```text
https://apex-ai-trading-assistant.onrender.com
Expected version: 3.7.0-signal-alpha21
Database: PostgreSQL persistent
Live execution: false
Shadow worker: disabled
External wake endpoint: 404
```

### Staging

```text
https://apex-ai-chaos-staging.onrender.com
Expected version: 3.7.0-signal-alpha21
Database: Neon Free PostgreSQL / persistent
Schema: v18
Worker: enabled
Worker interval: 900 seconds
Live execution: false
Testnet execution: false
```

### External Free Cron

```text
Provider: cron-job.org
Title: APEX Shadow Wake
Method: POST
Interval: every 5 minutes
URL: https://apex-ai-chaos-staging.onrender.com/internal/signal-shadow-wake
Header name: X-Shadow-External-Token
Header value: secret, never record here
Body: empty
Timeout: 30 seconds
```

اجرای عملی cron-job.org تأیید شد:

```text
HTTP 202 Accepted
Execution 1: successful
Execution 2: successful
```

Endpoint به‌صورت Async پاسخ می‌دهد و Collector در Background ادامه پیدا می‌کند.

---

## 6. وضعیت تست و سلامت فعلی

آخرین Test Gate محلی Alpha 21:

```text
Targeted tests: 38 passed
Full Backend: 148 passed, 1 skipped
Dependency vulnerabilities: 0
Bandit Medium/High: 0
```

آخرین CI GitHub Alpha 21:

```text
Backend Tests: success
Security and Supply Chain: success
Build Android APK: success
```

OpenAPI:

```text
Public path count: 98
/internal/signal-shadow-cycle: hidden
/internal/signal-shadow-wake: hidden
```

Readiness مورد انتظار:

```text
database.connected=true
database.backend=postgresql
database.persistent=true
database.migration_current=true
live_execution_enabled=false
```

---

## 7. Snapshot واقعی Shadow در آخرین بررسی

بعد از فعال‌شدن Cron خارجی رایگان:

```text
total_observations=215
no_trade_count=184
watch_count=31
candidate_count=0
pending_outcomes=0
resolved_outcomes=0
activated_resolved_outcomes=0
status=INSUFFICIENT_EVIDENCE
precision_claimed=false
actionable_for_live=false
live_execution_enabled=false
```

Diagnostics:

```text
observations_analyzed=215
evidence_integrity_failures=0
outcome_counts.NOT_APPLICABLE=215
all_frames_stale_observations_historical=54
threshold_relaxation_allowed=false
```

Leading failed gates:

```text
explicit_invalidation
trigger_actionable
trigger_matches_context
context_regime
context_consensus
frame_data_quality
frame_freshness
no_opposing_trigger
```

تفسیر:

- Candidate صفر به‌معنای خرابی خودکار Resolver اثبات نشده است.
- Snapshot زنده‌ی آخر هفته نشان داد Crypto عمدتاً `choppy` بوده است.
- Forex/Gold/Indices هنگام تعطیلی بازار stale بودند.
- Alpha 20 از این پس Observation سیستمی را وقتی تمام Frameها stale باشند ذخیره نمی‌کند.
- Thresholdها نباید برای افزایش Candidate کاهش یابند.

---

## 8. چهار مرحله اصلی باقی‌مانده

### Stage 1 — جمع‌آوری OOS و Outcome واقعی

وضعیت:

```text
IN_PROGRESS_AUTOMATED
```

مسیر خودکار:

1. cron-job.org هر ۵ دقیقه Staging را Wake می‌کند.
2. Endpoint خارجی `202` برمی‌گرداند.
3. Worker فقط Observationهای Due را با فاصله حداقل ۹۰۰ ثانیه Capture می‌کند.
4. Pending Candidateها ابتدا با کندل آینده Resolve می‌شوند.
5. Marketهایی که همه Frameهایشان stale است ذخیره نمی‌شوند.

Universe ثابت فعلی:

```text
BTCUSDT
ETHUSDT
XRPUSDT
XAUUSD
EURUSD
GBPUSD
USDJPY
NAS100
US30
```

Exit Gate مرحله 1:

```text
terminal_outcomes >= 30
activated_terminal_outcomes >= 30
evidence_integrity_failures == 0
metric_completeness_failures == 0
```

Outcomeهای مجاز:

```text
WIN
LOSS
EXPIRED_NO_ENTRY
EXPIRED_ACTIVE
```

قواعد:

- فقط کندل‌های بسته‌شده پس از Capture؛
- Entry activation واقعی؛
- اگر SL و TP در یک Bar لمس شوند: `stop_first => LOSS`؛
- Candidate فعال در پایان Horizon با `EXPIRED_ACTIVE` خاتمه می‌یابد؛
- Outcome دستی ممنوع؛
- Backfill پس‌نگر برای ساخت نتیجه ممنوع.

زمان پایان Stage 1 قابل تضمین نیست و وابسته به وقوع Setupهای واقعی است.

### Stage 2 — ارزیابی آماری و Walk-forward

شروع فقط پس از Exit Gate مرحله 1.

اقدامات:

1. قفل Dataset با SHA-256؛
2. ثبت بازه زمانی Observationها؛
3. محاسبه Empirical Target-hit Rate؛
4. Wilson 95% Confidence Interval؛
5. Average / Median / Cumulative R؛
6. Max Drawdown برحسب R؛
7. تفکیک Market، Symbol و Context Regime؛
8. Purged Walk-forward با Embargo؛
9. جلوگیری از انتخاب مدل با Final Holdout؛
10. گزارش No-entry و Active-expiry؛
11. بررسی Selection Bias و Multiple Testing؛
12. عدم معرفی نرخ تجربی به‌عنوان Probability آینده.

Exit Gate مرحله 2:

- Dataset integrity کامل؛
- حداقل نمونه پاس شده؛
- CI و Breakdownها محاسبه شده؛
- هیچ Precision بدون نمونه منتشر نشده؛
- نتیجه همچنان `actionable_for_live=false`.

### Stage 3 — اصلاح مبتنی بر شواهد و Final Holdout

شروع فقط بعد از Stage 2.

اصول:

- هیچ Threshold بر اساس Final Holdout تنظیم نمی‌شود؛
- تغییرها فقط روی Development/Train windows طراحی می‌شوند؛
- Final Holdout یک‌بار و پس از Lock سیاست استفاده می‌شود؛
- AI حق Override ندارد؛
- تصمیم اصلی Deterministic باقی می‌ماند.

اقدامات احتمالی فقط در صورت اثبات داده‌ای:

- حذف Gate تکراری و نه Gate حفاظتی؛
- اصلاح Regime classifier؛
- اصلاح Trigger/context interaction؛
- اصلاح Data freshness tolerance فقط با تحلیل Provider latency؛
- اصلاح Target/Expiry policy؛
- Calibration مدل تخمینی؛
- Re-test کامل OOS و Walk-forward.

Exit Gate مرحله 3:

- بهبود OOS واقعی و نه فقط In-sample؛
- عدم تخریب Tail Risk؛
- Integrity و Anti-look-ahead پاس؛
- Final Holdout پاس؛
- No-Trade default حفظ؛
- Live authorization همچنان false.

### Stage 4 — Operational Promotion و Staging Soak

اقدامات:

1. حداقل سه Drift window متوالی `STABLE`؛
2. SLO برابر `WITHIN_SLO`؛
3. PostgreSQL persistent و migration current؛
4. Cron/Worker soak بدون Duplicate؛
5. Security audit و SBOM مجدد؛
6. Android test/lint/build؛
7. Backup/restore check؛
8. عدم Mutation تولید توسط Chaos؛
9. Promotion Panel نهایی.

Exit Gate مرحله 4:

```text
consecutive_stable >= 3
slo_status=WITHIN_SLO
database_ready=true
security_gate=PASS
staging_soak=PASS
operational_candidate=true
```

حتی عبور Stage 4 به‌تنهایی مجوز Live نیست.

---

## 9. مرحله انتشار که عمداً بعد از چهار مرحله باقی می‌ماند

طبق دستور صریح مالک:

```text
Signed AAB / Google Play publication must remain the final task.
```

وضعیت:

- Workflow Signed AAB آماده است؛
- Upload Key هنوز Provision نشده؛
- Signed AAB تولید نشده؛
- Play Store upload انجام نشده؛
- هیچ ادعای production-signed artifact وجود ندارد.

Workflow:

```text
.github/workflows/android-signed-release.yml
```

Secrets لازم در آینده:

```text
ANDROID_UPLOAD_KEYSTORE_BASE64
ANDROID_UPLOAD_STORE_PASSWORD
ANDROID_UPLOAD_KEY_ALIAS
ANDROID_UPLOAD_KEY_PASSWORD
```

---

## 10. تاریخچه فازهای انجام‌شده

### Core Alpha 1 تا 5

```text
Alpha 1: 90c50424de39262bd2751f7af4ce35341bfe3280
Alpha 2: 73aa247a527c4687681aa36c78016b556d45e9e1
Alpha 3 repair: ba83486f3d64289dadaf5c6eefbf78221d6292ac
Alpha 4: 1cfdf50b24e853b5114e5ab71438800eee4f8946
Alpha 5: 7c98c893822c64af0df4d67a37f3415bcd2ad36e
RC feature: 82ac9fcbe330a80c323766554ead3f39338d4a83
RC repair: 961851e66511b125db03d4345c3a44519757ea4e
```

قابلیت‌ها:

- SMC/ICT engine؛
- Data Quality و Market Regime؛
- Strict deterministic decision؛
- Real crypto order flow؛
- transparent Forex proxy؛
- Setup lifecycle؛
- Portfolio risk؛
- conservative backtest؛
- provider-agnostic AI explanation؛
- PostgreSQL persistence؛
- monitoring/rate limits/backup/restore.

### Quant/Data/Research/Robustness/Validation/BYOK

```text
Quant Alpha 1: 23522cdde99d59da43e21301f1167b8f30b55d6e
Data Alpha 1: 07b594c1f5fdda4686b35d4d1973e4672e280986
Research Alpha 1: 231afaeba95feca8fb359cc5ec32d610713529e6
Robustness Alpha 1: 50e9251ca2a19690b17dedd0ae5159ce91356cb2
```

قابلیت‌ها:

- Bootstrap و Sign-flip؛
- Bonferroni؛
- Monte Carlo؛
- Calibration metrics؛
- immutable gzip datasets؛
- purged walk-forward و embargo؛
- CSCV/PBO؛
- PSR/DSR؛
- AES-256-GCM user-scoped BYOK؛
- Raw Secret هرگز در API برگردانده نمی‌شود.

### Paper Alpha 1 تا 9

```text
Alpha 1: fad3828...
Alpha 2: 0cdf95ac0d8d710acc37c61fb1e7be53f52b2b0f
Alpha 3: 784e00d5af0c6f8d4111148e75f63fdeb65dc206
Alpha 4: 79b7ef7157a325cc2f06c47e61e2cb7a3d754027
Alpha 5: 2181814b5634992dc51f6d6ecce9aac0728c2e4d
PostgreSQL repair: 9a981e9fc6cd4168f38bd1c5cfe216fa67c93604
Alpha 6: d2e8b4d4009324ec245a8269e080282f1e8b6335
Alpha 7: 096e65dc09ff6b8335588d424fcf056ceee95888
Alpha 8: 648b4e7fbbb16bb78c9e510e19e504e310c18973
Alpha 9: 5b2acda146d394aadb6b49aad903c42680c6e50d
```

قابلیت‌ها:

- OMS، fills و event ledger؛
- cash/equity/positions؛
- real public quotes؛
- margin/funding/liquidation؛
- recovery/concentration؛
- stored statistical correlation؛
- private read-only Testnet reconciliation؛
- deterministic chaos/recovery؛
- Testnet place/cancel safety code.

Testnet عملیاتی متوقف است:

- Binance از Region بررسی HTTP 451؛
- Bybit HTTP 403؛
- Testnet credential وجود ندارد؛
- `ENABLE_TESTNET_EXECUTION=false` باقی می‌ماند.

### Operational Alpha 10 و 11

```text
Alpha 10: 759115a61d9f4787df5e9d892eae9b95a0228812
Alpha 11: 0b5e2d794f780e6df5bacb14f6d570d364ac2714
```

قابلیت‌ها:

- PSI، KS، volatility ratio و mean return shift؛
- P95 latency و server error rate؛
- سه Drift window پایدار برای Promotion؛
- هیچ Promotion خودکار به Live.

آخرین نتیجه شناخته‌شده Promotion:

```text
status=WATCH
consecutive_stable=0
required=3
slo_status=WITHIN_SLO
database_ready=true
operational_candidate=false
live_authorized=false
```

### Release Alpha 12 و 13

```text
Alpha 12: 30ce2527877d315cb99ad5a0042057d296142815
Alpha 13: 9695a4fdbea12e048081695fd046094303d6e250
```

قابلیت‌ها:

- pip-audit strict؛
- Bandit؛
- Python/Android CycloneDX SBOM؛
- OpenAPI fingerprint؛
- Signed AAB manual workflow؛
- keystore cleanup؛
- strict signature verification؛
- Unsigned release fail-closed.

### Signal Alpha 14 تا 21

```text
Alpha 14: 0b518e654989d0237d6e598b8e347bdfb0c5dc65
Alpha 15: 3d1da4339898cd0448a680012264c3176f66f253
Alpha 16: 356ea32aad186811a4f7e849159150996ec26e3a
Alpha 17: 6f6e14092306542c0924b23839aeb7fb5b384c76
Alpha 18: dfdef4f86a397125dd007b6b99f01ff1194e1b12
Alpha 19: 42ac2a28f70320b1ba7b943f8bd25648c985f60b
Schedule repair: b696582a5c3d64cd5117c63ebefadea82c1d3d17
Alpha 20: ac2989836089c42e7b186bb37a2a544f7548275c
Heartbeat failover: 5e8d254334e30e0ca217610e4ad052a57fe91595
Alpha 21: 477d960ecb7c5d272421db7ffd0a5c35e7fa0c75
```

Alpha 14:

- 5m/15m trigger؛
- 1h/4h context؛
- precision-first hard gates؛
- real crypto flow requirement؛
- no live authorization.

Alpha 15:

- persistent Shadow observations؛
- canonical Evidence SHA-256؛
- Candidateها Pending؛
- NO_TRADE/WATCH برابر NOT_APPLICABLE.

Alpha 16:

- future-only resolver؛
- entry activation؛
- stop-first؛
- manual outcome ممنوع.

Alpha 17:

- automated staging worker؛
- fixed panel؛
- duplicate suppression؛
- automatic resolution.

Alpha 18:

- hidden GitHub wake endpoint؛
- HMAC-safe compare؛
- staging-only؛
- concurrency lock.

Alpha 19:

- completed candles only؛
- frame freshness hard gate؛
- TP1 contract repair؛
- EXPIRED_ACTIVE؛
- Schema v18؛
- Research panel؛
- Wilson interval و R metrics بعد از Gate.

Alpha 20:

- skip all-frames-stale observations؛
- diagnostics endpoint؛
- sanitized Cron summary؛
- GitHub Job Summary؛
- Research Autopilot.

Alpha 21:

- free external cron wake؛
- independent token؛
- async 202؛
- cron-job.org integration؛
- Production 404؛
- shared lock و due guard.

---

## 11. APIهای مهم فعلی

### Fusion

```text
GET /api/v1/analysis/intraday-fusion
```

### Shadow

```text
POST /api/v1/analysis/intraday-fusion/shadow
POST /api/v1/analysis/intraday-fusion/shadow/{observation_id}/resolve
GET  /api/v1/analysis/intraday-fusion/shadow/panel
GET  /api/v1/analysis/intraday-fusion/shadow/system-panel
GET  /api/v1/analysis/intraday-fusion/shadow/diagnostics
GET  /api/v1/analysis/intraday-fusion/shadow/system-diagnostics
GET  /api/v1/analysis/intraday-fusion/shadow/research-panel
GET  /api/v1/analysis/intraday-fusion/shadow/system-research-panel
```

### Internal hidden

```text
POST /internal/signal-shadow-cycle
Header: X-Shadow-Cron-Token

POST /internal/signal-shadow-wake
Header: X-Shadow-External-Token
```

### Operational

```text
POST /api/v1/operations/drift
POST /api/v1/operations/slo
POST /api/v1/operations/promotion-panel
```

---

## 12. Workflows مهم

```text
.github/workflows/backend-tests.yml
.github/workflows/android-apk-build.yml
.github/workflows/security-supply-chain.yml
.github/workflows/android-signed-release.yml
.github/workflows/signal-shadow-schedule.yml   # manual recovery
.github/workflows/signal-shadow-heartbeat.yml  # GitHub best-effort heartbeat
```

cron-job.org اکنون Wake اصلی Free Tier است. GitHub Heartbeat فقط Failover محسوب می‌شود چون Schedule آن Cadence تضمین‌شده نداشت.

---

## 13. فایل‌های گزارش

```text
OMEGA_PRO_PAPER_ALPHA1_REPORT_FA.md
OMEGA_PRO_PAPER_ALPHA2_REPORT_FA.md
OMEGA_PRO_PAPER_ALPHA3_REPORT_FA.md
OMEGA_PRO_PAPER_ALPHA4_REPORT_FA.md
OMEGA_PRO_PAPER_ALPHA5_REPORT_FA.md
OMEGA_PRO_PAPER_ALPHA6_REPORT_FA.md
OMEGA_PRO_PAPER_ALPHA7_REPORT_FA.md
OMEGA_PRO_PAPER_ALPHA8_REPORT_FA.md
OMEGA_PRO_PAPER_ALPHA9_REPORT_FA.md
OMEGA_PRO_OPERATIONAL_ALPHA10_REPORT_FA.md
OMEGA_PRO_OPERATIONAL_ALPHA11_REPORT_FA.md
OMEGA_PRO_RELEASE_ALPHA12_REPORT_FA.md
OMEGA_PRO_RELEASE_ALPHA13_REPORT_FA.md
OMEGA_PRO_SIGNAL_ALPHA14_REPORT_FA.md
OMEGA_PRO_SIGNAL_ALPHA15_REPORT_FA.md
OMEGA_PRO_SIGNAL_ALPHA16_REPORT_FA.md
OMEGA_PRO_SIGNAL_ALPHA17_REPORT_FA.md
OMEGA_PRO_SIGNAL_ALPHA18_REPORT_FA.md
OMEGA_PRO_SIGNAL_ALPHA19_REPORT_FA.md
OMEGA_PRO_SIGNAL_ALPHA20_REPORT_FA.md
OMEGA_PRO_SIGNAL_ALPHA21_REPORT_FA.md
```

سندهای مادر:

```text
APEX_AI_MASTER_HANDOFF_FA.md
APEX_AI_BUILD_DOCUMENTATION.json
APEX_OMEGA_PRO_ROADMAP_FA.md
APEX_AI_RECOVERY_CONTINUATION_MASTER_FA.md
```

---

## 14. Git و Arena — هشدار مهم

Arena ممکن است فایل‌ها را حفظ کند ولی Git metadata را به HEAD قدیمی برگرداند.

روال اجباری قبل از هر Push:

1. فقط مسیرهای دقیق فاز جدید را Snapshot کن؛
2. `git fetch origin main`؛
3. `git reset --hard origin/main`؛
4. فقط همان مسیرهای Snapshot را Restore کن؛
5. Test اجرا کن؛
6. Commit و Push را در یک Tool Call انجام بده؛
7. Force Push ممنوع؛
8. Remote GitHub منبع حقیقت است.

GitHub OAuth:

- فقط Device Flow رسمی؛
- Client رسمی GitHub CLI استفاده شود؛
- Token در همان Tool Call استفاده و حذف شود؛
- موفقیت فقط بعد از مقایسه Remote SHA اعلام شود.

---

## 15. دستورات بررسی در بازیابی

بعد از Clone تازه:

```bash
git fetch origin main
git checkout main
git reset --hard origin/main
cd backend
python -m pip install -r requirements.txt -r requirements-security.txt pytest
python -m pytest -q
python -m pip_audit -r requirements.txt --strict
bandit -q -r app -x app_data -ll -s B608
```

بررسی Live:

```text
GET https://apex-ai-trading-assistant.onrender.com/health
GET https://apex-ai-trading-assistant.onrender.com/ready
GET https://apex-ai-chaos-staging.onrender.com/health
GET https://apex-ai-chaos-staging.onrender.com/ready
```

Expected:

```text
version=3.7.0-signal-alpha21
migration_current=true
live_execution_enabled=false
```

---

## 16. چه چیزی نباید انجام شود

- Candidate مصنوعی نساز؛
- Threshold را برای رسیدن سریع به ۳۰ Outcome پایین نیاور؛
- Outcome دستی ثبت نکن؛
- In-progress candle را Label نکن؛
- Final Holdout را برای تنظیم مدل استفاده نکن؛
- AI را صاحب تصمیم نکن؛
- Forex proxy را real order flow معرفی نکن؛
- Testnet را در Region مسدودشده روشن نکن؛
- Live Execution را روشن نکن؛
- Signed AAB را پیش از دستور نهایی نساز؛
- Secret را در Chat یا Screenshot نمایش نده.

---

## 17. اقدام بعدی دقیق

```text
CURRENT_STAGE=1
CURRENT_STATUS=AUTOMATED_COLLECTION_RUNNING
```

در بررسی بعدی:

1. System Panel را بخوان؛
2. Candidate/Pending/Resolved را ثبت کن؛
3. Diagnostics integrity را کنترل کن؛
4. Execution History cron-job.org را برای 202 Success بررسی کن؛
5. تا رسیدن به ۳۰ Outcome فعال منتظر داده واقعی بمان؛
6. سپس Stage 2 را شروع کن.

هیچ ETA قطعی برای Stage 1 اعلام نشود.

---

## 18. تعهد به مستندسازی نهایی

این فایل Snapshot زنده‌ی فعلی است. پس از هر یک از چهار مرحله باید بخش‌های زیر به‌روزرسانی شوند:

- Version و Commit؛
- Test results؛
- Live deployment state؛
- Dataset fingerprint؛
- Outcome counts؛
- Metrics و CI؛
- Drift/SLO؛
- تصمیم‌های پذیرفته یا ردشده؛
- Remaining work.

پس از پایان Stage 4، نسخه Final Comprehensive Handoff باید شامل Timeline کامل، همه Evidenceهای مجاز، تمام Gateها، نتایج OOS، دلیل تغییرهای مدل، وضعیت Release و دستور بازیابی صفر تا صد باشد.
