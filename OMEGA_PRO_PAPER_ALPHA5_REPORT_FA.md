# گزارش APEX Omega Pro — Paper Alpha 5

## هدف

افزودن بازیابی اتصال، حسابرسی کامل Ledger، Shadow Reconciliation و کنترل تمرکز Portfolio بدون فعال‌کردن هیچ مسیر سفارش واقعی.

## قابلیت‌های اصلی

### Public Testnet Probe

- Binance Futures Testnet public-time probe
- Bybit Testnet public-time probe
- اندازه‌گیری Latency و Server clock offset
- Checkpoint پایدار کاربرمحور
- Exponential backoff پس از خطا
- Error code پاک‌سازی‌شده بدون URL، Credential یا متن خام Provider
- `public_connectivity_only=true`
- `authenticated=false`
- `order_routing_enabled=false`

### Shadow Reconciliation

- دریافت Snapshot خارجی برای مقایسه فقط‌خواندنی
- مقایسه Status، Filled quantity، Average fill و Fees
- شناسایی External order ناشناخته
- شناسایی Local open order غایب در Snapshot
- Run ID و Snapshot ID کاربرمحور و Idempotent
- Payload conflict detection
- Snapshot ورودی کاربر همیشه:
  - `snapshot_verified_by_provider=false`
  - `actionable_for_live=false`

### Ledger Audit

- تطبیق Order با Fill aggregation
- تطبیق Weighted average و Fees
- بررسی Sequence رویدادهای سفارش
- بررسی Terminal status/timestamp
- Replay پوزیشن از Fill و Liquidation event
- تطبیق Position quantity، Realized PnL و Fees
- تطبیق Account realized/fees/funding/liquidation count
- بررسی Cash identity:

```text
cash = initial_cash + realized_pnl - total_fees - total_funding
```

- Audit فقط تشخیصی است و هیچ Repair خودکاری انجام نمی‌دهد.

### Structural Concentration Controls

- Symbol margin concentration
- Risk-group margin concentration
- Directional notional exposure
- کنترل دوباره هنگام Fill برای سفارش‌های Working
- Risk groupهای شفاف و deterministic:
  - `crypto_major_structural_proxy`
  - `crypto_alt_structural_proxy`
  - `crypto_stable_structural_proxy`
  - `metals_usd_structural_proxy`
  - `forex_usd_structural_proxy`
  - `forex_eur_structural_proxy`
  - `other_structural_proxy`
- `correlation_source=structural_proxy`
- این گروه‌بندی هم‌بستگی آماری واقعی معرفی نمی‌شود.

## Schema v9

### ستون‌های جدید Control

- `max_symbol_margin_pct`
- `max_risk_group_margin_pct`
- `max_directional_notional_multiple`

### ستون‌های جدید Order/Position

- `risk_group`

### جداول جدید

```text
paper_connector_checkpoints
paper_shadow_reconciliations
```

## API

```text
GET  /api/v1/paper/testnet/checkpoints
POST /api/v1/paper/testnet/connectors/{connector}/probe
POST /api/v1/paper/testnet/shadow-reconcile
GET  /api/v1/paper/audit
```

## تست واقعی عمومی

در Smoke محلی این فاز:

```text
Binance Futures Testnet = connected
Bybit Testnet = public_probe_http_error -> backoff
```

این نتیجه فقط وضعیت همان لحظه Provider/Region است و تضمین دسترس‌پذیری آینده نیست.

## قرارداد ایمنی و صداقت

- Probe عمومی هیچ Credential استفاده نمی‌کند.
- هیچ سفارش Testnet یا Live ارسال نمی‌شود.
- Shadow Snapshot کاربر به‌عنوان Snapshot تأییدشده Provider معرفی نمی‌شود.
- Structural risk group برابر با Correlation آماری نیست.
- Audit مجوز Live صادر نمی‌کند.
- `live_routed=false` و `ENABLE_LIVE_EXECUTION=false` باقی می‌مانند.
- هیچ سود، Win Rate، دقت یا عملکرد آینده تضمین نمی‌شود.

## محدودیت‌های باقی‌مانده

- Reconciliation احرازشده با API خصوصی Testnet هنوز پیاده‌سازی نشده است.
- Retry برای Place/Cancel واقعی Testnet وجود ندارد، چون Routing عمداً خاموش است.
- Correlation matrix آماری از Dataset زنده هنوز به Portfolio OMS متصل نشده است.
- Disaster recovery چندمنطقه‌ای و Chaos testing هنوز باقی است.
