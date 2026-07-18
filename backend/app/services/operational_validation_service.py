from __future__ import annotations

import hashlib
import json
import math
from bisect import bisect_right
from datetime import datetime, timezone

from app.config import settings
from app.models import OperationalDriftRequest, OperationalDriftResponse, OperationalSloRequest, OperationalSloResponse
from app.services.database_service import DatabaseManager
from app.services.historical_data_service import HistoricalDataError, HistoricalDatasetStore


class OperationalValidationError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class OperationalValidationService:
    def __init__(self, database: DatabaseManager, store: HistoricalDatasetStore) -> None:
        self.database = database
        self.store = store

    @staticmethod
    def _hash(value: dict) -> str:
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()

    @staticmethod
    def _returns(candles) -> list[float]:
        ordered = sorted(candles, key=lambda item: item.timestamp)
        values = []
        for previous, current in zip(ordered, ordered[1:]):
            if previous.close > 0 and current.close > 0:
                values.append(math.log(float(current.close) / float(previous.close)))
        return values

    @staticmethod
    def _std(values: list[float]) -> float:
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        return math.sqrt(sum((item - mean) ** 2 for item in values) / (len(values) - 1))

    @staticmethod
    def _ks(left: list[float], right: list[float]) -> float:
        points = sorted(set(left + right)); a = sorted(left); b = sorted(right)
        ia = ib = 0; maximum = 0.0
        for point in points:
            while ia < len(a) and a[ia] <= point: ia += 1
            while ib < len(b) and b[ib] <= point: ib += 1
            maximum = max(maximum, abs(ia / len(a) - ib / len(b)))
        return maximum

    @staticmethod
    def _psi(baseline: list[float], candidate: list[float]) -> float:
        ordered = sorted(baseline)
        edges = []
        for index in range(1, 10):
            edge = ordered[min(len(ordered) - 1, int(len(ordered) * index / 10))]
            if not edges or edge > edges[-1]: edges.append(edge)
        bins = len(edges) + 1; base_counts = [0] * bins; candidate_counts = [0] * bins
        for value in baseline: base_counts[bisect_right(edges, value)] += 1
        for value in candidate: candidate_counts[bisect_right(edges, value)] += 1
        epsilon = 1e-6; result = 0.0
        for a, b in zip(base_counts, candidate_counts):
            pa = max(epsilon, a / len(baseline)); pb = max(epsilon, b / len(candidate))
            result += (pb - pa) * math.log(pb / pa)
        return result

    def run_drift(self, user_id: int, request: OperationalDriftRequest) -> OperationalDriftResponse:
        request_hash = self._hash(request.model_dump(mode="json", exclude={"run_id"}))
        with self.database.connection() as conn:
            existing = conn.execute("SELECT * FROM operational_drift_runs WHERE user_id=? AND run_id=?", (user_id, request.run_id)).fetchone()
        if existing:
            if existing["request_hash"] != request_hash: raise OperationalValidationError("drift_run_id_payload_conflict")
            data = json.loads(existing["result_json"]); data["duplicate"] = True
            return OperationalDriftResponse(**data)
        try:
            baseline_manifest = self.store.get_manifest(user_id, request.baseline.dataset_id, request.baseline.version)
            candidate_manifest = self.store.get_manifest(user_id, request.candidate.dataset_id, request.candidate.version)
            baseline = self._returns(self.store.load_candles(user_id, request.baseline.dataset_id, request.baseline.version))
            candidate = self._returns(self.store.load_candles(user_id, request.candidate.dataset_id, request.candidate.version))
        except HistoricalDataError as exc:
            raise OperationalValidationError(exc.code) from exc
        if baseline_manifest.manifest.symbol != candidate_manifest.manifest.symbol: raise OperationalValidationError("drift_symbol_mismatch")
        if baseline_manifest.manifest.timeframe != candidate_manifest.manifest.timeframe: raise OperationalValidationError("drift_timeframe_mismatch")
        if min(len(baseline), len(candidate)) < request.minimum_observations: raise OperationalValidationError("drift_insufficient_observations")
        psi = self._psi(baseline, candidate); ks = self._ks(baseline, candidate)
        base_std = self._std(baseline); candidate_std = self._std(candidate)
        ratio = candidate_std / base_std if base_std > 1e-18 else (1.0 if candidate_std <= 1e-18 else 999.0)
        shift = sum(candidate) / len(candidate) - sum(baseline) / len(baseline)
        failed = []
        if psi >= 0.25: failed.append("psi_block")
        if ks >= 0.20: failed.append("ks_block")
        if ratio < 0.5 or ratio > 2.0: failed.append("volatility_ratio_block")
        if failed: status = "BLOCKED"
        elif psi >= 0.10 or ks >= 0.10 or ratio < 0.75 or ratio > 1.5: status = "WATCH"
        else: status = "STABLE"
        now = datetime.now(timezone.utc).isoformat()
        response = OperationalDriftResponse(
            run_id=request.run_id, symbol=baseline_manifest.manifest.symbol,
            timeframe=baseline_manifest.manifest.timeframe,
            baseline_ref=f"{request.baseline.dataset_id}:{request.baseline.version}",
            candidate_ref=f"{request.candidate.dataset_id}:{request.candidate.version}",
            baseline_observations=len(baseline), candidate_observations=len(candidate),
            psi=round(psi, 8), ks_statistic=round(ks, 8), volatility_ratio=round(ratio, 8),
            mean_return_shift=round(shift, 12), status=status, failed_gates=failed,
            probability_claimed=False, actionable_for_live=False,
            live_execution_enabled=settings.enable_live_execution, created_at=now,
        )
        with self.database.connection() as conn:
            conn.execute("INSERT INTO operational_drift_runs (user_id,run_id,request_hash,symbol,timeframe,status,result_json,created_at) VALUES (?,?,?,?,?,?,?,?)",
                         (user_id, request.run_id, request_hash, response.symbol, response.timeframe, status, response.model_dump_json(), now)); conn.commit()
        return response

    @staticmethod
    def evaluate_slo(snapshot: dict, request: OperationalSloRequest) -> OperationalSloResponse:
        requests = int(snapshot.get("requests_total", 0)); samples = int(snapshot.get("sample_window", 0)); errors = int(snapshot.get("server_errors_total", 0))
        error_rate = errors / requests * 100 if requests else 0.0; p95 = int(snapshot.get("latency_p95_ms", 0)); failed = []
        if samples < request.minimum_samples: status = "INSUFFICIENT_EVIDENCE"
        else:
            if p95 > request.max_p95_latency_ms: failed.append("p95_latency_slo")
            if error_rate > request.max_server_error_rate_pct: failed.append("server_error_rate_slo")
            status = "SLO_BREACH" if failed else "WITHIN_SLO"
        return OperationalSloResponse(status=status, requests_total=requests, sample_window=samples, latency_p95_ms=p95,
            server_error_rate_pct=round(error_rate, 6), failed_gates=failed, actionable_for_live=False,
            live_execution_enabled=settings.enable_live_execution, evaluated_at=datetime.now(timezone.utc).isoformat())
