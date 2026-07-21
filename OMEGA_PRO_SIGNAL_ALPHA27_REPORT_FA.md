# گزارش Signal Research Alpha 27 — Feasibility Audit Panel Preparation

## هدف

آماده‌سازی بررسی عینی Candidate scarcity بدون تغییر سلیقه‌ای Gateها. این Panel فقط زمانی فعال می‌شود که Sample و پوشش زمانی ازپیش‌ثبت‌شده کامل شده باشند.

## Eligibility Gate

```text
valid_non_all_stale_observations >= 1000
observation_span_days >= 5
candidate_count == 0
evidence_integrity_failures == 0
timestamps_complete == true
```

وضعیت‌های API:

```text
NOT_ELIGIBLE
CANDIDATES_OBSERVED
AVAILABLE
INTEGRITY_FAILED
```

پیش از Gate:

```text
audit_metrics_available=false
failed_gate_counts={}
single_gate_near_miss_counts={}
top_cofailure_pairs={}
threshold_change_authorized=false
```

## Metricهای Audit

### Failure Cardinality

تعداد Gateهای شکست‌خورده در هر Observation:

```text
0 failed gates
1 failed gate
2 failed gates
...
```

خروجی:

```text
minimum_failed_gates_observed
zero_failed_gate_observations
failure_cardinality_counts
```

### Single-gate Near Miss

Observationهایی که دقیقاً یک Gate شکست‌خورده دارند، برحسب نام Gate شمارش می‌شوند:

```text
single_gate_near_miss_counts
```

این شمارش فقط برای تشخیص bottleneck است و مجوز حذف Gate نیست.

### Pairwise Co-failure

برای هر Observation، Pairهای Gate شکست‌خورده محاسبه و ۲۰ Pair پرتکرار ثبت می‌شوند:

```text
top_cofailure_pairs
```

این Metric مشخص می‌کند Gateها مستقل شکست می‌خورند یا یک خوشه‌ی مشترک داده/Regime وجود دارد.

### Pass/Fail Counts

```text
failed_gate_counts
passed_gate_counts
```

Gate state از Evidence immutable خوانده می‌شود.

## Data Filtering

- Evidence SHA-256 پیش از Audit بررسی می‌شود؛
- Observationهای `all_frames_stale` از Audit حذف می‌شوند؛
- ترتیب Observationها تغییر نمی‌کند؛
- Outcome یا Candidate rate برای Eligibility ساخته نمی‌شود.

## APIها

```text
GET /api/v1/analysis/intraday-fusion/shadow/feasibility-panel
GET /api/v1/analysis/intraday-fusion/shadow/system-feasibility-panel
```

هر دو API احراز هویت می‌خواهند.

## معنی Audit

Feasibility Audit فقط پاسخ می‌دهد:

- نزدیک‌ترین Observation چند Gate با Candidate فاصله داشته؟
- آیا یک Gate منفرد دائماً مانع بوده؟
- آیا Gateها به‌صورت خوشه‌ای شکست خورده‌اند؟
- آیا ترکیب Strict Policy در Sample مشاهده شده است؟

Audit اجازه موارد زیر نیست:

```text
threshold relaxation
manual candidate
manual outcome
final holdout consumption
live/testnet routing
```

## Safety Contract

```text
audit_metrics_available=false before Gate
candidate_rate_claimed=false
threshold_change_authorized=false
threshold_relaxation_allowed=false
diagnostic_only=true
order_routed=false
actionable_for_live=false
ENABLE_TESTNET_EXECUTION=false
ENABLE_LIVE_EXECUTION=false
```
