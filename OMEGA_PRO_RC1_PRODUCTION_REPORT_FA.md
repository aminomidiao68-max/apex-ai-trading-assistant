# گزارش RC1 — Production & Release Candidate Gate

نسخه هدف: `3.0.0-rc1`

## وضعیت

پیاده‌سازی RC1 کامل شده است. پذیرش نهایی منوط به موارد زیر است:

- SQLite Regression CI
- PostgreSQL 16 Integration CI
- Android Test/Lint/APK CI
- Render Deploy
- `/ready` با `database.backend=postgresql`
- `migration_current=true`
- Release Manifest و APK Digest

## ۱) PostgreSQL Production Persistence

فایل اصلی:

`backend/app/services/database_service.py`

قابلیت‌ها:

- انتخاب PostgreSQL با `DATABASE_URL`
- SQLite فقط برای Local/Test
- `psycopg` و Connection Pool
- Placeholder translation امن
- `RETURNING id` برای Insertهای PostgreSQL
- Row mapping سازگار با SQLite/PostgreSQL
- Fail-closed در نبود PostgreSQL Driver/Connection
- عدم نمایش Connection String در Status/Error

## ۲) Migration Manager

Schema Version فعلی: `1`

جداول:

- `schema_migrations`
- `users`
- `sessions`
- `signals`
- `trades`
- `device_tokens`
- `notification_events`

Migration:

- هنگام Startup اجرا می‌شود.
- Idempotent است.
- Legacy SQLite را In-place ارتقا می‌دهد.
- PostgreSQL از `BIGSERIAL` و `ADD COLUMN IF NOT EXISTS` استفاده می‌کند.
- Indexهای User/Session/Notification ساخته می‌شوند.

## ۳) Auth Hardening

- Session Token خام در DB ذخیره نمی‌شود.
- SHA-256 Token Digest در جدول Session ثبت می‌شود.
- Password جدید: `PBKDF2-SHA256` با `310,000` Iteration.
- Hash قدیمی پس از Login موفق Upgrade می‌شود.
- Duplicate Email و Database Error بدون افشای Constraint/SQL مدیریت می‌شوند.

## ۴) Monitoring

- `X-Request-ID`
- `X-Response-Time-Ms`
- Structured JSON HTTP Log
- Route Template بدون Query String
- Client Hash بدون IP خام
- Request count
- 5xx count
- Rate-limit count
- Average latency
- P95 latency

Endpointهای Health:

```text
GET /health
GET /ready
GET /api/v1/system/health/deep   (Bearer)
GET /api/v1/system/metrics       (Bearer)
```

## ۵) Rate Limiting و Request Guard

Policy پیش‌فرض در دقیقه:

- Auth: 10
- AI: 20
- Heavy: 15
- Default: 120

موارد امنیتی:

- Sliding Window
- Client identity hash
- Proxy header validation به‌عنوان IP
- `Retry-After`
- حداکثر Body برابر 2 MiB
- 413/429 با Request ID

## ۶) Security Headers و Error Handling

- HSTS در Production
- CSP
- X-Content-Type-Options
- X-Frame-Options
- Referrer-Policy
- Permissions-Policy
- Cache-Control no-store برای Auth/AI
- Unhandled Error عمومی با Request ID
- Raw Exception، Query، Token، API Key و DB URL به Client ارسال نمی‌شوند.

## ۷) Backup و Restore

ابزارها:

```text
backend/scripts/backup_database.py
backend/scripts/restore_database.py
```

قابلیت‌ها:

- PostgreSQL Custom Dump با `pg_dump`
- SQLite Online Backup API
- SQLite Integrity Check
- Manifest
- SHA-256
- Retention cleanup
- Restore فقط با Confirmation صریح
- Safety copy پیش از SQLite Restore
- `pg_restore --exit-on-error`

Runbook:

`docs/rc_production_runbook_fa.md`

## ۸) Render Blueprint

`render.yaml` شامل:

- PostgreSQL 16
- `fromDatabase.connectionString`
- `/ready` Health Check
- Auto Deploy
- Production Rate Limits
- Connection Pool
- External AI خاموش
- Live Execution خاموش

اگر سرویس فعلی Render تحت Blueprint نباشد، Blueprint باید در داشبورد Sync شود. هیچ Connection String نباید در Git ثبت شود.

## ۹) Release Provenance

Android CI فایل زیر را کنار APK می‌سازد:

```text
release-manifest.json
```

محتوا:

- Version
- Git Commit SHA
- APK filename/size
- APK SHA-256
- Safety flags
- Required gates

Artifact RC:

```text
apex-ai-rc-debug-apk
```

## ۱۰) تست‌ها

فایل جدید:

`backend/tests/test_rc_production_gate.py`

پوشش:

- Legacy SQLite migration
- Schema version/integrity
- PostgreSQL SQL dialect
- BIGSERIAL و idempotent columns
- Hashed session token
- Legacy password upgrade
- Sliding-window rate limiter
- Request ID validation
- Proxy IP validation
- Monitoring counters/P95
- Production readiness block روی SQLite
- Backup/manifest/restore roundtrip
- Liveness/readiness/deep health/metrics
- Body-size rejection

PostgreSQL واقعی:

`backend/tests/test_postgres_integration.py`

GitHub Actions یک PostgreSQL 16 واقعی اجرا می‌کند و Auth/Session/Journal/Migration را Roundtrip می‌کند.

نتیجه محلی:

```text
38 passed, 1 skipped
```

Skip فقط PostgreSQL Server محلی است؛ CI آن را اجرا می‌کند.

## ۱۱) محدودیت‌های صریح

- Rate Limit فعلی In-process است؛ برای چند Replica باید Redis اضافه شود.
- Backup زمان‌بندی‌شده نیازمند Cron/Provider Automation است؛ ابزار و Runbook آماده‌اند.
- RC مجوز Live Trading نیست.
- External AI پیش‌فرض خاموش است.
- Live Execution خاموش است.
- هیچ سود، دقت یا عملکرد آینده تضمین نمی‌شود.
