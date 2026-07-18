# گزارش APEX Omega Pro — Paper Alpha 9

## هدف
Testnet Place/Cancel با Feature Flag، Vault، Allowlist، Idempotency و Kill Switch مستقل؛ بدون Live routing.

## قابلیت‌ها
- کنترل مستقل و پیش‌فرض `enabled=false / kill_switch=true`
- الزام `APP_ENV=staging`
- الزام `ENABLE_TESTNET_EXECUTION=true`
- مسدودشدن در صورت `ENABLE_LIVE_EXECUTION=true`
- Symbol allowlist، Max notional و Max open orders
- Idempotency key + request hash
- client order ID قطعی و محدود
- Binance Futures Testnet Market Place و Cancel امضاشده
- Bybit Testnet Market Place و Cancel امضاشده
- دو فاز `submission_pending` و `cancel_pending`
- وضعیت `unknown` در قطع اتصال و Kill Switch خودکار
- API Secret فقط از Vault رمزنگاری‌شده
- `testnet_only=true` و `live_routed=false`

## Schema v13
```text
paper_testnet_execution_controls
paper_testnet_orders
```

## API
```text
GET/POST /api/v1/paper/testnet/execution/control
POST     /api/v1/paper/testnet/execution/orders
GET      /api/v1/paper/testnet/execution/orders
POST     /api/v1/paper/testnet/execution/orders/{order_id}/cancel
```

## وضعیت فعال‌سازی
Production و Staging هر دو با `ENABLE_TESTNET_EXECUTION=false` Deploy می‌شوند. فعال‌سازی Staging فقط پس از ورود Credential تست‌نت، Allowlist و تأیید Kill Switch انجام می‌شود. Live Execution خاموش است.

## محدودیت
- Fill stream پیوسته و Reduce-only position verification کامل هنوز باقی است.
- هیچ سود یا عملکرد آینده تضمین نمی‌شود.
