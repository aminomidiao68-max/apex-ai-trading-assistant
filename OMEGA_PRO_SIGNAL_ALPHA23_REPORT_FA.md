# گزارش Signal Shadow Alpha 23 — Candidate Scarcity Monitor

## هدف

جلوگیری از دو خطای پژوهشی متضاد:

1. تغییر زودهنگام Gateها فقط به‌دلیل Candidate صفر؛
2. انتظار نامحدود بدون داشتن Trigger عینی برای بررسی امکان‌پذیری معماری.

Alpha 23 هیچ تصمیم سیگنال یا Thresholdی را تغییر نمی‌دهد. فقط یک Gate ازپیش‌ثبت‌شده برای Feasibility Audit ایجاد می‌کند.

## Snapshot پیش از Alpha 23

```text
total_observations=272
valid evidence=272
evidence_integrity_failures=0
candidate=0
resolved=0
```

Leading blockers:

```text
trigger_actionable=271
explicit_invalidation=271
context_regime=270
context_consensus=195
```

این Observationها مستقل کامل نیستند؛ بنابراین از نسبت Candidate صفر برای ادعای نرخ یا Probability استفاده نمی‌شود.

## Scarcity Review Gate

حداقل‌های قفل‌شده:

```text
SIGNAL_SHADOW_SCARCITY_MIN_OBSERVATIONS=1000
SIGNAL_SHADOW_SCARCITY_MIN_SPAN_DAYS=5
```

کد اجازه نمی‌دهد این حداقل‌ها از ۱۰۰۰ Observation یا ۵ روز کمتر شوند، حتی اگر Environment مقدار پایین‌تری تنظیم کند.

برای مجازشدن Feasibility Audit باید همه شروط زیر برقرار باشند:

1. Candidate هنوز صفر باشد؛
2. حداقل ۱۰۰۰ Observation معتبر و غیر all-frames-stale وجود داشته باشد؛
3. فاصله اولین تا آخرین Observation حداقل ۵ روز باشد؛
4. Evidence integrity failures برابر صفر باشد؛
5. Timestamp تمام Evidenceهای معتبر قابل‌خواندن باشد.

## وضعیت‌ها

```text
COLLECTING_EVIDENCE
CANDIDATES_OBSERVED
ELIGIBLE_FOR_FEASIBILITY_AUDIT
```

- اگر Candidate ظاهر شود، وضعیت `CANDIDATES_OBSERVED` می‌شود و Scarcity Audit دیگر علت ندارد.
- اگر Sample/Span کافی نباشد، وضعیت `COLLECTING_EVIDENCE` می‌ماند.
- فقط در صورت عبور همه شروط، `ELIGIBLE_FOR_FEASIBILITY_AUDIT` صادر می‌شود.

## Diagnostics جدید

```text
valid_non_all_stale_observations
observation_started_at
observation_latest_at
observation_span_days
scarcity_min_observations
scarcity_min_span_days
scarcity_review_status
feasibility_audit_authorized
candidate_rate_claimed
threshold_change_authorized
```

Cycle Summary و GitHub Job Summary نیز وضعیت Scarcity را نمایش می‌دهند.

## معنی Feasibility Audit

Feasibility Audit فقط بررسی می‌کند آیا ترکیب Gateها از نظر منطقی و داده‌ای قابل‌دستیابی است یا خیر. این مجوز موارد زیر نیست:

- کاهش Threshold؛
- حذف Gate حفاظتی؛
- استفاده از Final Holdout برای تنظیم؛
- ساخت Candidate مصنوعی؛
- معرفی نرخ Candidate به‌عنوان Probability؛
- فعال‌سازی Testnet یا Live.

هر تغییر احتمالی بعدی باید روی Development data طراحی و دوباره OOS ارزیابی شود.

## کنترل‌های ایمنی

```text
candidate_rate_claimed=false
threshold_change_authorized=false
threshold_relaxation_allowed=false
precision_claimed=false
order_routed=false
actionable_for_live=false
ENABLE_TESTNET_EXECUTION=false
ENABLE_LIVE_EXECUTION=false
```

Alpha 23 یک ابزار حاکمیت پژوهشی است، نه موتور تولید سیگنال بیشتر.
