# گزارش APEX Omega Pro — Paper Alpha 4

## هدف

افزودن شبیه‌سازی محافظه‌کارانه Margin، Funding و Liquidation به Paper OMS، بدون فعال‌کردن هیچ مسیر اجرای زنده.

## قابلیت‌های این فاز

- Leverage در محدوده 1x تا سقف کنترل‌شده کاربر
- Isolated و Cross margin
- Initial margin و Maintenance margin
- Used margin، Free margin، Margin utilization و Margin level
- سقف Margin utilization قبل از پذیرش سفارش
- جلوگیری از تغییر ناسازگار Leverage/Margin mode هنگام افزایش همان پوزیشن
- آزادسازی نسبی Margin هنگام Partial close
- تخصیص مجدد Margin هنگام Direction flip
- Liquidation price تخمینی و شفاف
- Liquidation محافظه‌کارانه با Bid/Ask، Slippage و Liquidation fee
- Kill Switch خودکار و لغو سفارش‌های باز پس از Liquidation
- Funding settlement امضادار برای Long/Short
- Funding Event ID و Payload hash برای جلوگیری از ثبت تکراری
- دفتر Append-only رویدادهای Funding و Liquidation
- PostgreSQL Schema v8
- Android Margin dashboard و ورودی Leverage/Cross/Isolated

## مدل Margin

### Initial Margin

```text
initial_margin = abs(quantity × entry_price) / leverage
```

### Maintenance Margin

```text
maintenance_margin = abs(quantity × mark_price) × maintenance_margin_rate
```

### Equity و Free Margin

```text
equity = cash_balance + unrealized_pnl
free_margin = equity - used_margin
```

### Funding

```text
funding_amount = signed_quantity × mark_price × funding_rate
cash_balance = cash_balance - funding_amount
```

بنابراین در Funding rate مثبت، Long پرداخت می‌کند و Short دریافت می‌کند.

## Liquidation

- در Isolated، Equity همان پوزیشن با Maintenance margin و هزینه بستن مقایسه می‌شود.
- در Cross، Collateral مشترک با مجموع Maintenance requirement مقایسه می‌شود.
- خروج Long با Bid و خروج Short با Ask انجام می‌شود.
- Slippage و Liquidation fee به‌صورت محافظه‌کارانه اعمال می‌شوند.
- Liquidation باعث فعال‌شدن Kill Switch و خاموش‌شدن Feed خودکار می‌شود.
- هیچ Liquidation به Broker یا Exchange ارسال نمی‌شود.

## Schema v8

### ستون‌های جدید Control

- `max_leverage`
- `default_maintenance_margin_rate`
- `liquidation_fee_bps`
- `max_margin_utilization_pct`

### ستون‌های جدید Position

- `leverage`
- `margin_mode`
- `initial_margin`
- `maintenance_margin_rate`
- `liquidation_price`
- `accumulated_funding`
- `position_status`
- `liquidated_at`

### جدول جدید

```text
paper_margin_events
```

رویدادها در محدوده هر کاربر با `(user_id, event_id)` یکتا هستند.

## API

```text
POST /api/v1/paper/mark
POST /api/v1/paper/funding/settle
GET  /api/v1/paper/margin/events
GET  /api/v1/paper/portfolio
```

مسیر `paper/mark` حتی هنگام فعال بودن Kill Switch فقط Mark-to-Market و کنترل Liquidation را انجام می‌دهد و هیچ سفارش جدیدی Fill نمی‌کند.

## قرارداد صداقت

- نرخ Funding ورودی API کاربر، همیشه `is_real_rate=false` ثبت می‌شود.
- Liquidation price یک تخمین ساده‌شده Paper است، نه Tier واقعی صرافی.
- Insurance fund، ADL، Portfolio margin، Risk tierهای پویا و Bankruptcy price کامل هنوز مدل نشده‌اند.
- Cross margin مدل محافظه‌کارانه داخلی است و جایگزین موتور ریسک صرافی نیست.
- `live_routed=false` و `ENABLE_LIVE_EXECUTION=false` باقی می‌مانند.
- هیچ سود، دقت، Win Rate یا عملکرد آینده‌ای تضمین نمی‌شود.
