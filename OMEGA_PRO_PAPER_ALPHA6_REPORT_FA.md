# گزارش APEX Omega Pro — Paper Alpha 6

## هدف

افزودن Correlation آماری قابل‌بازتولید از Datasetهای immutable و زیرساخت اتصال خصوصی فقط‌خواندنی Testnet، بدون فعال‌سازی Place/Cancel یا Live routing.

## Statistical Correlation Snapshot

- ورودی فقط Datasetهای user-scoped ذخیره‌شده
- بررسی یکسان‌بودن Timeframe
- الزام Symbolهای یکتا
- محاسبه Log return از Closeهای مرتب‌شده
- هم‌ترازی دقیق Timestamp بین همه Datasetها
- حداقل ۳۰ مشاهده و پیش‌فرض ۶۰ مشاهده
- Winsorization قطعی 1%/99%
- Pearson correlation
- Shrinkage به سمت صفر:

```text
shrunk_correlation = raw_correlation × n / (n + 20)
```

- Cluster قطعی بر اساس `abs(correlation) >= threshold`
- Canonical SHA-256 شامل Dataset SHA، Matrix، Cluster و پارامترها
- Snapshot ID و Request hash برای Idempotency
- `correlation_source=stored_dataset_statistical`
- `actionable_for_live=false`

## اتصال Snapshot به Paper OMS

- سفارش می‌تواند `correlation_snapshot_id` مشخص کند.
- Snapshot باید متعلق به همان کاربر باشد.
- Symbol سفارش باید داخل Snapshot باشد.
- Cluster آماری به Risk group سفارش و پوزیشن تبدیل می‌شود.
- Group concentration هنگام Submit و Fill دوباره بررسی می‌شود.
- بدون Snapshot، سیستم همچنان از `structural_proxy` شفاف استفاده می‌کند.

## Private Testnet Read-Only Vault

Providerهای جدید:

```text
binance_testnet
bybit_testnet
```

- API Key و API Secret در Vault AES-256-GCM موجود رمزنگاری می‌شوند.
- API Secret هرگز در Status یا Response برگردانده نمی‌شود.
- Android مقدار Secret را در Preferences ذخیره نمی‌کند و پس از Save پاک می‌کند.
- Binance: signed GET روی Account endpoint تست‌نت
- Bybit: signed GET روی Wallet Balance endpoint تست‌نت
- هیچ متد POST/Place/Cancel در Probe استفاده نمی‌شود.
- `ENABLE_LIVE_EXECUTION=false` باقی می‌ماند.

## Schema v10

### جدول جدید

```text
paper_correlation_snapshots
```

### ستون‌های جدید Order/Position

```text
correlation_source
correlation_snapshot_id
```

## API

```text
POST /api/v1/paper/risk/correlation/snapshots
```

Provider Vault APIهای موجود نیز دو Provider تست‌نت جدید را پشتیبانی می‌کنند.

## قرارداد صداقت

- Correlation آماری، علیت یا عملکرد آینده را اثبات نمی‌کند.
- Correlation فقط روی بازه و Datasetهای انتخاب‌شده معتبر است.
- Shrinkage و Winsorization تخمین را پایدارتر می‌کنند، اما آن را قطعی نمی‌کنند.
- Private Testnet Probe فقط‌خواندنی است؛ Reconciliation کامل Order/Fill خصوصی هنوز نیازمند مرحله بعد است.
- هیچ Testnet order یا Live order ارسال نمی‌شود.
- هیچ سود، Win Rate یا دقت آینده تضمین نمی‌شود.
