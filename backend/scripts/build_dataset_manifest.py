#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_COLUMNS = {"timestamp", "open", "high", "low", "close", "volume"}


def parse_timestamp(value: str) -> datetime:
    raw = value.strip()
    try:
        numeric = float(raw)
        if numeric > 1e12:
            numeric /= 1000.0
        return datetime.fromtimestamp(numeric, tz=timezone.utc)
    except ValueError:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a versioned APEX quant dataset manifest")
    parser.add_argument("csv_file")
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--market", choices=["crypto", "forex"], required=True)
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--point-in-time", action="store_true")
    parser.add_argument("--survivorship-controlled", action="store_true")
    parser.add_argument("--independent-holdout", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    source = Path(args.csv_file).resolve()
    if not source.exists() or not source.is_file():
        raise SystemExit("dataset CSV does not exist")

    timestamps: list[datetime] = []
    with source.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - fields
        if missing:
            raise SystemExit("dataset CSV is missing required OHLCV columns")
        for line_number, row in enumerate(reader, start=2):
            try:
                timestamp = parse_timestamp(str(row["timestamp"]))
                open_price = float(row["open"])
                high = float(row["high"])
                low = float(row["low"])
                close = float(row["close"])
                volume = float(row["volume"])
            except Exception as exc:
                raise SystemExit(f"invalid dataset value at CSV line {line_number}") from exc
            if min(open_price, high, low, close) <= 0 or volume < 0:
                raise SystemExit(f"invalid non-positive OHLC or negative volume at CSV line {line_number}")
            if high < max(open_price, close, low) or low > min(open_price, close, high):
                raise SystemExit(f"invalid OHLC integrity at CSV line {line_number}")
            if timestamps and timestamp <= timestamps[-1]:
                raise SystemExit("timestamps must be strictly increasing without duplicates")
            timestamps.append(timestamp)

    if len(timestamps) < 30:
        raise SystemExit("dataset requires at least 30 valid rows")

    manifest = {
        "schema": "apex.quant-dataset-manifest.v1",
        "dataset_id": args.dataset_id,
        "version": args.version,
        "source": args.source,
        "symbol": args.symbol.upper(),
        "market": args.market,
        "timeframe": args.timeframe,
        "start_time": timestamps[0].isoformat(),
        "end_time": timestamps[-1].isoformat(),
        "sample_count": len(timestamps),
        "source_sha256": sha256_file(source),
        "is_point_in_time": args.point_in_time,
        "is_survivorship_bias_controlled": args.survivorship_controlled,
        "is_independent_holdout": args.independent_holdout,
        "data_quality_score": 100.0,
        "validation": {
            "required_columns": sorted(REQUIRED_COLUMNS),
            "ohlc_integrity": True,
            "timestamps_strictly_increasing": True,
            "duplicates": 0,
        },
        "notes": [
            "Manifest verifies file integrity and OHLCV structure; it does not independently verify provider truthfulness.",
            "Point-in-time, survivorship and holdout flags are operator attestations and require external audit evidence.",
        ],
    }
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"created": True, "sample_count": len(timestamps), "source_sha256": manifest["source_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
