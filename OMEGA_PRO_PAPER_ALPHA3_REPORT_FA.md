# گزارش APEX Omega Pro — Paper Alpha 3

## هدف

افزودن خوراک خودکار و قابل‌بازیابی بازار به Paper OMS بدون فعال‌کردن هیچ مسیر اجرای زنده.

## قابلیت‌های این فاز

- اشتراک کاربرمحور برای نمادهای Crypto/USDT
- دریافت Best Bid/Ask عمومی و واقعی از OKX
- ثبت صریح منبع `okx_public_real_best_bid_ask`
- استفاده محافظه‌کارانه از کمینه Bid/Ask size برای نقدشوندگی قابل‌پرشدن
- کنترل Quote کهنه، Quote آینده، قیمت Crossed و نقدشوندگی صفر
- شناسه رویداد قطعی و جلوگیری از Fill تکراری هنگام Retry
- تشخیص تعارض یک Event ID با Payload متفاوت
- دفتر پایدار `paper_market_ticks`
- Worker خودکار Opt-in با Lease دیتابیس برای کاهش پردازش هم‌زمان تکراری
- Backoff نمایی و خطاهای Sanitized بدون URL یا Secret
- کنترل مستقل `automated_feed_enabled`
- Kill Switch باعث خاموش‌شدن Feed خودکار می‌شود
- API وضعیت، اشتراک، لغو اشتراک و Sync دستی
- Android Feed dashboard و کنترل Subscribe/Auto/Sync

## قرارداد صداقت داده

- در این فاز Feed خودکار فقط Crypto را پشتیبانی می‌کند.
- Quoteهای OKX واقعی هستند، اما Fill همچنان شبیه‌سازی محافظه‌کارانه Paper است.
- Forex به‌علت نبود Bid/Ask عمومی هم‌سطح، در این فاز با Quote مصنوعی به‌عنوان داده واقعی ارائه نمی‌شود.
- `is_real_market_quote=true` فقط درباره Quote عمومی OKX است، نه درباره Fill یا اجرای بروکر.
- تمام خروجی‌ها `live_routed=false` هستند.

## Schema v7

### `paper_feed_subscriptions`

- وضعیت اشتراک کاربر و نماد
- Poll interval و زمان Poll بعدی
- آخرین Quote موفق و Event ID
- شمار خطا، Error code و Backoff
- Lease owner/expiry برای Worker

### `paper_market_ticks`

- Event ID یکتا در محدوده کاربر
- Payload hash
- Bid/Ask، نقدشوندگی و Provider timestamp
- شناسه سفارش‌های تحت‌تأثیر
- زمان دریافت و پردازش

## API

```text
GET    /api/v1/paper/feed/status
GET    /api/v1/paper/feed/subscriptions
POST   /api/v1/paper/feed/subscriptions
DELETE /api/v1/paper/feed/subscriptions/{symbol}
POST   /api/v1/paper/feed/sync
```

## اصول ایمنی

- Feed و Paper Trading به‌صورت پیش‌فرض خاموش‌اند.
- فعال‌سازی Feed فقط در Paper Mode مسلح و Kill Switch آزاد ممکن است.
- Tick تکراری Fill دوم ایجاد نمی‌کند.
- Tick کهنه یا آینده رد می‌شود.
- Provider failure هیچ سفارش زنده‌ای ایجاد نمی‌کند.
- `ENABLE_LIVE_EXECUTION=false` تغییر نکرده است.

## محدودیت‌های باقی‌مانده

- این فاز Order Book کامل یا Queue position را مدل نمی‌کند.
- WebSocket مستقیم Provider هنوز جای Polling عمومی را نگرفته است.
- Funding، Margin، Liquidation و Mark/Index price مجزا هنوز پیاده‌سازی نشده‌اند.
- Testnet exchange reconciliation در فاز مستقل انجام می‌شود.
- این قابلیت هیچ سود، دقت، Win Rate یا عملکرد آینده‌ای را تضمین نمی‌کند.
