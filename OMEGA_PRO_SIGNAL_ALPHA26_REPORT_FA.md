# گزارش Signal Research Alpha 26 — Immutable Snapshot Gate

## هدف

ایجاد نقطه شروع ممیزی‌پذیر برای Stage 2. ارزیابی آماری نباید روی Dataset متغیر و بدون هویت ثابت اجرا شود؛ بنابراین Alpha 26 Research Result را فقط پس از عبور Gate به‌صورت immutable قفل می‌کند.

## Schema v19

جدول جدید:

```text
signal_shadow_research_snapshots
```

فیلدهای اصلی:

```text
snapshot_id
user_id
dataset_sha256
result_sha256
policy_version
terminal_outcomes
activated_terminal_outcomes
result_json
locked_at
```

Unique Constraint:

```text
(user_id, dataset_sha256, policy_version)
```

## Lock Gate

Snapshot فقط وقتی ساخته می‌شود که:

```text
research_ready=true
status=RESEARCH_READY
```

در غیر این صورت:

```text
shadow_research_not_ready
```

این Gate حداقل‌های Research Panel، Integrity و Metric completeness را به ارث می‌برد.

## Identity و Integrity

### Dataset Identity

```text
evidence_dataset_sha256
```

شامل Observation ID، Evidence hash، Outcome، Realized R، Capture/Resolve time و Resolution policy است.

### Result Identity

```text
result_sha256 = SHA256(canonical result_json)
```

هنگام هر Read، SHA دوباره محاسبه می‌شود. هر Mutation پایگاه‌داده باعث:

```text
shadow_research_snapshot_integrity_failed
```

می‌شود.

## Idempotency

درخواست تکراری برای User، Dataset و Policy یکسان:

- Snapshot جدید ایجاد نمی‌کند؛
- همان `snapshot_id` و `result_sha256` را برمی‌گرداند؛
- `duplicate=true` می‌شود.

## Scope

Snapshotهای زیر جدا هستند:

```text
user_id=<authenticated user>
user_id=0  # system shadow dataset
```

کاربر دیگر نمی‌تواند Snapshot User را با ID بخواند.

## APIها

```text
POST /api/v1/analysis/intraday-fusion/shadow/research-snapshot
POST /api/v1/analysis/intraday-fusion/shadow/system-research-snapshot
GET  /api/v1/analysis/intraday-fusion/shadow/research-snapshot/{snapshot_id}
GET  /api/v1/analysis/intraday-fusion/shadow/system-research-snapshot/{snapshot_id}
```

همه APIها احراز هویت می‌خواهند.

## Snapshot Response Safety

```text
immutable=true
manual_outcome_allowed=false
threshold_change_authorized=false
actionable_for_live=false
```

Snapshot فقط Evidence را قفل می‌کند و مجوز Promotion، Testnet یا Live نیست.

## تست‌ها

- Lock پیش از Gate رد می‌شود؛
- Snapshot آماده Persist می‌شود؛
- Duplicate request همان ID را می‌دهد؛
- User isolation پاس می‌شود؛
- تعداد Row برای درخواست تکراری یک می‌ماند؛
- Mutation `result_json` هنگام Read کشف می‌شود؛
- Research Result ذخیره‌شده با Result محاسبه‌شده برابر است.

## کنترل‌های نهایی

```text
stage_2_executed=false
snapshot_available_current_dataset=false
manual_outcome_allowed=false
threshold_change_authorized=false
order_routed=false
actionable_for_live=false
ENABLE_TESTNET_EXECUTION=false
ENABLE_LIVE_EXECUTION=false
```
