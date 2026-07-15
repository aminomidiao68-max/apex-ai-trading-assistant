# گزارش Validation Alpha 1 — Automated Panel, DSR & Final Holdout Lock

نسخه هدف: `3.2.0-validation-alpha1`

## هدف

حذف انتخاب دستی Strategy، قفل Final Holdout پیش از Panel generation، اندازه‌گیری Selection Bias و اجرای Candidate فقط یک‌بار روی Holdout.

هیچ خروجی این مرحله Live Execution را مجاز نمی‌کند.

## فایل‌ها

- `backend/app/services/automated_panel_service.py`
- `backend/app/services/deflated_performance_service.py`
- `backend/tests/test_automated_panel_service.py`
- `backend/tests/test_deflated_performance_service.py`

## Automated Parameter Panel

Parameter Grid:

- window size
- lookahead
- score threshold
- take-profit index

قواعد:

- حداقل سه و حداکثر 100 ترکیب
- Strategyهای فاقد حداقل Development trade حذف می‌شوند.
- Dense return series یکسان برحسب Candle observation ساخته می‌شود.
- Strategy ID از Parameterها به‌صورت deterministic ساخته می‌شود.
- Panel به CSCV/PBO ارسال می‌شود.

## Immutable Experiment Lock

PostgreSQL migration/schema version: `3`

Table:

```text
research_experiments
```

ذخیره می‌کند:

- user_id
- experiment ID/version
- dataset ID/version/SHA
- request SHA
- development end
- holdout start/end
- status
- final result JSON
- created/updated time

قواعد:

- Experiment ID/version جدید قبل از محاسبه Holdout را قفل می‌کند.
- همان Experiment و همان Request، نتیجه ذخیره‌شده را برمی‌گرداند.
- همان Experiment/version با Request یا Dataset متفاوت Conflict می‌دهد.
- اجرای دوم Holdout را دوباره مصرف نمی‌کند.
- Registry User-scoped است.

## Partition

```text
Development | Embargo | Final Holdout
```

- Holdout fraction بین 10% و 40%
- Embargo حداقل برابر بیشترین Lookahead
- Panel فقط روی Development ساخته می‌شود.
- اگر PBO Panel پاس نشود، Holdout اصلاً اجرا نمی‌شود.
- فقط Strategy منتخب Development روی Holdout اجرا می‌شود.

## Final Holdout

- Configuration پس از Panel ثابت است.
- هیچ Parameter selection روی Holdout انجام نمی‌شود.
- Tradeها باید داخل Boundary قفل‌شده باشند.
- Holdout return، timestamp و source Candle index ثبت می‌شود.
- Same-window market baseline ساخته می‌شود.
- Quant diagnostics روی Holdout اجرا می‌شود.

## Probabilistic Sharpe Ratio

فرمول PSR بر اساس:

- observed non-annualized Sharpe-like
- reference Sharpe
- sample count
- skewness
- Pearson kurtosis

استفاده می‌شود.

این Metric Annualized Sharpe نیست و Future probability تضمین‌شده نیست.

## Deflated Sharpe

Expected maximum Sharpe threshold از Distribution Strategy Panel و تعداد Trialها ساخته می‌شود.

- Panel mean Sharpe
- Panel Sharpe dispersion
- Number of strategy trials
- Expected maximum Gaussian selection threshold
- Euler-Mascheroni approximation

سپس PSR Holdout نسبت به Deflated threshold محاسبه می‌شود.

Gateها:

- حداقل 30 Active holdout trade
- Positive holdout expectancy
- PSR vs zero >= 0.95
- DSR probability >= 0.95
- حداقل سه Strategy trial

Scope:

```text
per_observation_non_annualized
```

## Final Gates

- panel_robustness
- minimum_holdout_trades
- positive_holdout_net_rr
- positive_holdout_expectancy_interval
- holdout_market_baseline_outperformance
- multiple_testing_adjusted_significance
- deflated_performance
- dataset_point_in_time
- survivorship_bias_controlled
- data_quality
- live_execution_disabled

## Statusها

- `REJECT`
- `INCONCLUSIVE`
- `HIGH_OVERFIT_RISK`
- `HOLDOUT_FAILED`
- `FINAL_HOLDOUT_CANDIDATE`

حتی بالاترین Status:

```text
actionable_for_live=false
```

## Fixture Validation

Fixture deterministic با پنج Threshold:

```text
panel_status=ROBUSTNESS_CANDIDATE
selected=w20-l3-t50-tp0
holdout_trades=150
deflated_eligible=true
deflated_sharpe_probability=0.97722754
status=FINAL_HOLDOUT_CANDIDATE
failed_gates=[]
```

این Fixture فقط correctness Pipeline را ثابت می‌کند و Evidence Strategy واقعی نیست.

## تست‌ها

- Automated panel generation
- Holdout locked before panel
- Holdout not consumed on weak panel
- Idempotent stored result
- Immutable experiment conflict
- User isolation
- Grid cap
- Embargo gate
- PSR/DSR positive case
- Weak/small holdout rejection
- Missing panel fail-closed
- PostgreSQL schema v3 presence
- Authenticated endpoint
- Live authorization false

نتیجه کامل محلی:

```text
71 passed, 1 skipped
```

## محدودیت‌ها

- Gaussian expected-maximum approximation کامل‌ترین مدل DSR ممکن نیست.
- Correlated Strategy variants effective trial count را کاهش می‌دهند.
- Holdout با Experiment ID جدید می‌تواند دوباره مصرف شود؛ Governance باید تعداد Experimentها را کنترل کند.
- یک Final Holdout موفق آینده را تضمین نمی‌کند.
- Paper Trading و real execution evidence هنوز لازم است.
- Live Execution خاموش است.
