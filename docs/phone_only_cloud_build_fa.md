# مسیر واقعی برای کاربر فقط-گوشی (Phone-Only Path)

اگر فقط گوشی داری و کامپیوتر نداری، برای اینکه اپ واقعاً build و اجرا شود باید این دو کار را از طریق سرویس‌های ابری انجام دهی:

## بخش A) انتشار سورس در GitHub
1. یک مخزن GitHub بساز.
2. فایل‌های پروژه را داخل آن قرار بده.
3. از فایل‌های زیر برای انتشار استفاده کن:
   - `README.md`
   - `README_GITHUB_PUBLIC.md`
   - `docs/github_publish_steps_fa.md`

## بخش B) Build APK در GitHub Actions
من فایل آماده این کار را ساختم:
- `.github/workflows/android-apk-build.yml`

### چه کاری باید انجام بدهی؟
در تنظیمات مخزن GitHub:
- Variables بساز:
  - `APEX_API_BASE_URL`
  - `APEX_WS_BASE_URL`
- اگر Firebase واقعی می‌خواهی، Secret بساز:
  - `GOOGLE_SERVICES_JSON`
- اگر release signing می‌خواهی، Secret بساز:
  - `ANDROID_RELEASE_KEYSTORE_BASE64`
  - `ANDROID_KEYSTORE_PASSWORD`
  - `ANDROID_KEY_ALIAS`
  - `ANDROID_KEY_PASSWORD`

بعد workflow را اجرا کن و APK را از بخش Artifacts دانلود کن.

## بخش C) Deploy بک‌اند روی Render
من فایل آماده این کار را ساختم:
- `render.yaml`

### کارهایی که باید بکنی:
1. وارد Render شو.
2. مخزن GitHub را وصل کن.
3. سرویس را از روی `render.yaml` بساز.
4. envهای لازم را در Render تنظیم کن.

### مهم‌ترین envها:
- `TWELVEDATA_API_KEY`
- `FIREBASE_PROJECT_ID`
- `FIREBASE_SERVICE_ACCOUNT_JSON`
- `BINANCE_API_KEY`
- `BINANCE_API_SECRET`
- `OANDA_API_TOKEN`
- `OANDA_ACCOUNT_ID`

## نتیجه نهایی
وقتی Render دامنه API را به تو داد، همان را به‌عنوان:
- `APEX_API_BASE_URL`
- `APEX_WS_BASE_URL`
در GitHub Actions تنظیم می‌کنی
و بعد APK می‌سازی.

## نکته خیلی مهم
روی گوشی، اجرای «واقعی» بدون:
- یک backend عمومی روی اینترنت
- و build APK در cloud
عملاً ممکن نیست.

برای همین، این مسیر phone-only واقعی‌ترین و منطقی‌ترین راه است.
