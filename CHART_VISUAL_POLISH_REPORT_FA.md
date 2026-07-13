# گزارش پولیش بصری چارت APEX AI v2.2.3

## ایرادهای مشاهده‌شده در تصاویر

- تکرار چند BSL یا SSL نزدیک هم؛
- بریده‌شدن ابتدای Legend در رابط RTL؛
- هم‌پوشانی Labelهای BOS/CHoCH؛
- هم‌پوشانی IDMهای نزدیک؛
- نام طولانی Order Block داخل باکس کوچک؛
- باقی‌ماندن Scroll قبلی هنگام تغییر Symbol/Timeframe.

## اصلاحات

- انتخاب فقط آخرین BSL، SSL، EQH و EQL؛
- Legend با LayoutDirection چپ‌به‌راست، Padding امن و Scroll افقی؛
- برچسب کوتاه `Bull OB` و `Bear OB`؛
- Reset خودکار Scroll هنگام تغییر نماد، تایم‌فریم یا Refresh؛
- Collision Detection دوبعدی برای BOS/CHoCH؛
- Collision Detection برای IDM و سقف سه نشانگر؛
- اعتبارسنجی Lifecycle هر Zone قبل از رسم؛
- اضافه‌شدن `ChartRenderPolicy` مستقل و Unit Test اندروید.

## تست

- Backend Regression: 9 passed
- Android Unit Tests: در CI اجرا می‌شوند
- Build/Lint/Test Gate: اجباری
