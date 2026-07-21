# گزارش Signal Research Alpha 29 — One-shot Final Holdout Consumption Preparation

## هدف

آماده‌سازی مصرف صریح، یک‌باره و ممیزی‌پذیر Final Holdout در Stage 3. این قابلیت روی Dataset فعلی اجرا نمی‌شود؛ فقط زیرساخت Fail-closed آن ساخته می‌شود.

## Schema v21

فیلدهای زیر به Forward Holdout Plan افزوده شدند:

```text
holdout_result_sha256
holdout_result_json
consumption_request_sha256
```

فیلدهای قبلی زیر نیز استفاده می‌شوند:

```text
holdout_dataset_sha256
holdout_member_ids_json
ready_at
consumed_at
```

## Preconditions

مصرف فقط وقتی مجاز است که:

1. Plan وجود داشته باشد؛
2. Plan برابر `READY` باشد؛
3. Membership قفل شده باشد؛
4. Holdout Dataset SHA موجود باشد؛
5. Acknowledgement دقیق ارسال شود:

```text
CONSUME_FINAL_HOLDOUT_ONCE
```

در غیر این صورت درخواست Fail-closed می‌شود.

## Integrity Re-verification

پیش از مصرف:

- Member ID JSON parse می‌شود؛
- تعداد Memberها باید دقیقاً برابر Required sample باشد؛
- Member IDها باید Unique باشند؛
- تمام Memberها باید بعد از Cutoff باشند؛
- تمام Memberها باید Activated terminal outcome باشند؛
- Evidence SHA هر Member دوباره بررسی می‌شود؛
- Realized R باید کامل باشد؛
- Canonical Holdout payload دوباره ساخته می‌شود؛
- SHA بازسازی‌شده باید با SHA قفل‌شده برابر باشد.

هر اختلاف باعث رد کامل Consumption می‌شود.

## One-shot Request Identity

```text
consumption_request_sha256 = SHA256(
  acknowledgement + plan_id + holdout_dataset_sha256 + policy_version
)
```

Result نیز به‌صورت Canonical JSON ذخیره و SHA می‌شود:

```text
holdout_result_sha256 = SHA256(holdout_result_json)
```

## Metrics

فقط برای اعضای قفل‌شده‌ی Holdout:

```text
activated_outcomes
wins
losses
expired_active
target_hit_rate_pct
wilson_95_lower_pct
wilson_95_upper_pct
average_realized_rr
median_realized_rr
cumulative_realized_rr
max_drawdown_rr
profit_factor_rr
max_consecutive_nonwins
bootstrap_average_rr_95_lower
bootstrap_average_rr_95_upper
bootstrap_block_length
bootstrap_replicates=2000
```

Bootstrap از Holdout Dataset SHA به‌عنوان Seed استفاده می‌کند.

## Idempotent Replay

درخواست اول:

```text
duplicate=false
consumed_at=<UTC timestamp>
```

درخواست‌های بعدی با همان Plan:

```text
duplicate=true
```

Result ذخیره‌شده بازگردانده می‌شود و Holdout دوباره محاسبه نمی‌شود.

اگر Result JSON پس از Persist تغییر کند، Replay با خطای Integrity رد می‌شود.

## APIها

```text
POST /api/v1/analysis/intraday-fusion/shadow/forward-holdout-plan/{plan_id}/consume
POST /api/v1/analysis/intraday-fusion/shadow/system-forward-holdout-plan/{plan_id}/consume
```

Request:

```json
{
  "acknowledgement": "CONSUME_FINAL_HOLDOUT_ONCE"
}
```

## Safety

```text
current_holdout_consumed=false
holdout_metrics_currently_exposed=false
threshold_change_authorized=false
live_authorized=false
order_routed=false
actionable_for_live=false
ENABLE_TESTNET_EXECUTION=false
ENABLE_LIVE_EXECUTION=false
```

حتی Result نهایی Holdout به‌تنهایی مجوز Live نیست و باید وارد Operational Promotion شود.
