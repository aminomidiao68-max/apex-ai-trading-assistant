# نسخه نهایی تحویلی APEX AI

## وضعیت تحویل
این پروژه اکنون به‌صورت یک **نسخه نهایی تحویلی و قابل توسعه** آماده شده و شامل این بخش‌هاست:
- اپ اندروید Native با Kotlin + Compose
- بک‌اند FastAPI
- موتور تحلیل ICT / SMC
- مدیریت ریسک حرفه‌ای
- سیگنال، ژورنال، بک‌تست، sweep، walk-forward
- چارت زنده و WebSocket
- foundation برای بروکرها و صرافی‌ها
- اسناد راه‌اندازی، انتشار، ریسک و حریم خصوصی

---

## اجزای اصلی تحویل
### 1) اپ اندروید
مسیر:
- `android/`

ویژگی‌ها:
- Splash با تصویر برند APEX AI
- Login / Register
- Dashboard
- Signals
- Chart
- Risk
- Broker
- Profile
- Settings
- Journal
- Backtest Lab
- Analytics Center

### 2) بک‌اند
مسیر:
- `backend/`

ویژگی‌ها:
- REST API
- WebSocket
- تحلیل بازار
- مدیریت ریسک
- ذخیره‌سازی SQLite
- notification foundation
- execution preview
- execution routes

### 3) مستندات
مسیر:
- `docs/`

شامل:
- معماری
- طراحی API
- راهنمای استقرار
- چک‌لیست release
- Firebase setup
- connector setup
- privacy policy
- terms and risk

### 4) نقشه فایل‌ها
- `FILE_MAP.txt`

---

## فایل‌های کلیدی برای شروع سریع
### اندروید
- `android/app/src/main/java/com/arena/smartmoney/MainActivity.kt`
- `android/app/src/main/java/com/arena/smartmoney/SplashActivity.kt`
- `android/app/src/main/java/com/arena/smartmoney/ui/TradingAiApp.kt`
- `android/app/build.gradle.kts`

### بک‌اند
- `backend/app/main.py`
- `backend/app/models.py`
- `backend/app/services/`
- `backend/requirements.txt`

### تنظیمات
- `backend/.env.example`
- `backend/.env.production.example`
- `android/keystore.properties.example`

---

## اجرای سریع
### بک‌اند
```bash
cd project/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### اندروید
- پوشه `project/android` را در Android Studio باز کن.
- برای emulator، آدرس پیش‌فرض روی `10.0.2.2` تنظیم شده.

---

## موارد لازم قبل از استفاده واقعی
1. تنظیم `.env` واقعی
2. اضافه کردن `google-services.json`
3. تنظیم Firebase project
4. آماده‌سازی keystore release
5. استفاده از testnet / demo پیش از live
6. بررسی کامل risk rules
7. تنظیم HTTPS و دامنه production

---

## نکات مهم تحویل
- این پروژه **سود قطعی را تضمین نمی‌کند**.
- بخش‌هایی مانند MT5 و cTrader هنوز در سطح foundation هستند و برای اجرای واقعی باید bridge / integration تکمیل شود.
- بخش FCM در سطح آماده‌سازی نهایی است و برای ارسال واقعی نیازمند credential و فایل‌های نهایی Firebase است.

---

## پیشنهاد بعد از تحویل
اگر بخواهی بعداً توسعه ادامه پیدا کند، بهترین اولویت‌ها این‌ها هستند:
1. Firebase واقعی
2. MT5 bridge واقعی
3. cTrader routing واقعی
4. بهینه‌سازی حرفه‌ای‌تر استراتژی
5. انتشار نسخه production

---

## نتیجه
پروژه در این مرحله یک **نسخه نهایی تحویلی MVP/Product-Ready Foundation** محسوب می‌شود که هم برای دمو، هم برای توسعه تیمی، و هم برای تبدیل به محصول production-ready بسیار مناسب است.
