# گزارش Alpha 4 — Risk & Conservative Backtest

نسخه هدف: `3.0.0-alpha4`

## وضعیت

پیاده‌سازی کامل شده است. پذیرش انتشار منوط به سبز شدن Backend و Android GitHub CI روی همان Commit و مشاهده نسخه Alpha 4 در Render است.

## ۱) موتور ریسک پرتفوی

`backend/app/services/risk_engine.py` از محاسبه ساده حجم به یک Policy Engine قطعی ارتقا یافت.

Hard Gateها:

1. جهت غیرخنثی
2. هندسه صحیح Entry/SL
3. سقف زیان روزانه
4. سقف تعداد معاملات روزانه
5. سقف زیان‌های متوالی
6. سقف تعداد موقعیت‌های باز
7. سقف Drawdown
8. موجود بودن Spread اندازه‌گیری‌شده
9. سقف Spread
10. سقف Slippage
11. Open-Risk Budget
12. Portfolio Heat
13. Correlation Exposure
14. Effective Stop

خروجی شامل Base Risk، Adjusted Risk، Position Size، Effective Stop، Execution Cost، Heat، Open Risk، Correlated Risk، بودجه باقی‌مانده، ضرایب Drawdown/Volatility و فهرست Gateهای ردشده است.

### Drawdown

- تا `drawdown_reduction_start_pct`: ضریب ۱
- بین آستانه کاهش و سقف Drawdown: کاهش خطی و قطعی ریسک
- در `max_drawdown_pct`: Block کامل

### Correlation

- اگر Correlation صریح ارائه شود، همان مقدار با جهت موقعیت استفاده می‌شود.
- اگر موجود نباشد، فقط `structural_proxy` شفاف استفاده می‌شود.
- پروکسی ساختاری هرگز Correlation تاریخی یا کالیبره‌شده معرفی نمی‌شود.
- برای فارکس، هم‌پوشانی Exposure ارز پایه/مقابل محاسبه می‌شود؛ برای Crypto/Index/Metals از Bucket محافظه‌کارانه استفاده می‌شود.

### هزینه اجرا

- Spread اندازه‌گیری‌شده برای تأیید Strict الزامی است.
- Slippage می‌تواند صریح باشد یا با برچسب Policy Default محاسبه شود.
- Effective Stop شامل بافر Spread و Slippage است.
- نوسان شدید یا فشردگی غیرعادی می‌تواند ریسک را کاهش دهد.

## ۲) بک‌تست محافظه‌کارانه

Execution Model: `conservative_ohlc_v2`

اصول:

- سیگنال فقط از کندل‌های بسته‌شده پیش از زمان تصمیم ساخته می‌شود.
- معامله تا زمانی که قیمت Entry را لمس نکند وجود ندارد.
- Entry دارای Expiry برحسب تعداد کندل است.
- اگر SL و TP در یک کندل لمس شوند، نتیجه `stop_first` است.
- Gap منفی در Stop با Open بدتر محاسبه می‌شود.
- Gap مثبت در TP بهبود غیرواقعی دریافت نمی‌کند.
- معاملات هم‌پوشان به‌صورت پیش‌فرض ممنوع‌اند.
- معاملات بسته‌نشده به‌صورت پیش‌فرض Mark-to-Market می‌شوند.

### هزینه‌های بک‌تست

از نتیجه ناخالص کسر می‌شوند:

- Fee هر سمت
- Spread
- Slippage هر Fill
- Funding برحسب زمان نگهداری

گزارش هر معامله:

- Activated / No Entry
- Activation Time و Bars to Entry
- Exit Reason
- Gross R
- Costs R
- Fee R
- Funding R
- Net Realized R

گزارش کل:

- Activated Signals و No Entry
- Gross / Cost / Net R
- Profit Factor و Expectancy پس از هزینه
- Maximum Drawdown R
- مدل اجرا و فرضیات
- `anti_lookahead_enforced=true`

## ۳) Sweep و Walk-Forward

- Candidate بدون حداقل تعداد معاملات فعال‌شده وارد Ranking نمی‌شود.
- Ranking علاوه بر Net R و Expectancy، Drawdown و Sample Size را لحاظ می‌کند.
- Walk-Forward پارامتر را فقط از Training انتخاب می‌کند و روی Test خارج از نمونه ارزیابی می‌کند.

## ۴) تست‌ها

فایل جدید:

`backend/tests/test_alpha4_risk_backtest.py`

پوشش:

- Drawdown reduction/block
- Heat/Open-Risk block
- Explicit correlation
- Transparent structural proxy
- Hedge direction
- Unknown spread block
- Entry not activated
- Same-bar SL/TP stop-first
- Fees/Spread/Slippage/Funding
- Mark-to-market
- Closed-candle anti-look-ahead
- Overlap prevention
- Non-monotonic timestamp rejection

نتیجه محلی Backend:

```text
18 passed
```

## ۵) Android

- DTOهای Risk و Backtest با قرارداد Alpha 4 هماهنگ شدند.
- Risk UI اکنون Heat، Correlated Risk، Budget، Drawdown/Volatility Multipliers و Failed Gates را نمایش می‌دهد.
- Backtest UI اکنون Activated/No Entry، Gross/Cost/Net R، Fees/Funding، Drawdown، Exit Reason و Anti-Look-Ahead را نمایش می‌دهد.
- متن UI هیچ نتیجه مثبت بک‌تست را تضمین عملکرد آینده یا مجوز Live معرفی نمی‌کند.

## ۶) ایمنی

- `NO_TRADE` و Block پیش‌فرض در نبود Spread معتبر حفظ شده است.
- هیچ Correlation پروکسی به‌عنوان داده تاریخی واقعی معرفی نمی‌شود.
- بک‌تست احتمال موفقیت آینده یا سود را تضمین نمی‌کند.
- Live Execution همچنان خاموش است و هیچ Credential بروکر تغییر نکرده است.
