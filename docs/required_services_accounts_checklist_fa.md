# چک‌لیست سرویس‌ها، اکانت‌ها و credentialهای موردنیاز برای APEX AI

این سند مشخص می‌کند برای اینکه APEX AI در دنیای واقعی و حرفه‌ای کار کند، دقیقاً چه سرویس‌ها و اکانت‌هایی باید تهیه یا فعال شوند.

---

## 1) سرویس‌های اجباری پایه

### 1.1 Git / Repository Hosting
**پیشنهاد:**
- GitHub
- GitLab

**کاربرد:**
- نگه‌داری سورس
- version control
- issue tracking
- release management

---

### 1.2 Domain + HTTPS
**نیاز دارید به:**
- دامنه واقعی
- گواهی SSL/TLS

**پیشنهاد:**
- دامنه اختصاصی
- Cloudflare / Nginx / Caddy

**کاربرد:**
- production API
- production WebSocket
- امنیت ارتباطات

---

### 1.3 سرور یا هاست بک‌اند
**نیاز دارید به:**
- VPS یا cloud instance

**پیشنهاد:**
- Hetzner
- DigitalOcean
- AWS / GCP / Azure

**کاربرد:**
- اجرای FastAPI
- اجرای WebSocket
- نگه‌داری env و service credentials

---

## 2) سرویس‌های داده بازار

### 2.1 Crypto Market Data
#### حداقل یکی از این‌ها:
- Binance public API
- Bybit public API
- OKX public API

**در پروژه فعلی مهم‌تر:**
- Binance
- Bybit

**کاربرد:**
- ticker
- candles
- live monitoring

---

### 2.2 Forex / Gold Market Data
#### حداقل یکی از این‌ها:
- TwelveData
- OANDA market data
- Polygon / FX providerهای مشابه

**در پروژه فعلی:**
- TwelveData
- OANDA practice/live

**نیازمندی:**
- API key معتبر

---

## 3) سرویس‌های اجرای سفارش

### 3.1 Binance Futures
**نیاز دارید به:**
- Binance account
- API key
- API secret
- دسترسی testnet یا live

**کاربرد:**
- اجرای سفارش کریپتو futures

---

### 3.2 Bybit
**نیاز دارید به:**
- Bybit account
- API key
- API secret
- testnet/live access

**کاربرد:**
- route اجرای سفارش Bybit

---

### 3.3 OANDA
**نیاز دارید به:**
- OANDA account
- API token
- account id
- practice/live endpoint

**کاربرد:**
- اجرای سفارش forex در محیط practice/live

---

### 3.4 MT5
**نیاز دارید به:**
- MT5 broker account
- server name
- login
- password
- یک bridge واقعی مثل MetaAPI یا bridge اختصاصی

**نکته مهم:**
در پروژه فعلی، MT5 هنوز foundation-only است. برای اجرای واقعی بدون bridge کافی نیست.

---

### 3.5 cTrader
**نیاز دارید به:**
- cTrader/Open API app
- client id
- client secret
- access token
- account mapping
- session management

**نکته مهم:**
در پروژه فعلی foundation آماده است ولی route نهایی کامل نشده است.

---

## 4) سرویس‌های Push Notification

### 4.1 Firebase Project
**نیاز دارید به:**
- Firebase project
- Android app registration
- `google-services.json`

**کاربرد:**
- device registration
- push notification client side

---

### 4.2 Firebase Server Credential
**نیاز دارید به:**
- service account JSON
- project id

**کاربرد:**
- ارسال push واقعی از backend

**در envهای مهم:**
- `FIREBASE_PROJECT_ID`
- `FIREBASE_SERVICE_ACCOUNT_JSON`

---

## 5) Android Release Requirements

### 5.1 Keystore
**نیاز دارید به:**
- release keystore
- store password
- key alias
- key password

**کاربرد:**
- build نهایی APK / AAB
- انتشار در Play Store

---

### 5.2 Android Developer Account
**اگر می‌خواهی منتشر کنی:**
- Google Play Developer account

**کاربرد:**
- انتشار رسمی اپ در Google Play

---

## 6) سرویس‌های عملیات و مانیتورینگ

### 6.1 Logging / Monitoring
**پیشنهاد:**
- Sentry
- Grafana / Prometheus
- Logtail / ELK / Loki

**کاربرد:**
- crash monitoring
- API errors
- WebSocket stability
- execution failures

---

### 6.2 Backup / Database Hosting
اگر به production واقعی نزدیک شوی:
- PostgreSQL managed یا self-hosted
- backup policy
- restore testing

---

## 7) سرویس‌های حقوقی / اعتماد / برند

### 7.1 Privacy / Terms Hosting
**نیاز دارید به:**
- محل انتشار privacy policy
- محل انتشار terms & risk disclosure

**مثال:**
- وب‌سایت رسمی
- GitHub Pages
- docs site

---

### 7.2 Website / Landing Page
**پیشنهاد:**
- دامنه اصلی
- landing page
- contact form

**کاربرد:**
- برندینگ
- معرفی محصول
- جمع‌آوری کاربر alpha/beta

---

## 8) اکانت‌ها و اطلاعاتی که باید واقعاً داشته باشی

### حداقل برای نسخه دمو واقعی و قوی
- [ ] GitHub account
- [ ] VPS / hosting account
- [ ] Domain
- [ ] Firebase project
- [ ] `google-services.json`
- [ ] Firebase service account JSON
- [ ] TwelveData API key
- [ ] Binance testnet credentials
- [ ] OANDA practice credentials
- [ ] Android keystore

### برای توسعه execution حرفه‌ای‌تر
- [ ] Bybit testnet credentials
- [ ] MT5 bridge provider یا MetaAPI
- [ ] cTrader Open API app credentials

### برای انتشار تجاری
- [ ] Google Play Developer account
- [ ] privacy/terms public URL
- [ ] monitoring service
- [ ] production database plan

---

## 9) پیشنهاد اولویت تهیه سرویس‌ها

### اولویت 1
- Firebase project
- `google-services.json`
- Firebase service account
- TwelveData key
- Binance testnet
- OANDA practice

### اولویت 2
- دامنه و VPS
- Android keystore
- monitoring

### اولویت 3
- Bybit testnet
- MT5 bridge
- cTrader Open API
- Google Play Developer account

---

## 10) جمع‌بندی نهایی
اگر بخواهی این پروژه از حالت foundation به یک محصول واقعی نزدیک شود، **فقط کدنویسی کافی نیست**. باید یک لایه از:
- سرویس‌ها
- اکانت‌ها
- credentialها
- زیرساخت انتشار
- زیرساخت حقوقی و عملیاتی

هم روی آن سوار شود.

به زبان ساده:
- پروژه آماده است
- اما برای عملیاتی شدن واقعی، باید این اکوسیستم اطرافش را کامل کنی.
