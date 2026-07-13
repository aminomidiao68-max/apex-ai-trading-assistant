# گزارش پایداری شبکه و حالت Demo — APEX AI v2.2.1

## علت خطاهای مشاهده‌شده

- قطع موقت مسیر موبایل به Render یا Cold Start هنگام Deploy؛
- استفاده از Local Demo بدون Bearer Token در مسیرهای محافظت‌شده؛
- باقی‌ماندن Token قدیمی پس از Restart دیتابیس SQLite؛
- نمایش مستقیم متن IOException شامل Host/IP در رابط کاربری.

## اصلاحات

- Retry خودکار GET تا سه مرتبه با Backoff؛
- Retry پاسخ‌های 429، 502، 503 و 504؛
- Connect Timeout برابر 45 ثانیه، Read Timeout برابر 120 ثانیه و Call Timeout برابر 150 ثانیه؛
- Cache محلی آخرین Chart، Setup Scan و Public Signal Scan؛
- نمایش آخرین چارت ذخیره‌شده هنگام قطع موقت؛
- خطای فارسی ساده بدون Host، IP یا جزئیات داخلی؛
- صفحه Signal در Local Demo از تحلیل عمومی SMC استفاده می‌کند؛
- History و Journal در Demo به‌جای HTTP 401 پیام نیاز به ورود نشان می‌دهند؛
- Token سروری نامعتبر باعث پاک‌شدن Session و بازگشت خودکار به صفحه Login می‌شود.

## تست

- Backend Regression: 9 passed
- Health، Chart، Setup Scan و Public Signal Scan روی Render فعال و HTTP 200
- مسیر Signal History بدون Token به‌درستی 401 باقی مانده و داده کاربران عمومی نشده است.
