# گزارش اصلاح سراسری نمودار — APEX AI v2.1.7

**تاریخ:** ۱۲ ژوئیهٔ ۲۰۲۶  
**دامنه:** تمام ۱۰ نماد رابط نمودار و تمام ۷ تایم‌فریم

## مشکلات مشاهده‌شده در تصاویر

- فشرده‌شدن کندل‌ها یا نمایش بدنه‌های بسیار بلند؛
- قرارگرفتن Event/IDM/OB/FVG در کندل اشتباه؛
- تکرار ده‌ها Killzone و هم‌پوشانی عنوان‌ها؛
- تراکم زیاد خطوط BSL/SSL، IDM، BOS و CHoCH؛
- نمایش Killzone روی تایم‌فریم‌های 4h و 1d؛
- بریده‌شدن محور قیمت و نام اولین Symbol؛
- نمایش چارت تایم‌فریم قبلی هنگام بارگذاری تایم‌فریم جدید؛
- خطاهای 429 برای Forex هنگام تغییر سریع تایم‌فریم؛
- خطای 400 برای `1d`؛
- نمایش URL کامل Provider و API Key در متن خطا.

## علت‌های اصلی

1. Backend آخرین ۱۲۰ کندل را برمی‌گرداند، ولی Index تمام Overlayها همچنان متعلق به ۲۶۰ کندل بود.
2. محدوده قیمت از کل تاریخ تحلیل محاسبه می‌شد، نه کندل‌های واقعاً قابل‌مشاهده.
3. تمام Sessionهای تاریخی بدون محدودیت رسم می‌شدند.
4. هر تغییر تایم‌فریم Forex یک درخواست جدید برای داده اصلی و یک درخواست جداگانه برای HTF ایجاد می‌کرد.
5. `1d` مستقیماً به TwelveData ارسال می‌شد، در حالی که مقدار صحیح `1day` است.
6. درخواست‌های قبلی Android هنگام تغییر سریع Symbol/Timeframe لغو نمی‌شدند.

## اصلاحات Backend

- Rebase کامل Indexهای Event، OB، FVG، Breaker، Inducement، Label و Killzone پس از Trim؛
- بازه نمودار ۱۶۰ کندلی با Indexهای معتبر ۰ تا ۱۵۹؛
- محاسبه `visible_range` دقیقاً از همان کندل‌های خروجی؛
- محدودسازی تعداد Overlayها؛
- حذف Killzone در 4h و 1d؛
- نگه‌داشتن فقط Sessionهای دو یا سه روز اخیر در تایم‌فریم‌های Intraday؛
- ساخت HTF از داده فعلی با Resampling و حذف درخواست دوم Provider؛
- Cache وابسته به تایم‌فریم، Lock برای درخواست تکراری و Stale-cache تا ۲۴ ساعت؛
- Yahoo Finance به‌عنوان Provider اصلی Chart برای Forex، Gold و Index؛
- TwelveData به‌عنوان Fallback همراه Circuit Breaker نودثانیه‌ای برای 429؛
- اصلاح نگاشت `1d → 1day`؛
- پشتیبانی از XAUUSD، EURUSD، GBPUSD، USDJPY، AUDUSD، US30 و NAS100؛
- خطاهای Provider کاملاً Sanitized و بدون URL/API Key.

## اصلاحات Android

- لغو خودکار درخواست قبلی با `LaunchedEffect`؛
- پاک‌کردن Report قدیمی هنگام تغییر Symbol/Timeframe؛
- Scale پیش‌فرض متناسب با تایم‌فریم؛
- محاسبه محور قیمت فقط از کندل‌های Visible؛
- محور قیمت عریض‌تر با Precision پویا؛
- مخفی‌کردن Volume Pane در Forex بدون Volume؛
- محدودسازی و فاصله‌گذاری Labelهای Liquidity؛
- حذف Clamp اشتباه Eventهای خارج از محدوده؛
- کاهش Opacity و تعداد Killzoneها؛
- نمایش عنوان Killzone فقط در صورت وجود فضای کافی؛
- Clip کردن Zoneها داخل محدوده چارت؛
- نمایش Label زون فقط در صورت فضای کافی؛
- Symbol/Timeframe selector با جهت LTR و Auto-scroll؛
- فیلتر دفاعی متن خطا برای جلوگیری از نمایش Secret.

## آزمون‌ها

### ماتریس Provider

- ۱۰ نماد × ۷ تایم‌فریم = **۷۰ حالت**
- نتیجه: **70/70 موفق**
- کنترل‌ها: حداقل ۳۰ کندل، ترتیب Timestamp، اعتبار OHLC و نبود خطای Provider

### ماتریس SMC/Overlay

- ۱۰ نماد × ۷ تایم‌فریم = **۷۰ حالت**
- نتیجه: **70/70 موفق**
- کنترل‌ها:
  - Status برابر `ok`؛
  - ۳۰ تا ۱۶۰ کندل؛
  - تمام Indexها داخل محدوده؛
  - Visible Range شامل تمام Wickها؛
  - نبود Killzone در 4h/1d؛
  - نبود API Key در Response.

### Regression Test

- **8 passed**
- شامل Rebase Index، Timeframe Mapping، Aggregation، Killzone Policy و Secret Redaction.

## نسخه

- Backend/API: `2.1.7`
- Android: `versionCode 54`, `versionName 2.1.7`
- Live Execution: بدون تغییر و همچنان خاموش
