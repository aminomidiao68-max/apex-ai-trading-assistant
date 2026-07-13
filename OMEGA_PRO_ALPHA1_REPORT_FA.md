# گزارش APEX Omega Pro v3 Alpha 1 — Strict Core

## موتور کیفیت داده

امتیاز ۰ تا ۱۰۰ براساس:

- حداقل تاریخچه؛
- OHLC معتبر؛
- ترتیب Timestamp؛
- Duplicate؛
- Gap متناسب با Timeframe؛
- Range Outlier؛
- پوشش Volume و تفاوت Crypto/Forex.

## موتور Regime

- Trending
- Balanced
- Volatile
- Compressed
- Choppy

برای هر Regime، Risk Multiplier مستقل تولید می‌شود.

## Strict Omega — دوازده Hard Gate

1. Data Quality ≥ 78
2. Data Integrity
3. Direction معتبر
4. Grade A+/A/B
5. Confluence ≥ 65
6. Estimated Probability ≥ 68
7. RR ≥ 2
8. News Clear
9. HTF Alignment یا Reversal Exception تأییدشده
10. بازار غیر Choppy یا Confluence بسیار بالا
11. Conflict Budget
12. Trade Plan معتبر

Order Flow Evidence فعلاً Gate نرم است و در Alpha 2 با داده واقعی Crypto تقویت می‌شود.

## رفتار خروجی

- ACTIONABLE: تمام Hard Gateها پاس شده‌اند.
- WATCH: ستاپ واقعی وجود دارد ولی یک یا چند Gate ناقص است.
- REJECT: داده یا ساختار برای معامله کافی نیست.

Probability فعلاً `model_estimate_not_calibrated` است و صریحاً Calibrated اعلام نمی‌شود.

## نتیجه تست اسکن واقعی

از ۷۰ ترکیب:

- Confirmed سخت‌گیرانه: ۲
- Forming: ۲۰
- تمام Confirmedها ۱۲/۱۲ Hard Gate را پاس کردند.
- Data Quality نمونه‌های Confirmed: ۱۰۰
- Backend Regression: ۱۰ تست موفق
