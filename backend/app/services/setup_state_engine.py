from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.market_quality_engine import timeframe_seconds


ACTIVE_STATES = {"forming", "armed", "confirmed", "triggered"}
TERMINAL_STATES = {"invalidated", "expired"}


class SetupStateEngine:
    """In-memory deterministic setup lifecycle and deduplication engine."""

    def __init__(self) -> None:
        self._records: dict[str, dict] = {}

    def update(
        self,
        candidates: list[dict],
        market_prices: dict[str, float],
        now: datetime | None = None,
    ) -> dict[str, list[dict]]:
        now = now or datetime.now(timezone.utc)
        seen: set[str] = set()

        for candidate in candidates:
            key = str(candidate["id"])
            seen.add(key)
            timeframe = str(candidate.get("timeframe") or "15m")
            current_price = float(candidate.get("price") or 0)
            existing = self._records.get(key)

            if existing and existing["lifecycle_state"] in TERMINAL_STATES:
                cooldown = _parse_time(existing.get("cooldown_until"))
                if cooldown and now < cooldown:
                    continue
                existing = None

            desired = self._desired_state(candidate)
            if existing is None:
                record = self._new_record(candidate, desired, now)
            else:
                record = existing
                record.update(deepcopy(candidate))
                record["last_seen_at"] = now.isoformat()
                record["scan_count"] = int(record.get("scan_count", 0)) + 1
                record["missing_scans"] = 0
                self._transition(record, desired, now)

            if self._is_invalidated(record, current_price):
                self._terminate(record, "invalidated", "price_crossed_invalidation", now)
            elif record["lifecycle_state"] == "confirmed" and self._entry_touched(record, current_price):
                record["lifecycle_state"] = "triggered"
                record["triggered_at"] = now.isoformat()
                record["transition_reason"] = "price_entered_entry_zone"
            elif self._is_expired(record, now):
                self._terminate(record, "expired", "time_expired", now)

            self._records[key] = record

        for key, record in list(self._records.items()):
            if key in seen or record.get("lifecycle_state") in TERMINAL_STATES:
                continue
            market_key = f"{record.get('symbol')}:{record.get('timeframe')}"
            current_price = float(market_prices.get(market_key) or 0)
            record["missing_scans"] = int(record.get("missing_scans", 0)) + 1
            record["scan_count"] = int(record.get("scan_count", 0)) + 1
            if self._is_invalidated(record, current_price):
                self._terminate(record, "invalidated", "price_crossed_invalidation", now)
            elif self._is_expired(record, now):
                self._terminate(record, "expired", "time_expired", now)
            elif record["missing_scans"] >= 2:
                self._terminate(record, "expired", "missing_for_two_scans", now)

        self._cleanup(now)
        output = {state: [] for state in (*ACTIVE_STATES, *TERMINAL_STATES)}
        for record in self._records.values():
            state = str(record.get("lifecycle_state"))
            if state in output:
                output[state].append(deepcopy(record))
        for state, records in output.items():
            records.sort(
                key=lambda item: (
                    int(item.get("confluence") or 0),
                    int(item.get("probability") or 0),
                    float(item.get("rr") or 0),
                ),
                reverse=True,
            )
        return output

    def _desired_state(self, candidate: dict) -> str:
        if candidate.get("status") == "confirmed" and candidate.get("omega_compliant"):
            return "confirmed"
        decision = candidate.get("decision") or {}
        passed = int(decision.get("hard_gates_passed") or 0)
        total = int(decision.get("hard_gates_total") or 0)
        quality = float((candidate.get("data_quality") or {}).get("score") or 0)
        if total > 0 and passed >= total - 2 and quality >= 72:
            return "armed"
        return "forming"

    def _new_record(self, candidate: dict, state: str, now: datetime) -> dict:
        timeframe = str(candidate.get("timeframe") or "15m")
        expiry_bars = int((candidate.get("decision") or {}).get("expires_after_bars") or 5)
        expires_at = now + timedelta(seconds=timeframe_seconds(timeframe) * expiry_bars)
        record = deepcopy(candidate)
        record.update(
            {
                "lifecycle_state": state,
                "first_seen_at": now.isoformat(),
                "last_seen_at": now.isoformat(),
                "armed_at": now.isoformat() if state == "armed" else None,
                "confirmed_at": now.isoformat() if state == "confirmed" else None,
                "triggered_at": None,
                "terminated_at": None,
                "expires_at": expires_at.isoformat(),
                "cooldown_until": None,
                "transition_reason": f"initial_{state}",
                "scan_count": 1,
                "missing_scans": 0,
                "state_version": 1,
            }
        )
        entry = record.get("entry")
        if entry is not None:
            entry = float(entry)
            atr = max(float(record.get("atr") or 0), abs(entry) * 0.0003)
            if record.get("entry_low") is None:
                record["entry_low"] = entry - atr * 0.12
            if record.get("entry_high") is None:
                record["entry_high"] = entry + atr * 0.12
        return record

    def _transition(self, record: dict, desired: str, now: datetime) -> None:
        current = str(record.get("lifecycle_state") or "forming")
        if current == "triggered":
            return
        if current == "confirmed" and desired != "confirmed":
            self._terminate(record, "invalidated", "strict_gate_lost_before_trigger", now)
            return
        if desired == "confirmed" and current != "confirmed":
            record["lifecycle_state"] = "confirmed"
            record["confirmed_at"] = now.isoformat()
            record["transition_reason"] = f"{current}_to_confirmed"
            return
        if desired == "armed" and current == "forming":
            record["lifecycle_state"] = "armed"
            record["armed_at"] = now.isoformat()
            record["transition_reason"] = "forming_to_armed"
            return
        if desired == "forming" and current == "armed":
            record["lifecycle_state"] = "forming"
            record["transition_reason"] = "armed_to_forming"

    def _entry_touched(self, record: dict, price: float) -> bool:
        if price <= 0:
            return False
        low = record.get("entry_low")
        high = record.get("entry_high")
        entry = record.get("entry")
        if low is None or high is None:
            if entry is None:
                return False
            tolerance = max(abs(float(entry)) * 0.0005, 1e-9)
            low, high = float(entry) - tolerance, float(entry) + tolerance
        return float(low) <= price <= float(high)

    def _is_invalidated(self, record: dict, price: float) -> bool:
        if price <= 0:
            return False
        invalidation = record.get("invalidation") or record.get("stop_loss")
        if invalidation is None:
            return False
        invalidation = float(invalidation)
        direction = record.get("direction")
        if direction == "long":
            return price <= invalidation
        if direction == "short":
            return price >= invalidation
        return False

    def _is_expired(self, record: dict, now: datetime) -> bool:
        expiry = _parse_time(record.get("expires_at"))
        if not expiry:
            return False
        if record.get("lifecycle_state") == "triggered":
            triggered = _parse_time(record.get("triggered_at"))
            if triggered:
                timeframe = timeframe_seconds(str(record.get("timeframe") or "15m"))
                return now >= triggered + timedelta(seconds=timeframe * 12)
        return now >= expiry

    def _terminate(self, record: dict, state: str, reason: str, now: datetime) -> None:
        timeframe = timeframe_seconds(str(record.get("timeframe") or "15m"))
        record["lifecycle_state"] = state
        record["terminated_at"] = now.isoformat()
        record["cooldown_until"] = (now + timedelta(seconds=timeframe * 3)).isoformat()
        record["transition_reason"] = reason

    def _cleanup(self, now: datetime) -> None:
        cutoff = now - timedelta(hours=48)
        for key, record in list(self._records.items()):
            if record.get("lifecycle_state") not in TERMINAL_STATES:
                continue
            terminated = _parse_time(record.get("terminated_at"))
            if terminated and terminated < cutoff:
                del self._records[key]


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None
