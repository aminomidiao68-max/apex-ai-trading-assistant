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


_CONFIRMATION = "RESTORE_APEX_DATABASE"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_manifest(backup: Path) -> None:
    manifest_path = backup.with_suffix(backup.suffix + ".manifest.json")
    if not manifest_path.exists():
        raise SystemExit("Backup manifest is required")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("file") != backup.name:
        raise SystemExit("Backup manifest filename mismatch")
    if manifest.get("sha256") != sha256_file(backup):
        raise SystemExit("Backup SHA-256 verification failed")


def restore_sqlite(backup: Path, destination: Path) -> None:
    source = sqlite3.connect(str(backup))
    try:
        result = source.execute("PRAGMA integrity_check").fetchone()
        if not result or result[0] != "ok":
            raise SystemExit("Source SQLite backup failed integrity check")
    finally:
        source.close()

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safety_copy = destination.with_suffix(destination.suffix + f".pre-restore-{stamp}")
        shutil.copy2(destination, safety_copy)
    temp = destination.with_suffix(destination.suffix + ".restore-tmp")
    shutil.copy2(backup, temp)
    os.replace(temp, destination)


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore a verified APEX database backup")
    parser.add_argument("backup")
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--sqlite-destination", default=os.getenv("DATABASE_PATH", "app_data/smartmoney.db"))
    args = parser.parse_args()

    if args.confirm != _CONFIRMATION:
        raise SystemExit(f"Refusing restore: pass --confirm {_CONFIRMATION}")
    backup = Path(args.backup).resolve()
    if not backup.exists() or not backup.is_file():
        raise SystemExit("Backup file does not exist")
    verify_manifest(backup)

    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url.startswith(("postgresql://", "postgres://")):
        if shutil.which("pg_restore") is None:
            raise SystemExit("pg_restore is required for PostgreSQL restore")
        env = os.environ.copy()
        env["PGDATABASE"] = database_url
        subprocess.run(
            [
                "pg_restore",
                "--clean",
                "--if-exists",
                "--no-owner",
                "--no-acl",
                "--exit-on-error",
                str(backup),
            ],
            env=env,
            check=True,
            stdin=subprocess.DEVNULL,
        )
        backend = "postgresql"
    else:
        restore_sqlite(backup, Path(args.sqlite_destination).resolve())
        backend = "sqlite"

    print(json.dumps({"restored": True, "backend": backend, "backup": backup.name}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
