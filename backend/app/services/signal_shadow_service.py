from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

from app.config import settings
from app.models import SignalShadowCaptureResponse, SignalShadowPanelResponse
from app.services.database_service import DatabaseManager


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
        with self.database.connection() as conn:
            conn.execute(
                """INSERT INTO signal_shadow_observations (
                    observation_id,user_id,symbol,market,fusion_status,side,evidence_sha256,
                    evidence_json,outcome_status,realized_rr,captured_at,resolved_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (observation_id,user_id,str(result.get("symbol") or "UNKNOWN"),str(result.get("market") or "unknown"),
                 status,str(result.get("side") or "flat"),digest,raw,outcome,None,now,None),
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
            order_routed=False,
            actionable_for_live=False,
            captured_at=now,
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
