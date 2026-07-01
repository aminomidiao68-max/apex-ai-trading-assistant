# Master Launch Plan — APEX AI

این سند، **برنامه جامع نهایی برای رساندن APEX AI به عرضه واقعی** است و همه چیز را در یک نقشه اجرایی واحد جمع می‌کند:
- اولویت‌ها
- فازها
- سرویس‌های لازم
- ترتیب اجرای کارها
- معیار عبور از هر مرحله
- ریسک‌ها

---

## 1) هدف نهایی
رساندن APEX AI از وضعیت فعلیِ **Product-Ready Foundation** به یک محصول:
1. **پایدار**
2. **قابل تست با کاربر واقعی**
3. **ایمن از نظر ریسک اجرایی**
4. **قابل انتشار محدود یا private beta**

---

## 2) تعریف فازهای کلان

### فاز A — Production Readiness
تمرکز:
- تکمیل تنظیمات فنی
- آماده‌سازی release
- فعال‌سازی زیرساخت‌های واقعی

### فاز B — Private Alpha
تمرکز:
- تست محدود با کاربران منتخب
- جمع‌آوری باگ و feedback
- تثبیت UX و connectorها

### فاز C — Closed Beta / Soft Launch
تمرکز:
- افزایش تعداد کاربر
- سنجش پایداری عملیاتی
- آماده‌سازی برای عرضه عمومی محدود

---

## 3) اولویت‌های اجرایی از بالا به پایین

### اولویت سطح 1 — حیاتی
- Firebase واقعی
- Backend production env
- Release build اندروید
- Binance Futures testnet
- OANDA practice
- HTTPS + domain

### اولویت سطح 2 — بسیار مهم
- Bybit testnet
- Monitoring و logging
- بهبود UX خطاها و loading
- تست دستگاه واقعی
- privacy / terms / risk نهایی

### اولویت سطح 3 — توسعه بعدی
- MT5 bridge واقعی
- cTrader routing واقعی
- optimization گسترده‌تر
- chart interaction پیشرفته‌تر
- monetization / pricing validation

---

## 4) Workstreamهای اصلی

## 4.1 Workstream محصول
### خروجی‌ها
- بهبود onboarding
- بهبود Settings
- نهایی‌سازی disclaimer و risk acknowledgment
- سناریوهای اصلی کاربر

### معیار تکمیل
- کاربر بتواند بدون ابهام مسیرهای اصلی را طی کند
- خطاها و وضعیت‌های loading قابل فهم باشند

---

## 4.2 Workstream اندروید
### کارها
- افزودن `google-services.json`
- تست FCM token
- تست notification واقعی
- تست release signing
- ساخت AAB/APK release
- تست روی چند دستگاه واقعی

### معیار تکمیل
- release build موفق
- بدون crash بحرانی
- توکن FCM ثبت شود

---

## 4.3 Workstream بک‌اند
### کارها
- ساخت `.env` واقعی staging/production
- تنظیم HTTPS و domain
- تنظیم secretها
- تست endpoints حیاتی
- لاگ‌گیری و مانیتورینگ

### معیار تکمیل
- health / analytics / execution preview پایدار باشند
- خطاها قابل ردیابی باشند

---

## 4.4 Workstream connectorها
### Crypto
- Binance Futures
- Bybit

### Forex
- OANDA
- MT5 bridge
- cTrader session/routing

### معیار تکمیل
- حداقل یک connector crypto و یک connector forex در محیط دمو/تست عملیاتی باشند

---

## 4.5 Workstream اعتبارسنجی استراتژی
### کارها
- backtest روی نمادهای منتخب
- sweep روی پارامترهای اصلی
- walk-forward روی داده‌های بیشتر
- بازبینی thresholdها

### معیار تکمیل
- strategy evaluation workflow قابل اتکا و قابل تکرار باشد

---

## 4.6 Workstream انتشار و برند
### کارها
- README عمومی نهایی
- screenshots
- play store copy
- release notes
- privacy / terms
- landing / presentation assets

### معیار تکمیل
- پروژه برای ارائه، نمایش و انتشار محدود آماده باشد

---

## 5) برنامه زمانی ۱۲ هفته‌ای

## هفته 1 تا 2
### تمرکز
- env واقعی
- domain / HTTPS
- keystore
- Firebase setup

### خروجی
- backend staging up
- android release signing scaffold verified
- FCM client config حاضر

---

## هفته 3 تا 4
### تمرکز
- Binance testnet
- OANDA practice
- تست notification واقعی
- تست release build

### خروجی
- حداقل یک سناریوی crypto route
- حداقل یک سناریوی forex route
- FCM واقعی تست‌شده

---

## هفته 5 تا 6
### تمرکز
- بهبود UX
- تست کامل flowهای اصلی
- logging / monitoring
- review خطاها

### خروجی
- نسخه private alpha ready
- باگ‌های بحرانی دسته‌بندی و کاهش یافته

---

## هفته 7 تا 8
### تمرکز
- private alpha
- feedback واقعی کاربران محدود
- اصلاح Journal / Broker / Chart / Signals

