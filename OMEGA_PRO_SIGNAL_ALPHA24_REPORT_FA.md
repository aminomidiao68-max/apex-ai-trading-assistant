# گزارش Signal Research Alpha 24 — Dependence-Aware Metrics Preparation

## هدف

آماده‌سازی فنی Stage 2 در زمان ادامه جمع‌آوری Stage 1، بدون اجرای زودهنگام ارزیابی و بدون تغییر Signal Logic.

تمام Metricهای جدید پشت همان Research Gate قرار دارند:

```text
terminal_outcomes >= 30
activated_terminal_outcomes >= 30
evidence_integrity_failures == 0
metric_completeness_failures == 0
```

تا قبل از Gate، مقادیر آماری جدید `null` و `dependence_aware_metrics_available=false` باقی می‌مانند.

## مسئله وابستگی

Outcomeهای Shadow ممکن است:

- در زمان نزدیک به هم ثبت شوند؛
- بین Symbolهای مرتبط هم‌بستگی داشته باشند؛
- در Regime یکسان متراکم شوند.

بنابراین CI ساده‌ی i.i.d. برای Average R می‌تواند بیش‌ازحد خوش‌بینانه باشد.

## Moving-block Bootstrap

Alpha 24 از Circular Moving-block Bootstrap استفاده می‌کند:

```text
replicates=2000
block_length=round(sqrt(active_sample_size))
seed=evidence_dataset_sha256
method=deterministic_circular_moving_block
```

ویژگی‌ها:

- ترتیب زمانی Outcomeها حفظ می‌شود؛
- Blockها به‌صورت circular نمونه‌برداری می‌شوند؛
- خروجی برای Dataset یکسان کاملاً تکرارپذیر است؛
- Percentile 2.5% و 97.5% برای CI Average R استفاده می‌شود؛
- حداقل ۱۰۰ تکرار به‌صورت Fail-safe در Helper اعمال می‌شود؛
- Pipeline فعلی همیشه ۲۰۰۰ تکرار اجرا می‌کند.

## Metricهای جدید

فقط پس از Research Gate:

```text
profit_factor_rr
average_win_rr
average_nonwin_rr
active_expiry_rate_pct
no_entry_rate_pct
max_consecutive_nonwins
bootstrap_average_rr_95_lower
bootstrap_average_rr_95_upper
bootstrap_block_length
bootstrap_replicates
bootstrap_method
dependence_aware_metrics_available
```

## تعریف‌ها

### Profit Factor R

```text
sum(positive realized R) / abs(sum(negative realized R))
```

اگر Outcome منفی وجود نداشته باشد، مقدار `null` می‌ماند و Infinity گزارش نمی‌شود.

### Non-win

برای Target-hit analysis، هر Outcome فعال غیر `WIN` یک Non-win است؛ شامل:

```text
LOSS
EXPIRED_ACTIVE
```

حتی اگر `EXPIRED_ACTIVE` با R مثبت تمام شود، چون Target لمس نشده است در streak هدف‌نخورده قرار می‌گیرد.

### No-entry Rate

```text
EXPIRED_NO_ENTRY / all valid terminal candidates
```

### Active-expiry Rate

```text
EXPIRED_ACTIVE / all activated terminal candidates
```

## تست قطعی

Fixture با ۳۰ Outcome فعال:

```text
15 WIN at +2R
15 LOSS at -1R
```

نتیجه مورد انتظار:

```text
average_R=0.5
cumulative_R=15
profit_factor_R=2
average_win_R=2
average_nonwin_R=-1
max_consecutive_nonwins=1
block_length=5
```

Bootstrap با Dataset SHA یکسان باید در اجرای تکراری CI کاملاً یکسان تولید کند.

## کنترل‌های ایمنی

```text
stage_2_executed=false
metrics_withheld_before_gate=true
probability_is_calibrated=false
threshold_change_authorized=false
signal_logic_changed=false
order_routed=false
actionable_for_live=false
ENABLE_TESTNET_EXECUTION=false
ENABLE_LIVE_EXECUTION=false
```

Alpha 24 فقط ابزار ارزیابی آینده را آماده می‌کند؛ هیچ ادعای عملکردی درباره Dataset فعلی ندارد.
