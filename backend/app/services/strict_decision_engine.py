from __future__ import annotations

from typing import Any

from app.services.market_quality_engine import assess_data_quality, classify_market_regime


def _gate(name: str, passed: bool, actual: Any, required: str, hard: bool = True) -> dict:
    return {
        "name": name,
        "passed": bool(passed),
        "actual": actual,
        "required": required,
        "hard": hard,
    }


def apply_strict_decision(
    report: dict,
    candles: list[dict],
    market: str,
    timeframe: str,
    orderflow_source: str = "ohlcv_proxy",
    orderflow_confidence: float = 0.45,
) -> dict:
    """Apply capital-preservation gates without inventing confidence.

    This layer may downgrade an existing setup but never upgrades its raw
    confluence/probability. Actionable plans require every hard gate to pass.
    """
    quality = assess_data_quality(candles, timeframe, market)
    regime = classify_market_regime(candles)
    direction = report.get("direction", "neutral")
    grade = report.get("grade", "F")
    confluence = int(report.get("confluence") or 0)
    probability = int(report.get("probability") or 0)
    rr = float(report.get("rr") or 0)
    htf_bias = report.get("htf_bias")
    setup_type = str(report.get("setup_type") or "-")
    events = report.get("events") or []
    has_choch = any(item.get("kind") == "CHoCH" for item in events)
    reversal_setup = any(
        token in setup_type.lower()
        for token in ("تغییر ساختار", "لیکوئیدیتی", "mmxm", "sweep", "choch")
    )
    expected_htf = "bullish" if direction == "long" else "bearish" if direction == "short" else None
    htf_aligned = expected_htf is not None and htf_bias == expected_htf
    htf_exception = reversal_setup and has_choch and confluence >= 75
    high_timeframe = timeframe in ("4h", "1d")

    negative_factors = [
        item for item in (report.get("confluence_factors") or [])
        if float(item.get("points") or 0) < 0
    ]
    negative_points = abs(sum(float(item.get("points") or 0) for item in negative_factors))
    conflict_limit = 10.0 if grade in ("A+", "A") else 7.0

    gates = [
        _gate("data_quality", quality["score"] >= 78, quality["score"], ">=78"),
        _gate("data_integrity", quality["tradable"], quality["tradable"], "true"),
        _gate("direction", direction in ("long", "short"), direction, "long|short"),
        _gate("grade", grade in ("A+", "A", "B"), grade, "A+|A|B"),
        _gate("confluence", confluence >= 65, confluence, ">=65"),
        _gate("estimated_probability", probability >= 68, probability, ">=68"),
        _gate("risk_reward", rr >= 2.0, round(rr, 2), ">=2.0"),
        _gate("news_clear", not bool(report.get("news_blocked")), bool(report.get("news_blocked")), "false"),
        _gate(
            "htf_alignment",
            high_timeframe or htf_aligned or htf_exception,
            {"htf": htf_bias, "aligned": htf_aligned, "reversal_exception": htf_exception},
            "aligned or confirmed reversal",
        ),
        _gate("market_not_choppy", regime["name"] != "choppy" or confluence >= 78, regime["name"], "not choppy"),
        _gate("conflict_budget", negative_points <= conflict_limit, round(negative_points, 1), f"<={conflict_limit}"),
        _gate("trade_plan", bool(report.get("plan_lines")), len(report.get("plan_lines") or []), ">0"),
        _gate(
            "orderflow_evidence",
            orderflow_confidence >= 0.35,
            {"source": orderflow_source, "confidence": round(orderflow_confidence, 2)},
            ">=0.35",
            hard=False,
        ),
    ]
    failed_hard = [item for item in gates if item["hard"] and not item["passed"]]
    passed_hard = [item for item in gates if item["hard"] and item["passed"]]

    if not failed_hard:
        status = "actionable"
    elif (
        quality["score"] >= 65
        and direction in ("long", "short")
        and setup_type not in ("", "-")
        and confluence >= 35
    ):
        status = "watch"
    else:
        status = "reject"

    if status == "actionable":
        strong = grade in ("A+", "A") and confluence >= 75 and probability >= 75 and rr >= 2.2
        if direction == "long":
            action_label = "STRONG_LONG" if strong else "LONG"
        else:
            action_label = "STRONG_SHORT" if strong else "SHORT"
    elif status == "watch":
        action_label = "WATCH"
    else:
        action_label = "NO_TRADE"

    risk_tier = "normal"
    if regime["risk_multiplier"] < 0.7 or quality["score"] < 85 or negative_points > 5:
        risk_tier = "reduced"
    if status != "actionable":
        risk_tier = "blocked"

    failed_names = [item["name"] for item in failed_hard]
    decision = {
        "status": status,
        "side": direction if direction in ("long", "short") else "flat",
        "action_label": action_label,
        "strict_omega_compliant": status == "actionable",
        "risk_tier": risk_tier,
        "risk_multiplier": regime["risk_multiplier"] if status == "actionable" else 0.0,
        "data_quality": quality,
        "market_regime": regime,
        "orderflow": {
            "source": orderflow_source,
            "is_real": orderflow_source not in ("ohlcv_proxy", "forex_proxy"),
            "confidence": round(orderflow_confidence, 2),
        },
        "hard_gates_total": len([item for item in gates if item["hard"]]),
        "hard_gates_passed": len(passed_hard),
        "failed_gates": failed_names,
        "gates": gates,
        "negative_evidence_points": round(negative_points, 1),
        "probability_is_calibrated": False,
        "probability_label": "model_estimate_not_calibrated",
        "no_trade_reason": failed_names[0] if failed_names else None,
        "expires_after_bars": 3 if timeframe in ("1m", "5m") else 5 if timeframe in ("15m", "30m") else 8,
    }

    report["legacy_omega_compliant"] = bool(report.get("omega_compliant"))
    report["omega_compliant"] = status == "actionable"
    report["strict_omega_compliant"] = status == "actionable"
    report["action_label"] = action_label
    report["decision"] = decision
    report["data_quality"] = quality
    report["market_regime"] = regime
    report.setdefault("orderflow", {})["source"] = orderflow_source
    report["orderflow"]["is_real"] = decision["orderflow"]["is_real"]
    report["orderflow"]["confidence"] = decision["orderflow"]["confidence"]

    if status != "actionable":
        report["plan_lines"] = []
        overlay = dict(report.get("overlay") or {})
        overlay["lines"] = [
            item for item in (overlay.get("lines") or [])
            if item.get("kind") not in ("entry", "sl", "tp1", "tp2", "tp3")
        ]
        report["overlay"] = overlay

    ai = dict(report.get("ai") or {})
    ai["decision_status"] = status
    ai["decision_label"] = action_label
    ai["evidence"] = [
        item.get("name") for item in (report.get("confluence_factors") or [])
        if float(item.get("points") or 0) > 0
    ][:6]
    ai["risks"] = failed_names[:6] + [str(item.get("name")) for item in negative_factors[:3]]
    ai["what_would_confirm"] = failed_names[:5]
    ai["grounded"] = True
    ai["probability_is_calibrated"] = False
    report["ai"] = ai
    return report
