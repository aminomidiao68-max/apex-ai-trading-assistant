# گزارش APEX Omega Pro — Operational Alpha 10

## هدف
پایش Drift داده/بازده/نوسان و SLO عملیاتی، بدون تبدیل خروجی به ادعای سود یا مجوز Live.

## Drift
- Datasetهای immutable و user-scoped
- Log return مرتب‌شده
- PSI با binهای مرجع
- KS statistic بدون p-value یا Probability claim
- Volatility ratio و Mean-return shift
- حداقل نمونه پیش‌فرض ۶۰
- وضعیت‌های STABLE / WATCH / BLOCKED
- Run ID و Request hash و ذخیره PostgreSQL
- `probability_claimed=false`
- `actionable_for_live=false`

## SLO
- حداقل Sample Gate
- P95 latency threshold
- Server error-rate threshold
- INSUFFICIENT_EVIDENCE / WITHIN_SLO / SLO_BREACH
- مجوز Live صادر نمی‌کند.

## Schema v14
```text
operational_drift_runs
```

## API
```text
POST /api/v1/operations/drift
POST /api/v1/operations/slo
```

## ایمنی
Testnet عملیاتی به‌دلیل محدودیت جغرافیایی متوقف و Flagهای Testnet/Live خاموش باقی مانده‌اند. هیچ تضمین عملکرد آینده وجود ندارد.
