"""Honest edge layer (v3.31) — single source of truth for win-rate claims.

Problem this file fixes
-----------------------
The handbook/strategy tables shipped hardcoded marketing win rates
("۶۵٪ الی ۷۵٪") that CONTRADICTED the project's own walk-forward
measurements in ``strategy_pack_v2._EDGE_CALIBRATION`` (most setups are net
losing after fees, pf < 1). Those numbers were shown to users in chat, prompts
and setup cards, which is the single most harmful defect in the system.

Rules enforced here (no exceptions anywhere in the app):
1. A win rate may be shown ONLY if it was measured by the in-app honest
   backtest engine on real candles, with n >= EDGE_CALIBRATION_MIN_N.
2. Unmeasured setups report "اندازه‌گیری‌نشده" — never an invented range.
3. A setup whose measured profit factor is <= 1.0 is marked NOT tradeable
   (``tradeable=False``); the decision engine blocks it from actionable plans.
4. Nothing in this module invents, smooths or rounds up a number.
"""

from __future__ import annotations

from typing import Any

from app.services.strategy_pack_v2 import (
    EDGE_CALIBRATION_MIN_N,
    EDGE_CALIBRATION_SOURCE,
    _EDGE_CALIBRATION,
)

UNMEASURED_FA = "اندازه‌گیری‌نشده (بدون بک‌تست معتبر — فقط آموزشی)"
MIN_TRADEABLE_PF = 1.0

# Handbook strategy id (1-30) -> measured detector key in _EDGE_CALIBRATION.
# None means: this school/pattern has no honest measurement in this codebase.
HANDBOOK_TO_DETECTOR: dict[int, str | None] = {
    1: "turtle_breakout",
    2: "engulfing_level",
    3: "head_shoulders",
    4: None,
    5: "ob_retest",
    6: "fvg_tap",
    7: "liquidity_sweep",
    8: "ob_retest",
    9: "ob_retest",
    10: None,
    11: None,
    12: "wyckoff_spring",
    13: "ema_pullback",
    14: "three_drives",
    15: "nr7_breakout",
    16: None,
    17: "orb",
    18: "judas_swing",
    19: None,
    20: None,
    21: "silver_bullet",
    22: "liquidity_sweep",
    23: "ob_retest",
    24: "fvg_tap",
    25: "judas_swing",
    26: "wyckoff_spring",
    27: "wyckoff_upthrust",
    28: None,
    29: None,
    30: "fvg_tap",
}

# Free-text setup keywords -> detector key, for call sites that only have a
# setup string (AI vision output, live scanner labels).
KEYWORD_TO_DETECTOR: list[tuple[str, str]] = [
    ("SILVER", "silver_bullet"),
    ("JUDAS", "judas_swing"),
    ("SPRING", "wyckoff_spring"),
    ("UPTHRUST", "wyckoff_upthrust"),
    ("UTAD", "wyckoff_upthrust"),
    ("SOS", "wyckoff_sos"),
    ("SWEEP", "liquidity_sweep"),
    ("LIQUID", "liquidity_sweep"),
    ("EQH", "eqh_eql_raid"),
    ("EQL", "eqh_eql_raid"),
    ("FVG", "fvg_tap"),
    ("IMBALANCE", "fvg_tap"),
    ("GAP", "fvg_tap"),
    ("ORDER BLOCK", "ob_retest"),
    ("ORDERBLOCK", "ob_retest"),
    ("OB", "ob_retest"),
    ("BREAKER", "ob_retest"),
    ("TRIANGLE", "triangle_break"),
    ("HEAD", "head_shoulders"),
    ("DOUBLE TOP", "double_top"),
    ("DOUBLE BOTTOM", "double_bottom"),
    ("ENGULF", "engulfing_level"),
    ("INSIDE", "inside_bar"),
    ("HIKKAKE", "hikkake"),
    ("VWAP", "vwap_bounce"),
    ("ICHIMOKU", "ichimoku_system"),
    ("EMA", "ema_pullback"),
    ("NR7", "nr7_breakout"),
    ("NR4", "nr7_breakout"),
    ("ORB", "orb"),
    ("OPENING RANGE", "orb"),
    ("ASIAN", "asian_sweep"),
    ("PIVOT", "pivot_reject"),
    ("RSI", "rsi2_reversion"),
    ("DIVERG", "three_drives"),
    ("TURTLE", "turtle_breakout"),
    ("BREAKOUT", "turtle_breakout"),
]


def _pct_fa(value: float) -> str:
    digits = str(int(round(value * 100)))
    table = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    return f"{digits.translate(table)}٪"


