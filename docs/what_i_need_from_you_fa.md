# چیزهایی که برای واقعی‌سازی کامل APEX AI از شما لازم است

برای اینکه بتوانم در مراحل بعدی پروژه را از foundation به حالت نزدیک‌تر به production واقعی هدایت کنم، این اطلاعات/فایل‌ها از سمت شما لازم خواهند بود.

---

## 1) برای Firebase واقعی
- [ ] فایل `google-services.json`
- [ ] `FIREBASE_PROJECT_ID`
- [ ] مسیر فایل `service-account.json`

---

## 2) برای Crypto execution
### Binance Futures
- [ ] `BINANCE_API_KEY`
- [ ] `BINANCE_API_SECRET`
- [ ] ترجیحاً testnet access

### Bybit
- [ ] `BYBIT_API_KEY`
- [ ] `BYBIT_API_SECRET`
- [ ] ترجیحاً testnet access

---

## 3) برای Forex execution
### OANDA
- [ ] `OANDA_API_TOKEN`
- [ ] `OANDA_ACCOUNT_ID`
- [ ] practice account

### MT5
- [ ] broker/server name
- [ ] login
- [ ] password
- [ ] تصمیم درباره نوع bridge (MetaAPI / local bridge / custom)

### cTrader
- [ ] `CTRADER_CLIENT_ID`
- [ ] `CTRADER_CLIENT_SECRET`
- [ ] `CTRADER_ACCESS_TOKEN`
- [ ] مشخصات account mapping

---

## 4) برای انتشار اندروید
- [ ] release keystore
- [ ] keystore passwords
- [ ] نام نهایی package/release config در صورت نیاز
- [ ] Google Play Developer account (اگر انتشار می‌خواهید)

---

## 5) برای production backend
- [ ] دامنه واقعی API
- [ ] دامنه WebSocket
- [ ] سرور/VPS یا cloud host
- [ ] strategy برای HTTPS/SSL

---

## 6) برای فاز private alpha
- [ ] تعداد کاربر هدف alpha
- [ ] نمادهای اولویت‌دار
- [ ] بازار اولویت‌دار (crypto / forex / هر دو)
- [ ] آیا execution فقط demo باشد یا live محدود؟

---

## جمع‌بندی
هر زمان این موارد را آماده کردی، من می‌توانم مرحله بعدی را خیلی دقیق‌تر و نزدیک‌تر به اجرا/production هدایت کنم.
