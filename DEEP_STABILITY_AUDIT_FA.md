# ممیزی عمیق پایداری APEX AI v2.2.2

## موارد تأییدشده

- Backend CI و Android CI سبز؛
- API، Chart، Setup Scan و Public Signal Scan فعال؛
- Live Execution خاموش؛
- مسیرهای خصوصی بدون Token به‌درستی 401؛
- هیچ Secret واقعی در Tree فعلی پیدا نشد؛
- ماتریس‌های Chart/Zone/Setup قبلی موفق.

## باگ‌های اصلاح‌شده

1. Dashboard در Demo به‌علت شکست Trade Stats کل داده عمومی را Offline می‌کرد؛ درخواست‌های عمومی و خصوصی اکنون مستقل‌اند.
2. Journal در Demo به‌جای راهنما خطای 401 نشان می‌داد؛ اکنون پیام ورود نمایش داده می‌شود.
3. Analytics و Backtest در Demo خطای خام داشتند؛ اکنون Demo-safe هستند.
4. APKهای GitHub با Debug Key تصادفی ساخته می‌شدند و Update نصب نمی‌شد؛ Debug Key ثابت و صرفاً توسعه‌ای اضافه شد.
5. Force Scan قابل تکرار سریع بود؛ Cooldown شصت‌ثانیه‌ای اضافه شد.
6. Security Headerهای HTTP وجود نداشت؛ HSTS، nosniff، frame deny، referrer و permissions policy اضافه شدند.
7. هشدار Node 20 در CI؛ Checkout و Upload Artifact به نسخه‌های Node 24 ارتقا یافتند.
8. خطر دیتابیس Ephemeral پنهان بود؛ Readiness اکنون هشدار صریح Persistence می‌دهد.

## محدودیت زیرساختی باقی‌مانده

SQLite محلی Render برای حساب Production پایدار نیست. مهاجرت واقعی به PostgreSQL نیازمند ساخت Database و `DATABASE_URL` در حساب Render است. تا آن زمان Local Demo و قابلیت‌های عمومی پایدارند، اما حساب‌ها و ژورنال سروری ممکن است با Redeploy از بین بروند.

## امضای Debug

فایل `android/app/apex-debug.keystore` فقط برای Debug و با رمز استاندارد `android` است و نباید برای Release استفاده شود. نصب نسخه 2.2.2 ممکن است یک بار نیازمند حذف APK قبلی باشد؛ نسخه‌های بعدی Debug روی 2.2.2 قابل Update خواهند بود.
