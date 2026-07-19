# Signal Shadow Alpha 15

- ثبت user-scoped خروجی Fusion بدون سفارش
- Evidence JSON canonical و SHA-256
- NO_TRADE/WATCH بدون Outcome ساختگی
- ACTIONABLE_CANDIDATE با Outcome=PENDING
- حداقل ۳۰ Outcome resolved پیش از Research Ready
- precision_claimed=false
- actionable_for_live=false
- order_routed=false
- Schema v16: signal_shadow_observations

حل Outcome فقط با کندل‌های آینده و سیاست stop-first در فاز بعد انجام می‌شود؛ نتیجه آینده ساخته نمی‌شود.
