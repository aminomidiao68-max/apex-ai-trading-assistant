# گزارش Paper Alpha 2 — Portfolio Equity & Drawdown Ledger

نسخه: `3.4.0-paper-alpha2`

## قابلیت‌ها

- PostgreSQL schema v6
- `paper_accounts`
- `paper_positions`
- initial cash و cash balance
- signed position quantity
- weighted average entry
- position netting و direction flip
- realized PnL
- unrealized PnL
- fee ledger
- mark-to-market
- equity و peak equity
- daily start equity و daily drawdown
- automatic kill switch پس از عبور از max daily drawdown
- Android Equity/Unrealized/Daily-DD/Position UI

## Accounting Model

Paper account به‌صورت derivatives-style ledger کار می‌کند:

- Fill جدید هم‌جهت: average entry وزنی
- Fill خلاف جهت: close quantity و realized PnL
- Position flip: average entry جدید برابر fill price
- Fee بلافاصله از cash کم می‌شود.
- Equity = cash balance + unrealized PnL

## Safety

- Default cash: 100,000 paper units
- Default max daily drawdown: 3%
- عبور از Drawdown limit، Kill Switch را درگیر و سفارش‌های باز را لغو می‌کند.
- PostgreSQL row locks برای Order/Control
- Live routing همیشه false

## API

```text
GET /api/v1/paper/portfolio
```

Tick processing علاوه بر Orderها، Position mark و Drawdown را به‌روزرسانی می‌کند.

## تست

- long position creation
- mark-to-market unrealized profit/loss
- opposite-side close و realized PnL
- fees
- flat position
- auto drawdown kill switch
- portfolio API
- PostgreSQL schema v6

نتیجه:

```text
87 passed, 1 skipped
```

## محدودیت

این Accounting شبیه‌سازی است؛ Margin rules، liquidation tiers، exchange funding settlement و cross/isolated margin واقعی هنوز مرحله بعد هستند. Live Execution خاموش است.
