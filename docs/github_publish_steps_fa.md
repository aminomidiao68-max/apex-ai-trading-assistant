# راهنمای انتشار در GitHub

## فایل README عمومی
یک نسخه مناسب GitHub برای README ساخته شده در:
- `project/README_GITHUB_PUBLIC.md`

اگر بخواهی آن را README اصلی مخزن کنی، کافی است هنگام انتشار:
- نام آن را به `README.md` تغییر بده
- یا محتوایش را داخل README اصلی جایگزین کنی

---

## قبل از Push به GitHub این موارد را چک کن
- `android/app/google-services.json` داخل مخزن نباشد
- `backend/.env` داخل مخزن نباشد
- keystore واقعی داخل مخزن نباشد
- credentialهای broker و Firebase داخل سورس hardcode نشده باشند

---

## فایل‌های مهمی که بهتر است در مخزن عمومی بمانند
- `README_GITHUB_PUBLIC.md`
- `docs/`
- `android/`
- `backend/`
- `.gitignore`

---

## فایل‌هایی که نباید عمومی شوند
- `backend/.env`
- `android/app/google-services.json`
- فایل‌های keystore
- service accountهای Firebase
- API keyها و secretها

---

## پیشنهاد برای انتشار حرفه‌ای‌تر
- اسکرین‌شات اپ اضافه کن
- توضیح فارسی و انگلیسی محصول بنویس
- roadmap بساز
- بخش Known Limitations اضافه کن
- Release Notes آماده کن
