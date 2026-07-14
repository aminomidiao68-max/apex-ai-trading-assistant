# گزارش Data Alpha 1 — Historical Data Pipeline

نسخه هدف: `3.1.0-data-alpha1`

## هدف

ساخت Pipeline واقعی، نسخه‌بندی‌شده و قابل ممیزی برای داده تاریخی؛ بدون اینکه Range ناقص، کندل باز یا Dataset غیرمستقل به‌عنوان داده کامل/holdout معرفی شود.

## Provider Architecture

فایل:

`backend/app/services/historical_data_service.py`

Providerها:

- OKX historical swap candles برای Crypto
- TwelveData time series برای Forex/Gold در صورت Configuration
- Yahoo chart fallback برای Forex/Index با محدودیت Range صریح
- معماری قابل توسعه برای Providerهای دیگر

## OKX Pagination

Endpoint:

```text
/api/v5/market/history-candles
```

- `after` برای صفحه‌های قدیمی‌تر
- حداکثر 100 ردیف در هر صفحه
- Stalled cursor detection
- `confirm=1` برای کندل بسته‌شده
- Instrument از نوع USDT SWAP
- داده Exchange-specific است و کل بازار Crypto نیست.

## Yahoo Honesty Gate

Yahoo فقط fallback بدون SLA نهادی است.

Pipeline به‌صورت Fail-fast محدودیت‌های بازه را اعمال می‌کند:

- 1m بیش از بازه مجاز رد می‌شود.
- Intraday چندماهه/چندساله بی‌صدا truncate نمی‌شود.
- 1h محدودیت تاریخی دارد.
- Unsupported timeframe رد می‌شود.

## TwelveData

- start/end UTC
- outputsize محدود
- no raw provider error
- no API key exposure
- licensing/redistribution review در Manifest ذکر می‌شود.

## Canonicalization

- UTC timezone
- start/end range filter
- فقط finalized candles
- OHLC validation از Pydantic Candle
- sort ascending
- duplicate removal و count
- gap estimation
- Forex weekend adjustment
- gap ratio
- data quality score
- canonical JSON SHA-256

## Dataset Manifest

- dataset_id
- immutable version
- source
- symbol/market/timeframe
- actual first/last candle
- sample count
- source/canonical SHA-256
- point-in-time attestation
- survivorship-control attestation
- independent-holdout attestation
- quality score
- issues/limitations

هیچ‌کدام از Attestationها به‌صورت خودکار True نمی‌شوند.

## PostgreSQL Registry

Migration version: `2`

Table:

```text
quant_datasets
```

ذخیره می‌کند:

- Metadata
- Manifest JSON
- Canonical SHA
- Gzip-compressed canonical candles
- creation time
- `user_id` و User-scoped isolation
- unique(user_id, dataset_id, version)

Immutability:

- همان ID/version و همان SHA: idempotent
- همان ID/version و SHA متفاوت: `immutable_dataset_version_conflict`
- Dataset قبلی overwrite نمی‌شود.

## API

```text
POST /api/v1/research/historical/collect
GET  /api/v1/research/datasets
GET  /api/v1/research/datasets/{dataset_id}/{version}
```

همه نیازمند Bearer Authentication هستند و زیر Rate Limit گروه Heavy قرار دارند.

## Live Smoke واقعی

OKX BTCUSDT SWAP، timeframe 1h، بازه هفت‌روزه:

```text
provider=okx_swap_history_public
pages=2
raw_rows=200
accepted_rows=167
duplicates=0
missing=0
finalized_only=true
stored=false
sha256_length=64
holdout=false
```

این Smoke فقط Pipeline را تأیید می‌کند و Evidence سودآوری نیست.

## تست‌ها

فایل:

`backend/tests/test_historical_data_service.py`

پوشش:

- pagination result contract
- finalized candle filtering
- duplicate removal
- gap detection
- SHA-256
- gzip persistence
- list/get/load registry
- immutable dataset version
- Yahoo range fail-fast
- missing dataset error
- migration v2
- PostgreSQL table integration
- authenticated API persistence

نتیجه کامل محلی:

```text
53 passed, 1 skipped
```

Skip فقط PostgreSQL local است و در CI با PostgreSQL 16 اجرا می‌شود.

## محدودیت‌های صریح

- Dataset جمع‌آوری‌شده به‌تنهایی Edge را ثابت نمی‌کند.
- Provider truthfulness و licensing نیازمند Audit خارجی است.
- Survivorship/holdout flags operator attestations هستند.
- Yahoo institutional-grade نیست.
- Raw datasets بزرگ در PostgreSQL رایگان باید از نظر Capacity مانیتور شوند؛ Object Storage برای Scale مرحله بعد است.
- Live Execution همچنان خاموش است.
