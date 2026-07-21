# گزارش Signal Research Alpha 25 — Chronological OOS Stability Preparation

## هدف

آماده‌سازی ارزیابی پایداری زمانی برای Fixed Policy فعلی، بدون شروع زودهنگام Stage 2 و بدون انتخاب مجدد Model یا Threshold.

## Gate مستقل

Chronological Stability فقط وقتی فعال می‌شود که:

```text
research_ready=true
activated_terminal_outcomes >= 60
```

حداقل ۳۰ Outcome برای Research Panel پایه کافی است، اما برای سه Fold زمانی حداقل مستقل ۶۰ Outcome لازم است.

پیش از این حد:

```text
chronological_stability_status=WITHHELD_INSUFFICIENT_SAMPLE
chronological_folds=[]
worst_fold_average_rr=null
positive_average_rr_folds=null
all_folds_positive_average_rr=null
```

## روش تقسیم

- Outcomeهای فعال بر اساس `captured_at, observation_id` مرتب می‌شوند؛
- هیچ Shuffle انجام نمی‌شود؛
- سه Fold زمانی پیوسته ساخته می‌شود؛
- اگر تعداد بر سه بخش‌پذیر نباشد، Remainder از Fold اول توزیع می‌شود؛
- هیچ Train-time انتخاب یا Parameter tuning در این Panel وجود ندارد.

این Panel یک Chronological Fixed-policy OOS Stability Check است و نباید با Walk-forward model selection اشتباه گرفته شود.

## Metric هر Fold

```text
fold_index
sample_count
observed_from
observed_to
wins
losses
expired_active
target_hit_rate_pct
average_realized_rr
cumulative_realized_rr
max_drawdown_rr
max_consecutive_nonwins
```

## Metric تجمیعی

```text
worst_fold_average_rr
positive_average_rr_folds
all_folds_positive_average_rr
```

این خروجی‌ها صرفاً Stability Diagnostics هستند و به‌تنهایی مجوز Promotion یا Live نیستند.

## کنترل جلوگیری از Leakage

```text
chronological_model_reselection_used=false
chronological_shuffle_used=false
final_holdout_used=false
```

Final Holdout برای Stage 3 محفوظ می‌ماند و در Alpha 25 مصرف نمی‌شود.

## تست قطعی

Fixture با ۶۰ Outcome فعال متناوب:

```text
30 WIN at +2R
30 LOSS at -1R
```

سه Fold ۲۰تایی باید تولید کند:

```text
sample_count_each=20
average_R_each=0.5
worst_fold_average_R=0.5
positive_average_R_folds=3
all_folds_positive_average_R=true
```

در Dataset ناقص یا Integrity failure، Foldها باید خالی بمانند.

## ایمنی

```text
stage_2_executed=false
signal_logic_changed=false
threshold_change_authorized=false
probability_is_calibrated=false
precision_claimed_before_gate=false
order_routed=false
actionable_for_live=false
ENABLE_TESTNET_EXECUTION=false
ENABLE_LIVE_EXECUTION=false
```
