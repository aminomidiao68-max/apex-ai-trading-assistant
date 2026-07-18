#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="apex-openapi-") as directory:
        os.environ["APP_ENV"] = "test"
        os.environ["SEED_DEMO_USER"] = "false"
        os.environ["ENABLE_LIVE_EXECUTION"] = "false"
        os.environ["ENABLE_TESTNET_EXECUTION"] = "false"
        os.environ["DATABASE_PATH"] = str(Path(directory) / "openapi.db")
        backend_root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(backend_root))
        from app.main import app

        schema = app.openapi()
    canonical = json.dumps(schema, sort_keys=True, separators=(",", ":")).encode()
    payload = {
        "schema": "apex.openapi-fingerprint.v1",
        "sha256": hashlib.sha256(canonical).hexdigest(),
        "path_count": len(schema.get("paths", {})),
        "component_schema_count": len(schema.get("components", {}).get("schemas", {})),
        "live_execution_expected": False,
        "testnet_execution_expected": False,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
