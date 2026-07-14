# گزارش Quant Alpha 1 — Evidence & Calibration Lab

نسخه هدف: `3.1.0-quant-alpha1`

## هدف واقعی

این مرحله برای افزایش تعداد Indicator یا تولید سیگنال بیشتر ساخته نشده است. هدف آن جلوگیری از ادعای سودآوری بدون مدرک و ایجاد یک Gate آماری قابل بازتولید است.

هیچ خروجی این سرویس Live Execution را مجاز نمی‌کند:

```text
actionable_for_live=false
```

بالاترین وضعیت ممکن فقط:

```text
RESEARCH_CANDIDATE
```

است.

## Dataset Manifest

ابزار:

`backend/scripts/build_dataset_manifest.py`

الزامات CSV:

- timestamp
- open
- high
- low
- close
- volume

Validation:

- OHLC integrity
- قیمت مثبت
- Volume غیرمنفی
- timestamp strictly increasing
- duplicate rejection
- حداقل sample
- SHA-256 فایل
- start/end/sample count

Attestationهای اجباری برای Research Candidate:

- `is_point_in_time=true`
- `is_survivorship_bias_controlled=true`
- `is_independent_holdout=true`
- `data_quality_score>=90`
- source SHA-256

این Flagها ادعای Operator هستند و جای Audit مستقل Provider را نمی‌گیرند.

## Quant Validation

فایل:

`backend/app/services/quant_validation_service.py`

Endpointها:

```text
POST /api/v1/research/quant-validate
POST /api/v1/research/purged-split-plan
```

هر دو نیازمند Bearer Authentication هستند و Rate Limit گروه Heavy دارند.

## آمار توصیفی

- empirical win rate
- net R
- expectancy R
- median R
- standard deviation
- profit factor
- max drawdown R

این موارد فقط توصیف Sample تاریخی هستند و Probability آینده نیستند.

## Expectancy Interval

- Circular block bootstrap
- حفظ نسبی dependence محلی در مقایسه با IID bootstrap
- Confidence level قابل تنظیم
- Seed ثابت و reproducible
- Lower bound باید بالاتر از صفر باشد تا Gate پاس شود.

## Null Test و Multiple Testing

- Sign-flip test حول Null برابر صفر
- One-sided p-value
- Bonferroni alpha برابر `0.05 / strategies_tried`
- Strategy mining زیاد باعث سخت‌ترشدن Gate می‌شود.

این مرحله جلوی انتخاب بهترین نتیجه از میان هزاران آزمایش بدون Penalty را می‌گیرد.

## Benchmark Gate

- Benchmark returns باید هم‌طول Strategy باشد.
- Paired difference محاسبه می‌شود.
- Block-bootstrap interval اختلاف ساخته می‌شود.
- Lower bound اختلاف باید مثبت باشد.

بدون Benchmark، خروجی نمی‌تواند Research Candidate شود.

## Purged Walk-forward

هر Fold شامل:

- train start/end index
- embargo bars
- test start/end index
- selected config ID
- test returns

Validation:

- Train/Test chronology
- Embargo اجباری
- Test range non-overlap
- Fold returns باید دقیقاً با Slice Dataset برابر باشد.
- حداقل سه Fold
- حداقل 60% Fold مثبت
- Aggregate test net R مثبت

Endpoint Split Plan یک Plan deterministic و fingerprint‌شده می‌سازد و overlap را گزارش می‌کند.

## Monte Carlo

- Shuffle drawdown distribution
- P50/P95/P99 Max Drawdown R
- Bootstrap-with-replacement equity paths
- Risk fraction per trade
- Ruin drawdown threshold

`simulated_risk_of_ruin` فقط Simulation Estimate است و Probability کالیبره Live نیست.

## Calibration Diagnostics

در صورت ارائه Prediction و Outcome:

- Brier Score
- Base-rate Brier Score
- Brier Skill Score
- Expected Calibration Error
- Maximum Calibration Error
- Log Loss
- Reliability bins

Calibration فقط وقتی مجاز است که:

1. حداقل 500 prediction خارج از نمونه وجود داشته باشد.
2. Dataset independent holdout باشد.
3. Point-in-time باشد.
4. Data Quality حداقل 90 باشد.
5. Brier Skill مثبت باشد.
6. ECE حداکثر 0.05 باشد.
7. MCE حداکثر 0.15 باشد.

فقط در این صورت Calibration ID ساخته می‌شود. Scope آن همچنان Dataset-specific independent holdout است.

## Hard Gates

- source_fingerprint
- point_in_time_dataset
- survivorship_bias_controlled
- independent_holdout
- data_quality
- strict_timestamps
- minimum_sample_size
- positive_expectancy_interval
- benchmark_available
- benchmark_outperformance
- multiple_testing_control
- purged_walk_forward_contract
- walk_forward_stability
- drawdown_budget
- risk_of_ruin_budget
- probability_calibration، فقط هنگام ارائه Probability

## Statusها

- `REJECT`: Dataset integrity کافی نیست.
- `INSUFFICIENT_EVIDENCE`: Sample/Benchmark/Fold کافی نیست.
- `WATCH`: Evidence وجود دارد ولی همه Gateها پاس نشده‌اند.
- `RESEARCH_CANDIDATE`: تمام Core Gateها پاس شده‌اند؛ هنوز Live مجاز نیست.

## محدودیت‌های صریح

- Historical result آینده را تضمین نمی‌کند.
- PBO/CSCV به Matrix چند Strategy نیاز دارد و از یک Return Series ساخته نمی‌شود.
- Sign-flip exchangeability assumption دارد.
- Risk-of-ruin simulation estimate است.
- Dataset flags نیازمند Audit خارجی هستند.
- هیچ داده چندساله واقعی در این Commit به‌صورت مصنوعی ساخته نشده است.

## تست

فایل:

`backend/tests/test_quant_validation_service.py`

پوشش:

- Research Candidate با Evidence کامل
- deterministic reproducibility
- dataset reject
- multiple-testing penalty
- calibration holdout gate
- fold-return tampering rejection
- purged split overlap
- timestamp/sample mismatch
- CSV manifest SHA/OHLCV validation
- Auth API contract
- Live authorization always false

نتیجه محلی کامل:

```text
47 passed, 1 skipped
```

Skip مربوط به PostgreSQL local است و CI PostgreSQL آن را جداگانه اجرا می‌کند.
