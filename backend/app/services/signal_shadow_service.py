from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from statistics import median
from uuid import uuid4

from app.config import settings
from app.models import (
    SignalShadowCaptureResponse,
    SignalShadowDiagnosticsResponse,
    SignalShadowPanelResponse,
    SignalShadowResearchBreakdown,
    SignalShadowResearchPanelResponse,
    SignalShadowResolutionResponse,
)
from app.services.database_service import DatabaseManager

_TERMINAL_OUTCOMES = {"WIN", "LOSS", "EXPIRED_NO_ENTRY", "EXPIRED_ACTIVE"}
_ACTIVATED_TERMINAL_OUTCOMES = {"WIN", "LOSS", "EXPIRED_ACTIVE"}
_RESOLUTION_POLICY = "future_only_stop_first_horizon_v2"


class SignalShadowError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class SignalShadowService:
    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    @staticmethod
    def _canonical(result: dict) -> tuple[str, str]:
        raw = json.dumps(result, sort_keys=True, separators=(",", ":"), default=str)
        return raw, hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    def _number(value) -> float | None:
        try:
            number = float(value) if value is not None else None
        except (TypeError, ValueError):
            return None
        if number is None or not math.isfinite(number):
            return None
        return number

    @staticmethod
    def _timestamp(value: str) -> float:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()

    @staticmethod
    def _timeframe_seconds(timeframe: str | None) -> int:
        value = str(timeframe or "").strip().lower()
        aliases = {"60m": "1h", "240m": "4h"}
        value = aliases.get(value, value)
        try:
            if value.endswith("m"):
                return int(value[:-1]) * 60
            if value.endswith("h"):
                return int(value[:-1]) * 3600
            if value.endswith("d"):
                return int(value[:-1]) * 86400
        except (TypeError, ValueError):
            pass
        raise SignalShadowError("shadow_resolution_timeframe_invalid")

    @classmethod
    def _completed_future_candles(
        cls,
        candles: list[dict],
        *,
        captured_at: str,
        timeframe: str,
    ) -> list[dict]:
        """Return unique, valid, completed candles strictly after capture.

        Provider candle timestamps are treated as bar-open timestamps. A bar is
        eligible only after its full timeframe has elapsed, which prevents an
        in-progress candle from becoming a label.
        """
        captured = cls._timestamp(captured_at)
        duration = cls._timeframe_seconds(timeframe)
        now = datetime.now(timezone.utc).timestamp()
        unique: dict[float, dict] = {}
        for item in candles:
            try:
                timestamp = float(item.get("t") or 0)
                if timestamp > 1e12:
                    timestamp /= 1000.0
                open_price = float(item["o"])
                high = float(item["h"])
                low = float(item["l"])
                close = float(item["c"])
            except (KeyError, TypeError, ValueError):
                continue
            values = (timestamp, open_price, high, low, close)
            if not all(math.isfinite(value) for value in values):
                continue
            if timestamp <= captured or timestamp + duration > now:
                continue
            if low > high or not (low <= open_price <= high and low <= close <= high):
                continue
            unique[timestamp] = {
                "t": timestamp,
                "o": open_price,
                "h": high,
                "l": low,
                "c": close,
                "v": cls._number(item.get("v")) or 0.0,
            }
        return [unique[key] for key in sorted(unique)]

    def capture(self, user_id: int, result: dict) -> SignalShadowCaptureResponse:
        raw, digest = self._canonical(result)
        observation_id = uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        status = str(result.get("status") or "NO_TRADE")
        if status not in {"NO_TRADE", "WATCH", "ACTIONABLE_CANDIDATE"}:
            raise SignalShadowError("fusion_status_invalid")
        side = str(result.get("side") or "flat")
        outcome = "PENDING" if status == "ACTIONABLE_CANDIDATE" else "NOT_APPLICABLE"
        levels = result.get("levels") or {}
        entry = self._number(levels.get("entry"))
        stop = self._number(levels.get("sl"))
        # Fusion now forwards TP1 explicitly. Keep compatibility with direct
        # SMC/legacy payloads without inventing a target value.
        target = self._number(levels.get("tp1"))
        if target is None:
            target = self._number(result.get("tp1"))
        if target is None:
            target = self._number(levels.get("tp"))
        resolution_tf = result.get("resolution_timeframe")
        try:
            max_bars = int(result.get("max_resolution_bars") or 12)
        except (TypeError, ValueError) as exc:
            raise SignalShadowError("candidate_resolution_contract_incomplete") from exc
        if outcome == "PENDING":
            if (
                entry is None
                or stop is None
                or target is None
                or not resolution_tf
                or side not in {"long", "short"}
                or not 1 <= max_bars <= 500
            ):
                raise SignalShadowError("candidate_resolution_contract_incomplete")
            self._timeframe_seconds(str(resolution_tf))
            geometry_valid = (
                stop < entry < target if side == "long" else target < entry < stop
            )
            if not geometry_valid or min(entry, stop, target) <= 0:
                raise SignalShadowError("candidate_resolution_geometry_invalid")
        with self.database.connection() as conn:
            conn.execute(
                """INSERT INTO signal_shadow_observations (
                    observation_id,user_id,symbol,market,fusion_status,side,evidence_sha256,
                    evidence_json,outcome_status,realized_rr,captured_at,resolved_at,
                    resolution_timeframe,entry_price,stop_price,target_price,max_resolution_bars,activated,
                    bars_observed,resolution_reason,resolution_close_price,resolution_policy
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    observation_id,
                    user_id,
                    str(result.get("symbol") or "UNKNOWN").upper(),
                    str(result.get("market") or "unknown"),
                    status,
                    side,
                    digest,
                    raw,
                    outcome,
                    None,
                    now,
                    None,
                    resolution_tf,
                    entry,
                    stop,
                    target,
                    max_bars,
                    0,
                    0,
                    None,
                    None,
                    _RESOLUTION_POLICY,
                ),
            )
            conn.commit()
        return SignalShadowCaptureResponse(
            observation_id=observation_id,
            symbol=str(result.get("symbol") or "UNKNOWN").upper(),
            market=str(result.get("market") or "unknown"),
            fusion_status=status,
            side=side,
            evidence_sha256=digest,
            outcome_status=outcome,
            resolution_timeframe=resolution_tf,
            entry_price=entry,
            stop_price=stop,
            target_price=target,
            order_routed=False,
            actionable_for_live=False,
            captured_at=now,
        )

    def should_capture(self, user_id: int, symbol: str, minimum_interval_seconds: int) -> bool:
        with self.database.connection() as conn:
            row = conn.execute(
                "SELECT MAX(captured_at) AS captured_at FROM signal_shadow_observations WHERE user_id=? AND symbol=?",
                (user_id, symbol.upper()),
            ).fetchone()
        if not row or not row["captured_at"]:
            return True
        age = datetime.now(timezone.utc).timestamp() - self._timestamp(row["captured_at"])
        return age >= max(60, minimum_interval_seconds)

    def pending_contexts(self, user_id: int, limit: int = 50) -> list[dict]:
        with self.database.connection() as conn:
            rows = conn.execute(
                "SELECT observation_id,symbol,market,resolution_timeframe,outcome_status "
                "FROM signal_shadow_observations WHERE user_id=? AND outcome_status='PENDING' "
                "ORDER BY captured_at LIMIT ?",
                (user_id, max(1, min(limit, 200))),
            ).fetchall()
        return [dict(row) for row in rows]

    def resolution_context(self, user_id: int, observation_id: str) -> dict:
        with self.database.connection() as conn:
            row = conn.execute(
                "SELECT symbol,market,resolution_timeframe,outcome_status "
                "FROM signal_shadow_observations WHERE user_id=? AND observation_id=?",
                (user_id, observation_id),
            ).fetchone()
        if row is None:
            raise SignalShadowError("shadow_observation_not_found")
        return dict(row)

    def resolve(self, user_id: int, observation_id: str, candles: list[dict]) -> SignalShadowResolutionResponse:
        with self.database.connection() as conn:
            row = conn.execute(
                "SELECT * FROM signal_shadow_observations WHERE user_id=? AND observation_id=?",
                (user_id, observation_id),
            ).fetchone()
        if row is None:
            raise SignalShadowError("shadow_observation_not_found")
        if row["outcome_status"] == "NOT_APPLICABLE":
            raise SignalShadowError("shadow_outcome_not_applicable")
        if row["outcome_status"] in _TERMINAL_OUTCOMES:
            return SignalShadowResolutionResponse(
                observation_id=observation_id,
                outcome_status=row["outcome_status"],
                activated=bool(row["activated"]),
                bars_observed=int(row["bars_observed"] or 0),
                realized_rr=row["realized_rr"],
                resolution_reason=row["resolution_reason"],
                resolution_close_price=row["resolution_close_price"],
                resolution_policy=str(row["resolution_policy"] or _RESOLUTION_POLICY),
                resolved_at=row["resolved_at"],
            )

        future = self._completed_future_candles(
            candles,
            captured_at=row["captured_at"],
            timeframe=row["resolution_timeframe"],
        )
        max_bars = int(row["max_resolution_bars"])
        future = future[:max_bars]
        entry, stop, target = map(
            float,
            (row["entry_price"], row["stop_price"], row["target_price"]),
        )
        side = str(row["side"])
        activated = bool(row["activated"])
        outcome = "PENDING"
        reason = None
        realized_rr = None
        resolution_close = None
        for candle in future:
            high = float(candle["h"])
            low = float(candle["l"])
            if not activated and low <= entry <= high:
                activated = True
            if not activated:
                continue
            stop_hit = low <= stop if side == "long" else high >= stop
            target_hit = high >= target if side == "long" else low <= target
            if stop_hit:  # conservative stop-first when both occur in one bar
                outcome, reason, realized_rr = "LOSS", "stop_hit", -1.0
                resolution_close = stop
                break
            if target_hit:
                risk = abs(entry - stop)
                outcome, reason = "WIN", "target_hit"
                realized_rr = abs(target - entry) / risk if risk > 0 else 0.0
                resolution_close = target
                break
        if outcome == "PENDING" and len(future) >= max_bars:
            last_close = float(future[-1]["c"])
            resolution_close = last_close
            if not activated:
                outcome, reason, realized_rr = (
                    "EXPIRED_NO_ENTRY",
                    "entry_not_touched_before_horizon",
                    0.0,
                )
            else:
                risk = abs(entry - stop)
                raw_rr = (
                    (last_close - entry) / risk
                    if side == "long"
                    else (entry - last_close) / risk
                )
                target_rr = abs(target - entry) / risk
                outcome, reason = "EXPIRED_ACTIVE", "active_horizon_elapsed"
                realized_rr = max(-1.0, min(target_rr, raw_rr))
        if realized_rr is not None:
            realized_rr = round(float(realized_rr), 8)
        bars_observed = max(int(row["bars_observed"] or 0), len(future))
        resolved_at = datetime.now(timezone.utc).isoformat() if outcome != "PENDING" else None
        with self.database.connection() as conn:
            conn.execute(
                "UPDATE signal_shadow_observations SET outcome_status=?,realized_rr=?,activated=?,"
                "bars_observed=?,resolution_reason=?,resolution_close_price=?,resolution_policy=?,resolved_at=? "
                "WHERE user_id=? AND observation_id=?",
                (
                    outcome,
                    realized_rr,
                    int(activated),
                    bars_observed,
                    reason,
                    resolution_close,
                    _RESOLUTION_POLICY,
                    resolved_at,
                    user_id,
                    observation_id,
                ),
            )
            conn.commit()
        return SignalShadowResolutionResponse(
            observation_id=observation_id,
            outcome_status=outcome,
            activated=activated,
            bars_observed=bars_observed,
            realized_rr=realized_rr,
            resolution_reason=reason,
            resolution_close_price=resolution_close,
            resolution_policy=_RESOLUTION_POLICY,
            resolved_at=resolved_at,
        )

    def panel(self, user_id: int, minimum_required_resolved: int = 30) -> SignalShadowPanelResponse:
        with self.database.connection() as conn:
            rows = conn.execute(
                "SELECT fusion_status,outcome_status,activated "
                "FROM signal_shadow_observations WHERE user_id=?",
                (user_id,),
            ).fetchall()
        statuses = [str(row["fusion_status"]) for row in rows]
        pending = sum(1 for row in rows if row["outcome_status"] == "PENDING")
        resolved = sum(1 for row in rows if row["outcome_status"] in _TERMINAL_OUTCOMES)
        activated_resolved = sum(
            1
            for row in rows
            if row["outcome_status"] in _ACTIVATED_TERMINAL_OUTCOMES and bool(row["activated"])
        )
        research_ready = (
            resolved >= minimum_required_resolved
            and activated_resolved >= minimum_required_resolved
        )
        return SignalShadowPanelResponse(
            total_observations=len(rows),
            no_trade_count=statuses.count("NO_TRADE"),
            watch_count=statuses.count("WATCH"),
            candidate_count=statuses.count("ACTIONABLE_CANDIDATE"),
            pending_outcomes=pending,
            resolved_outcomes=resolved,
            activated_resolved_outcomes=activated_resolved,
            minimum_required_resolved=minimum_required_resolved,
            minimum_required_activated=minimum_required_resolved,
            status="RESEARCH_READY" if research_ready else "INSUFFICIENT_EVIDENCE",
            # This summary panel never claims precision; only the stricter
            # research panel may expose an empirical estimate after all gates.
            precision_claimed=False,
            actionable_for_live=False,
            live_execution_enabled=settings.enable_live_execution,
        )

    @staticmethod
    def _scarcity_review(
        *,
        candidate_count: int,
        valid_observations: int,
        span_days: float,
        integrity_failures: int,
        timestamps_complete: bool,
        minimum_observations: int,
        minimum_span_days: float,
    ) -> tuple[str, bool]:
        if candidate_count > 0:
            return "CANDIDATES_OBSERVED", False
        eligible = bool(
            integrity_failures == 0
            and timestamps_complete
            and valid_observations >= minimum_observations
            and span_days >= minimum_span_days
        )
        return (
            "ELIGIBLE_FOR_FEASIBILITY_AUDIT" if eligible else "COLLECTING_EVIDENCE",
            eligible,
        )

    def diagnostics(self, user_id: int) -> SignalShadowDiagnosticsResponse:
        """Aggregate immutable evidence without changing any decision threshold."""
        with self.database.connection() as conn:
            fetched = conn.execute(
                "SELECT fusion_status,outcome_status,evidence_sha256,evidence_json,captured_at "
                "FROM signal_shadow_observations WHERE user_id=? ORDER BY captured_at",
                (user_id,),
            ).fetchall()
        rows = [dict(row) for row in fetched]
        statuses = Counter(str(row.get("fusion_status") or "UNKNOWN") for row in rows)
        outcomes = Counter(str(row.get("outcome_status") or "UNKNOWN") for row in rows)
        gates: Counter[str] = Counter()
        regimes: Counter[str] = Counter()
        analyzed = integrity_failures = stale_observations = all_stale_observations = 0
        valid_non_all_stale_observations = 0
        valid_timestamps: list[tuple[float, str]] = []
        for row in rows:
            raw = str(row.get("evidence_json") or "")
            if hashlib.sha256(raw.encode()).hexdigest() != row.get("evidence_sha256"):
                integrity_failures += 1
                continue
            try:
                evidence = json.loads(raw)
            except (TypeError, ValueError, json.JSONDecodeError):
                integrity_failures += 1
                continue
            if not isinstance(evidence, dict):
                integrity_failures += 1
                continue
            analyzed += 1
            captured_at = str(row.get("captured_at") or "")
            try:
                valid_timestamps.append((self._timestamp(captured_at), captured_at))
            except (TypeError, ValueError):
                # Integrity covers immutable evidence. A malformed database
                # timestamp blocks only the span calculation, not gate counts.
                pass
            failed_gates = evidence.get("failed_gates") or []
            gates.update(str(item) for item in failed_gates if item)
            frames = [item for item in (evidence.get("frames") or []) if isinstance(item, dict)]
            freshness = [item.get("fresh") for item in frames if "fresh" in item]
            if freshness and any(value is False for value in freshness):
                stale_observations += 1
            all_frames_stale = bool(
                frames
                and len(freshness) == len(frames)
                and all(value is False for value in freshness)
            )
            if all_frames_stale:
                all_stale_observations += 1
            else:
                valid_non_all_stale_observations += 1
            for frame in frames:
                if str(frame.get("timeframe")) in {"1h", "4h"}:
                    regimes[str(frame.get("regime") or "unknown")] += 1
        leading = [
            name
            for name, _ in sorted(gates.items(), key=lambda item: (-item[1], item[0]))[:10]
        ]
        started_at = latest_at = None
        observation_span_days = 0.0
        if valid_timestamps:
            started_timestamp, started_at = min(valid_timestamps, key=lambda item: item[0])
            latest_timestamp, latest_at = max(valid_timestamps, key=lambda item: item[0])
            observation_span_days = max(0.0, (latest_timestamp - started_timestamp) / 86400.0)
        scarcity_min_observations = max(
            1000,
            settings.signal_shadow_scarcity_min_observations,
        )
        scarcity_min_span_days = max(
            5.0,
            settings.signal_shadow_scarcity_min_span_days,
        )
        scarcity_review_status, feasibility_audit_authorized = self._scarcity_review(
            candidate_count=int(statuses.get("ACTIONABLE_CANDIDATE", 0)),
            valid_observations=valid_non_all_stale_observations,
            span_days=observation_span_days,
            integrity_failures=integrity_failures,
            timestamps_complete=len(valid_timestamps) == analyzed,
            minimum_observations=scarcity_min_observations,
            minimum_span_days=scarcity_min_span_days,
        )
        return SignalShadowDiagnosticsResponse(
            total_observations=len(rows),
            observations_analyzed=analyzed,
            evidence_integrity_failures=integrity_failures,
            status_counts=dict(sorted(statuses.items())),
            outcome_counts=dict(sorted(outcomes.items())),
            failed_gate_counts=dict(sorted(gates.items())),
            context_regime_counts=dict(sorted(regimes.items())),
            stale_frame_observations=stale_observations,
            all_frames_stale_observations=all_stale_observations,
            leading_failed_gates=leading,
            collection_universe=list(dict.fromkeys(item.upper() for item in settings.signal_shadow_symbols)),
            collection_interval_seconds=max(300, settings.signal_shadow_interval_seconds),
            collector_max_concurrency=max(1, min(settings.signal_shadow_max_concurrency, 8)),
            universe_policy="pre_registered_data_quality_qualified",
            valid_non_all_stale_observations=valid_non_all_stale_observations,
            observation_started_at=started_at,
            observation_latest_at=latest_at,
            observation_span_days=round(observation_span_days, 6),
            scarcity_min_observations=scarcity_min_observations,
            scarcity_min_span_days=scarcity_min_span_days,
            scarcity_review_status=scarcity_review_status,
            feasibility_audit_authorized=feasibility_audit_authorized,
            candidate_rate_claimed=False,
            threshold_change_authorized=False,
            diagnostic_only=True,
            threshold_relaxation_allowed=False,
            precision_claimed=False,
            actionable_for_live=False,
            live_execution_enabled=settings.enable_live_execution,
        )

    @staticmethod
    def _wilson_95(wins: int, total: int) -> tuple[float, float]:
        if total <= 0:
            return 0.0, 0.0
        z = 1.959963984540054
        proportion = wins / total
        denominator = 1.0 + z * z / total
        centre = proportion + z * z / (2.0 * total)
        margin = z * math.sqrt((proportion * (1.0 - proportion) + z * z / (4.0 * total)) / total)
        return max(0.0, (centre - margin) / denominator), min(1.0, (centre + margin) / denominator)

    @staticmethod
    def _max_drawdown_rr(values: list[float]) -> float:
        equity = peak = 0.0
        maximum = 0.0
        for value in values:
            equity += value
            peak = max(peak, equity)
            maximum = max(maximum, peak - equity)
        return maximum

    @staticmethod
    def _context_regime(evidence: dict) -> str:
        regimes = [
            str(item.get("regime") or "unknown")
            for item in (evidence.get("frames") or [])
            if str(item.get("timeframe")) in {"1h", "4h"}
        ]
        if len(regimes) != 2:
            return "unknown"
        return regimes[0] if regimes[0] == regimes[1] else "mixed_context"

    def _breakdowns(
        self,
        terminal_rows: list[dict],
        *,
        overall_ready: bool,
        minimum_activated: int,
    ) -> list[SignalShadowResearchBreakdown]:
        grouped: dict[tuple[str, str], list[dict]] = {}
        for row in terminal_rows:
            evidence = row.get("_evidence") or {}
            values = {
                "market": str(row.get("market") or "unknown"),
                "symbol": str(row.get("symbol") or "UNKNOWN"),
                "context_regime": self._context_regime(evidence),
            }
            for group_type, group_value in values.items():
                grouped.setdefault((group_type, group_value), []).append(row)
        output = []
        for (group_type, group_value), rows in sorted(grouped.items()):
            active = [row for row in rows if row["outcome_status"] in _ACTIVATED_TERMINAL_OUTCOMES]
            wins = sum(1 for row in active if row["outcome_status"] == "WIN")
            sample_eligible = overall_ready and len(active) >= minimum_activated
            lower = upper = None
            rate = average_rr = None
            if sample_eligible:
                low_value, high_value = self._wilson_95(wins, len(active))
                rate = round(100.0 * wins / len(active), 4)
                lower = round(100.0 * low_value, 4)
                upper = round(100.0 * high_value, 4)
                average_rr = round(
                    sum(float(row["realized_rr"]) for row in active) / len(active),
                    6,
                )
            output.append(
                SignalShadowResearchBreakdown(
                    group_type=group_type,
                    group_value=group_value,
                    terminal_outcomes=len(rows),
                    activated_outcomes=len(active),
                    wins=wins,
                    losses=sum(1 for row in active if row["outcome_status"] == "LOSS"),
                    expired_active=sum(
                        1 for row in active if row["outcome_status"] == "EXPIRED_ACTIVE"
                    ),
                    expired_no_entry=sum(
                        1 for row in rows if row["outcome_status"] == "EXPIRED_NO_ENTRY"
                    ),
                    minimum_required_activated=minimum_activated,
                    sample_eligible=sample_eligible,
                    target_hit_rate_pct=rate,
                    wilson_95_lower_pct=lower,
                    wilson_95_upper_pct=upper,
                    average_realized_rr=average_rr,
                )
            )
        return output

    def research_panel(
        self,
        user_id: int,
        *,
        minimum_terminal_outcomes: int = 30,
        minimum_activated_outcomes: int = 30,
        breakdown_minimum_activated: int = 10,
    ) -> SignalShadowResearchPanelResponse:
        minimum_terminal_outcomes = max(30, int(minimum_terminal_outcomes))
        minimum_activated_outcomes = max(30, int(minimum_activated_outcomes))
        breakdown_minimum_activated = max(10, int(breakdown_minimum_activated))
        with self.database.connection() as conn:
            fetched = conn.execute(
                "SELECT observation_id,symbol,market,evidence_sha256,evidence_json,outcome_status,"
                "realized_rr,captured_at,resolved_at,activated,resolution_policy "
                "FROM signal_shadow_observations WHERE user_id=? "
                "AND fusion_status='ACTIONABLE_CANDIDATE' ORDER BY captured_at,observation_id",
                (user_id,),
            ).fetchall()
        rows = [dict(row) for row in fetched]
        terminal = [row for row in rows if row["outcome_status"] in _TERMINAL_OUTCOMES]
        pending = sum(1 for row in rows if row["outcome_status"] == "PENDING")
        integrity_failures = 0
        valid_terminal: list[dict] = []
        for row in terminal:
            raw = str(row.get("evidence_json") or "")
            digest_valid = hashlib.sha256(raw.encode()).hexdigest() == row.get("evidence_sha256")
            try:
                evidence = json.loads(raw)
                json_valid = isinstance(evidence, dict)
            except (TypeError, ValueError, json.JSONDecodeError):
                evidence, json_valid = {}, False
            if not digest_valid or not json_valid:
                integrity_failures += 1
                continue
            row["_evidence"] = evidence
            valid_terminal.append(row)
        activated = [
            row for row in valid_terminal if row["outcome_status"] in _ACTIVATED_TERMINAL_OUTCOMES
        ]
        completeness_failures = 0
        realized_values: list[float] = []
        for row in activated:
            value = self._number(row.get("realized_rr"))
            if not bool(row.get("activated")) or value is None:
                completeness_failures += 1
            else:
                realized_values.append(value)
        dataset_payload = [
            {
                "observation_id": row.get("observation_id"),
                "evidence_sha256": row.get("evidence_sha256"),
                "outcome_status": row.get("outcome_status"),
                "realized_rr": row.get("realized_rr"),
                "captured_at": row.get("captured_at"),
                "resolved_at": row.get("resolved_at"),
                "resolution_policy": row.get("resolution_policy"),
            }
            for row in rows
        ]
        dataset_raw = json.dumps(dataset_payload, sort_keys=True, separators=(",", ":"), default=str)
        dataset_sha256 = hashlib.sha256(dataset_raw.encode()).hexdigest()
        enough_evidence = (
            len(terminal) >= minimum_terminal_outcomes
            and len(activated) >= minimum_activated_outcomes
        )
        integrity_ok = integrity_failures == 0 and completeness_failures == 0
        ready = enough_evidence and integrity_ok
        if not integrity_ok:
            status = "INTEGRITY_FAILED"
        elif ready:
            status = "RESEARCH_READY"
        else:
            status = "INSUFFICIENT_EVIDENCE"
        wins = sum(1 for row in activated if row["outcome_status"] == "WIN")
        losses = sum(1 for row in activated if row["outcome_status"] == "LOSS")
        expired_active = sum(1 for row in activated if row["outcome_status"] == "EXPIRED_ACTIVE")
        expired_no_entry = sum(
            1 for row in valid_terminal if row["outcome_status"] == "EXPIRED_NO_ENTRY"
        )
        rate = lower = upper = average_rr = median_rr = cumulative_rr = max_drawdown = None
        if ready:
            low_value, high_value = self._wilson_95(wins, len(activated))
            rate = round(100.0 * wins / len(activated), 4)
            lower = round(100.0 * low_value, 4)
            upper = round(100.0 * high_value, 4)
            average_rr = round(sum(realized_values) / len(realized_values), 6)
            median_rr = round(float(median(realized_values)), 6)
            cumulative_rr = round(sum(realized_values), 6)
            max_drawdown = round(self._max_drawdown_rr(realized_values), 6)
        observed = [str(row["captured_at"]) for row in terminal]
        breakdowns = (
            self._breakdowns(
                valid_terminal,
                overall_ready=ready,
                minimum_activated=breakdown_minimum_activated,
            )
            if integrity_ok
            else []
        )
        return SignalShadowResearchPanelResponse(
            status=status,
            total_candidates=len(rows),
            terminal_outcomes=len(terminal),
            activated_terminal_outcomes=len(activated),
            pending_outcomes=pending,
            wins=wins,
            losses=losses,
            expired_active=expired_active,
            expired_no_entry=expired_no_entry,
            minimum_required_terminal_outcomes=minimum_terminal_outcomes,
            minimum_required_activated_outcomes=minimum_activated_outcomes,
            evidence_integrity_checked=len(terminal),
            evidence_integrity_failures=integrity_failures,
            metric_completeness_failures=completeness_failures,
            evidence_dataset_sha256=dataset_sha256,
            observed_from=min(observed) if observed else None,
            observed_to=max(observed) if observed else None,
            target_hit_rate_pct=rate,
            wilson_95_lower_pct=lower,
            wilson_95_upper_pct=upper,
            average_realized_rr=average_rr,
            median_realized_rr=median_rr,
            cumulative_realized_rr=cumulative_rr,
            max_drawdown_rr=max_drawdown,
            breakdown_minimum_activated=breakdown_minimum_activated,
            breakdowns=breakdowns,
            precision_claimed=ready,
            research_ready=ready,
            actionable_for_live=False,
            live_execution_enabled=settings.enable_live_execution,
        )
