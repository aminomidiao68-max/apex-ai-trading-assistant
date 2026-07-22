#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add backend directory to sys.path
backend_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_root))

from app.models import (
    Candle,
    MarketType,
    OperationalDriftRequest,
    OperationalPromotionPanelRequest,
    PaperCorrelationDatasetRef,
    QuantDatasetManifest
)
from app.services.database_service import DatabaseManager
from app.services.historical_data_service import HistoricalDatasetStore
from app.services.operational_validation_service import OperationalValidationService


def save_dataset(store: HistoricalDatasetStore, dataset_id: str, returns: list[float]) -> None:
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    close = 100.0
    candles = [
        Candle(
            timestamp=start,
            open=100.0, high=101.0, low=99.0, close=100.0, volume=1.0
        )
    ]
    for index, r in enumerate(returns, 1):
        old = close
        close *= math.exp(r)
        candles.append(
            Candle(
                timestamp=start + timedelta(hours=index),
                open=old,
                high=max(old, close),
                low=min(old, close),
                close=close,
                volume=1.0
            )
        )
    
    manifest = QuantDatasetManifest(
        dataset_id=dataset_id,
        version="v1",
        source="drift_simulation_fixture",
        symbol="BTCUSDT",
        market=MarketType.crypto,
        timeframe="1h",
        start_time=candles[0].timestamp,
        end_time=candles[-1].timestamp,
        sample_count=len(candles),
        source_sha256="a" * 64,
        is_point_in_time=True,
        data_quality_score=100
    )
    # user_id = 1
    store.save(1, manifest, ("b" if dataset_id == "base" else "c") * 64, candles)


def main() -> int:
    print("=" * 70)
    print("APEX OMEGA PRO — OPERATIONAL LEVEL 10 & 11 PROMOTION SIMULATOR")
    print("=" * 70)
    
    with tempfile.TemporaryDirectory(prefix="apex-op-") as directory:
        db_path = str(Path(directory) / "operational_test.db")
        print(f"[+] Initializing isolated database: {db_path}")
        
        # 1. Initialize DB and Services
        db = DatabaseManager(db_path=db_path)
        store = HistoricalDatasetStore(db)
        svc = OperationalValidationService(db, store)
        
        # 2. Seed Mock Datasets (Baseline and Candidate with very similar returns to guarantee STABLE status)
        print("[+] Seeding mock datasets for drift comparison...")
        base_returns = [0.001 * math.sin(i / 5) for i in range(120)]
        # Candidate has extremely low variance from base (1.001 multiplier)
        candidate_returns = [x * 1.001 for x in base_returns]
        
        save_dataset(store, "base", base_returns)
        save_dataset(store, "candidate", candidate_returns)
        
        # 3. Simulate 3 consecutive Stable Drift Checks
        print("[+] Simulating 3 consecutive STABLE drift windows...")
        for i in range(3):
            req = OperationalDriftRequest(
                run_id=f"simulated-drift-run-000{i+1}",
                baseline=PaperCorrelationDatasetRef(dataset_id="base", version="v1"),
                candidate=PaperCorrelationDatasetRef(dataset_id="candidate", version="v1"),
                minimum_observations=60
            )
            result = svc.run_drift(1, req)
            print(f"    -> Drift Run #{i+1} [{result.run_id}]: status={result.status}, PSI={result.psi:.6f}, KS={result.ks_statistic:.6f}, Vol_Ratio={result.volatility_ratio:.4f}")
            assert result.status == "STABLE", "Simulated drift is not stable!"
            
        # 4. Define SLO Monitoring Snapshot
        print("[+] Defining SLO monitoring snapshot...")
        monitoring_snapshot = {
            "requests_total": 5000,
            "sample_window": 1000,
            "server_errors_total": 0,
            "latency_p95_ms": 78
        }
        print(f"    -> Monitoring stats: Requests={monitoring_snapshot['requests_total']}, P95 Latency={monitoring_snapshot['latency_p95_ms']}ms, Errors={monitoring_snapshot['server_errors_total']}")
        
        # 5. Evaluate Promotion Panel
        print("[+] Evaluating Promotion Panel...")
        panel_req = OperationalPromotionPanelRequest(
            panel_id="simulated-promotion-panel-0001",
            required_consecutive_stable=3,
            minimum_slo_samples=100,
            max_p95_latency_ms=200,
            max_server_error_rate_pct=1.0
        )
        
        panel_res = svc.evaluate_promotion_panel(1, panel_req, monitoring_snapshot)
        
        # 6. Display Dashboard Result (Mirroring Android UI)
        print("\n" + "=" * 50)
        print("          MISSION CONTROL PANEL - ACTIVE STATE")
        print("=" * 50)
        print(f"  System Status:       {panel_res.status}")
        print(f"  Consecutive Stable:  {panel_res.consecutive_stable} / {panel_res.required_consecutive_stable} [PASS]")
        print(f"  SLO Status:          {panel_res.slo_status} [PASS]")
        print(f"  Database Ready:      {panel_res.database_ready} [PASS]")
        print(f"  Operational Candidate: {panel_res.operational_candidate}")
        print("-" * 50)
        print(f"  Testnet Authorized:  {panel_res.testnet_authorized} (Hard Locked)")
        print(f"  Live Authorized:     {panel_res.live_authorized} (Hard Locked)")
        print(f"  Actionable for Live: {panel_res.actionable_for_live} (Hard Locked)")
        print(f"  Evaluated At:        {panel_res.evaluated_at}")
        print("=" * 50 + "\n")
        
        assert panel_res.status == "OPERATIONAL_CANDIDATE", "System failed to reach Operational Candidate state!"
        print("[+] LEVEL 10 & 11 PROMOTION PIPELINE SIMULATION COMPLETED SUCCESSFULLY!")
        
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
