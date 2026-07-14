from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys

import pytest

from app.models import (
    MarketType,
    PurgedSplitPlanRequest,
    QuantDatasetManifest,
    QuantValidationRequest,
    QuantWalkForwardFold,
)
from app.services.quant_validation_service import QuantValidationService


def _candidate_request(**overrides) -> QuantValidationRequest:
    n = 600
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    returns = [1.0 if index % 5 < 3 else -0.4 for index in range(n)]
    outcomes = [1 if value > 0 else 0 for value in returns]
    probabilities = [0.98 if outcome else 0.02 for outcome in outcomes]
    folds = []
    for fold_index, test_start in enumerate((100, 200, 300), start=1):
        test_end = test_start + 99
        folds.append(
            QuantWalkForwardFold(
                fold_id=f"fold-{fold_index}",
                train_start_index=0,
                train_end_index=test_start - 2,
                test_start_index=test_start,
                test_end_index=test_end,
                embargo_bars=1,
                selected_config_id="strict-core-v1",
                test_returns_rr=returns[test_start : test_end + 1],
            )
        )
    values = {
        "strategy_id": "apex-strict-core",
        "strategy_version": "3.0.0-rc1",
        "dataset": QuantDatasetManifest(
            dataset_id="btc-15m-holdout",
            version="v1",
            source="versioned_test_fixture",
            symbol="BTCUSDT",
            market=MarketType.crypto,
            timeframe="15m",
            start_time=start,
            end_time=start + timedelta(minutes=15 * n),
            sample_count=n,
            source_sha256="a" * 64,
            is_point_in_time=True,
            is_survivorship_bias_controlled=True,
            is_independent_holdout=True,
            data_quality_score=100,
        ),
        "returns_rr": returns,
        "timestamps": [start + timedelta(minutes=15 * index) for index in range(n)],
        "benchmark_returns_rr": [value - 0.2 for value in returns],
        "predicted_probabilities": probabilities,
        "binary_outcomes": outcomes,
        "walk_forward_folds": folds,
        "bootstrap_samples": 500,
        "monte_carlo_paths": 500,
        "random_seed": 12345,
    }
    values.update(overrides)
    return QuantValidationRequest(**values)


def test_quant_candidate_requires_reproducible_positive_out_of_sample_evidence():
    service = QuantValidationService()
    request = _candidate_request()
    first = service.validate(request)
    second = service.validate(request)

    assert first.status == "RESEARCH_CANDIDATE"
    assert first.actionable_for_live is False
    assert first.expectancy_interval.lower > 0
    assert first.benchmark_difference_interval is not None
    assert first.benchmark_difference_interval.lower > 0
    assert first.multiple_testing_adjusted_significant is True
    assert first.walk_forward.available is True
    assert first.walk_forward.stable is True
    assert first.calibration.probability_is_calibrated is True
    assert first.calibration.calibration_id.startswith("cal-")
    assert all(first.hard_gates.values())
    assert first.model_dump() == second.model_dump()
    assert first.analysis_fingerprint == second.analysis_fingerprint
    assert any("do not prove future profitability" in item for item in first.limitations)


def test_quant_gate_rejects_untraceable_or_non_point_in_time_dataset():
    request = _candidate_request()
    request.dataset.source_sha256 = None
    request.dataset.is_point_in_time = False
    request.timestamps = []

    result = QuantValidationService().validate(request)

    assert result.status == "REJECT"
    assert result.actionable_for_live is False
    assert "source_fingerprint" in result.failed_gates
    assert "point_in_time_dataset" in result.failed_gates
    assert "strict_timestamps" in result.failed_gates


def test_multiple_testing_penalty_prevents_false_research_promotion():
    request = _candidate_request(strategies_tried=10_000)
    result = QuantValidationService().validate(request)

    assert result.status == "WATCH"
    assert result.multiple_testing_adjusted_significant is False
    assert "multiple_testing_control" in result.failed_gates


def test_calibration_is_diagnostic_only_without_independent_holdout():
    request = _candidate_request()
    request.dataset.is_independent_holdout = False
    result = QuantValidationService().validate(request)

    assert result.calibration.available is True
    assert result.calibration.probability_is_calibrated is False
    assert result.calibration.calibration_id is None
    assert "independent_holdout" in result.calibration.failed_requirements
    assert "probability_calibration" in result.failed_gates


