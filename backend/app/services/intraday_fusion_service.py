from __future__ import annotations

from typing import Any

_REQUIRED = ("5m", "15m", "1h", "4h")


def _side(report: dict) -> str:
    decision = report.get("decision") or {}
    side = str(decision.get("side") or report.get("direction") or "flat")
    if side in {"long", "bullish", "buy"}:
        return "long"
    if side in {"short", "bearish", "sell"}:
        return "short"
    bias = str(report.get("bias") or "neutral")
    return "long" if bias == "bullish" else "short" if bias == "bearish" else "flat"


def _gate(name: str, passed: bool, actual: Any, required: str) -> dict:
    return {"name": name, "passed": bool(passed), "actual": actual, "required": required, "hard": True}


class IntradayFusionService:
    """Causal precision-first fusion. It can only downgrade frame decisions."""

    def fuse(self, symbol: str, market: str, frames: list[dict]) -> dict:
        by_tf = {str(item.get("timeframe")): item.get("report") or {} for item in frames}
        available = sorted(tf for tf in _REQUIRED if tf in by_tf)
        context = [by_tf.get("1h", {}), by_tf.get("4h", {})]
        triggers = [by_tf.get("5m", {}), by_tf.get("15m", {})]
        context_sides = [_side(item) for item in context]
        trigger_sides = [_side(item) for item in triggers]
        actionable_triggers = [
            item for item in triggers if (item.get("decision") or {}).get("status") == "actionable"
        ]
        actionable_sides = [_side(item) for item in actionable_triggers]
        consensus_side = context_sides[0] if len(context_sides) == 2 and context_sides[0] == context_sides[1] else "flat"
        qualities = {
            tf: float(((by_tf.get(tf, {}).get("data_quality") or {}).get("score") or 0))
            for tf in _REQUIRED
        }
        freshness = {
            tf: dict(by_tf.get(tf, {}).get("frame_freshness") or {})
            for tf in _REQUIRED
        }
        freshness_ok = all(item.get("fresh") is True for item in freshness.values())
        opposing_trigger = consensus_side != "flat" and any(
            side not in {"flat", consensus_side} for side in trigger_sides
        )
        crypto_flow_ok = True
        flow_evidence = []
        for tf in ("5m", "15m"):
            flow = (by_tf.get(tf, {}).get("decision") or {}).get("orderflow") or by_tf.get(tf, {}).get("orderflow") or {}
            is_real = bool(flow.get("is_real"))
            pressure = str(flow.get("pressure") or "neutral")
            aligned = pressure in {"neutral", "buy" if consensus_side == "long" else "sell"}
            if market == "crypto" and ((by_tf.get(tf, {}).get("decision") or {}).get("status") == "actionable"):
                crypto_flow_ok = crypto_flow_ok and is_real and aligned
            flow_evidence.append({"timeframe": tf, "is_real": is_real, "pressure": pressure, "aligned": aligned})
        context_regimes = [str((item.get("market_regime") or {}).get("name") or "unknown") for item in context]
        regime_ok = all(name not in {"choppy", "volatile", "insufficient_data"} for name in context_regimes)
        invalidations = [item.get("invalidation") or (item.get("levels") or {}).get("sl") for item in actionable_triggers]
        invalidation_ok = bool(actionable_triggers) and all(value is not None for value in invalidations)
        gates = [
            _gate("all_frames_available", len(available) == 4, available, list(_REQUIRED)),
            _gate("context_consensus", consensus_side in {"long", "short"}, context_sides, "1h and 4h aligned"),
            _gate("trigger_actionable", bool(actionable_triggers), actionable_sides, ">=1 strict actionable trigger"),
            _gate("trigger_matches_context", bool(actionable_sides) and all(side == consensus_side for side in actionable_sides), actionable_sides, consensus_side),
            _gate("no_opposing_trigger", not opposing_trigger, trigger_sides, "no opposing 5m/15m evidence"),
            _gate("frame_data_quality", all(qualities[tf] >= 78 for tf in _REQUIRED), qualities, ">=78 each frame"),
            _gate("frame_freshness", freshness_ok, freshness, "latest completed bar within 2.5x timeframe"),
            _gate("context_regime", regime_ok, context_regimes, "not choppy/volatile/insufficient"),
            _gate("crypto_real_flow", crypto_flow_ok, flow_evidence, "real aligned flow for actionable crypto triggers"),
            _gate("explicit_invalidation", invalidation_ok, invalidations, "every actionable trigger has invalidation"),
        ]
        failed = [item["name"] for item in gates if not item["passed"]]
        if not failed:
            status = "ACTIONABLE_CANDIDATE"
            action = "LONG" if consensus_side == "long" else "SHORT"
        elif consensus_side in {"long", "short"} and not opposing_trigger and len(available) >= 3:
            status = "WATCH"
            action = "WATCH"
        else:
            status = "NO_TRADE"
            action = "NO_TRADE"
        best_trigger = max(
            actionable_triggers,
            key=lambda item: float(item.get("confluence") or 0),
            default=None,
        )
        best_trigger_tf = next(
            (tf for tf in ("5m", "15m") if by_tf.get(tf) is best_trigger),
            None,
        )
        resolution_levels = None
        if best_trigger and status == "ACTIONABLE_CANDIDATE":
            raw_levels = dict(best_trigger.get("levels") or {})
            # SMC keeps TP1 at report level while `levels.tp` is a farther
            # target. Preserve TP1 explicitly for a deterministic resolver.
            first_target = best_trigger.get("tp1")
            if first_target is None:
                first_target = raw_levels.get("tp1")
            if first_target is None:
                first_target = raw_levels.get("tp")
            resolution_levels = {
                "entry": raw_levels.get("entry"),
                "sl": raw_levels.get("sl"),
                "tp1": first_target,
                "tp": raw_levels.get("tp"),
            }
        return {
            "symbol": symbol.upper(),
            "market": market,
            "policy": "precision_first_intraday_v1",
            "status": status,
            "action_label": action,
            "side": consensus_side if status == "ACTIONABLE_CANDIDATE" else "flat",
            "failed_gates": failed,
            "gates": gates,
            "frames": [
                {
                    "timeframe": tf,
                    "side": _side(by_tf.get(tf, {})),
                    "status": (by_tf.get(tf, {}).get("decision") or {}).get("status", "missing"),
                    "quality": qualities[tf],
                    "fresh": freshness[tf].get("fresh") is True,
                    "age_seconds": freshness[tf].get("age_seconds"),
                    "regime": (by_tf.get(tf, {}).get("market_regime") or {}).get("name"),
                }
                for tf in _REQUIRED
            ],
            "orderflow_evidence": flow_evidence,
            "invalidation": best_trigger.get("invalidation") if best_trigger else None,
            "levels": resolution_levels,
            "resolution_timeframe": best_trigger_tf if status == "ACTIONABLE_CANDIDATE" else None,
            "max_resolution_bars": 12,
            "probability_is_calibrated": False,
            "probability_label": "model_estimate_not_calibrated",
            "ai_override_allowed": False,
            "live_authorized": False,
            "actionable_for_live": False,
        }
