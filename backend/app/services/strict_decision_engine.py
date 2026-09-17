from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.precision_window import (
    DEFAULT_BAND,
    VOLATILITY_BANDS,
    atr_value,
    confirmation_close_ok,
    efficiency_ratio,
    in_killzone,
    in_volatility_band,
)

from app.services.market_quality_engine import assess_data_quality, classify_market_regime
from app.services.trade_cost_gate import evaluate as evaluate_trade_cost
from app.services.trade_cost_gate import project_plan as project_trade_plan


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
    orderflow_snapshot: dict | None = None,
    now_utc: datetime | None = None,
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
    htf_exception = False  # v3.25 WEEKLY-GRADE: reversal exception RETIRED
    high_timeframe = timeframe in ("4h", "1d")

    flow = orderflow_snapshot or report.get("orderflow") or {}
    orderflow_source = str(flow.get("source") or orderflow_source)
    orderflow_confidence = float(flow.get("confidence") or orderflow_confidence)
    orderflow_is_real = bool(flow.get("is_real"))
    flow_pressure = str(flow.get("pressure") or "neutral")
    flow_expected = "buy" if direction == "long" else "sell" if direction == "short" else None
    flow_aligned = flow_expected is not None and flow_pressure in (flow_expected, "neutral")
    spread_bps = flow.get("spread_bps")
    depth_imbalance = flow.get("depth_imbalance")
    funding_rate = flow.get("funding_rate")
    requires_real_flow = market == "crypto" and timeframe not in ("4h", "1d")
    depth_conflict = False
    if depth_imbalance is not None and flow_expected:
        depth_value = float(depth_imbalance)
        depth_conflict = (flow_expected == "buy" and depth_value < -0.12) or (
            flow_expected == "sell" and depth_value > 0.12
        )
    funding_crowded = False
    if funding_rate is not None and flow_expected:
        funding_value = float(funding_rate)
        funding_crowded = (flow_expected == "buy" and funding_value > 0.0005) or (
            flow_expected == "sell" and funding_value < -0.0005
        )  # v3.25 (was 0.0010)

    # v3.24: deterministic footprint/micro confirmation when REAL micro data exists
    micro = flow.get("micro") or report.get("microstructure") or {}
    footprint_is_real = bool(micro.get("is_real")) or bool((micro.get("order_flow") or {}).get("is_real"))
    try:
        _delta = float(micro.get("delta") if micro.get("delta") is not None
                       else (micro.get("order_flow") or {}).get("delta") or 0.0)
    except (TypeError, ValueError):
        _delta = 0.0
    try:
        _lti = float(micro.get("large_trade_imbalance") or 0.0)
    except (TypeError, ValueError):
        _lti = 0.0
    footprint_ok = True
    if footprint_is_real and direction in ("long", "short"):
        if direction == "long":
            footprint_ok = _delta > 0.0 and _lti > -0.10   # v3.25: AFFIRMATIVE delta
        else:
            footprint_ok = _delta < 0.0 and _lti < 0.10
    footprint_detail = {"is_real": footprint_is_real, "delta": round(_delta, 4),
                        "large_trade_imbalance": round(_lti, 4), "expected": flow_expected}

    positive_factors = [
        item for item in (report.get("confluence_factors") or [])
        if float(item.get("points") or 0) > 0
    ]
    negative_factors = [
        item for item in (report.get("confluence_factors") or [])
        if float(item.get("points") or 0) < 0
    ]
    negative_points = abs(sum(float(item.get("points") or 0) for item in negative_factors))
    conflict_limit = 0.0  # v3.26 ZERO-ERROR: ANY negative evidence vetoes

    # v3.20 trade-cost/geometry gate: a plan whose round-trip fee exceeds 0.30R
    # or whose stop sits inside the ATR noise band is untradeable regardless of
    # direction quality. Audit 2026-09-16 measured this geometry turning -1R
    # stop-losses into -2..-5R post-fee losses on real OKX data.
    cost = evaluate_trade_cost(
        (report.get("levels") or {}).get("entry"),
        (report.get("levels") or {}).get("sl"),
        report.get("tp1") or (report.get("levels") or {}).get("tp"),
        direction,
        atr=report.get("atr"),
    )
    cost_projection = None
    if cost["applicable"] and not cost["passed"]:
        # v3.22: compute what a rescue WOULD look like (protective stop widened
        # to the cost/noise floor) — informational only. Measured on real OKX
        # walk-forwards, projected-rescue trades added no expectancy (PRIME:
        # 0/625 rescuable; pack: near-breakeven on 2 windows, negative on 2),
        # so the hard gate still rejects on original geometry and the
        # projection explains WHY the plan is untradable, in Persian.
        cost_projection = project_trade_plan(
            (report.get("levels") or {}).get("entry"),
            (report.get("levels") or {}).get("sl"),
            report.get("tp1") or (report.get("levels") or {}).get("tp"),
            direction,
            atr=report.get("atr"),
        )
        cost["projection"] = cost_projection

    _conf_close = confirmation_close_ok(candles, direction)
    _er = efficiency_ratio(candles)
    _vol_ok, _vol_atr = in_volatility_band(candles, market)
    _now = now_utc or datetime.now(timezone.utc)
    _atr = float(report.get("atr") or 0.0) or atr_value(candles)
    _entry = (report.get("levels") or {}).get("entry")
    _tp1 = report.get("tp1") or (report.get("levels") or {}).get("tp")
    if direction in ("long", "short") and _entry is not None and _tp1 is not None and _atr > 0:
        _reach = abs(float(_tp1) - float(_entry)) <= 3.0 * _atr
        _reach_actual = round(abs(float(_tp1) - float(_entry)) / _atr, 2)
    else:
        _reach, _reach_actual = True, "n/a"

    gates = [
        _gate("data_quality", quality["score"] >= 92, quality["score"], ">=92"),
        _gate("data_integrity", quality["tradable"], quality["tradable"], "true"),
        _gate("direction", direction in ("long", "short"), direction, "long|short"),
        _gate("grade", grade == "A+", grade, "A+ only (v3.25)"),
        _gate("confluence", confluence >= 85, confluence, ">=85"),
        _gate("estimated_probability", probability >= 88, probability, ">=88"),
        _gate("risk_reward", rr >= 3.5, round(rr, 2), ">=3.5"),
        _gate(
            "trade_cost",
            (not cost["applicable"]) or cost["passed"],
            {
                "fee_r": cost["fee_r"], "risk_pct": cost["risk_pct"], "net_rr": cost["net_rr"],
                "rescue_possible": bool(cost_projection and cost_projection.get("viable")),
                "rescue_reason_fa": cost["reasons_fa"] + (
                    (cost_projection or {}).get("reasons_fa")
                    if (cost_projection or {}).get("projected") else []
                ),
            },
            "fee<=0.30R, stop>=0.35×ATR, netRR>=1.5",
        ),
        _gate("news_clear", not bool(report.get("news_blocked")), bool(report.get("news_blocked")), "false"),
        _gate(
            "htf_alignment",
            high_timeframe or htf_aligned,
            {"htf": htf_bias, "aligned": htf_aligned, "reversal_exception": False},
            "aligned (exception retired in v3.25)",
        ),
        _gate("market_not_choppy", regime["name"] in ("trending", "balanced", "compressed"), regime["name"], "trending|balanced|compressed (v3.25)"),
        _gate("conflict_budget", negative_points <= conflict_limit, round(negative_points, 1), f"<={conflict_limit}"),
        _gate("trade_plan", bool(report.get("plan_lines")), len(report.get("plan_lines") or []), ">0"),
        _gate(
            "invalidation",
            report.get("invalidation") is not None or (report.get("levels") or {}).get("sl") is not None,
            report.get("invalidation") if report.get("invalidation") is not None else (report.get("levels") or {}).get("sl"),
            "explicit deterministic invalidation",
        ),
        _gate(
            "real_orderflow_available",
            not requires_real_flow or orderflow_is_real,
            {"required": requires_real_flow, "source": orderflow_source, "is_real": orderflow_is_real},
            "real exchange flow for crypto <=1h",
        ),
        _gate(
            "orderflow_alignment",
            not orderflow_is_real or flow_pressure == flow_expected,
            {"pressure": flow_pressure, "expected": flow_expected},
            "exact pressure match (neutral retired in v3.25)",
            hard=orderflow_is_real,
        ),
        _gate(
            "execution_spread",
            not orderflow_is_real or (spread_bps is not None and float(spread_bps) <= 3.0),
            spread_bps,
            "<=3 bps (v3.25)",
            hard=orderflow_is_real,
        ),
        _gate(
            "depth_conflict",
            not orderflow_is_real or not depth_conflict,
            depth_imbalance,
            "no strong opposing imbalance",
            hard=orderflow_is_real,
        ),
        _gate(
            "funding_crowding",
            not funding_crowded,
            funding_rate,
            "not crowded (|funding|<=0.0005 against side)",
        ),
        _gate(
            "orderflow_evidence",
            orderflow_confidence >= (0.60 if requires_real_flow else 0.40),
            {"source": orderflow_source, "confidence": round(orderflow_confidence, 2)},
            ">=0.60 real-flow / >=0.40 proxy (v3.25)",
            hard=requires_real_flow,
        ),
        _gate(
            "mtf_alignment",
            bool(report.get("mtf_aligned")),
            {"mtf_aligned": report.get("mtf_aligned"), "htf_exception": False},
            "MTF aligned (exception retired in v3.25)",
        ),
        _gate(
            "footprint_confirmation",
            footprint_ok,
            footprint_detail,
            "delta/large-flow AFFIRMATIVE in trade direction",
            hard=footprint_is_real,
        ),
        _gate(
            "session_killzone",
            in_killzone(_now),
            _now.strftime("%H:%M UTC %a"),
            "London AM 07-10 or London/NY overlap 12-16 UTC",
        ),
        _gate(
            "confirmation_close",
            _conf_close[0],
            _conf_close[1],
            "last closed candle decisive in trade direction",
        ),
        _gate(
            "trend_efficiency",
            _er >= 0.30,
            round(_er, 3),
            ">=0.30 Kaufman ER(100) (v3.26)",
        ),
        _gate(
            "volatility_band",
            _vol_ok,
            round(_vol_atr, 5),
            f"ATR% within {VOLATILITY_BANDS.get(str(market).lower(), DEFAULT_BAND)}",
        ),
        _gate(
            "evidence_diversity",
            len(positive_factors) >= 4,
            len(positive_factors),
            ">=4 independent positive evidence factors (v3.26)",
        ),
        _gate(
            "target_reachability",
            _reach,
            _reach_actual,
            "tp1 within 3.0x ATR (v3.26)",
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
        strong = grade == "A+" and confluence >= 88 and probability >= 88 and rr >= 3.5
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
            "is_real": orderflow_is_real,
            "confidence": round(orderflow_confidence, 2),
            "pressure": flow_pressure,
            "aligned": flow_aligned,
            "spread_bps": spread_bps,
            "depth_imbalance": depth_imbalance,
            "funding_rate": funding_rate,
            "open_interest_change_pct": flow.get("open_interest_change_pct"),
            # Informational passthrough of real microstructure (L2/footprint/VP);
            # read-only facts, never used to override the deterministic gates.
            "micro": flow.get("micro"),
        },
        "hard_gates_total": len([item for item in gates if item["hard"]]),
        "hard_gates_passed": len(passed_hard),
        "failed_gates": failed_names,
        "trade_cost": cost,
        "exit_management": {
            "model": "scale_50pct_at_1r_then_breakeven",
            "instruction_fa": (
                "مدیریت خروج توصیه‌شده (v3.21، همان مدل بک‌تست): ۵۰٪ حجم در +1R سیو شود و "
                "استاپ باقی‌مانده به نقطه ورود (ریسک‌فری) منتقل شود؛ باقی تا هدف اصلی. "
                "این مدیریت، معاملاتِ +1R-بازگشتی را از ضرر کامل به برد کوچک تبدیل می‌کند."
            ),
            "backtest_default": True,
        },
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
    ai["orderflow_evidence"] = {
        "source": orderflow_source,
        "is_real": orderflow_is_real,
        "confidence": round(orderflow_confidence, 2),
        "pressure": flow_pressure,
        "depth_imbalance": depth_imbalance,
        "spread_bps": spread_bps,
        "funding_rate": funding_rate,
    }
    ai["grounded"] = True
    ai["probability_is_calibrated"] = False
    report["ai"] = ai

    # The synchronous decision path always receives a verified deterministic
    # explanation. Optional external providers are invoked only by the async
    # explainability service and can never modify this decision.
    try:
        from app.services.ai_explainability_service import (
            ai_explainability_service,
            build_evidence_request_from_report,
        )

        evidence_request = build_evidence_request_from_report(
            report,
            market=market,
            timeframe=timeframe,
            provider="deterministic",
            language="fa",
        )
        ai.update(ai_explainability_service.explain_embedded(evidence_request))
        report["ai"] = ai
    except Exception:
        # Explainability must fail closed without taking down the deterministic
        # market decision or exposing provider/internal errors.
        ai.update(
            {
                "mode": "refusal",
                "provider": "deterministic",
                "verified": True,
                "verifier_status": "refused_internal_contract",
                "grounded": False,
                "deterministic_core_preserved": True,
                "refusal_reason": "explainability_contract_unavailable",
            }
        )
        report["ai"] = ai
    return report
