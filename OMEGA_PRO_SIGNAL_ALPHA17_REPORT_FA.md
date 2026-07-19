# Signal Shadow Alpha 17 — Automated Collector/Resolver

- Worker فقط در Staging فعال
- Capture پنل ثابت ۹ نمادی هر ۱۵ دقیقه
- جلوگیری از Duplicate با minimum interval
- Resolve خودکار Outcomeهای Pending از کندل‌های آینده
- خطای Provider فقط Skip می‌شود
- حساب سیستمی user_id=0 و Panel جدا
- Production worker=false
- order_routed=false / live=false
- Precision فقط پس از ۳۰ Outcome resolved
