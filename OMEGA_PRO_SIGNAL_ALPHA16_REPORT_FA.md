# Signal Shadow Alpha 16 — Future Outcome Resolver

- Entry/SL/TP و resolution timeframe هنگام Capture ذخیره می‌شوند
- فقط کندل‌های timestamp بعد از captured_at پذیرفته می‌شوند
- Entry activation واقعی
- Stop-first در برخورد هم‌زمان SL/TP
- WIN / LOSS / EXPIRED_NO_ENTRY / PENDING
- Outcome دستی ممنوع؛ Resolver از MarketData server استفاده می‌کند
- حداقل ۳۰ Outcome resolved پیش از Research Ready
- order_routed=false و actionable_for_live=false
- Schema v17
