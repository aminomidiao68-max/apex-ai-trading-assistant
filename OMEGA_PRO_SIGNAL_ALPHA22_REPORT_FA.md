# گزارش Signal Shadow Alpha 22 — Qualified Universe Collector

## هدف

افزایش پوشش معتبر Stage 1 بدون کاهش Threshold یا انتخاب نماد بر اساس Outcome معاملاتی. نمادها فقط با معیارهای Data Availability، Freshness و Quality قبل از وجود هر Candidate/Outcome انتخاب شدند.

## Snapshot پیش از تغییر

```text
total_observations=236
no_trade=205
watch=31
candidate=0
resolved=0
precision_claimed=false
```

به‌دلیل Candidate و Outcome صفر، هیچ Performance نتیجه‌ای برای انتخاب Universe استفاده نشده است.

## Qualification Policy

هر نماد جدید باید:

1. هر چهار Frame `5m/15m/1h/4h` را داشته باشد؛
2. هر چهار Frame `fresh=true` باشند؛
3. Data Quality هر Frame حداقل 78 باشد؛
4. Provider خطای 503 ندهد؛
5. انتخاب آن مستقل از Status سیگنال و Outcome باشد.

## نتایج Qualification

### پذیرفته‌شده

```text
USDCAD: quality 91.5 / 92 / 96 / 100, all fresh
USDCHF: quality 100 / 100 / 96 / 100, all fresh
```

### ردشده

```text
SOLUSDT  provider 503
BNBUSDT  provider 503
ADAUSDT  provider 503
DOGEUSDT provider 503
LINKUSDT provider 503
XAGUSD   provider 503
SPX500   provider 503

AUDUSD quality 5m=65
NZDUSD quality 5m=65
EURJPY quality 5m=76
GBPJPY quality 5m=76
AUDJPY quality 5m=76
```

نمادهای ردشده Observation جعلی تولید نمی‌کنند.

## Universe قفل‌شده Alpha 22

```text
BTCUSDT
ETHUSDT
XRPUSDT
XAUUSD
EURUSD
GBPUSD
USDJPY
USDCAD
USDCHF
NAS100
US30
```

## Collector Cooldown

Wake خارجی هر ۵ دقیقه اجرا می‌شود، اما Capture interval برابر ۹۰۰ ثانیه است. پیش از Alpha 22، بازار کاملاً stale یا Provider-error چون Observation ذخیره نمی‌کرد، در Wake بعدی دوباره درخواست می‌شد.

Alpha 22 زمان آخرین Attempt هر Symbol را ثبت می‌کند؛ بنابراین موارد زیر هم ۹۰۰ ثانیه Cooldown دارند:

```text
captured
all_frames_stale
provider_error
```

این کنترل API load را بدون کاهش Observation معتبر کم می‌کند.

## Bounded Concurrency

```text
SIGNAL_SHADOW_MAX_CONCURRENCY=3
hard_cap=8
```

Collector نمادهای Due را هم‌زمان اما با Semaphore محدود پردازش می‌کند. Symbolهای تکراری قبل از پردازش حذف می‌شوند.

Cycle Summary جدید:

```text
attempted_symbols
not_due_symbols
collector_max_concurrency
```

## Diagnostics

Diagnostics اکنون Pre-registration را گزارش می‌کند:

```text
collection_universe
collection_interval_seconds
collector_max_concurrency
universe_policy=pre_registered_data_quality_qualified
```

## کنترل‌های ایمنی

```text
performance_outcomes_used_for_selection=false
threshold_relaxation=false
probability_is_calibrated=false
precision_claimed=false
order_routed=false
actionable_for_live=false
ENABLE_TESTNET_EXECUTION=false
ENABLE_LIVE_EXECUTION=false
```

Alpha 22 فقط کیفیت و کارایی جمع‌آوری Stage 1 را ارتقا می‌دهد و هیچ ادعای عملکردی ایجاد نمی‌کند.
