# راهنمای استقرار و آماده‌سازی production

## 1) بک‌اند
### اجرای ساده
```bash
cd project/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### اجرای داکر
```bash
cd project
docker compose up --build
```

## 2) فایل env تولیدی
از این فایل استفاده کن:
- `project/backend/.env.production.example`

سپس یک فایل `.env` واقعی بساز و secretها را داخل آن قرار بده.

## 3) HTTPS
برای production بهتر است:
- دامنه واقعی داشته باشی
- reverse proxy مثل Nginx/Caddy داشته باشی
- SSL/TLS فعال کنی

## 4) اندروید release
در release build الآن placeholder تعریف شده:
- `API_BASE_URL = https://api.example.com/`
- `WS_BASE_URL = wss://api.example.com/ws/market`

قبل از build نهایی مطمئن شو این URLها با دامنه واقعی تو هماهنگ باشند.

## 5) Firebase Push
برای push واقعی این مراحل لازم است:
- `google-services.json` را داخل `project/android/app/` قرار بده
- Firebase project را کامل تنظیم کن
- در صورت نیاز credential سمت بک‌اند برای ارسال remote push اضافه کن

## 6) اجرای زنده سفارش
تا وقتی این مقدار خاموش است:
```env
ENABLE_LIVE_EXECUTION=false
```
اپ و بک‌اند در حالت محافظه‌کارانه می‌مانند.

برای live واقعی:
- اول demo/testnet را کامل تست کن
- بعد credential واقعی را اضافه کن
- بعد `ENABLE_LIVE_EXECUTION=true`
را فقط با احتیاط فعال کن
