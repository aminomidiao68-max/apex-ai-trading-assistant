# فعال‌سازی حالت واقعی Firebase Push در بک‌اند

## وضعیت فعلی
در نسخه فعلی:
- اگر `FIREBASE_PROJECT_ID` و `FIREBASE_SERVICE_ACCOUNT_JSON` تنظیم نشده باشند، سیستم در حالت `dry-run` می‌ماند.
- اگر این دو مقدار تنظیم شوند، backend تلاش می‌کند push واقعی FCM را از طریق FCM HTTP v1 ارسال کند.

## متغیرهای لازم
در فایل env تولیدی یا توسعه:
```env
FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_SERVICE_ACCOUNT_JSON=/absolute/path/to/service-account.json
```

## نکات مهم
- فایل service account را داخل مخزن قرار نده.
- مسیر فایل باید روی سروری که backend اجرا می‌شود معتبر باشد.
- بعد از تنظیم این دو مقدار، endpoint زیر می‌تواند ارسال واقعی را امتحان کند:

```text
POST /api/v1/notifications/test
```

## روند کار
1. credential از service account خوانده می‌شود.
2. access token گوگل ساخته می‌شود.
3. درخواست به FCM v1 endpoint ارسال می‌شود.
4. نتیجه برای هر device token بررسی می‌شود.

## هشدار
- قبل از استفاده واقعی، حتماً روی پروژه Firebase و tokenهای واقعی تست انجام بده.
- اگر credentialها اشتباه باشند، سیستم عملاً ارسال موفق نخواهد داشت.
