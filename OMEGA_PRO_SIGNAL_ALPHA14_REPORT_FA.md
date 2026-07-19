# Signal Intelligence Alpha 14 — Precision-first Intraday Fusion

## سیاست
- Crypto + Forex/Gold
- Intraday 5m/15m با Context 1h/4h
- Default NO_TRADE
- هیچ Timeframe به‌تنهایی مجوز سیگنال نمی‌دهد

## Hard Gates
- حضور هر چهار Frame
- اجماع 1h و 4h
- حداقل یک Trigger strict-actionable
- Trigger هم‌جهت Context
- نبود Trigger مخالف
- Data quality >=78 در هر Frame
- Context regime غیر choppy/volatile
- Crypto actionable trigger فقط با Real aligned order flow
- Invalidation صریح

## صداقت
- Forex order flow همچنان Proxy و is_real=false
- Probability کالیبره معرفی نمی‌شود
- AI حق Override ندارد
- خروجی حداکثر ACTIONABLE_CANDIDATE است و مجوز Live نیست
