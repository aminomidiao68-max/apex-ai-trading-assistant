# راهنمای تکمیل Firebase Push برای APEX AI

## وضعیت فعلی
در پروژه این موارد از قبل آماده شده‌اند:
- Firebase Messaging dependency در اندروید
- `ApexFirebaseMessagingService`
- ثبت device token در بک‌اند
- endpointهای تست notification
- local notification fallback

اما برای **push واقعی Firebase** هنوز باید پیکربندی پروژه خودت را اضافه کنی.

---

## مرحله 1: ساخت پروژه Firebase
1. وارد Firebase Console شو.
2. یک پروژه جدید بساز.
3. اپ اندرویدی را با package name زیر ثبت کن:
   - `com.arena.smartmoney`

---

## مرحله 2: دریافت `google-services.json`
بعد از ثبت اپ اندرویدی:
1. فایل `google-services.json` را دانلود کن.
2. آن را داخل این مسیر قرار بده:

```text
project/android/app/google-services.json
```

> این فایل نباید داخل workspace عمومی بدون کنترل قرار بگیرد اگر اطلاعات واقعی تولیدی داخلش باشد.

---

## مرحله 3: فعال‌سازی Gradle plugin در اندروید
در نسخه فعلی dependency مربوط به FCM اضافه شده، اما برای تکمیل setup معمولاً باید Google Services plugin هم فعال شود.

مواردی که در مرحله بعد می‌توان اضافه کرد:
- plugin مربوط به `com.google.gms.google-services`
- sync مجدد پروژه در Android Studio

---

## مرحله 4: تست دریافت توکن
بعد از اجرای اپ:
- لاگین کن
- از صفحه Profile روی:
  - `Register Device for Push`
بزن

سپس در بک‌اند:
- `GET /api/v1/notifications/devices`
را بررسی کن

اگر token ذخیره شد یعنی registration موفق بوده است.

---

## مرحله 5: ارسال Push واقعی از سرور
برای ارسال remote push واقعی، backend نیاز به credential معتبر Firebase دارد.

در فاز بعدی می‌توان این‌ها را اضافه کرد:
- service account JSON
- Firebase Admin SDK یا REST integration
- ارسال push واقعی به tokenهای ذخیره‌شده

---

## هشدار امنیتی
- `google-services.json` را با دقت مدیریت کن.
- credentialهای server-side Firebase را هرگز داخل اپ قرار نده.
- کلیدها فقط باید سمت بک‌اند نگه‌داری شوند.
