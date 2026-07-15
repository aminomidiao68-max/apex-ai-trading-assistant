# گزارش Paper Alpha 1 — Paper OMS & Execution Safety

نسخه هدف: `3.4.0-paper-alpha1`

## هدف

افزایش بلوغ Execution بدون ارسال هیچ سفارش واقعی. تمام سفارش‌ها فقط در Paper Ledger داخلی پردازش می‌شوند.

```text
live_routed=false
ENABLE_LIVE_EXECUTION=false
```

## Paper OMS

فایل:

`backend/app/services/paper_oms_service.py`

Stateها:

- accepted
- working
- partially_filled
- filled
- canceled
- rejected
- expired

Terminal stateها قابل بازگشت نیستند.

## PostgreSQL Schema v5

Tables:

- `paper_execution_controls`
- `paper_orders`
- `paper_fills`
- `paper_order_events`

تمام داده‌ها User-scoped هستند.

## Default Safety

برای هر کاربر:

```text
paper_trading_enabled=false
kill_switch_engaged=true
```

فعال‌سازی نیازمند acknowledgement دقیق است:

```text
I_UNDERSTAND_PAPER_ONLY
```

## Risk Gates

- Paper mode enabled
- Kill switch released
- Risk approved
- Signal score >= 75
- Max open orders
- Max order notional
- Positive quantity/prices
- Valid bid/ask
- Valid limit geometry

## Idempotency

- unique(user_id, idempotency_key)
- Request canonical SHA-256
- همان Key و همان Payload: همان Order برگردانده می‌شود.
- همان Key و Payload متفاوت: Conflict
- PostgreSQL Control row با `FOR UPDATE` قفل می‌شود.

## Fill Simulation

### Market

- Buy از Ask با adverse slippage
- Sell از Bid با adverse slippage
- Fee براساس Notional

### Limit

- Buy فقط وقتی Ask <= Limit
- Sell فقط وقتی Bid >= Limit
- Slippage هرگز Limit را بدتر نمی‌کند.

### Liquidity

- available quantity
- partial fill
- weighted average fill price
- accumulated fees

### Time in Force

- GTC
- IOC؛ partial fill سپس remainder cancel
- FOK؛ اگر Liquidity کافی نباشد بدون Fill cancel

## Concurrency

- PostgreSQL `FOR UPDATE` روی User control
- PostgreSQL `FOR UPDATE` روی Order هنگام Tick
- جلوگیری از double fill و race روی limits/idempotency

## Kill Switch

فعال‌کردن Kill Switch:

- تمام Accepted/Working/Partially-filled orderها را Cancel می‌کند.
- Event جداگانه ثبت می‌کند.
- Tick processing را متوقف می‌کند.

## Append-only Event Ledger

هر Event:

- UUID
- sequence
- event type
- from/to status
- reason
- payload hash
- timestamp

Payload حساس ذخیره نمی‌شود؛ فقط Hash ثبت می‌شود.

## Reconciliation

بررسی می‌کند:

- sum(fill quantity) == order filled quantity
- weighted average == order average
- sum(fees) == order fee total
- event sequence contiguous
- terminal status/timestamp consistency

هر ناسازگاری با Issue code گزارش می‌شود.

## API

```text
GET  /api/v1/paper/control
POST /api/v1/paper/control
POST /api/v1/paper/orders
GET  /api/v1/paper/orders
GET  /api/v1/paper/orders/{order_id}
POST /api/v1/paper/orders/{order_id}/cancel
POST /api/v1/paper/ticks
GET  /api/v1/paper/orders/{order_id}/reconcile
```

همه نیازمند Bearer Authentication هستند.

## Android Broker UI

- Paper mode status
- Kill switch status
- Live Routed = FALSE
- Arm/Kill/Disable controls
- Paper reference price
- Market/Limit selector
- Limit price
- Submit paper order
- Recent paper orders
- Fill/fee/status
- Cancel
- Reconcile

## تست‌ها

- default disabled/kill switch
- acknowledgement
- market conservative fill
- idempotent replay
- payload conflict
- limit partial fills
- IOC/FOK
- kill-switch cancellation
- risk/score/notional/open-order limits
- user isolation
- reconciliation corruption detection
- API auth/idempotency/reconcile
- PostgreSQL schema v5

نتیجه محلی:

```text
85 passed, 1 skipped
```

## محدودیت‌ها

- Tickها شبیه‌سازی‌شده‌اند و Exchange queue position واقعی نیست.
- Latency، maker priority و hidden liquidity مدل کامل ندارند.
- Paper success آینده Live را تضمین نمی‌کند.
- Broker reconciliation واقعی هنوز جداست.
- Live Execution خاموش است.
