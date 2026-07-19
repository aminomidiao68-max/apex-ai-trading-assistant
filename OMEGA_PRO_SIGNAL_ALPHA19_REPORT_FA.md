# گزارش Signal Research Alpha 19 — Causal Outcome Integrity

## هدف

این فاز مسیر Shadow را برای ارزیابی واقعی آماده می‌کند؛ نه برای افزایش مصنوعی تعداد Candidate و نه برای ادعای سودآوری. سیاست تصمیم همچنان `precision-first` و حالت پیش‌فرض همچنان `NO_TRADE` است.

## اصلاح‌های حیاتی

### 1. قرارداد واقعی Target

خروجی واقعی SMC، `tp1` را در سطح اصلی Report و یک Target دورتر را در `levels.tp` نگه می‌داشت؛ اما Fusion فقط `levels` را عبور می‌داد و Collector فقط `levels.tp1` را می‌خواند. در صورت ایجاد Candidate واقعی، این ناسازگاری می‌توانست Capture را رد کند. Alpha 19 اکنون TP1 واقعی را صریحاً در قرارداد Fusion حفظ می‌کند و برای سازگاری Payloadهای قدیمی، نام‌های `tp1` و `tp` را بدون ساختن یا حدس‌زدن مقدار جدید می‌پذیرد. هندسه نیز Fail-closed اعتبارسنجی می‌شود:

- Long: `SL < Entry < Target`
- Short: `Target < Entry < SL`

### 2. فقط کندل بسته‌شده

Fusion و Outcome Resolver اکنون کندل درحال‌تشکیل را حذف می‌کنند. Timestamp کندل به‌عنوان زمان بازشدن Bar در نظر گرفته می‌شود و Bar فقط پس از سپری‌شدن کامل Timeframe مجاز است. Candleهای تکراری، نامعتبر، قبل از Capture یا دارای OHLC ناسازگار حذف می‌شوند.

### 3. Hard Gate تازگی داده

برای هر Frame، زمان بسته‌شدن آخرین Candle با زمان فعلی مقایسه می‌شود. اگر سن آخرین Bar بسته‌شده بیشتر از `2.5 × Timeframe` باشد، Gate مستقل `frame_freshness` شکست می‌خورد و خروجی نمی‌تواند `ACTIONABLE_CANDIDATE` باشد. این کنترل مانع تولید Candidate از Cache کهنه یا بازار بسته می‌شود.

### 4. پایان قطعی Outcome فعال

در نسخه قبل، Candidate فعال‌شده‌ای که تا پایان افق نه Stop و نه Target را لمس می‌کرد، می‌توانست برای همیشه `PENDING` بماند. Outcome جدید زیر اضافه شد:

```text
EXPIRED_ACTIVE
```

در این وضعیت، R در آخرین Close بسته‌شده‌ی افق محاسبه و بین `-1R` و Target R محدود می‌شود. سیاست برخورد هم‌زمان Stop و Target همچنان محافظه‌کارانه است:

```text
stop-first => LOSS
```

### 5. Schema v18

فیلدهای زیر به Observation اضافه شدند:

```text
bars_observed
resolution_reason
resolution_close_price
resolution_policy
```

## Research Gate

Endpointهای جدید:

```text
GET /api/v1/analysis/intraday-fusion/shadow/research-panel
GET /api/v1/analysis/intraday-fusion/shadow/system-research-panel
```

هیچ معیار Precision تجربی نمایش داده نمی‌شود مگر اینکه همه‌ی Gateهای زیر پاس شوند:

1. حداقل ۳۰ Outcome نهایی؛
2. حداقل ۳۰ Outcome فعال (`WIN/LOSS/EXPIRED_ACTIVE`)؛
3. صفر شکست SHA-256 شواهد؛
4. صفر Outcome فعال با R ناقص یا وضعیت Activation ناسازگار.

`EXPIRED_NO_ENTRY` در تعداد Outcomeهای نهایی ثبت می‌شود، اما وارد مخرج Target-hit Rate نمی‌شود. `EXPIRED_ACTIVE` به‌صورت محافظه‌کارانه Target-hit محسوب نمی‌شود.

## معیارهای مجاز پس از Gate

- Empirical Target-hit Rate؛
- Wilson 95% Confidence Interval؛
- Average / Median / Cumulative R؛
- Max Drawdown برحسب R؛
- تفکیک Market، Symbol و Context Regime با حداقل نمونه‌ی مستقل.

این معیارها Probability کالیبره‌شده یا تضمین عملکرد آینده نیستند. Label صریح:

```text
empirical_shadow_target_hit_rate_not_probability
```

## کنترل‌های ایمنی

```text
probability_is_calibrated=false
threshold_relaxation=false
ai_override_allowed=false
order_routed=false
actionable_for_live=false
ENABLE_TESTNET_EXECUTION=false
ENABLE_LIVE_EXECUTION=false
```

Signed AAB و انتشار Play Store طبق دستور مالک پروژه همچنان به مرحله‌ی نهایی انتشار موکول شده‌اند.

## وضعیت شواهد فعلی

در زمان شروع این فاز، System Shadow هنوز Candidate و Outcome حل‌شده‌ی کافی نداشت. بنابراین:

```text
status=INSUFFICIENT_EVIDENCE
precision_claimed=false
```

Alpha 19 زیرساخت ارزیابی را آماده می‌کند؛ نتیجه‌ی آماری واقعی فقط پس از جمع‌آوری نمونه‌های آینده و عبور Gate گزارش خواهد شد.
