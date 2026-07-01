# راهنمای آماده‌سازی کانکتورها

## 1) Binance Futures
در فایل `.env`:
```env
BINANCE_API_KEY=...
BINANCE_API_SECRET=...
BINANCE_FUTURES_BASE_URL=https://testnet.binancefuture.com
ENABLE_LIVE_EXECUTION=false
```

پیشنهاد:
- اول فقط testnet
- بعد بررسی از داخل Broker Screen
- بعد preview route
- بعد execute dry-run / live

---

## 2) Bybit
در فایل `.env`:
```env
BYBIT_API_KEY=...
BYBIT_API_SECRET=...
BYBIT_BASE_URL=https://api-testnet.bybit.com
ENABLE_LIVE_EXECUTION=false
```

وضعیت فعلی:
- route backend اضافه شده
- order create foundation فعال است
- نیازمند credential واقعی برای تست زنده

---

## 3) OANDA
در فایل `.env`:
```env
OANDA_API_TOKEN=...
OANDA_ACCOUNT_ID=...
OANDA_BASE_URL=https://api-fxpractice.oanda.com
ENABLE_LIVE_EXECUTION=false
```

پیشنهاد:
- ابتدا practice account
- بررسی symbol mapping مثل `EUR_USD`

---

## 4) MT5
در فایل `.env`:
```env
MT5_SERVER=...
MT5_LOGIN=...
MT5_PASSWORD=...
ENABLE_LIVE_EXECUTION=false
```

وضعیت فعلی:
- foundation-only
- برای اجرای واقعی نیاز است:
  - MetaAPI
  - یا local MT5 bridge
  - یا سرویس واسط اختصاصی

---

## 5) cTrader
در فایل `.env`:
```env
CTRADER_CLIENT_ID=...
CTRADER_CLIENT_SECRET=...
CTRADER_ACCESS_TOKEN=...
CTRADER_BASE_URL=https://demo.ctraderapi.com
ENABLE_LIVE_EXECUTION=false
```

وضعیت فعلی:
- foundation-only
- برای اجرای واقعی نیاز است:
  - Open API session
  - account mapping
  - routing logic

---

## نکته مهم
تا وقتی:
```env
ENABLE_LIVE_EXECUTION=false
```
باشد، سیستم وارد حالت محافظه‌کارانه می‌ماند و از اجرای واقعی جلوگیری می‌کند.
