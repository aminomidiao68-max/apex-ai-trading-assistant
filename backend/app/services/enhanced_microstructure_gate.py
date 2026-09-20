"""Enhanced Microstructure Gates — v4.0

Deep integration of real microstructure data (L2, Footprint, Volume Profile,
Order Flow) into the strict decision engine as additional hard/soft gates.

These gates go far beyond the simple delta/large_trade_imbalance checks in the
existing strict_decision_engine. They analyze:

  1. Volume Profile shape (P/b/D/B/thin) — rejects trades in thin/choppy profiles
  2. Footprint POC migration — confirms directional momentum
  3. L2 wall proximity — validates stop placement relative to real liquidity walls
  4. Delta acceleration — confirms building momentum in trade direction
  5. Absorption at key levels — detects institutional absorption
  6. CVD divergence with price — detects exhaustion/reversal
  7. Volume profile value area position — price should be entering from edge of VA
  8. Unfinished auction detection — price pulled toward unfinished levels

All gates are deterministic, use ONLY real microstructure data, and are labeled
with `is_real` status. When microstructure is not real, gates pass-through (neutral).
"""
from __future__ import annotations

from typing import Any


def evaluate_enhanced_microstructure(
    micro: dict | None,
    direction: str,
    entry: float | None,
    sl: float | None,
    tp: float | None,
    atr: float = 0.0,
) -> dict:
    """Evaluate deep microstructure gates.

    Returns:
        gates: list of gate dicts (name, passed, actual, required, hard)
        all_passed: bool — all HARD gates passed
        score: float 0..1 — microstructure quality score
        summary_fa: str — Persian summary of microstructure alignment
    """
    gates: list[dict] = []
    score = 0.0
    max_score = 0.0

    if not micro or not micro.get("is_real"):
        # No real microstructure — all gates pass-through
        return {
            "gates": [],
            "all_passed": True,
            "score": 0.0,
            "summary_fa": "داده خردساختار واقعی موجود نیست — گیت‌های میکرو غیرفعال.",
            "is_real": False,
        }

    flow = micro.get("flow") or {}
    vp = micro.get("vp") or {}
    fp = micro.get("footprint") or {}
    l2 = micro.get("l2") or {}
    filters = micro.get("filters") or {}
    fp_summary = fp.get("summary") or {}

    is_long = direction == "long"
    is_short = direction == "short"

    # ─── Gate 1: Volume Profile Shape ──────────────────────────────────
    max_score += 1.0
    shape = str(vp.get("shape") or "")
    shape_note = str(vp.get("shape_note") or "")
    vp_ok = True
    vp_reason = ""

    if shape == "thin":
        vp_ok = False
        vp_reason = "پروفایل حجم نازک/ذره‌ای — نقدینگی واقعی کم است"
    elif is_long and shape == "P":
        vp_ok = False
        vp_reason = "پروفایل P (توزیع سقف) — ورود لانگ در توزیع خطرناک است"
    elif is_short and shape == "b":
        vp_ok = False
        vp_reason = "پروفایل b (انباشت کف) — ورود شورت در انباشت خطرناک است"
    elif shape in ("D",):
        vp_ok = False
        vp_reason = "پروفایل D (رنج متعادل) — جهت گیری نامشخص، ورود ریسک‌دار"
    elif shape in ("B",):
        # B shape = transition — acceptable but reduced confidence
        score += 0.5
        vp_reason = "پروفایل B (انتقال ساختار) — با احتیاط"
    elif is_long and shape == "b":
        score += 1.0
        vp_reason = "پروفایل b (روند نزولی/انباشت کف) — پولبک به POC برای لانگ"
    elif is_short and shape == "P":
        score += 1.0
        vp_reason = "پروفایل P (روند صعودی/توزیع سقف) — پولبک به POC برای شورت"
    else:
        score += 0.5
        vp_reason = "پروفایل متعادل"

    gates.append({
        "name": "vp_shape",
        "passed": vp_ok,
        "actual": {"shape": shape, "note": shape_note},
        "required": "not thin/D, not P for long, not b for short",
        "hard": True,
        "reason_fa": vp_reason,
    })

    # ─── Gate 2: Price vs Value Area ───────────────────────────────────
    max_score += 1.0
    poc = vp.get("poc")
    vah = vp.get("vah")
    val = vp.get("val")
    va_ok = True
    va_reason = ""

    if poc is not None and vah is not None and val is not None and entry:
        poc_f = float(poc)
        vah_f = float(vah)
        val_f = float(val)
        entry_f = float(entry)

        if is_long:
            if entry_f > vah_f:
                # Entering above VA — chasing
                va_ok = False
                va_reason = "ورود بالای VAH — قیمت از ناحیه ارزش خارج شده (chasing)"
            elif entry_f < val_f:
                # Below VA — discount entry, good for long
                score += 1.0
                va_reason = "ورود زیر VAL — ناحیه دیسکانت واقعی"
            elif val_f <= entry_f <= vah_f:
                # Inside VA — neutral
                score += 0.5
                va_reason = "ورود داخل ناحیه ارزش"
        elif is_short:
            if entry_f < val_f:
                va_ok = False
                va_reason = "ورود زیر VAL — قیمت از ناحیه ارزش خارج شده (chasing)"
            elif entry_f > vah_f:
                score += 1.0
                va_reason = "ورود بالای VAH — ناحیه پرمیوم واقعی"
            elif val_f <= entry_f <= vah_f:
                score += 0.5
                va_reason = "ورود داخل ناحیه ارزش"
    else:
        score += 0.5

    gates.append({
        "name": "vp_value_area_position",
        "passed": va_ok,
        "actual": {"poc": poc, "vah": vah, "val": val, "entry": entry},
        "required": "entering from VA edge, not chasing outside",
        "hard": True,
        "reason_fa": va_reason or "داده VA موجود نیست",
    })

    # ─── Gate 3: Footprint POC Migration ───────────────────────────────
    max_score += 1.0
    poc_migration = fp_summary.get("poc_migration")
    fp_poc_ok = True
    fp_poc_reason = ""

    if poc_migration:
        if is_long and poc_migration == "falling":
            fp_poc_ok = False
            fp_poc_reason = "مهاجرت POC نزولی — فشار فروش ادامه دارد"
        elif is_short and poc_migration == "rising":
            fp_poc_ok = False
            fp_poc_reason = "مهاجرت POC صعودی — فشار خرید ادامه دارد"
        elif is_long and poc_migration == "rising":
            score += 1.0
            fp_poc_reason = "مهاجرت POC صعودی — تایید فشار خرید"
        elif is_short and poc_migration == "falling":
            score += 1.0
            fp_poc_reason = "مهاجرت POC نزولی — تایید فشار فروش"
        elif poc_migration == "flat":
            score += 0.3
            fp_poc_reason = "مهاجرت POC خنثی"
    else:
        score += 0.3

    gates.append({
        "name": "footprint_poc_migration",
        "passed": fp_poc_ok,
        "actual": poc_migration,
        "required": "POC migration in trade direction (or flat)",
        "hard": False,  # Soft gate — POC migration is supplementary
        "reason_fa": fp_poc_reason or "داده مهاجرت POC موجود نیست",
    })

    # ─── Gate 4: Stacked Imbalance Bias ────────────────────────────────
    max_score += 1.0
    stacked_bias = str(fp_summary.get("stacked_bias") or "none")
    stacked_buy = int(fp.get("stacked_buy") or 0)
    stacked_sell = int(fp.get("stacked_sell") or 0)
    stacked_ok = True
    stacked_reason = ""

    if is_long:
        if stacked_bias == "sell" and stacked_sell >= 3:
            stacked_ok = False
            stacked_reason = f"ایمبالانس روی‌هم فروش قوی ({stacked_sell}) — خلاف جهت ورود"
        elif stacked_bias == "buy" and stacked_buy >= 3:
            score += 1.0
            stacked_reason = f"ایمبالانس روی‌هم خرید قوی ({stacked_buy}) — تایید جهت"
        elif stacked_buy >= 2:
            score += 0.5
            stacked_reason = f"ایمبالانس خرید متوسط ({stacked_buy})"
    elif is_short:
        if stacked_bias == "buy" and stacked_buy >= 3:
            stacked_ok = False
            stacked_reason = f"ایمبالانس روی‌هم خرید قوی ({stacked_buy}) — خلاف جهت ورود"
        elif stacked_bias == "sell" and stacked_sell >= 3:
            score += 1.0
            stacked_reason = f"ایمبالانس روی‌هم فروش قوی ({stacked_sell}) — تایید جهت"
        elif stacked_sell >= 2:
            score += 0.5
            stacked_reason = f"ایمبالانس فروش متوسط ({stacked_sell})"

    gates.append({
        "name": "footprint_stacked_bias",
        "passed": stacked_ok,
        "actual": {"bias": stacked_bias, "buy": stacked_buy, "sell": stacked_sell},
        "required": "no opposing stacked imbalance >= 3",
        "hard": True,
        "reason_fa": stacked_reason or "ایمبالانس خنثی",
    })

    # ─── Gate 5: L2 Wall Protection ────────────────────────────────────
    max_score += 1.0
    bid_wall = (l2.get("bid_wall") or {}).get("price") if isinstance(l2.get("bid_wall"), dict) else None
    ask_wall = (l2.get("ask_wall") or {}).get("price") if isinstance(l2.get("ask_wall"), dict) else None
    l2_ok = True
    l2_reason = ""

    if sl and atr > 0:
        sl_f = float(sl)
        if is_long and bid_wall:
            bw = float(bid_wall)
            # Wall should be near or below SL (provides support)
            if bw > 0 and bw >= sl_f * 0.995 and bw <= sl_f * 1.01:
                score += 1.0
                l2_reason = f"دیوار خرید در قیمت {bw:g} نزدیک استاپ — حمایت واقعی"
            elif bw > 0 and bw < sl_f:
                l2_ok = False
                l2_reason = f"دیوار خرید ({bw:g}) زیر استاپ است — استاپ در ناحیه خالی قرار دارد"
            else:
                score += 0.3
        elif is_short and ask_wall:
            aw = float(ask_wall)
            if aw > 0 and aw <= sl_f * 1.005 and aw >= sl_f * 0.99:
                score += 1.0
                l2_reason = f"دیوار فروش در قیمت {aw:g} نزدیک استاپ — مقاومت واقعی"
            elif aw > 0 and aw > sl_f:
                l2_ok = False
                l2_reason = f"دیوار فروش ({aw:g}) بالای استاپ است — استاپ در ناحیه خالی قرار دارد"
            else:
                score += 0.3
        else:
            score += 0.3
    else:
        score += 0.3

    gates.append({
        "name": "l2_wall_proximity",
        "passed": l2_ok,
        "actual": {"bid_wall": bid_wall, "ask_wall": ask_wall, "sl": sl},
        "required": "L2 wall near SL for support/resistance",
        "hard": False,  # Soft gate — wall may not always be present
        "reason_fa": l2_reason or "دیوار L2 قابل ارزیابی نیست",
    })

    # ─── Gate 6: Delta Trend Confirmation ───────────────────────────────
    max_score += 1.0
    delta_trend = fp_summary.get("delta_trend")
    delta_ok = True
    delta_reason = ""

    if delta_trend:
        if is_long and delta_trend == "accelerating_sell":
            delta_ok = False
            delta_reason = "روند دلتا شتاب‌گیر فروش — خلاف جهت ورود"
        elif is_short and delta_trend == "accelerating_buy":
            delta_ok = False
            delta_reason = "روند دلتا شتاب‌گیر خرید — خلاف جهت ورود"
        elif is_long and delta_trend == "accelerating_buy":
            score += 1.0
            delta_reason = "روند دلتا شتاب‌گیر خرید — تایید قوی"
        elif is_short and delta_trend == "accelerating_sell":
            score += 1.0
            delta_reason = "روند دلتا شتاب‌گیر فروش — تایید قوی"
        elif delta_trend == "mixed":
            score += 0.3
            delta_reason = "روند دلتا مختلط"
    else:
        score += 0.3

    gates.append({
        "name": "delta_trend",
        "passed": delta_ok,
        "actual": delta_trend,
        "required": "delta accelerating in trade direction (or mixed)",
        "hard": False,
        "reason_fa": delta_reason or "داده روند دلتا موجود نیست",
    })

    # ─── Gate 7: CVD Divergence ────────────────────────────────────────
    max_score += 1.0
    cvd_div = flow.get("cvd_divergence")
    cvd_ok = True
    cvd_reason = ""

    if cvd_div:
        if is_long and cvd_div == "bearish":
            # Price going up but CVD going down — bearish divergence
            # For a long entry, this is actually a REVERSAL signal — could be good
            # if we're entering after a sweep. But for continuation, it's bad.
            score += 0.5
            cvd_reason = "واگرایی نزولی CVD — ممکن است برگشت را تایید کند (با احتیاط)"
        elif is_short and cvd_div == "bullish":
            score += 0.5
            cvd_reason = "واگرایی صعودی CVD — ممکن است برگشت را تایید کند (با احتیاط)"
        elif is_long and cvd_div == "bullish":
            score += 1.0
            cvd_reason = "واگرایی صعودی CVD — تایید برگشت صعودی"
        elif is_short and cvd_div == "bearish":
            score += 1.0
            cvd_reason = "واگرایی نزولی CVD — تایید برگشت نزولی"
    else:
        score += 0.3

    gates.append({
        "name": "cvd_divergence_check",
        "passed": cvd_ok,
        "actual": cvd_div,
        "required": "no conflicting CVD divergence",
        "hard": False,
        "reason_fa": cvd_reason or "واگرایی CVD موجود نیست",
    })

    # ─── Gate 8: Absorption Detection ──────────────────────────────────
    max_score += 1.0
    absorption = flow.get("absorption")
    climax = flow.get("climax")
    abs_ok = True
    abs_reason = ""

    if climax:
        if is_long:
            # Climax in a long entry area could mean exhaustion of sellers — good for long
            score += 0.8
            abs_reason = "کلایمکس فروش — خستگی فروشندگان، ورود لانگ محتمل"
        elif is_short:
            abs_ok = False
            abs_reason = "کلایمکس — خستگی، احتمال برگشت قریب‌الوقوع"
    elif absorption:
        if is_long:
            score += 0.7
            abs_reason = "جذب سفارش — نهادها در حال خرید هستند"
        elif is_short:
            score += 0.7
            abs_reason = "جذب سفارش — نهادها در حال فروش هستند"
    else:
        score += 0.3

    gates.append({
        "name": "absorption_climax",
        "passed": abs_ok,
        "actual": {"absorption": absorption, "climax": climax},
        "required": "no climax against direction",
        "hard": True,
        "reason_fa": abs_reason or "جذب/کلایمکس قابل ارزیابی نیست",
    })

    # ─── Gate 9: Unfinished Auction ────────────────────────────────────
    max_score += 1.0
    unfinished_bias = fp_summary.get("unfinished_bias")
    unf_ok = True
    unf_reason = ""

    if unfinished_bias:
        if is_long and unfinished_bias == "up":
            score += 1.0
            unf_reason = "مزایده ناتمام صعودی — قیمت به سمت بالا کشیده می‌شود"
        elif is_short and unfinished_bias == "down":
            score += 1.0
            unf_reason = "مزایده ناتمام نزولی — قیمت به سمت پایین کشیده می‌شود"
        elif is_long and unfinished_bias == "down":
            unf_ok = False
            unf_reason = "مزایده ناتمام نزولی — خلاف جهت ورود"
        elif is_short and unfinished_bias == "up":
            unf_ok = False
            unf_reason = "مزایده ناتمام صعودی — خلاف جهت ورود"
    else:
        score += 0.3

    gates.append({
        "name": "unfinished_auction",
        "passed": unf_ok,
        "actual": unfinished_bias,
        "required": "unfinished auction pulling in trade direction",
        "hard": False,
        "reason_fa": unf_reason or "مزایده ناتمام قابل ارزیابی نیست",
    })

    # ─── Gate 10: Microstructure Filter Alignment ──────────────────────
    max_score += 1.0
    net_bias = str(filters.get("net_bias") or "neutral")
    filter_score = float(filters.get("score") or 0.0)
    filter_ok = True
    filter_reason = ""

    if is_long:
        if net_bias == "bearish" and filter_score < -0.3:
            filter_ok = False
            filter_reason = f"فیلتر خردساختار قویاً نزولی (score={filter_score:.2f}) — خلاف جهت"
        elif net_bias == "bullish":
            score += 1.0
            filter_reason = f"فیلتر خردساختار صعودی (score={filter_score:.2f}) — تایید"
        elif net_bias == "neutral":
            score += 0.3
            filter_reason = "فیلتر خردساختار خنثی"
    elif is_short:
        if net_bias == "bullish" and filter_score > 0.3:
            filter_ok = False
            filter_reason = f"فیلتر خردساختار قویاً صعودی (score={filter_score:.2f}) — خلاف جهت"
        elif net_bias == "bearish":
            score += 1.0
            filter_reason = f"فیلتر خردساختار نزولی (score={filter_score:.2f}) — تایید"
        elif net_bias == "neutral":
            score += 0.3
            filter_reason = "فیلتر خردساختار خنثی"

    gates.append({
        "name": "micro_filter_alignment",
        "passed": filter_ok,
        "actual": {"net_bias": net_bias, "score": filter_score},
        "required": "micro filter not strongly opposing",
        "hard": True,
        "reason_fa": filter_reason or "فیلتر قابل ارزیابی نیست",
    })

    # ─── Compute final score ───────────────────────────────────────────
    final_score = score / max_score if max_score > 0 else 0.0
    all_passed = all(g["passed"] for g in gates if g["hard"])

    # Build Persian summary
    passed_gates = [g for g in gates if g["passed"]]
    failed_gates = [g for g in gates if not g["passed"]]
    summary_parts = []
    if failed_gates:
        summary_parts.append(f"❌ {len(failed_gates)} گیت خردساختار رد شد: " + "، ".join(g["name"] for g in failed_gates))
    else:
        summary_parts.append(f"✅ تمام {len(gates)} گیت خردساختار عبور کردند")
    summary_parts.append(f"امتیاز خردساختار: {final_score:.1%}")
    # Add key reasons
    for g in gates:
        reason = g.get("reason_fa") or ""
        if reason and (not g["passed"] or g.get("hard")):
            summary_parts.append(f"• {g['name']}: {reason}")

    return {
        "gates": gates,
        "all_passed": all_passed,
        "score": round(final_score, 4),
        "summary_fa": "\n".join(summary_parts),
        "is_real": True,
        "hard_gates_total": len([g for g in gates if g["hard"]]),
        "hard_gates_passed": len([g for g in gates if g["hard"] and g["passed"]]),
        "failed_hard_gates": [g["name"] for g in gates if g["hard"] and not g["passed"]],
    }
