# Runbook نسخه RC — APEX AI Trading Assistant

نسخه: `3.0.0-rc1`

## اصل توقف انتشار

RC فقط وقتی قابل پذیرش است که تمام موارد زیر سبز باشند:

- Backend SQLite Regression
- Backend PostgreSQL Integration
- Android Unit Test
- Android Lint
- Android APK Build
- Render `/ready`
- PostgreSQL `migration_current=true`
- Live Execution خاموش

## PostgreSQL

متغیر اصلی:

```text
DATABASE_URL=postgresql://...
```

Connection String باید فقط در Secret Store میزبان نگهداری شود. برنامه URL، Password یا Host دیتابیس را در Health، Log یا Error نمایش نمی‌دهد.

Render Blueprint فایل `render.yaml` شامل PostgreSQL و اتصال `fromDatabase` است. اگر سرویس موجود به‌صورت Blueprint مدیریت نمی‌شود، باید Blueprint در داشبورد Render Sync شود؛ Connection String نباید دستی در Git ثبت شود.

### Migration

Migration هنگام Startup و پیش از سرویس‌دهی اجرا می‌شود. Endpoint زیر فقط در صورت اتصال DB و جاری بودن Schema پاسخ Ready می‌دهد:

```text
GET /ready
```

خروجی عمیق نیازمند Bearer Token است:

```text
GET /api/v1/system/health/deep
```

## Backup

### PostgreSQL

روی Host دارای `pg_dump`:

```bash
cd backend
DATABASE_URL='set-in-secret-environment' \
python scripts/backup_database.py --output-dir /secure/backups --retention-days 14
```

Connection String از `PGDATABASE` به Process داده می‌شود و چاپ نمی‌شود. خروجی شامل Dump و Manifest با SHA-256 است.

### SQLite محلی

```bash
cd backend
DATABASE_PATH=app_data/smartmoney.db \
python scripts/backup_database.py --output-dir backups
```

Backup با API آنلاین SQLite و `PRAGMA integrity_check` ساخته می‌شود.

## Restore

Restore مخرب است و فقط در Maintenance Window انجام می‌شود:

```bash
python scripts/restore_database.py /secure/backups/apex-postgresql-....dump \
  --confirm RESTORE_APEX_DATABASE
```

قواعد:

1. ابتدا Manifest و SHA-256 بررسی می‌شود.
2. ترافیک Write متوقف شود.
3. از DB فعلی Safety Backup گرفته شود.
4. Restore اجرا شود.
5. `/ready` و Deep Health بررسی شوند.
6. Auth/Journal Smoke Test اجرا شود.
7. در صورت شکست، Rollback انجام شود.

## Monitoring

تمام Requestها دارای موارد زیر هستند:

- `X-Request-ID`
- `X-Response-Time-Ms`
- Structured JSON log
- Route Template به‌جای Query String
- Client Hash به‌جای IP خام

Metrics احراز هویت‌شده:

```text
GET /api/v1/system/metrics
```

Metrics شامل تعداد Request، 5xx، Rate Limit، Average Latency و P95 است و هیچ Credential یا Payload ذخیره نمی‌کند.

## Rate Limit

Policyهای پیش‌فرض در دقیقه:

- Auth: 10
- AI Explain: 20
- Heavy Analysis/Backtest/Scanner: 15
- Default: 120

در پاسخ 429:

- `Retry-After`
- `X-Request-ID`
- پیام عمومی بدون اطلاعات داخلی

این Rate Limiter درون‌پردازه‌ای است. برای چند Replica، جایگزینی State با Redis در نسخه Production Scale توصیه می‌شود.

## Security

- Session Token فقط به‌صورت SHA-256 در DB ذخیره می‌شود.
- Password جدید با PBKDF2-SHA256 و 310,000 Iteration ذخیره می‌شود.
- Hash قدیمی پس از Login موفق Upgrade می‌شود.
- Body بزرگ‌تر از 2 MiB رد می‌شود.
- CSP، HSTS، NoSniff، DENY Frame و No-Referrer فعال‌اند.
- Error عمومی شامل Request ID است و Raw Exception به Client نمی‌رسد.
- External AI پیش‌فرض خاموش است.
- Live Execution خاموش است.

## Release Provenance

Android CI کنار APK فایل زیر را تولید می‌کند:

```text
release-manifest.json
```

Manifest شامل موارد زیر است:

- Version
- Git Commit SHA
- APK SHA-256
- APK Size
- Safety Flags
- Required Gates

قبل از نصب، Digest فایل APK باید با Manifest و GitHub Artifact برابر باشد.

## Rollback

1. آخرین Commit سبز قبلی را در GitHub مشخص کنید.
2. از Database Backup جدید محافظت کنید.
3. Render را به Commit قبلی Deploy کنید.
4. Schema را فقط اگر Migration ناسازگار است و Runbook صریح دارد Restore کنید.
5. `/ready`، Login، Journal، Chart و AI Status را بررسی کنید.
6. Live Execution در تمام Rollback خاموش بماند.
