# گزارش Alpha 5 — Provider-Agnostic AI & Explainability

نسخه هدف: `3.0.0-alpha5`

## وضعیت

پیاده‌سازی کامل شده است. پذیرش انتشار منوط به سبز شدن Backend و Android GitHub CI روی همان Commit و مشاهده نسخه Alpha 5 در Render است.

## اصل معماری

موتور قطعی تنها مرجع تصمیم است. AI:

- نمی‌تواند `action_label` را تغییر دهد.
- نمی‌تواند یک تصمیم `WATCH/NO_TRADE` را Actionable کند.
- نمی‌تواند Entry، SL، TP، Position Size یا Probability جدید بسازد.
- مجوز اجرای سفارش صادر نمی‌کند.
- فقط شواهد ثبت‌شده توسط موتور قطعی را توضیح می‌دهد.

در همه پاسخ‌ها:

```text
deterministic_core_preserved=true
```

## ۱) معماری مستقل از Provider

فایل اصلی:

`backend/app/services/ai_explainability_service.py`

Providerها:

1. `deterministic`
2. `openai_compatible`
3. `gemini`

Adapter نوع OpenAI-compatible می‌تواند با Base URL و Model محیطی به OpenAI یا هر Endpoint سازگار دیگری متصل شود. Gemini Adapter از قرارداد مستقل خودش استفاده می‌کند.

External AI به‌صورت پیش‌فرض خاموش است:

```text
AI_PROVIDER=deterministic
AI_EXTERNAL_ENABLED=false
```

هیچ Key در کد، گزارش، Status یا Error چاپ نمی‌شود.

## ۲) Evidence Packet

هر درخواست توضیح شامل موارد زیر است:

- تصمیم قطعی و Action Label غیرقابل تغییر
- Symbol، Market و Timeframe
- Risk Tier
- Positive Evidence با `evidence_id`
- Negative Evidence با `evidence_id`
- Source برای هر Evidence
- `is_real` برای داده‌هایی مانند Order Flow
- Failed Hard Gates
- Invalidation
- Missing Data
- Probability Label و وضعیت Calibration

Evidence IDها یکتا و قابل Audit هستند.

برای Forex Order Flow، متن صریحاً اعلام می‌کند که داده `proxy` است و جریان متمرکز واقعی نیست.

## ۳) Negative Evidence اجباری

هیچ توضیحی بدون Negative Evidence تولید نمی‌شود. اگر تعارض اندازه‌گیری‌شده وجود نداشته باشد، ریسک باقیمانده بازار و اجرا با شناسه زیر ثبت می‌شود:

```text
N_RESIDUAL_UNCERTAINTY
```

این مورد مانع روایت‌های یک‌طرفه و بیش‌ازحد مطمئن می‌شود.

## ۴) Invalidation اجباری

Strict Decision Engine دارای Hard Gate جدید `invalidation` است. یک Setup بدون Invalidation قطعی نمی‌تواند Actionable شود.

Provider خارجی باید Invalidation را دقیقاً Echo کند. هر تغییر یا سطح ساختگی باعث رد پاسخ می‌شود.

## ۵) Critic / Verifier

Verifier موارد زیر را رد می‌کند:

- Evidence ID ناشناخته
- Citation بدون منبع
- Negative Evidence ساختگی
- Action Label متفاوت از موتور قطعی
- فیلدهای کنترلی مانند Entry، SL، TP، Position Size یا Recommendation
- عددی که در Evidence Packet وجود ندارد
- Probability/Win Rate درصدی بدون Calibration
- ادعای سود تضمینی، برد قطعی یا بدون ریسک
- دستور مستقیم Buy/Sell/Execute
- Invalidation متفاوت
- فیلد اضافه خارج از Schema
- Risk Note یا Confirmation بدون Citation

اگر Provider رد شود، پاسخ آن به کاربر نشان داده نمی‌شود و سیستم به Deterministic Fallback برمی‌گردد.

## ۶) Refusal

در نبود هرکدام از موارد حیاتی زیر، Provider فراخوانی نمی‌شود:

- Positive Evidence
- Negative Evidence
- Invalidation
- Deterministic Decision
- هر Missing Data صریح در قرارداد

خروجی:

```text
mode=refusal
grounded=false
refusal_reason=missing_critical_data
```

## ۷) Fail-Closed Reliability

برای Providerهای خارجی:

- Timeout محدود
- Cache مبتنی بر Hash شواهد
- Circuit Breaker
- Failure Threshold و Cooldown قابل تنظیم
- عدم Follow Redirect
- خطای عمومی `provider_unavailable`
- حذف کامل Raw Exception، URL و Secret از پاسخ

حتی در قطع کامل Provider، تصمیم قطعی و توضیح Deterministic در دسترس می‌ماند.

## ۸) API

### Status

```text
GET /api/v1/ai/status
```

فقط وضعیت پیکربندی را نشان می‌دهد؛ Key، Endpoint خصوصی یا Secret نمایش داده نمی‌شود.

### Explain

```text
POST /api/v1/ai/explain
```

- نیازمند Bearer Authentication
- ورودی Strongly Typed
- خروجی Grounded/Verified
- AI فقط نقش Explanation دارد

## ۹) ادغام با تحلیل زنده

- Strict Decision همیشه یک توضیح Deterministic و Verified تولید می‌کند.
- صفحه Chart می‌تواند در حالت opt-in از Provider خارجی استفاده کند.
- Scanner چندنمادی External AI را فراخوانی نمی‌کند تا هزینه و Latency کنترل شود.
- هر پاسخ خارجی پیش از نمایش از Verifier عبور می‌کند.

## ۱۰) Android Explainability Panel

پنل Android اکنون نمایش می‌دهد:

- Provider
- Mode: Generated / Deterministic / Fallback / Refusal
- Verified / Refused
- Deterministic Action Label
- Positive Evidence با Evidence ID
- Negative Evidence با Evidence ID
- What Would Confirm
- Invalidation
- Calibration Label
- قفل `Deterministic core preserved`

هیچ Probability کالیبره‌نشده به‌صورت احتمال واقعی نمایش داده نمی‌شود.

## ۱۱) تست‌ها

فایل جدید:

`backend/tests/test_alpha5_ai_explainability.py`

پوشش:

- Provider معتبر و Citation کامل
- Cache
- تلاش برای Override تصمیم
- Evidence ID ساختگی
- Probability و Win Rate ساختگی
- ادعای تضمین سود
- Invalidation ساختگی
- Refusal قبل از فراخوانی Provider
- Sanitization خطا و Secret
- Circuit Breaker
- Forex Proxy honesty
- الزام Calibration ID
- Endpoint Authentication
- Secret-safe Status
- ادغام با Strict Decision

نتیجه محلی:

```text
28 passed
```

## ۱۲) ایمنی

- `NO_TRADE` حالت پیش‌فرض باقی مانده است.
- External AI پیش‌فرض خاموش است.
- هیچ API Key یا Credential تغییر نکرده است.
- Live Execution همچنان خاموش است.
- این سیستم سود، دقت یا عملکرد آینده را تضمین نمی‌کند.
