#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prune(directory: Path, retention_days: int) -> None:
    cutoff = datetime.now(timezone.utc).timestamp() - max(1, retention_days) * 86400
    for path in directory.glob("apex-*.*"):
        if path.stat().st_mtime < cutoff:
            path.unlink(missing_ok=True)


def backup_sqlite(source: Path, target: Path) -> None:
    if not source.exists():
        raise SystemExit("SQLite source database does not exist")
    source_conn = sqlite3.connect(str(source))
    target_conn = sqlite3.connect(str(target))
    try:
        source_conn.backup(target_conn)
        result = target_conn.execute("PRAGMA integrity_check").fetchone()
        if not result or result[0] != "ok":
            raise SystemExit("SQLite backup integrity check failed")
    finally:
        target_conn.close()
        source_conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a secret-safe APEX database backup")
    parser.add_argument("--output-dir", default="backups")
    parser.add_argument("--retention-days", type=int, default=int(os.getenv("BACKUP_RETENTION_DAYS", "14")))
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    database_url = os.getenv("DATABASE_URL", "").strip()

    if database_url.startswith(("postgresql://", "postgres://")):
        if shutil.which("pg_dump") is None:
            raise SystemExit("pg_dump is required for PostgreSQL backup")
        target = output_dir / f"apex-postgresql-{timestamp}.dump"
        env = os.environ.copy()
        env["PGDATABASE"] = database_url
        subprocess.run(
            ["pg_dump", "--format=custom", "--no-owner", "--no-acl", "--file", str(target)],
            env=env,
            check=True,
            stdin=subprocess.DEVNULL,
        )
        backend = "postgresql"
    else:
        configured = os.getenv("DATABASE_PATH", "").strip()
        source = Path(configured or "app_data/smartmoney.db").resolve()
        target = output_dir / f"apex-sqlite-{timestamp}.db"
        backup_sqlite(source, target)
        backend = "sqlite"

    manifest = {
        "backend": backend,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "file": target.name,
        "size_bytes": target.stat().st_size,
        "sha256": sha256_file(target),
        "contains_connection_string": False,
    }
    manifest_path = target.with_suffix(target.suffix + ".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    prune(output_dir, args.retention_days)
    print(json.dumps(manifest, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