### خروجی
- گزارش بازخورد alpha
- کاهش friction در UX

---

## هفته 9 تا 10
### تمرکز
- sweep / walk-forward گسترده‌تر
- analytics پیشرفته‌تر
- Bybit testnet hardening

### خروجی
- معیارهای بهتر برای quality gates
- گزارش validation بهتر

---

## هفته 11 تا 12
### تمرکز
- closed beta readiness
- Play Store / distribution prep
- legal and release review

### خروجی
- نسخه آماده closed beta / soft launch

---

## 6) Gateهای عبور بین فازها

## Gate 1 — ورود به Private Alpha
همه این‌ها باید برقرار باشند:
- [ ] release build موفق
- [ ] Firebase token registration موفق
- [ ] backend staging پایدار
- [ ] Binance testnet یا OANDA practice عملیاتی
- [ ] risk guardها enforce شده
- [ ] privacy / terms / risk docs حاضر

## Gate 2 — ورود به Closed Beta
- [ ] crash بحرانی وجود نداشته باشد
- [ ] کاربران alpha بتوانند flowهای اصلی را کامل طی کنند
- [ ] feedbackهای اصلی اعمال شده باشند
- [ ] analytics و journal پایدار باشند

## Gate 3 — Soft Launch
- [ ] مانیتورینگ فعال باشد
- [ ] دامنه و HTTPS نهایی باشند
- [ ] حداقل یک route crypto و یک route forex پایدار باشند
- [ ] اسناد انتشار کامل باشند

---

## 7) چک‌لیست سرویس‌ها و اکانت‌ها

### لازم در همین ابتدای مسیر
- [ ] GitHub / Git hosting
- [ ] VPS / cloud server
- [ ] domain
- [ ] SSL/TLS
- [ ] Firebase project
- [ ] `google-services.json`
- [ ] Firebase service account JSON
- [ ] TwelveData API key
- [ ] Binance testnet credentials
- [ ] OANDA practice credentials
- [ ] Android release keystore

### لازم در فازهای بعدی
- [ ] Bybit testnet credentials
- [ ] MT5 bridge provider / MetaAPI
- [ ] cTrader Open API credentials
- [ ] Google Play Developer account
- [ ] monitoring stack

---

## 8) مسئولیت‌های پیشنهادی
اگر تیم کوچک باشد، این نقش‌ها لازم‌اند:

### Product / Founder
- اولویت‌بندی
- بازخورد کاربران
- تصمیم‌های release

### Android Engineer
- UX
- release build
- Firebase client
- performance UI

### Backend Engineer
- API
- execution preview
- connectors
- storage
- monitoring

### Quant / Strategy Reviewer
- بررسی کیفیت سیگنال
- review thresholdها
- تحلیل backtest / walk-forward

### Legal / Compliance Advisor
- risk disclosure
- privacy / terms review

---

## 9) ریسک‌های اصلی و پاسخ پیشنهادی

### ریسک 1: تکیه بیش از حد روی live execution
**پاسخ:**
- تا قبل از testnet/practice کامل، live execution خاموش بماند

### ریسک 2: کیفیت ناکافی دیتا
**پاسخ:**
- provider اصلی و fallback مشخص شود
- timeout / degraded mode پیاده‌سازی شود

### ریسک 3: برداشت اشتباه کاربر از محصول
**پاسخ:**
- branding و copy محصول روی «workflow assistant» متمرکز بماند، نه «ماشین سود»

### ریسک 4: connectorهای نیمه‌کامل
**پاسخ:**
- MT5 و cTrader فقط با برچسب foundation نگه‌داری شوند تا integration واقعی تکمیل شود

---

## 10) Deliverableهای نهایی برای Launch
در پایان این برنامه باید این خروجی‌ها آماده باشند:
- اپ release build
- backend staging/production-ready
- Firebase واقعی
- docs کامل
- screenshots / presentation / listing copy
- حداقل یک route crypto و یک route forex قابل اتکا
- user onboarding قابل قبول
- risk policy واضح

---

## 11) تصمیم نهایی پیشنهادی
اگر بخواهم خیلی عملیاتی جمع‌بندی کنم، ترتیب درست این است:
1. Firebase واقعی
2. Binance testnet + OANDA practice
3. release build اندروید
4. HTTPS + domain + monitoring
5. private alpha
6. بهبود UX و analytics
7. closed beta
8. سپس MT5 / cTrader full integration

---

## 12) جمع‌بندی نهایی
این Master Launch Plan طوری طراحی شده که APEX AI:
- با عجله وارد live execution نشود
- ولی به‌صورت واقعی و مرحله‌ای به یک محصول حرفه‌ای نزدیک شود
- هم از نظر فنی و هم از نظر تجاری، مسیر رشد مشخصی داشته باشد

اگر این برنامه با نظم اجرا شود، پروژه می‌تواند از یک foundation بسیار قوی به یک **Private Beta Ready Trading Product** تبدیل شود.
