# گزارش Robustness Alpha 1 — Market Baseline & CSCV/PBO

نسخه هدف: `3.1.0-robustness-alpha1`

## هدف

اندازه‌گیری دو ریسک مهم:

1. آیا Strategy روی همان پنجره‌ها از یک Market baseline بهتر است؟
2. آیا انتخاب بهترین Strategy از یک Panel نتیجه Backtest Overfitting است؟

این مرحله سودآوری آینده را ثابت نمی‌کند و Live Execution را مجاز نمی‌کند.

## Same-window Market Baseline

Stored Walk-forward برای هر Activated OOS trade یک Benchmark می‌سازد:

- Always-long buy-and-hold
- همان Strategy-conditioned time window
- Entry/holding horizon مشابه
- نرمال‌سازی با Stop Distance همان Setup
- خروجی در R قابل مقایسه

Benchmark return:

```text
(exit_close - strategy_entry) / abs(strategy_entry - strategy_stop)
```

محدودیت:

- این Benchmark به زمان‌هایی که Strategy سیگنال داده شرطی است.
- Full-period buy-and-hold نیست.
- Passive investable portfolio کامل نیست.
- Corporate actions/roll effects برای همه Instrumentها مدل نشده است.

## Strategy Panel

مدل‌ها:

- `StrategyReturnSeries`
- `StrategyPanelValidationRequest`
- `StrategyPanelValidationResponse`

Endpoint:

```text
POST /api/v1/research/strategy-panel/validate
```

نیازمند Bearer Authentication و Heavy Rate Limit است.

## CSCV

Combinatorially Symmetric Cross-validation:

1. Observationها به Blockهای زمانی پیوسته تقسیم می‌شوند.
2. Block count باید زوج باشد.
3. تمام ترکیب‌های نصف Blockها برای In-sample ساخته می‌شوند.
4. نیمه مکمل Out-of-sample است.
5. بهترین Strategy فقط با IS metric انتخاب می‌شود.
6. Rank همان Strategy در OOS اندازه‌گیری می‌شود.

Block count فعلی بین 4 و 12 است. برای 8 Block:

```text
C(8,4) = 70 combinations
```

## PBO

برای هر Split:

- OOS rank percentile Strategy منتخب محاسبه می‌شود.
- Percentile زیر یا مساوی Median به‌عنوان overfit event ثبت می‌شود.

```text
PBO = overfit_events / CSCV_combinations
```

Gateهای فعلی:

- PBO <= 0.20
- Median selected OOS rank >= 0.60
- Mean selected-strategy OOS metric > 0
- حداقل 5 Strategy
- حداقل 200 Observation
- حداقل 20 CSCV combination
- Dataset fingerprint
- Point-in-time
- Survivorship control
- Data Quality >= 90
- Strict timestamps

## Selection Metrics

- expectancy
- sharpe_like = mean / sample standard deviation

Sharpe-like در اینجا Annualized Sharpe یا Deflated Sharpe نیست و به‌عنوان آن معرفی نمی‌شود.

## Statusها

- `REJECT`: Dataset integrity کافی نیست.
- `INCONCLUSIVE`: Panel/Combination/Evidence کافی نیست.
- `HIGH_OVERFIT_RISK`: PBO یا OOS behavior ضعیف است.
- `ROBUSTNESS_CANDIDATE`: Gateهای Panel پاس شده‌اند؛ هنوز Final Holdout و Live Gate لازم است.

## Reproducibility

Fingerprint شامل:

- Panel ID/version
- Dataset manifest
- تمام Strategy return series
- timestamps
- block count
- selection metric
- method version

Random sampling استفاده نمی‌شود؛ CSCV deterministic است.

## تست‌های کلیدی

### Stable panel

Strategy برتر در همه Blockها برتر باقی می‌ماند:

- PBO = 0
- Median OOS Rank = 1
- Status = `ROBUSTNESS_CANDIDATE`

### Data-mined panel

هر Strategy فقط در Block مخصوص خودش Return بزرگ دارد و خارج آن ضعیف است:

- In-sample winner در OOS سقوط می‌کند.
- PBO بالا می‌رود.
- Status = `HIGH_OVERFIT_RISK`

### Contract tests

- Odd block count rejection
- Duplicate Strategy ID rejection
- Return-length mismatch rejection
- Untraceable dataset rejection
- Authenticated endpoint
- `actionable_for_live=false`

نتیجه کامل محلی:

```text
63 passed, 1 skipped
```

## محدودیت‌های صریح

- PBO فقط نسبت به Strategyهای همان Panel است.
- Strategy variantهای بسیار همبسته Diversity واقعی را کاهش می‌دهند.
- CSCV Final untouched holdout را جایگزین نمی‌کند.
- Low PBO آینده را تضمین نمی‌کند.
- Deflated Sharpe و full PBO probability model در مراحل بعد قابل توسعه‌اند.
- Live Execution خاموش است.
