from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone

from app.config import settings
from app.models import PaperCorrelationSnapshotRequest, PaperCorrelationSnapshotResponse
from app.services.database_service import DatabaseManager
from app.services.historical_data_service import HistoricalDataError, HistoricalDatasetStore


class PaperCorrelationError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class PaperCorrelationService:
    def __init__(self, database: DatabaseManager, store: HistoricalDatasetStore | None = None) -> None:
        self.database = database
        self.store = store or HistoricalDatasetStore(database)

    @staticmethod
    def _hash(payload: dict) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _winsorize(values: list[float]) -> list[float]:
        if len(values) < 20:
            return list(values)
        ordered = sorted(values)
        low = ordered[max(0, int(len(ordered) * 0.01) - 1)]
        high = ordered[min(len(ordered) - 1, int(len(ordered) * 0.99))]
        return [min(high, max(low, value)) for value in values]

    @staticmethod
    def _correlation(left: list[float], right: list[float]) -> float:
        n = len(left)
        if n != len(right) or n < 2:
            return 0.0
        mean_left = sum(left) / n
        mean_right = sum(right) / n
        covariance = sum((a - mean_left) * (b - mean_right) for a, b in zip(left, right))
        var_left = sum((a - mean_left) ** 2 for a in left)
        var_right = sum((b - mean_right) ** 2 for b in right)
        denominator = math.sqrt(var_left * var_right)
        return covariance / denominator if denominator > 1e-18 else 0.0

    @staticmethod
    def _clusters(symbols: list[str], matrix: dict[str, dict[str, float]], threshold: float) -> list[list[str]]:
        remaining = set(symbols)
        clusters: list[list[str]] = []
        while remaining:
            root = min(remaining)
            component = {root}
            queue = [root]
            remaining.remove(root)
            while queue:
                current = queue.pop(0)
                linked = [
                    symbol
                    for symbol in sorted(remaining)
                    if abs(matrix[current][symbol]) >= threshold
                ]
                for symbol in linked:
                    remaining.remove(symbol)
                    component.add(symbol)
                    queue.append(symbol)
            clusters.append(sorted(component))
        return sorted(clusters, key=lambda items: (items[0], len(items)))

    @staticmethod
    def _from_row(row, duplicate: bool) -> PaperCorrelationSnapshotResponse:
        return PaperCorrelationSnapshotResponse(
            snapshot_id=row["snapshot_id"],
            symbols=list(json.loads(row["symbols_json"])),
            dataset_refs=list(json.loads(row["dataset_refs_json"])),
            observations=int(row["observations"]),
            matrix=dict(json.loads(row["matrix_json"])),
            clusters=list(json.loads(row["clusters_json"])),
            cluster_threshold=float(row["cluster_threshold"]),
            shrinkage_weight=float(row["shrinkage_weight"]),
            canonical_sha256=row["canonical_sha256"],
            duplicate=duplicate,
            correlation_source="stored_dataset_statistical",
            actionable_for_live=False,
            live_execution_enabled=settings.enable_live_execution,
            created_at=row["created_at"],
        )

    def build_snapshot(
        self,
        user_id: int,
        request: PaperCorrelationSnapshotRequest,
    ) -> PaperCorrelationSnapshotResponse:
        payload = request.model_dump(mode="json", exclude={"snapshot_id"})
        request_hash = self._hash(payload)
        with self.database.connection() as conn:
            existing = conn.execute(
                "SELECT * FROM paper_correlation_snapshots WHERE user_id = ? AND snapshot_id = ?",
                (user_id, request.snapshot_id),
            ).fetchone()
        if existing is not None:
            if existing["request_hash"] != request_hash:
                raise PaperCorrelationError("correlation_snapshot_id_payload_conflict")
            return self._from_row(existing, duplicate=True)

        symbols: list[str] = []
        dataset_refs: list[str] = []
        canonical_inputs: list[str] = []
        returns_by_symbol: dict[str, dict[str, float]] = {}
        timeframe = None
        try:
            for reference in request.datasets:
                manifest = self.store.get_manifest(user_id, reference.dataset_id, reference.version)
                symbol = manifest.manifest.symbol.upper()
                if symbol in returns_by_symbol:
                    raise PaperCorrelationError("correlation_symbols_must_be_unique")
                if timeframe is None:
                    timeframe = manifest.manifest.timeframe
                elif manifest.manifest.timeframe != timeframe:
                    raise PaperCorrelationError("correlation_timeframes_must_match")
                candles = sorted(
                    self.store.load_candles(user_id, reference.dataset_id, reference.version),
                    key=lambda item: item.timestamp,
                )
                returns: dict[str, float] = {}
                previous = None
                for candle in candles:
                    close = float(candle.close)
                    if previous is not None and previous > 0 and close > 0:
                        returns[candle.timestamp.astimezone(timezone.utc).isoformat()] = math.log(close / previous)
                    previous = close
                symbols.append(symbol)
                dataset_refs.append(f"{reference.dataset_id}:{reference.version}")
                canonical_inputs.append(manifest.canonical_sha256)
                returns_by_symbol[symbol] = returns
        except HistoricalDataError as exc:
            raise PaperCorrelationError(exc.code) from exc

        common = set.intersection(*(set(values) for values in returns_by_symbol.values()))
        timestamps = sorted(common)
        if len(timestamps) < request.minimum_observations:
            raise PaperCorrelationError("correlation_insufficient_aligned_observations")
        aligned = {
            symbol: self._winsorize([returns_by_symbol[symbol][timestamp] for timestamp in timestamps])
            for symbol in symbols
        }
        weight = len(timestamps) / (len(timestamps) + 20.0)
        matrix: dict[str, dict[str, float]] = {symbol: {} for symbol in symbols}
        for left in symbols:
            for right in symbols:
                if left == right:
                    value = 1.0
                else:
                    value = self._correlation(aligned[left], aligned[right]) * weight
                matrix[left][right] = round(max(-1.0, min(1.0, value)), 8)
        clusters = self._clusters(symbols, matrix, request.cluster_threshold)
        canonical_payload = {
            "dataset_refs": dataset_refs,
            "dataset_sha256": canonical_inputs,
            "observations": len(timestamps),
            "matrix": matrix,
            "clusters": clusters,
            "threshold": request.cluster_threshold,
            "shrinkage_weight": round(weight, 12),
        }
        canonical_sha256 = self._hash(canonical_payload)
        now = datetime.now(timezone.utc).isoformat()
        with self.database.connection() as conn:
            conn.execute(
                """
                INSERT INTO paper_correlation_snapshots (
                    user_id, snapshot_id, request_hash, dataset_refs_json, symbols_json,
                    observations, matrix_json, clusters_json, cluster_threshold,
                    shrinkage_weight, canonical_sha256, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    request.snapshot_id,
                    request_hash,
                    json.dumps(dataset_refs, separators=(",", ":")),
                    json.dumps(symbols, separators=(",", ":")),
                    len(timestamps),
                    json.dumps(matrix, sort_keys=True, separators=(",", ":")),
                    json.dumps(clusters, separators=(",", ":")),
                    request.cluster_threshold,
                    weight,
                    canonical_sha256,
                    now,
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM paper_correlation_snapshots WHERE user_id = ? AND snapshot_id = ?",
                (user_id, request.snapshot_id),
            ).fetchone()
        return self._from_row(row, duplicate=False)
