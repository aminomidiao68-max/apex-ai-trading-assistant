# چک‌لیست فاز نهایی انتشار APEX AI

## اندروید
- [ ] بررسی `API_BASE_URL` و `WS_BASE_URL` برای release
- [ ] افزودن `google-services.json`
- [ ] فعال‌سازی Google Services plugin در Gradle در صورت استفاده از FCM واقعی
- [ ] تست Login / Register / Logout
- [ ] تست Dashboard / Signals / Chart / Journal / Backtest / Analytics
- [ ] تست نوتیفیکیشن محلی
- [ ] تست دریافت FCM token
- [ ] تست آیکون، splash و تجربه کاربری اولیه
- [ ] ساخت release keystore
- [ ] تنظیم `versionCode` و `versionName`
- [ ] تولید APK/AAB release

## بک‌اند
- [ ] ساخت فایل `.env` تولیدی از روی `backend/.env.production.example`
- [ ] خاموش نگه‌داشتن `ENABLE_LIVE_EXECUTION` تا پایان تست
- [ ] تنظیم credentialهای Binance / Bybit / OANDA در صورت نیاز
- [ ] تعیین strategy برای MT5 bridge یا cTrader Open API
- [ ] فعال‌سازی HTTPS در production
- [ ] بررسی CORS برای دامنه نهایی
- [ ] بررسی لاگ‌ها و مانیتورینگ
- [ ] تست endpointهای health / analytics / backtest / execution preview

## امنیت و ریسک
- [ ] عدم نگه‌داری secretها داخل سورس
- [ ] استفاده از testnet / practice قبل از live
- [ ] تست حداقل score و risk approval قبل از order routing
- [ ] بررسی daily loss limits و max positions
- [ ] ثبت disclaimer و risk warning داخل محصول

## آماده‌سازی مارکت/انتشار
- [ ] اسکرین‌شات اپ
- [ ] privacy policy
- [ ] terms / risk disclosure
- [ ] متن معرفی فارسی و انگلیسی
- [ ] تست روی چند دستگاه و نسخه اندروید
