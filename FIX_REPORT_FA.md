# گزارش اصلاح خطاهای غیرمرتبط با بروکر — APEX AI v2.1.6

**تاریخ:** ۱۲ ژوئیهٔ ۲۰۲۶  
**دامنه:** Backend، API، SMC/Signal، Risk، Auth، Journal، Analytics، Notification، Android و CI  
**خارج از دامنه:** فعال‌سازی Credential یا Live Route بروکرها

## وضعیت نهایی

خطاهای شناسایی‌شدهٔ غیرمرتبط با فعال‌سازی بروکرها در سورس اصلاح شدند. `ENABLE_LIVE_EXECUTION` همچنان `false` است و Credential هیچ بروکری اضافه نشده است.

## اصلاحات اصلی

- رفع `KeyError: 'score'` در Adapter بین SMC Engine و SignalEngine؛
- رفع خطاهای HTTP 500 در Analyze، Live Scan، Backtest Run، Sweep و Walk-forward؛
- بازگرداندن Adapter سبک SMC برای جلوگیری از کندی شدید Backtest؛
- اعتبارسنجی جهت معامله و محل Stop-Loss؛
- رد کردن Trade Plan با Direction خنثی؛
- صفرکردن Position Size برای معامله ردشده؛
- پاک‌کردن Levelهای معاملاتی در سیگنال Neutral؛
- محاسبه هم‌راستایی HTF بر اساس جهت واقعی Trade، نه صرفاً Bias محلی؛
- جلوگیری از Clip شدن Wickها در `visible_range`؛
- افزودن `omega_compliant`، `omega_reasons` و `action_label` به Scanner؛
- جداسازی `signals` قابل اقدام از `watching`؛
- رفع تنظیم چندباره و خالی Finnhub؛
- یکسان‌سازی News Health و Configuration؛
- محدودکردن CORS به Allowlist؛
- افزودن HTTP Bearer استاندارد به OpenAPI؛
- اجباری‌شدن Auth برای Journal، Analytics، Saved Signals، Backtest و Order Routeها؛
- جداسازی Signal/Trade/Analytics/Notification بر اساس `user_id`؛
- افزودن متد مفقود `delete_trade`؛
- جلوگیری از Close/Delete معامله متعلق به کاربر دیگر؛
- رفع متد Notification که به‌اشتباه بیرون Class قرار گرفته بود؛
- محدودکردن Push سیگنال به Deviceهای همان کاربر؛
- افزودن انقضای Session با مقدار پیش‌فرض ۱۶۸ ساعت؛
- غیرفعال‌کردن Seed حساب Demo در Production؛
- تبدیل خطای Provider بازار به پاسخ کنترل‌شده 502؛
- افزودن Bounds برای Limit و پارامترهای Market/Candle؛
- اصلاح Readiness: نبود Credential بروکر هنگام خاموش‌بودن Live Execution فقط Warning است؛
- حذف فایل‌های خروجی Render و فایل حاوی کلید Provider از Tree فعلی؛
- ارسال خودکار Bearer Token توسط OkHttp اندروید؛
- جلوگیری از Log شدن Authorization و Password/Body در Android Release؛
- حذف `Connection: close` برای استفاده مجدد از Connection؛
- رفع بررسی Permission نوتیفیکیشن در Android 13+؛
- ارتقای `compileSdk/targetSdk` به 35؛
- ارتقای AGP به 8.7.3 و افزودن Gradle Wrapper 8.9؛
- ارتقای نسخه محصول به 2.1.6؛
- افزودن Backend CI و Regression Test؛
- افزودن Lint و Unit Test به Android CI.

## نتایج تست

- تمام Smoke Testهای Backend: موفق؛
- Regression Testها: **5 passed**؛
- Python Compileall: موفق؛
- Analyze API با Payload معتبر: 200؛
- Live Scan با Market Mock: 200؛
- Backtest Run: 200؛
- Backtest Sweep: 200؛
- Walk-forward: 200؛
- تست جداسازی دو کاربر: موفق؛
- تست جلوگیری از Cross-user Close: موفق؛
- تست Delete Trade: موفق؛
- تست HTF مخالف جهت: موفق و بدون امتیاز Alignment؛
- تست Notification User Scope: موفق؛
- Android `assembleDebug`: **BUILD SUCCESSFUL**؛
- Android `testDebugUnitTest`: موفق (`NO-SOURCE`؛ هنوز Unit Test اندروید وجود ندارد)؛
- Android `lintDebug`: **0 errors, 20 warnings**؛
- APK Debug ساخته‌شده در محیط تست حدود 26 MB بود.

## تغییرات رفتاری مهم

1. مسیرهای خصوصی اکنون Bearer Token می‌خواهند. نسخه اندروید اصلاح‌شده Token را خودکار ارسال می‌کند.
2. حساب Demo در Production به‌صورت پیش‌فرض Seed نمی‌شود. برای محیط توسعه می‌توان `SEED_DEMO_USER=true` تنظیم کرد.
3. رکوردهای قدیمی SQLite که `user_id` ندارند به کاربران جدید نمایش داده نمی‌شوند؛ این رفتار برای جلوگیری از نشت داده عمدی است.
4. Scanner فقط سیگنال‌های Omega-compliant را در `signals` و موارد ضعیف‌تر را در `watching` قرار می‌دهد.
5. Broker Live Execution همچنان غیرفعال است.

## متغیرهای جدید یا اصلاح‌شده

```env
APP_VERSION=2.1.6
CORS_ALLOWED_ORIGINS=
DATABASE_PATH=
SESSION_TTL_HOURS=168
SEED_DEMO_USER=false
FINNHUB_API_KEY=
ENABLE_LIVE_EXECUTION=false
```

## هشدار امنیتی الزامی

یک کلید TwelveData در فایل قدیمی `render_env_result.json` داخل Repository ثبت شده بود. فایل از نسخه فعلی حذف شده، اما مقدار آن در Git History باقی می‌ماند.

اقدامات لازم مالک پروژه:

1. کلید را در پنل TwelveData فوراً Rotate/Revoke کند؛
2. مقدار جدید را فقط در Render Environment Variable قرار دهد؛
3. در صورت نیاز، History مخزن با ابزارهایی مانند `git filter-repo` پاک‌سازی و Force Push شود؛
4. Firebase Android API Key نیز در Google Cloud به Package Name و SHA Certificate محدود شود.

## موارد باقی‌مانده که خطای کد این مرحله نیستند

- Push و Deploy تغییرات روی GitHub/Render؛
- مهاجرت SQLite به PostgreSQL پیش از Production مقیاس‌پذیر؛
- Rotation کلید افشاشده توسط مالک حساب؛
- افزودن Android Unit/UI Test واقعی؛
- رسیدگی تدریجی به 20 هشدار غیرمسدودکننده Android Lint؛
- فعال‌سازی بروکرها فقط در فاز جداگانه و ابتدا روی Testnet/Demo.
