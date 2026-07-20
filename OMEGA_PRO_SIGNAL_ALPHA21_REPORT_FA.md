# گزارش Signal Shadow Alpha 21 — Free External Wake Failover

## هدف

تکمیل مسیر رایگان جمع‌آوری Shadow بدون ارتقای پولی Render. GitHub Schedule چند اجرای موفق واقعی داشت، اما Cadence آن پیوسته نبود؛ بنابراین Alpha 21 یک Wake خارجی مستقل و امن برای سرویس‌های Cron رایگان اضافه می‌کند.

## Endpoint جدید

```text
POST /internal/signal-shadow-wake
```

ویژگی‌ها:

- فقط در `APP_ENV=staging`؛
- مخفی از OpenAPI؛
- پاسخ سریع `202 Accepted`؛
- اجرای Collector در Background؛
- Token مستقل در Header؛
- مقایسه با `hmac.compare_digest`؛
- Production برابر 404؛
- Lock مشترک با Worker و GitHub Cycle؛
- هیچ Order Routing یا Live authorization.

Header:

```text
X-Shadow-External-Token: <independent-random-secret>
```

Environment:

```text
SIGNAL_SHADOW_EXTERNAL_CRON_TOKEN=<same-independent-secret>
```

Token خارجی از `SIGNAL_SHADOW_CRON_TOKEN` گیت‌هاب جداست تا افشای احتمالی یک سرویس ثالث، Credential گیت‌هاب را تحت‌تأثیر قرار ندهد.

## چرا پاسخ Async است؟

چرخه کامل تحلیل چند Symbol ممکن است بیشتر از Timeout سرویس Cron رایگان طول بکشد. Endpoint جدید پس از احراز هویت، Task را در Background ثبت و فوراً پاسخ می‌دهد:

```json
{
  "status": "accepted",
  "background_started": true,
  "actionable_for_live": false
}
```

اگر Cycle دیگری در حال اجرا باشد:

```json
{
  "status": "already_running",
  "background_started": false,
  "actionable_for_live": false
}
```

## تنظیم رایگان پیشنهادی

Provider:

```text
cron-job.org
```

Job:

```text
URL=https://apex-ai-chaos-staging.onrender.com/internal/signal-shadow-wake
Method=POST
Interval=Every 5 minutes
Header Name=X-Shadow-External-Token
Header Value=<independent secret>
Body=empty
```

Worker همچنان Capture را با `SIGNAL_SHADOW_INTERVAL_SECONDS=900` محدود می‌کند؛ بنابراین Wake پنج‌دقیقه‌ای Observation تکراری ایجاد نمی‌کند.

## وضعیت Research در زمان طراحی

```text
total_observations=169
no_trade=138
watch=31
candidate=0
resolved=0
evidence_integrity_failures=0
status=INSUFFICIENT_EVIDENCE
```

مهم‌ترین Blockerهای تشخیصی:

```text
trigger_actionable
trigger_matches_context
explicit_invalidation
context_regime
context_consensus
```

Candidate صفر با Threshold ضعیف‌تر یا داده ساختگی جبران نمی‌شود. Collector به‌صورت خودکار منتظر Setup واقعی می‌ماند.

## کنترل‌های ایمنی

```text
threshold_relaxation=false
probability_is_calibrated=false
precision_claimed=false
actionable_for_live=false
ENABLE_TESTNET_EXECUTION=false
ENABLE_LIVE_EXECUTION=false
```

رسیدن به ۳۰ Outcome فعال وابسته به زمان واقعی بازار است. Alpha 21 مسیر جمع‌آوری رایگان را پایدار می‌کند، اما Outcome آینده را جعل یا تضمین نمی‌کند.
