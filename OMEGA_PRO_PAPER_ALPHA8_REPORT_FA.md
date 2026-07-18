# گزارش APEX Omega Pro — Paper Alpha 8

## هدف
Chaos/Disaster Recovery قطعی در CI، سپس Staging مستقل؛ بدون Order Route و بدون Mutation تولید.

## قابلیت‌ها
- Snapshot کاربرمحور از Ledgerهای Paper
- Canonical JSON، Gzip قطعی و SHA-256
- Snapshot immutable و تشخیص تعارض
- Verify/restore در فضای ایزوله؛ `production_mutated=false`
- سناریوهای duplicate delivery، crash before commit، crash after commit before ack
- lease expiry takeover، provider timeout/backoff، database reconnect و restore checksum
- RPO/RTO شبیه‌سازی‌شده برحسب event/step، نه ادعای زمان واقعی
- Run ID و Request hash برای Idempotency
- `network_called=false` و `order_routing_enabled=false`

## Schema v12
```text
paper_recovery_snapshots
paper_chaos_runs
```

## API
```text
POST /api/v1/paper/recovery/snapshots
GET  /api/v1/paper/recovery/snapshots/{snapshot_id}/verify
POST /api/v1/paper/chaos/run
```

Chaos endpoint در Production با `PAPER_CHAOS_ENABLED=false` مسدود است. فایل `render.staging.yaml` سرویس و PostgreSQL مستقل با Feed/AI/Live خاموش تعریف می‌کند.

## محدودیت‌ها
- RPO/RTO این فاز شبیه‌سازی قطعی است، نه اندازه‌گیری شبکه چندمنطقه‌ای.
- ایجاد منابع واقعی Staging نیازمند OAuth و ظرفیت حساب Render است.
- Restore تولید انجام نمی‌شود.
- `ENABLE_LIVE_EXECUTION=false` و Testnet routing خاموش باقی می‌مانند.
- هیچ تضمین سود یا عملکرد آینده وجود ندارد.
