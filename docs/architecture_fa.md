# معماری پروژه

## 1) لایه موبایل
- Kotlin
- Jetpack Compose
- MVVM / stateful Compose
- Retrofit
- OkHttp WebSocket
- Coroutines / StateFlow
- SessionManager برای نگه‌داری سشن کاربر
- Local notifications برای هشدار سیگنال
- Firebase Messaging foundation برای push آینده

### صفحات فعلی
- Splash Screen تصویری
- Login / Register
- Dashboard زنده + stream summary
- Signals + history
- Candlestick Chart + live stream + zoom/pan + gesture پایه + crosshair
- Trade Journal
- Backtest Lab
- Analytics Center
- Risk Calculator
- Broker / Exchange Status + Execution Preview Lab
- Profile / Logout
- Settings / Final UX Controls

## 2) لایه بک‌اند
- FastAPI
- Pydantic
- موتور تحلیل چندلایه
- موتور مدیریت ریسک
- موتور تشخیص سشن‌های جهانی
- ماژول market data زنده
- connector اجرای معامله و foundation برای چند بروکر
- auth service با SQLite محلی
- storage service برای signal history و trade journal
- notification service برای ثبت device token و logging event
- backtest service برای شبیه‌سازی تاریخی، parameter sweep و walk-forward
- WebSocket برای استریم snapshot بازار

## 3) موتور سیگنال
### ورودی‌ها
- OHLCV
- داده order flow
- اخبار مهم
- تنظیمات ریسک
- زمان فعلی بازار

### خروجی‌ها
- جهت معامله
- امتیاز نهایی
- confidence
- محدوده ورود
- SL / TP
- دلایل تصمیم
- برنامه ریسک
- امکان ذخیره در دیتابیس

## 4) ذخیره‌سازی
### Signal History
- ذخیره سیگنال‌های live scan
- نگه‌داری جهت، امتیاز، سشن، ورود/حدضرر/اهداف، دلایل و زمان ثبت

### Trade Journal
- ثبت معامله باز
- بستن معامله
- ذخیره pnl و یادداشت
- آمار عملکرد: win rate / net pnl / تعداد معاملات باز و بسته

### Device Tokens
- ثبت token دستگاه برای فاز push واقعی
- نگه‌داری eventهای notification test

## 5) بک‌تست داخلی
- اجرای تحلیل روی windowهای متحرک داده تاریخی
- فیلتر بر اساس score_threshold
- انتخاب TP target با index
- ارزیابی win/loss/unclosed روی lookahead candles
- محاسبه net RR، expectancy، profit factor و streakها
- Parameter sweep برای window/lookahead/threshold/TP target
- Walk-forward analysis برای ارزیابی out-of-sample مرحله‌ای
- آماده برای توسعه به optimization گسترده‌تر

## 6) آنالیتیکس
- خلاصه تعداد سیگنال‌های ذخیره‌شده
- میانگین score سیگنال‌ها
- فعالیت 24 ساعت اخیر
- top symbols بر اساس تعداد سیگنال
- breakdown بر اساس symbol برای signals و trades
- اتصال به آمار ژورنال معاملات و notification activity

## 7) احراز هویت
- Register / Login / Me / Logout
- هش رمز عبور با PBKDF2
- سشن توکنی سمت سرور
- ذخیره توکن سمت موبایل
- اکانت دمو اولیه برای تست

## 8) اتصال داده زنده
### کریپتو
- Binance public REST
- ticker / klines
- websocket-ready backend stream

### فارکس / طلا
- TwelveData (نیازمند API Key)
- quote / time_series

## 9) اتصال بروکر / صرافی
### فعال/نیمه‌فعال
- Binance Futures connector
- Bybit connector
- OANDA connector

### foundation اضافه‌شده
- MT5
- cTrader

### ابزار کمکی
- execution capability discovery
- execution preview / normalized payload preview

## 10) Push Notification
### نسخه فعلی
- Local notification در کلاینت
- FCM service class در اندروید
- ثبت token در backend
- تست notification به‌صورت dry-run event

### برای تکمیل نهایی
- `google-services.json`
- Firebase project setup
- server credential برای ارسال remote push

## 11) پیشنهاد توسعه بعدی
- FCM remote delivery واقعی
- اجرای واقعی کانکتورهای Bybit / MT5 / cTrader
- optimization گسترده‌تر و auto parameter search
- candlestick chart حرفه‌ای‌تر با gesture/zoom کامل‌تر
- گزارش‌های پیشرفته‌تر ژورنال و analytics