def test_walk_forward_returns_must_match_dataset_slice():
    request = _candidate_request()
    request.walk_forward_folds[1].test_returns_rr[0] = 99.0
    result = QuantValidationService().validate(request)

    assert result.walk_forward.stable is False
    assert result.hard_gates["purged_walk_forward_contract"] is False
    assert result.status == "WATCH"


def test_purged_split_plan_is_deterministic_and_reports_overlap():
    service = QuantValidationService()
    clean = service.build_split_plan(
        PurgedSplitPlanRequest(
            sample_count=1000,
            train_size=300,
            test_size=100,
            step_size=100,
            embargo_bars=5,
            max_folds=5,
        )
    )
    repeated = service.build_split_plan(
        PurgedSplitPlanRequest(
            sample_count=1000,
            train_size=300,
            test_size=100,
            step_size=100,
            embargo_bars=5,
            max_folds=5,
        )
    )
    overlapping = service.build_split_plan(
        PurgedSplitPlanRequest(
            sample_count=1000,
            train_size=300,
            test_size=100,
            step_size=20,
            embargo_bars=5,
            max_folds=5,
        )
    )

    assert clean.fold_count == 5
    assert clean.all_boundaries_purged is True
    assert clean.overlap_detected is False
    assert clean.plan_fingerprint == repeated.plan_fingerprint
    assert overlapping.overlap_detected is True


def test_quant_contract_rejects_non_monotonic_time_and_length_mismatch():
    request = _candidate_request()
    payload = request.model_dump()
    payload["timestamps"][10] = payload["timestamps"][9]
    with pytest.raises(ValueError, match="strictly increasing"):
        QuantValidationRequest(**payload)

    payload = request.model_dump()
    payload["dataset"]["sample_count"] = 599
    with pytest.raises(ValueError, match="sample_count"):
        QuantValidationRequest(**payload)


def test_dataset_manifest_script_hashes_and_validates_real_csv(tmp_path):
    csv_path = tmp_path / "candles.csv"
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = ["timestamp,open,high,low,close,volume"]
    for index in range(40):
        timestamp = (start + timedelta(minutes=15 * index)).isoformat()
        rows.append(f"{timestamp},100,101,99,100.5,{1000 + index}")
    csv_path.write_text("\n".join(rows) + "\n")
    output = tmp_path / "manifest.json"
    backend_root = Path(__file__).resolve().parents[1]

    subprocess.run(
        [
            sys.executable,
            "scripts/build_dataset_manifest.py",
            str(csv_path),
            "--dataset-id",
            "btc-history",
            "--version",
            "v1",
            "--source",
            "fixture",
            "--symbol",
            "BTCUSDT",
            "--market",
            "crypto",
            "--timeframe",
            "15m",
            "--point-in-time",
            "--survivorship-controlled",
            "--independent-holdout",
            "--output",
            str(output),
        ],
        cwd=backend_root,
        check=True,
        capture_output=True,
        text=True,
    )
    manifest = json.loads(output.read_text())
    assert manifest["sample_count"] == 40
    assert len(manifest["source_sha256"]) == 64
    assert manifest["validation"]["ohlc_integrity"] is True
    assert manifest["validation"]["timestamps_strictly_increasing"] is True

    bad_path = tmp_path / "bad.csv"
    bad_rows = list(rows)
    bad_rows[5] = bad_rows[4]
    bad_path.write_text("\n".join(bad_rows) + "\n")
    failed = subprocess.run(
        [
            sys.executable,
            "scripts/build_dataset_manifest.py",
            str(bad_path),
            "--dataset-id",
            "bad",
            "--version",
            "v1",
            "--source",
            "fixture",
            "--symbol",
            "BTCUSDT",
            "--market",
            "crypto",
            "--timeframe",
            "15m",
            "--output",
            str(tmp_path / "bad.json"),
        ],
        cwd=backend_root,
        capture_output=True,
        text=True,
    )
    assert failed.returncode != 0
    assert "strictly increasing" in failed.stderr
