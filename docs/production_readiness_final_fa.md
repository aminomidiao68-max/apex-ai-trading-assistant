# چک نهایی Production Readiness برای APEX AI

این سند برای پاسخ به یک سؤال کلیدی نوشته شده:
**اگر بخواهیم APEX AI را از حالت foundation / MVP به یک محصول واقعی، پایدار و قابل استفاده عملیاتی نزدیک کنیم، دقیقاً چه چیزهایی باید تکمیل شوند؟**

---

## 1) حداقل‌های فنی اجباری قبل از Production

### 1.1 بک‌اند
- [ ] فایل `.env` تولیدی واقعی ساخته شود
- [ ] `APP_ENV=production` تنظیم شود
- [ ] `ENABLE_LIVE_EXECUTION=false` تا پایان تست کامل باقی بماند
- [ ] دامنه واقعی برای API تعیین شود
- [ ] HTTPS واقعی با گواهی معتبر فعال شود
- [ ] CORS فقط برای دامنه‌های مجاز محدود شود
- [ ] لاگ‌های ساختاریافته برای درخواست‌ها و خطاها فعال شوند
- [ ] rate limit برای endpointهای حساس در نظر گرفته شود
- [ ] backup strategy برای دیتابیس مشخص شود

### 1.2 دیتابیس
SQLite برای MVP مناسب است، اما برای production واقعی بهتر است:
- [ ] مهاجرت به PostgreSQL یا DB production-grade انجام شود
- [ ] migration strategy تعریف شود
- [ ] backup و restore تست شود
- [ ] retention policy برای لاگ‌ها و ژورنال مشخص شود

### 1.3 اندروید
- [ ] `google-services.json` اضافه شود
- [ ] release signing واقعی انجام شود
- [ ] `keystore.properties` یا envهای signing به‌صورت امن تنظیم شوند
- [ ] `API_BASE_URL` و `WS_BASE_URL` نسخه release روی دامنه واقعی قرار بگیرند
- [ ] build release واقعی (AAB/APK) تست شود
- [ ] اپ روی چند دستگاه واقعی تست شود

---

## 2) الزامات اجرای زنده سفارش

### 2.1 Binance Futures
- [ ] API key و secret واقعی یا testnet معتبر تنظیم شود
- [ ] symbol mapping واقعی تست شود
- [ ] min qty / step size / precision ruleها کنترل شوند
- [ ] پاسخ‌های خطا و retry policy بررسی شوند

### 2.2 Bybit
- [ ] API credential واقعی/testnet تنظیم شود
- [ ] mapping category / symbol / qty تست شود
- [ ] رفتار order create در سناریوهای خطا بررسی شود

### 2.3 OANDA
- [ ] practice/live account آماده شود
- [ ] instrument mapping مثل `EUR_USD` تست شود
- [ ] units و rounding ruleها کنترل شود

### 2.4 MT5
برای production واقعی، foundation فعلی کافی نیست.
باید یکی از این مسیرها انتخاب شود:
- [ ] MetaAPI integration
- [ ] local MT5 bridge service
- [ ] server-side bridge اختصاصی

### 2.5 cTrader
برای production واقعی باید:
- [ ] Open API session management تکمیل شود
- [ ] account mapping کامل شود
- [ ] symbol normalization کامل شود
- [ ] order lifecycle و error handling نهایی شود

---

## 3) امنیت و کنترل ریسک

### 3.1 اسرار و Credentialها
- [ ] هیچ secretی داخل سورس نباشد
- [ ] `.env` واقعی داخل مخزن commit نشود
- [ ] service account Firebase داخل مخزن نباشد
- [ ] keystore داخل مخزن نباشد
- [ ] API keys ترجیحاً در secret manager یا vault نگه‌داری شوند

### 3.2 ریسک معاملاتی
- [ ] حداقل score برای execution نهایی شود
- [ ] حداکثر daily loss enforce شود
- [ ] حداکثر open positions enforce شود
- [ ] حداکثر consecutive loss enforce شود
- [ ] حالت testnet-first در تنظیمات حفظ شود
- [ ] live execution toggle فقط با چند مرحله تأیید فعال شود

