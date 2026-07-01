# Playbook کامل قدم‌های بعدی APEX AI

این سند برای انجام **همه قدم‌های بعدی** ساخته شده است؛ یعنی:
1. اجرای واقعی روی سیستم
2. تکمیل Firebase
3. تکمیل connectorها
4. انتشار در GitHub
5. آماده‌سازی Play Store
6. حرکت به سمت production

---

# بخش 1) اجرای واقعی روی سیستم شما

## 1.1 اجرای بک‌اند
```bash
cd project/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### تست سریع
- Health: `http://127.0.0.1:8000/health`
- Swagger: `http://127.0.0.1:8000/docs`

## 1.2 اجرای اندروید
- Android Studio را باز کن
- مسیر `project/android` را انتخاب کن
- Gradle sync را کامل کن
- Emulator یا گوشی واقعی را وصل کن
- اپ را run کن

### نکته مهم
در حالت debug:
- API: `http://10.0.2.2:8000/`
- WS: `ws://10.0.2.2:8000/ws/market`

پس باید بک‌اند هم‌زمان روی سیستم شما در حال اجرا باشد.

---

# بخش 2) تکمیل Firebase واقعی

## 2.1 کارهایی که باید انجام دهید
1. در Firebase Console یک پروژه بسازید
2. package name زیر را ثبت کنید:
   - `com.arena.smartmoney`
3. فایل `google-services.json` را دانلود کنید
4. آن را در این مسیر قرار دهید:
   - `project/android/app/google-services.json`

## 2.2 تکمیل backend برای push واقعی
در `.env` یا production env این مقادیر را تنظیم کنید:
```env
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_SERVICE_ACCOUNT_JSON=/absolute/path/to/service-account.json
```

## 2.3 تست
- در اپ وارد شوید
- در Profile روی `Register Device for Push` بزنید
- سپس روی `Send Test Push Event` بزنید
- اگر همه‌چیز درست باشد backend از حالت dry-run به حالت Firebase-live نزدیک می‌شود

---

# بخش 3) تکمیل connectorهای واقعی

## 3.1 اولویت اجرای واقعی
### اولویت اول
- Binance Futures testnet
- OANDA practice

### اولویت دوم
- Bybit testnet

### اولویت سوم
- MT5 bridge واقعی
- cTrader Open API session واقعی

## 3.2 Binance Futures
در env:
```env
BINANCE_API_KEY=...
BINANCE_API_SECRET=...
BINANCE_FUTURES_BASE_URL=https://testnet.binancefuture.com
ENABLE_LIVE_EXECUTION=false
```

## 3.3 Bybit
```env
BYBIT_API_KEY=...
BYBIT_API_SECRET=...
BYBIT_BASE_URL=https://api-testnet.bybit.com
ENABLE_LIVE_EXECUTION=false
```

## 3.4 OANDA
```env
OANDA_API_TOKEN=...
OANDA_ACCOUNT_ID=...
OANDA_BASE_URL=https://api-fxpractice.oanda.com
ENABLE_LIVE_EXECUTION=false
```

## 3.5 MT5
برای MT5 foundation فعلی کافی نیست. باید یکی از این‌ها را انتخاب کنید:
- MetaAPI
- local bridge service
- bridge اختصاصی

## 3.6 cTrader
برای cTrader هم باید:
- client id
- client secret
- access token
- account mapping
- session management
تکمیل شود.

---

# بخش 4) انتشار در GitHub

## 4.1 فایل‌های آماده
- README اصلی: `project/README.md`
- README عمومی: `project/README_GITHUB_PUBLIC.md`
- README دو زبانه: `project/README_BILINGUAL.md`
- README landing: `project/README_LANDING.md`

## 4.2 قبل از Push
بررسی کنید این فایل‌ها داخل مخزن عمومی نباشند:
- `backend/.env`
- `android/app/google-services.json`
- keystore واقعی
- Firebase service account
- API key و secretها

## 4.3 راهنمای انتشار
- `project/docs/github_publish_steps_fa.md`
- `project/docs/github_repo_metadata_fa_en.md`

---

# بخش 5) آماده‌سازی Google Play

## 5.1 نیازمندی‌ها
- Google Play Developer account
- release keystore
- icon / screenshots / listing text

## 5.2 متن آماده
- `project/docs/play_store_listing_fa_en.md`

## 5.3 Release Signing
از این فایل نمونه استفاده کنید:
- `project/android/keystore.properties.example`

سپس فایل واقعی بسازید:
- `project/android/keystore.properties`

## 5.4 build release
```bash
cd project/android
./gradlew assembleRelease
```
یا
```bash
./gradlew bundleRelease
```

---

# بخش 6) آماده‌سازی Production واقعی

## 6.1 حداقل‌های فنی
- دامنه واقعی
- HTTPS
- production env
- لاگ‌گیری
- مانیتورینگ
- backup strategy

## 6.2 پیشنهاد زیرساخت
- VPS یا cloud instance
- reverse proxy مثل Nginx یا Caddy
- SSL/TLS
- بعدها PostgreSQL به‌جای SQLite

## 6.3 ترتیب فعال‌سازی
1. staging
2. testnet/demo connectors
3. Firebase واقعی
4. release build
5. private alpha
6. closed beta
7. production محدود

---

# بخش 7) بهترین ترتیب واقعی اجرا از الان

## هفته اول
- اجرای محلی کامل
- Firebase setup
- تست Device Token
- تست Binance testnet / OANDA practice

## هفته دوم
- release build اندروید
- بهبود UXهای خطا
- تست روی دستگاه واقعی

## هفته سوم و چهارم
- private alpha محدود
- جمع‌آوری feedback
- بازبینی journal / signal / chart / broker flows

---

# بخش 8) اگر بخواهید من دقیق‌تر ادامه بدهم
من در قدم بعدی می‌توانم یکی از این‌ها را برایتان آماده کنم:
1. checklist شخصی‌سازی‌شده برای credentialهایی که باید تهیه کنید
2. step-by-step setup برای Firebase روی همین پروژه
3. step-by-step setup برای Binance / Bybit / OANDA
4. plan نهایی private alpha launch

---

# جمع‌بندی نهایی
اگر بخواهیم خیلی عملیاتی بگوییم، بهترین ترتیب این است:
1. محلی اجرا شود
2. Firebase واقعی تکمیل شود
3. حداقل یک crypto route و یک forex route در demo/testnet تست شوند
4. release build تست شود
5. private alpha شروع شود

در این نقطه، پروژه از نظر ساختار و محصول آماده حرکت جدی است؛ باقی کارها بیشتر مربوط به **credentialها، integrationهای واقعی، و عملیات production** هستند.
