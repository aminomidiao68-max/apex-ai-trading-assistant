# گزارش APEX Omega Pro — Paper Alpha 7

## هدف

Reconciliation خصوصی و احرازشده Testnet به‌صورت کاملاً Read-only، همراه با Recovery Drill قطعی؛ بدون Place/Cancel.

## قابلیت‌ها

- Binance Futures Testnet: signed GET برای Open Orders و User Trades
- Bybit Testnet: signed GET برای Realtime Orders و Executions
- استفاده از API Key/Secret رمزنگاری‌شده و user-scoped
- تطبیق `clientOrderId` و `orderLinkId` با Paper `order_id`
- تطبیق Status و Filled quantity
- تشخیص سفارش خارجی ناشناخته و سفارش باز محلی غایب
- Snapshot با برچسب‌های:
  - `provider_authenticated=true`
  - `provider_snapshot_verified=true`
  - `read_only=true`
  - `order_routing_enabled=false`
  - `actionable_for_live=false`
- ذخیره پایدار نتیجه Reconciliation
- Recovery drill آفلاین برای success/failure/backoff
- Backoff نمایی محدود به ۶۰۰ ثانیه
- Drill قطعی، بدون Network و بدون Route

## Schema v11

```text
paper_private_testnet_reconciliations
```

## API

```text
POST /api/v1/paper/testnet/connectors/{connector}/private-reconcile
POST /api/v1/paper/testnet/recovery-drill
```

## محدودیت‌ها

- این فاز هیچ سفارش Testnet ایجاد یا لغو نمی‌کند.
- تطبیق فقط برای سفارش‌هایی معنادار است که External client ID آن‌ها با Paper order ID یکسان باشد.
- Snapshot احرازشده Testnet مجوز Live نیست.
- Chaos testing چندپردازه/چندمنطقه‌ای واقعی هنوز باقی است.
- `ENABLE_LIVE_EXECUTION=false` و Testnet order routing خاموش است.
- هیچ تضمین سود یا عملکرد آینده وجود ندارد.
