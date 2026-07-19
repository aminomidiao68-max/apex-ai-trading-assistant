from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

from app.config import settings
from app.models import SignalShadowCaptureResponse, SignalShadowPanelResponse, SignalShadowResolutionResponse
from app.services.database_service import DatabaseManager


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

    def capture(self, user_id: int, result: dict) -> SignalShadowCaptureResponse:
        raw, digest = self._canonical(result)
        observation_id = uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        status = str(result.get("status") or "NO_TRADE")
        outcome = "PENDING" if status == "ACTIONABLE_CANDIDATE" else "NOT_APPLICABLE"
        levels = result.get("levels") or {}
        def number(value):
            try:
                return float(value) if value is not None else None
            except (TypeError, ValueError):
                return None
        entry = number(levels.get("entry"))
        stop = number(levels.get("sl"))
        target = number(levels.get("tp1"))
        resolution_tf = result.get("resolution_timeframe")
        max_bars = int(result.get("max_resolution_bars") or 12)
        if outcome == "PENDING" and (entry is None or stop is None or target is None or not resolution_tf):
            raise SignalShadowError("candidate_resolution_contract_incomplete")
        with self.database.connection() as conn:
            conn.execute(
                """INSERT INTO signal_shadow_observations (
                    observation_id,user_id,symbol,market,fusion_status,side,evidence_sha256,
                    evidence_json,outcome_status,realized_rr,captured_at,resolved_at,
                    resolution_timeframe,entry_price,stop_price,target_price,max_resolution_bars,activated
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (observation_id,user_id,str(result.get("symbol") or "UNKNOWN"),str(result.get("market") or "unknown"),
                 status,str(result.get("side") or "flat"),digest,raw,outcome,None,now,None,
                 resolution_tf,entry,stop,target,max_bars,0),
            )
            conn.commit()
        return SignalShadowCaptureResponse(
            observation_id=observation_id,
            symbol=str(result.get("symbol") or "UNKNOWN"),
            market=str(result.get("market") or "unknown"),
            fusion_status=status,
            side=str(result.get("side") or "flat"),
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
        age = datetime.now(timezone.utc).timestamp() - datetime.fromisoformat(row["captured_at"]).timestamp()
        return age >= max(60, minimum_interval_seconds)

    def pending_contexts(self, user_id: int, limit: int = 50) -> list[dict]:
        with self.database.connection() as conn:
            rows = conn.execute(
                "SELECT observation_id,symbol,market,resolution_timeframe,outcome_status FROM signal_shadow_observations WHERE user_id=? AND outcome_status='PENDING' ORDER BY captured_at LIMIT ?",
                (user_id, max(1, min(limit, 200))),
            ).fetchall()
        return [dict(row) for row in rows]

    def resolution_context(self, user_id: int, observation_id: str) -> dict:
        with self.database.connection() as conn:
            row = conn.execute(
                "SELECT symbol,market,resolution_timeframe,outcome_status FROM signal_shadow_observations WHERE user_id=? AND observation_id=?",
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
        if row["outcome_status"] in {"WIN", "LOSS", "EXPIRED_NO_ENTRY"}:
            return SignalShadowResolutionResponse(
                observation_id=observation_id, outcome_status=row["outcome_status"],
                activated=bool(row["activated"]), bars_observed=0,
                realized_rr=row["realized_rr"], resolved_at=row["resolved_at"],
            )
        captured = datetime.fromisoformat(row["captured_at"]).timestamp()
        future = [item for item in candles if float(item.get("t") or 0) > captured]
        future = future[: int(row["max_resolution_bars"])]
        entry, stop, target = map(float, (row["entry_price"], row["stop_price"], row["target_price"]))
        side = row["side"]
        activated = bool(row["activated"])
        outcome = "PENDING"
        realized_rr = None
        for candle in future:
            high = float(candle["h"]); low = float(candle["l"])
            if not activated and low <= entry <= high:
                activated = True
            if not activated:
                continue
            stop_hit = low <= stop if side == "long" else high >= stop
            target_hit = high >= target if side == "long" else low <= target
            if stop_hit:  # conservative stop-first when both occur in one bar
                outcome, realized_rr = "LOSS", -1.0
                break
            if target_hit:
                risk = abs(entry - stop)
                outcome = "WIN"
                realized_rr = abs(target - entry) / risk if risk > 0 else 0.0
                break
        if outcome == "PENDING" and len(future) >= int(row["max_resolution_bars"]) and not activated:
            outcome = "EXPIRED_NO_ENTRY"
            realized_rr = 0.0
        resolved_at = datetime.now(timezone.utc).isoformat() if outcome != "PENDING" else None
        with self.database.connection() as conn:
            conn.execute(
                "UPDATE signal_shadow_observations SET outcome_status=?,realized_rr=?,activated=?,resolved_at=? WHERE observation_id=?",
                (outcome, realized_rr, int(activated), resolved_at, observation_id),
            )
            conn.commit()
        return SignalShadowResolutionResponse(
            observation_id=observation_id, outcome_status=outcome,
            activated=activated, bars_observed=len(future), realized_rr=realized_rr,
            resolved_at=resolved_at,
        )

    def panel(self, user_id: int, minimum_required_resolved: int = 30) -> SignalShadowPanelResponse:
        with self.database.connection() as conn:
            rows = conn.execute(
                "SELECT fusion_status,outcome_status FROM signal_shadow_observations WHERE user_id=?",
                (user_id,),
            ).fetchall()
        statuses = [str(row["fusion_status"]) for row in rows]
        pending = sum(1 for row in rows if row["outcome_status"] == "PENDING")
        resolved = sum(1 for row in rows if row["outcome_status"] not in {"PENDING", "NOT_APPLICABLE"})
        return SignalShadowPanelResponse(
            total_observations=len(rows),
            no_trade_count=statuses.count("NO_TRADE"),
            watch_count=statuses.count("WATCH"),
            candidate_count=statuses.count("ACTIONABLE_CANDIDATE"),
            pending_outcomes=pending,
            resolved_outcomes=resolved,
            minimum_required_resolved=minimum_required_resolved,
            status="RESEARCH_READY" if resolved >= minimum_required_resolved else "INSUFFICIENT_EVIDENCE",
            precision_claimed=False,
            actionable_for_live=False,
            live_execution_enabled=settings.enable_live_execution,
        )
