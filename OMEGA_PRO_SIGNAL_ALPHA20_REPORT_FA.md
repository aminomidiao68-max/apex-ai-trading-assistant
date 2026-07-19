# گزارش Signal Shadow Alpha 20 — Research Autopilot Diagnostics

## هدف

Alpha 20 بخش‌های باقی‌مانده‌ای را که امکان خودکارسازی دارند تکمیل می‌کند: اجرای زمان‌بندی‌شده، تشخیص علت کمبود Candidate، جلوگیری از آلودگی Observationها با بازار کاملاً stale و گزارش خودکار پیشرفت Research Gate.

این فاز Candidate مصنوعی ایجاد نمی‌کند، Thresholdها را کاهش نمی‌دهد و نتیجه‌ی آینده را تضمین نمی‌کند.

## شواهد عملی پیش از Alpha 20

دو اجرای واقعی GitHub Actions با event زیر ثبت و موفق شدند:

```text
event=schedule
conclusion=success
```

وضعیت System Shadow در بررسی عملی:

```text
total_observations=132
no_trade_count=105
watch_count=27
candidate_count=0
pending_outcomes=0
resolved_outcomes=0
activated_resolved_outcomes=0
status=INSUFFICIENT_EVIDENCE
precision_claimed=false
```

Snapshot زنده‌ی Gateها در یکشنبه نشان داد:

- Crypto Frameها تازه و Data Quality آن‌ها 100 بود؛
- Context عمدتاً `choppy` بود؛
- هیچ Trigger strict-actionable وجود نداشت؛
- Forex، Gold و Indices به‌علت بسته‌بودن بازار، در تمام Frameها stale بودند؛
- Hard Gateها به‌درستی Candidate را رد کردند.

بنابراین Candidate صفر به‌تنهایی نشانه‌ی خرابی Resolver نیست و نباید با کاهش Threshold اصلاح شود.

## اصلاح‌های Alpha 20

### 1. عدم ذخیره بازار کاملاً stale

System Collector اگر هر چهار Frame را با `fresh=false` ببیند، Observation جدید ذخیره نمی‌کند:

```text
skipped_all_frames_stale += 1
```

این کنترل از افزایش مصنوعی تعداد `NO_TRADE` در تعطیلی بازار جلوگیری می‌کند. درخواست‌های تحلیلی کاربر همچنان پاسخ Fail-closed دریافت می‌کنند؛ فقط Dataset سیستمی OOS آلوده نمی‌شود.

### 2. Shadow Diagnostics

Endpointهای جدید:

```text
GET /api/v1/analysis/intraday-fusion/shadow/diagnostics
GET /api/v1/analysis/intraday-fusion/shadow/system-diagnostics
```

خروجی‌ها:

- تعداد Observation کل و قابل‌تحلیل؛
- شکست SHA-256 شواهد؛
- توزیع Status و Outcome؛
- فراوانی Failed Gateها؛
- توزیع Context Regime؛
- تعداد Observationهای دارای Frame stale؛
- تعداد Observationهایی که تمام Frameهایشان stale بوده است؛
- Leading blockers.

Diagnostics فقط مشاهده‌ای است:

```text
diagnostic_only=true
threshold_relaxation_allowed=false
precision_claimed=false
actionable_for_live=false
```

### 3. Cron Research Summary

Endpoint داخلی Cron اکنون علاوه بر counts چرخه، وضعیت Dataset را به‌صورت Sanitized بازمی‌گرداند:

```text
captured
resolved
skipped_all_frames_stale
errors
total_observations
candidate_count
pending_outcomes
resolved_outcomes
activated_resolved_outcomes
research_status
research_ready
precision_claimed
actionable_for_live
```

Workflow فقط همین کلیدهای allowlisted را چاپ و در GitHub Job Summary ثبت می‌کند. Secret، Token، Evidence خام یا Credential وارد Log نمی‌شود.

## Research Autopilot

چرخه‌ی خودکار به این ترتیب ادامه می‌یابد:

1. Pending Candidateهای قبلی با کندل بسته‌شده‌ی آینده Resolve می‌شوند؛
2. بازارهای کاملاً stale از Capture حذف می‌شوند؛
3. Universe ثابت تحلیل می‌شود؛
4. Candidate فقط پس از عبور تمام Hard Gateها ذخیره می‌شود؛
5. Research metrics فقط پس از حداقل ۳۰ Outcome نهایی و ۳۰ Outcome فعال نمایش داده می‌شوند؛
6. هر شکست Integrity تمام Metricها را Fail-closed می‌کند.

## محدودیت واقعی باقی‌مانده

رسیدن به ۳۰ Outcome فعال وابسته به رخ‌دادن Setupهای واقعی در آینده است. اجرای فوری آن با داده‌ی ساختگی، Backfill پس‌نگر یا کاهش Gateها از نظر پژوهشی نامعتبر است.

تا عبور Gate:

```text
status=INSUFFICIENT_EVIDENCE
probability_is_calibrated=false
precision_claimed=false
actionable_for_live=false
ENABLE_TESTNET_EXECUTION=false
ENABLE_LIVE_EXECUTION=false
```

Signed AAB و انتشار Play Store طبق دستور مالک پروژه همچنان برای آخرین مرحله انتشار باقی می‌ماند.
