# گزارش Research Alpha 1 — Stored Historical Backtest & Purged Walk-forward

نسخه هدف: `3.1.0-research-alpha1`

## هدف

اتصال Datasetهای immutable ذخیره‌شده به Backtest و Quant Evidence، بدون نشت Train/Test و بدون معرفی Retrospective Backtest به‌عنوان Holdout.

## فایل اصلی

`backend/app/services/stored_research_service.py`

## Fixed Stored Backtest

Endpoint:

```text
POST /api/v1/research/stored-backtest
```

قواعد:

- Dataset فقط از Registry همان User خوانده می‌شود.
- Symbol/Market/Timeframe از Manifest گرفته می‌شود، نه Payload دلخواه.
- Configuration fingerprint ساخته می‌شود.
- فقط اگر `configuration_frozen_at` قبل از `dataset.start_time` باشد و Dataset مستقل attested شده باشد، Scope برابر `fixed_config_holdout` است.
- در غیر این صورت Scope برابر `retrospective_not_holdout` است.
- Full dataset backtest به‌تنهایی Evidence آینده نیست.
- `actionable_for_live=false`.

## Stored Purged Walk-forward

Endpoint:

```text
POST /api/v1/research/stored-walk-forward
```

برای هر Fold:

1. فقط Train candles به Parameter Sweep داده می‌شود.
2. Candidate بر اساس Train انتخاب می‌شود.
3. Embargo حداقل برابر بیشترین Lookahead است.
4. Test window بعد از Embargo آغاز می‌شود.
5. Test windows هم‌پوشانی ندارند؛ `step_size >= test_size`.
6. Signal فقط با Context موجود تا زمان تصمیم ساخته می‌شود.
7. Future candles خارج Test window وارد Outcome نمی‌شوند.
8. فقط Activated OOS trades به Quant Evidence فرستاده می‌شوند.

## Sparse OOS Return Mapping

Tradeها در همه Candleها رخ نمی‌دهند. برای جلوگیری از جعل Dense return series:

- هر Return دارای `return_source_index` واقعی Candle است.
- Fold دارای `test_return_indices` است.
- Indexها باید داخل Test window و strictly increasing باشند.
- Quant service Returnها را با Source index تطبیق می‌دهد.
- Tampered/mismatched return رد می‌شود.

## Multiple Testing

تعداد Strategy trial برابر:

```text
parameter_combinations_per_fold × executed_folds
```

است و به Quant Gate منتقل می‌شود تا Bonferroni penalty اعمال شود.

## Benchmark

در این مرحله Benchmark پیش‌فرض OOS برابر Zero-edge null baseline است.

این Benchmark:

- Buy-and-hold نیست.
- Investable benchmark نیست.
- فقط بررسی می‌کند Expectancy از Null صفر عبور می‌کند یا نه.
- محدودیت آن صریحاً در Response ثبت می‌شود.

Benchmarkهای Market/Passive واقعی در مرحله بعد اضافه می‌شوند.

## Quant Promotion

Quant Validation فقط وقتی اجرا می‌شود که:

- حداقل 30 Activated OOS trade وجود داشته باشد.
- حداقل سه Fold غیرخالی وجود داشته باشد.
- Dataset point-in-time و quality contract حفظ شود.
- Fold returns و source indices معتبر باشند.

حتی `RESEARCH_CANDIDATE`:

```text
actionable_for_live=false
```

باقی می‌ماند.

## Reproducibility

Fingerprintها:

- Dataset canonical SHA
- Request/parameter space
- Fold boundaries
- selected config
- OOS returns
- random seed

اجرای یک Payload و Dataset یکسان باید Response یکسان تولید کند.

## مدل‌ها

- `StoredBacktestResearchRequest/Response`
- `StoredWalkForwardResearchRequest/Response`
- `StoredWalkForwardFoldResult`
- `QuantWalkForwardFold.test_return_indices`
- `QuantValidationRequest.return_source_indices`

## تست‌ها

فایل:

`backend/tests/test_stored_research_service.py`

پوشش:

- pre-frozen fixed holdout
- retrospective scope rejection
- train-only selection
- embargo
- test non-overlap
- بیش از 500 OOS activated trades
- Quant Research Candidate روی Fixture قابل بازتولید
- deterministic repeated response
- user isolation
- missing dataset sanitization
- overlap rejection
- insufficient embargo rejection

نتیجه کامل محلی:

```text
57 passed, 1 skipped
```

Skip فقط PostgreSQL local است؛ CI PostgreSQL آن را جداگانه اجرا می‌کند.

## محدودیت‌ها

- Fixture مثبت تست، Evidence سودآوری Strategy واقعی نیست.
- برای Validation واقعی باید Dataset چندساله واقعی ذخیره و Run شود.
- Zero-edge benchmark باید با Buy-and-hold/volatility-matched baseline تکمیل شود.
- Walk-forward هنوز PBO/CSCV multi-strategy panel کامل نیست.
- Live Execution خاموش است.
