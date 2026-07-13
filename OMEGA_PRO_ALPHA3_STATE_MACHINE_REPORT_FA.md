# گزارش APEX Omega Pro v3 Alpha 3 — Setup State Machine

## Stateها

- FORMING: ستاپ واقعی تشخیص داده شده ولی Gateهای کافی ندارد.
- ARMED: حداکثر دو Hard Gate تا تأیید فاصله دارد و Data Quality مناسب است.
- CONFIRMED: تمام Strict Gateها پاس شده‌اند.
- TRIGGERED: قیمت وارد Entry Zone شده است.
- INVALIDATED: قیمت Invalidation را شکسته یا Strict Gate قبل از Trigger از دست رفته است.
- EXPIRED: زمان ستاپ گذشته یا در دو اسکن متوالی دیده نشده است.

## رفتار

- Deduplication با کلید Symbol/Timeframe/Direction/Setup Type؛
- Expiry متناسب با Timeframe و `expires_after_bars`؛
- Trigger با Entry Low/High؛
- Invalidation جهت‌دار Long/Short؛
- Cooldown سه کندلی بعد از Invalidated/Expired؛
- نگهداری Terminal State تا ۴۸ ساعت؛
- first_seen، armed_at، confirmed_at، triggered_at، terminated_at؛
- transition_reason، scan_count و missing_scans.

## Android

- تب Active شامل Confirmed و Triggered؛
- تب Armed؛
- تب Forming؛
- تب Closed شامل Invalidated و Expired؛
- نمایش Lifecycle Badge، دلیل Transition، تعداد Scan و Expiry.

## تست

- State progression کامل Forming → Armed → Confirmed → Triggered → Invalidated؛
- Cooldown test؛
- Scanner lifecycle contract test؛
- Backend Regression suite.
