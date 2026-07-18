#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_sha(root: Path) -> str:
    supplied = os.getenv("GITHUB_SHA", "").strip()
    if re.fullmatch(r"[0-9a-fA-F]{40}", supplied):
        return supplied.lower()
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate APEX release provenance manifest")
    parser.add_argument("--apk", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--version", default=os.getenv("APP_VERSION", "3.0.0-rc1"))
    args = parser.parse_args()

    apk = Path(args.apk).resolve()
    if not apk.exists() or not apk.is_file():
        raise SystemExit("APK file does not exist")
    root = Path(__file__).resolve().parents[2]
    manifest = {
        "schema": "apex.release-manifest.v1",
        "version": args.version,
        "source_commit": git_sha(root),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "artifact": {
            "name": apk.name,
            "size_bytes": apk.stat().st_size,
            "sha256": sha256_file(apk),
            "type": "debug_apk",
            "production_release_signed": False,
        },
        "safety": {
            "live_execution_expected": False,
            "external_ai_default": "disabled",
            "deterministic_core_override_allowed": False,
        },
        "required_gates": [
            "backend_sqlite_regression",
            "backend_postgresql_integration",
            "android_unit_test",
            "android_lint",
            "android_debug_apk",
            "render_readiness",
            "dependency_vulnerability_audit",
            "static_security_analysis",
            "python_cyclonedx_sbom",
            "android_cyclonedx_sbom",
            "openapi_contract_fingerprint",
        ],
    }
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
