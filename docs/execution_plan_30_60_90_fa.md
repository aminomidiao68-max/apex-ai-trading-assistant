# برنامه اجرایی ۳۰ / ۶۰ / ۹۰ روزه برای رساندن APEX AI به محصول واقعی

این برنامه برای تبدیل وضعیت فعلی پروژه از **Product-Ready Foundation** به یک **محصول واقعی قابل استفاده، قابل تست و نزدیک به عرضه** طراحی شده است.

---

## هدف کلی
در پایان ۹۰ روز:
- اپ و بک‌اند پایدار باشند
- Firebase واقعی فعال باشد
- حداقل یک مسیر crypto و یک مسیر forex در حالت demo/testnet عملیاتی باشند
- فرآیند release و deployment مشخص باشد
- private alpha یا closed beta قابل اجرا باشد

---

# فاز ۱ — ۳۰ روز اول
## هدف
**پایدارسازی فنی و آماده‌سازی زیرساخت واقعی**

## خروجی مورد انتظار
- Firebase واقعی کار کند
- backend production config تکمیل شود
- حداقل یک connector crypto و یک connector forex در demo/testnet آماده باشند
- build release اندروید قابل تولید باشد

## کارهای اصلی

### 1) زیرساخت اندروید
- افزودن `google-services.json`
- sync کامل Firebase در Android Studio
- تست گرفتن FCM token روی دستگاه واقعی
- تست local notification و remote notification
- ساخت keystore release
- تست `assembleRelease` و `bundleRelease`

### 2) زیرساخت بک‌اند
- ساخت `.env` واقعی توسعه و staging
- تست production-like config
- تنظیم `FIREBASE_PROJECT_ID`
- تنظیم `FIREBASE_SERVICE_ACCOUNT_JSON`
- تست endpoint:
  - `/api/v1/notifications/test`
- فعال‌سازی logging بهتر

### 3) connectorهای اولویت‌دار
#### Crypto
- Binance Futures testnet
- Bybit testnet

#### Forex
- OANDA practice

کارها:
- تست credentialها
- تست preview
- تست dry-run
- تست route واقعی روی testnet/practice
- بررسی خطاها و رفتار retry

### 4) کیفیت داده
- تست data providerهای فعلی
- بررسی timeoutها
- تست fallback behavior
- ثبت خطاهای provider

### 5) اسناد و سیاست‌ها
- بازبینی privacy policy
- بازبینی terms and risk
- نهایی‌سازی disclaimer داخل اپ

## KPI پایان فاز ۱
- اپ روی حداقل 2 دستگاه واقعی اجرا شود
- Firebase token registration موفق باشد
- حداقل 1 push واقعی تست شود
- Binance testnet و OANDA practice حداقل یک سناریوی موفق داشته باشند
- build release بدون خطای بحرانی ساخته شود

---

# فاز ۲ — ۶۰ روز اول
## هدف
**آماده‌سازی برای Private Alpha**

## خروجی مورد انتظار
- private alpha با تعداد محدود کاربر ممکن باشد
- ژورنال، سیگنال، backtest و analytics پایدار باشند
- execution preview و test routing قابل اتکا باشند

## کارهای اصلی

### 1) کیفیت UX
- بهبود onboarding
- بهبود error states
- بهبود loading states
- بازبینی Chart interaction
- بازبینی Broker Screen و Settings

### 2) کیفیت محصول
- تست کامل flowهای مهم:
  - login/register
  - dashboard
  - live scan
  - chart
  - journal
  - backtest
  - sweep
  - walk-forward
  - analytics
  - broker preview

### 3) داده و تحلیل
- بازبینی score thresholds
- مقایسه خروجی‌ها روی چند نماد مختلف
- بررسی کیفیت signal history
- ارزیابی KPIهای strategy validation:
  - expectancy
  - profit factor
  - streaks
  - win rate

### 4) alpha readiness
- تعریف 5 تا 20 کاربر آزمایشی
- تعریف فرم بازخورد
- تعریف issue labels برای bug / UX / strategy / data
- ثبت خطاها و بازخوردها در چرخه هفتگی

### 5) امنیت و کنترل ریسک
- enforce دقیق‌تر روی live execution toggle
- محدودسازی بیشتر modeهای execution
- تعیین allow-list نمادها برای نسخه alpha

## KPI پایان فاز ۲
- crash بحرانی نداشته باشی
- کاربران alpha بتوانند همه flowهای اصلی را تست کنند
- حداقل 70٪ flowهای اصلی بدون خطای مهم کار کنند
- feedback واقعی جمع شود
- لاگ‌های backend برای عیب‌یابی کافی باشند

---

# فاز ۳ — ۹۰ روز اول
## هدف
**ورود به Closed Beta / Soft Launch آماده**

## خروجی مورد انتظار
- محصول برای گروه بزرگ‌تری از کاربران قابل تست باشد
- مدل درآمدی اولیه قابل بررسی باشد
- انتشار عمومی محدود یا soft launch ممکن شود

## کارهای اصلی

### 1) مدل محصول و قیمت‌گذاری
- تعریف نسخه رایگان و نسخه Pro
- تعیین feature gating پیشنهادی:
  - backtest پایه در رایگان
  - sweep / walk-forward / analytics پیشرفته در Pro
  - execution tools پیشرفته در Pro

### 2) آمادگی انتشار
- نهایی‌سازی Play Store listing
- نهایی‌سازی اسکرین‌شات‌ها
- نهایی‌سازی README عمومی
- نهایی‌سازی landing assets
- نهایی‌سازی release notes

### 3) عملیات production
- دامنه واقعی
- HTTPS واقعی
- monitoring
- alerting
- backup policy
- incident response draft

### 4) connectorهای بعدی
- شروع برنامه واقعی برای MT5 bridge
- شروع برنامه واقعی برای cTrader session/routing
- بهبود execution preview برای سناریوهای بیشتر

### 5) metrics
- retention اولیه
- DAU/WAU
- تعداد scan
- تعداد backtest
- تعداد journal entry
- conversion به نسخه پولی در صورت فعال‌سازی

## KPI پایان فاز ۳
- closed beta پایدار
- build release و deployment production-like مشخص
- حداقل 1 crypto route و 1 forex route در حالت قابل اتکا
- اسناد محصول و انتشار کامل
- امکان تصمیم‌گیری درباره soft launch

---

# اولویت‌بندی خیلی مهم
اگر زمان محدود باشد، این ترتیب را رعایت کن:

## اولویت سطح 1
1. Firebase واقعی
2. Binance testnet / OANDA practice
3. build release اندروید
4. production env

## اولویت سطح 2
5. UX polishing
6. analytics quality review
7. alpha testing

## اولویت سطح 3
8. MT5 bridge
9. cTrader routing
10. pricing / launch strategy

---

# خروجی نهایی این ۹۰ روز
اگر درست اجرا شود، بعد از ۹۰ روز باید این را داشته باشی:
- یک محصول private beta-ready
- با execution کنترل‌شده
- با validation tools حرفه‌ای
- با اسناد کامل
- با قابلیت ارائه جدی به کاربر، تیم یا سرمایه‌گذار

---

# جمع‌بندی
این برنامه ۳۰/۶۰/۹۰ روزه به تو کمک می‌کند پروژه را از حالت «فاندیشن قوی» به «محصول واقعی قابل بهره‌برداری» نزدیک کنی، بدون اینکه بی‌دلیل زود وارد live execution پرریسک شوی.