def measured_stats(detector_key: str | None) -> dict[str, Any] | None:
    """Return the measured stats for a detector, or None when unmeasured."""
    if not detector_key:
        return None
    cal = _EDGE_CALIBRATION.get(detector_key)
    if not cal:
        return None
    n = int(cal.get("n") or 0)
    if n < EDGE_CALIBRATION_MIN_N:
        return None
    pf = cal.get("pf")
    wr = cal.get("wr")
    avg_r = float(cal.get("avgR") or 0.0)
    return {
        "detector": detector_key,
        "n": n,
        "win_rate": None if wr is None else float(wr),
        "avg_r": avg_r,
        "profit_factor": None if pf is None else float(pf),
        "source": EDGE_CALIBRATION_SOURCE,
    }


def detector_for_setup(setup_type: str | None) -> str | None:
    """Best-effort detector key from a free-text setup label."""
    clean = str(setup_type or "").upper()
    if not clean:
        return None
    for token, key in KEYWORD_TO_DETECTOR:
        if token in clean:
            return key
    return None


def edge_verdict(detector_key: str | None) -> dict[str, Any]:
    """Honest verdict for a detector key. Never invents a number."""
    stats = measured_stats(detector_key)
    if stats is None:
        return {
            "measured": False,
            "tradeable": False,
            "win_rate_fa": UNMEASURED_FA,
            "stats": None,
            "verdict_fa": (
                "این ستاپ در همین پروژه با موتور بک‌تست صادق اندازه‌گیری نشده است؛ "
                "هیچ نرخ بردی برای آن گزارش نمی‌شود و مبنای ورود واقعی نیست."
            ),
        }
    pf = stats["profit_factor"]
    wr = stats["win_rate"]
    tradeable = pf is not None and pf > MIN_TRADEABLE_PF and stats["avg_r"] > 0
    wr_fa = UNMEASURED_FA if wr is None else _pct_fa(wr)
    if tradeable:
        verdict = (
            f"edge اندازه‌گیری‌شده مثبت است (pf={pf}، میانگین {stats['avg_r']}R، n={stats['n']}) — "
            "قابل معامله با مدیریت ریسک."
        )
    else:
        verdict = (
            f"edge اندازه‌گیری‌شده پس از کارمزد منفی/صفر است (pf={pf}، میانگین {stats['avg_r']}R، "
            f"n={stats['n']}) — فقط رصد و آموزش، ورود واقعی مجاز نیست."
        )
    return {
        "measured": True,
        "tradeable": bool(tradeable),
        "win_rate_fa": wr_fa,
        "stats": stats,
        "verdict_fa": verdict,
    }


def enrich_strategy(strategy: dict[str, Any], handbook_id: int | None = None) -> dict[str, Any]:
    """Replace any claimed win rate with the measured one (or an honest gap)."""
    out = dict(strategy)
    sid = handbook_id if handbook_id is not None else out.get("number")
    detector = HANDBOOK_TO_DETECTOR.get(int(sid)) if sid is not None else None
    if detector is None:
        detector = detector_for_setup(out.get("name"))
    verdict = edge_verdict(detector)
    claimed = out.pop("win_rate", None)
    if claimed is not None:
        # kept only for audit/diff purposes; never render this to users
        out["win_rate_claimed_unvalidated"] = claimed
    out["win_rate"] = verdict["win_rate_fa"]
    out["win_rate_is_measured"] = verdict["measured"]
    out["measured_edge"] = verdict["stats"]
    out["tradeable"] = verdict["tradeable"]
    out["edge_verdict_fa"] = verdict["verdict_fa"]
    return out


HONESTY_PROMPT_ADDON = """
================================═══════════════════════════════════════
⚖️ قانون صداقت آماری (v3.31) — غیرقابل نقض
================================═══════════════════════════════════════
- هرگز نرخ برد (win rate) یا احتمال موفقیت را از خودت نساز و از دانش عمومی نقل نکن.
- تنها نرخ بردی مجاز است که در فیلد measured_edge همین سیستم آمده باشد
  (اندازه‌گیری walk-forward روی کندل واقعی با کارمزد). اگر measured_edge خالی است،
  صریح بگو: «نرخ برد این ستاپ اندازه‌گیری نشده است».
- اگر tradeable=False است، حتماً هشدار بده که edge اندازه‌گیری‌شده این ستاپ منفی است
  و آن را به‌عنوان فرصت ورود معرفی نکن.
- عدد «احتمال» موتور، یک امتیاز داخلی کالیبره‌نشده است، نه احتمال آماری واقعی؛
  همیشه با همین برچسب معرفی شود.
- هیچ‌گاه سود تضمینی، «سیگنال تضمینی» یا وین‌ریت هدف تبلیغاتی ارائه نده.
================================═══════════════════════════════════════
"""