### 3.3 کنترل محصول
- [ ] صفحه Risk Disclaimer اجباری شود
- [ ] کاربر قبل از live execution باید risk acknowledgement را تأیید کند
- [ ] Terms / Privacy / Risk Disclosure نهایی و حقوقی‌سازی شوند

---

## 4) کیفیت داده و تحلیل

### 4.1 دیتا
- [ ] provider اصلی کریپتو و provider اصلی فارکس مشخص شوند
- [ ] fallback provider در نظر گرفته شود
- [ ] timeout / retry / degraded mode طراحی شود
- [ ] data validation برای کندل‌ها و snapshotها فعال شود

### 4.2 تحلیل و سیگنال
- [ ] آستانه‌های score بازبینی شوند
- [ ] نتایج backtest و walk-forward روی بازارهای مختلف مقایسه شوند
- [ ] KPIهای استراتژی مثل expectancy، profit factor و drawdown پایش شوند
- [ ] signal quality review process تعریف شود

---

## 5) نوتیفیکیشن واقعی

### 5.1 سمت اندروید
- [ ] `google-services.json` اضافه شود
- [ ] Firebase Console setup کامل شود
- [ ] token registration روی دستگاه واقعی تست شود

### 5.2 سمت بک‌اند
- [ ] `FIREBASE_PROJECT_ID` تنظیم شود
- [ ] `FIREBASE_SERVICE_ACCOUNT_JSON` تنظیم شود
- [ ] endpoint تست notification روی token واقعی تست شود
- [ ] failure logging و invalid token cleanup تعریف شود

---

## 6) مانیتورینگ و عملیات

### 6.1 Observability
- [ ] health check واقعی برای سرویس‌ها پایش شود
- [ ] log aggregation در نظر گرفته شود
- [ ] alerting برای crash / execution failure / provider outage فعال شود

### 6.2 Incident Response
- [ ] plan برای قطع providerها تعریف شود
- [ ] plan برای disable سریع live execution تعریف شود
- [ ] plan برای rollback release نوشته شود

---

## 7) تست نهایی قبل از عرضه

### 7.1 تست فنی
- [ ] login/register/logout
- [ ] dashboard
- [ ] signals/live scan
- [ ] chart
- [ ] journal
- [ ] analytics
- [ ] backtest/sweep/walk-forward
- [ ] execution preview
- [ ] notification registration

### 7.2 تست مالی/عملیاتی
- [ ] testnet order routing
- [ ] demo journal workflow
- [ ] risk rejection scenarios
- [ ] invalid credential scenarios
- [ ] provider outage simulation

### 7.3 تست UX
- [ ] splash
- [ ] onboarding
- [ ] settings
- [ ] broker lab
- [ ] error messages
- [ ] loading states

---

## 8) معیار آمادگی برای ورود به Private Beta
حداقل اگر این‌ها برقرار باشند، می‌توان وارد private beta شد:
- backend پایدار
- اپ release build پایدار
- Firebase واقعی فعال
- حداقل یک connector واقعی testnet/demo کامل
- risk guardها enforce شده
- مستندات release و user guide تکمیل

---

## 9) معیار آمادگی برای ورود به Production محدود
- [ ] دو provider داده پایدار
- [ ] حداقل یک connector crypto و یک connector forex عملیاتی
- [ ] monitoring فعال
- [ ] alerting فعال
- [ ] legal docs نهایی
- [ ] privacy و disclaimer نهایی
- [ ] incident response مشخص
- [ ] چند هفته demo / paper / testnet بدون خطای بحرانی

---

## 10) جمع‌بندی نهایی
در وضعیت فعلی، APEX AI یک **Product-Ready Foundation** است.
برای production واقعی، بیشترین فاصله باقی‌مانده مربوط به این‌هاست:
1. credentialهای واقعی
2. push واقعی Firebase
3. bridge واقعی MT5
4. routing کامل cTrader
5. migration به زیرساخت production-grade

اگر این پنج محور تکمیل شوند، پروژه می‌تواند از یک foundation بسیار خوب به یک محصول عملیاتی جدی نزدیک شود.
