# گزارش BYOK Alpha 1 — Encrypted User Provider Vault

نسخه هدف: `3.3.0-byok-alpha1`

## هدف

امکان ورود API Key از داخل Android Settings بدون ذخیره Plaintext روی دستگاه، Git یا PostgreSQL.

کلیدهایی که قبلاً در گفتگو افشا شده‌اند نباید دوباره استفاده شوند و باید Rotate شوند.

## معماری امنیتی

```text
Android password field (RAM only)
  -> HTTPS + Bearer user session
  -> FastAPI SecretStr request
  -> AES-256-GCM encryption
  -> PostgreSQL user-scoped ciphertext
```

Master Key:

- فقط در Render Secret با نام `USER_SECRET_MASTER_KEY`
- 32-byte random key
- هرگز در Git، DB، API response یا Android ذخیره نمی‌شود.
- Key version با `USER_SECRET_KEY_VERSION` ثبت می‌شود.

Associated authenticated data:

```text
user_id + provider + key_version
```

بنابراین Ciphertext بین User/Provider قابل جابه‌جایی نیست.

## PostgreSQL

Schema migration version: `4`

Table:

```text
user_provider_secrets
```

Fields:

- user_id
- provider
- ciphertext
- nonce
- key_version
- enabled
- metadata_json بدون Secret
- last_test_status/time
- created/updated
- unique(user_id, provider)

## Providerها

- Groq
- OpenAI
- TwelveData
- Finnhub
- NewsAPI
- OANDA Practice

OANDA نیازمند Token و Account ID است. Live Execution همچنان خاموش می‌ماند.

## API

```text
GET    /api/v1/settings/providers
POST   /api/v1/settings/providers/{provider}
POST   /api/v1/settings/providers/{provider}/test
DELETE /api/v1/settings/providers/{provider}
GET    /api/v1/news/personalized
```

همه نیازمند Bearer Authentication هستند.

هیچ Endpointی Secret خام را برنمی‌گرداند:

```text
raw_secrets_returned=false
details_exposed=false
```

## Runtime Routing

### AI

- Groq از OpenAI-compatible API استفاده می‌کند.
- OpenAI Provider مستقل است.
- BYOK runtime provider فقط برای همان User استفاده می‌شود.
- Cache namespace User-scoped است.
- External AI فقط Explanation است و Decision را Override نمی‌کند.
- Deterministic fallback همیشه باقی می‌ماند.

### Historical Data

- TwelveData BYOK برای Collection همان User استفاده می‌شود.
- Key به Provider object همان Request تزریق می‌شود و Global state تغییر نمی‌کند.

### News

- Finnhub و NewsAPI برای Personalized News همان User استفاده می‌شوند.
- نتیجه Providerها normalize و deduplicate می‌شود.
- Economic-calendar block از Headlineها جعل نمی‌شود.

### OANDA

- فقط Credential connection test روی Practice endpoint.
- Live order execution همچنان توسط `ENABLE_LIVE_EXECUTION=false` مسدود است.

## Android Settings

- Secure API Vault card
- Provider selector
- Password-transformed key field
- OANDA Account ID field
- Optional AI model field
- Enabled toggle
- Save/Test/Delete
- Configured status
- Last connection status

Security behavior:

- Key در SharedPreferences ذخیره نمی‌شود.
- Key پس از Save یا Failure پاک می‌شود.
- Raw key read-back وجود ندارد.
- Local Demo اجازه Remote Secret storage ندارد.
- UI صریحاً Rotation کلیدهای افشاشده را توصیه می‌کند.

## Connection Tests

نتیجه فقط یکی از این Statusها است:

- connected
- auth_failed
- unavailable
- not_configured
- vault_unavailable

Raw response/error/provider URL به Client برنمی‌گردد.

## تست‌ها

- AES-GCM ciphertext does not contain raw key
- 12-byte nonce
- user isolation
- no read-back in status/JSON
- OANDA account requirement
- disabled key resolution block
- missing/wrong master key fail-closed
- sanitized connection result
- runtime Groq while global external AI is disabled
- user-scoped AI cache
- authenticated Settings API
- personalized news does not expose key
- PostgreSQL schema v4 presence

نتیجه محلی:

```text
77 passed, 1 skipped
```

## محدودیت‌ها

- Key rotation نیازمند Replace از UI است.
- Master-key rotation/re-encryption workflow باید در مرحله بعد اضافه شود.
- Provider usage/cost quota dashboard هنوز کامل نیست.
- NewsAPI headlineها Economic Calendar نیستند.
- کلیدهای افشاشده قبلی امن نمی‌شوند؛ باید Provider-side Rotate شوند.
- Live Execution خاموش است.
