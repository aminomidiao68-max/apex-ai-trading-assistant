# گزارش Signal Research Alpha 28 — Forward Holdout Plan Preparation

## هدف

آماده‌سازی Final Holdout واقعی و آینده‌نگر برای Stage 3. Holdout نباید بخشی از Dataset توسعه‌ای باشد یا پیش از تصمیم نهایی Metricهای آن مشاهده شود.

## Schema v20

جدول:

```text
signal_shadow_forward_holdout_plans
```

فیلدهای اصلی:

```text
plan_id
user_id
source_snapshot_id
source_dataset_sha256
policy_version
cutoff_at
required_activated_outcomes
holdout_dataset_sha256
holdout_member_ids_json
created_at
ready_at
consumed_at
```

Unique Constraint:

```text
(user_id, source_snapshot_id, policy_version)
```

## منبع Plan

Plan فقط از یک Research Snapshot معتبر ساخته می‌شود:

```text
source_snapshot.result.status=RESEARCH_READY
source_snapshot.immutable=true
```

اگر Snapshot وجود نداشته باشد، Plan ایجاد نمی‌شود.

## Cutoff آینده‌نگر

در زمان ایجاد Plan:

```text
cutoff_at = current UTC time
```

فقط Candidateهایی که شرط زیر را دارند عضو مجموعه‌ی آینده محسوب می‌شوند:

```text
captured_at > cutoff_at
```

بنابراین هیچ Outcome توسعه‌ای یا قدیمی وارد Holdout نمی‌شود.

## Minimum Holdout

```text
required_activated_outcomes >= 30
```

مقدار کمتر از ۳۰ در Service به ۳۰ افزایش داده می‌شود. Hard cap برابر ۱۰۰۰ است.

## وضعیت‌ها

### COLLECTING

```text
future_activated_outcomes < required
holdout_dataset_sha256=null
holdout_metrics_exposed=false
```

### READY

هنگامی که تعداد Outcome فعال آینده کافی شد:

- اولین N عضو فعال موجود در آن لحظه بر اساس `captured_at, observation_id` انتخاب می‌شوند؛
- Member IDها Persist می‌شوند؛
- Canonical payload ساخته می‌شود؛
- `holdout_dataset_sha256` و `ready_at` Persist می‌شوند.

پس از Ready، Candidate یا Outcome بعدی نمی‌تواند Membership یا SHA قفل‌شده را تغییر دهد.

### CONSUMED

این وضعیت برای اجرای صریح و یک‌باره‌ی Stage 3 رزرو شده است. Alpha 28 هیچ Consume endpoint یا Metric holdout ارائه نمی‌دهد.

## APIها

```text
POST /api/v1/analysis/intraday-fusion/shadow/forward-holdout-plan/{source_snapshot_id}
POST /api/v1/analysis/intraday-fusion/shadow/system-forward-holdout-plan/{source_snapshot_id}
GET  /api/v1/analysis/intraday-fusion/shadow/forward-holdout-plan/{plan_id}
GET  /api/v1/analysis/intraday-fusion/shadow/system-forward-holdout-plan/{plan_id}
```

## Idempotency و Scope

- درخواست تکراری برای Snapshot/Policy یکسان همان Plan ID را برمی‌گرداند؛
- `duplicate=true` می‌شود؛
- User نمی‌تواند Plan کاربر دیگر را بخواند؛
- System plan با `user_id=0` جداست.

## عدم Leakage

Response فقط Count و Status را برمی‌گرداند:

```text
future_candidates
future_terminal_outcomes
future_activated_outcomes
holdout_dataset_sha256  # only when membership locked
```

موارد زیر عمداً مخفی‌اند:

```text
holdout win rate
holdout average R
holdout outcomes list
holdout per-symbol metrics
```

## Safety

```text
immutable_cutoff=true
holdout_metrics_exposed=false
final_holdout_used=false
threshold_change_authorized=false
order_routed=false
actionable_for_live=false
ENABLE_TESTNET_EXECUTION=false
ENABLE_LIVE_EXECUTION=false
```

Alpha 28 Plan را آماده می‌کند اما Final Holdout را مصرف نمی‌کند.
