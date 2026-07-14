from __future__ import annotations

import base64
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from app.config import settings
from app.models import AuthLoginRequest, AuthRegisterRequest
from app.services.auth_service import AuthService
from app.services.database_service import ConnectionAdapter, DatabaseManager, LATEST_SCHEMA_VERSION
from app.services.production_guard_service import (
    MonitoringService,
    SlidingWindowRateLimiter,
    client_identity,
    request_id,
)
from app.services.readiness_service import ReadinessService


def test_sqlite_migration_upgrades_legacy_schema_and_reports_integrity(tmp_path):
    db_path = tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL, market TEXT NOT NULL, timeframe TEXT NOT NULL,
                direction TEXT NOT NULL, score REAL NOT NULL, confidence TEXT NOT NULL,
                session_name TEXT NOT NULL, news_blocked INTEGER NOT NULL,
                entry_low REAL, entry_high REAL, stop_loss REAL,
                take_profits_json TEXT NOT NULL, risk_to_reward REAL,
                reasons_json TEXT NOT NULL, created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL, market TEXT NOT NULL, direction TEXT NOT NULL,
                entry_price REAL NOT NULL, stop_loss REAL NOT NULL, take_profit REAL,
                exit_price REAL, size REAL NOT NULL, pnl_amount REAL, status TEXT NOT NULL,
                notes TEXT NOT NULL, created_at TEXT NOT NULL, closed_at TEXT
            )
            """
        )

    database = DatabaseManager(db_path=str(db_path))
    health = database.health()
    assert health["connected"] is True
    assert health["schema_version"] == LATEST_SCHEMA_VERSION
    assert health["migration_current"] is True
    assert database.sqlite_integrity_check() == "ok"

    with sqlite3.connect(db_path) as conn:
        signal_columns = {row[1] for row in conn.execute("PRAGMA table_info(signals)")}
        trade_columns = {row[1] for row in conn.execute("PRAGMA table_info(trades)")}
        migration = conn.execute("SELECT name FROM schema_migrations WHERE version=1").fetchone()
    assert {"user_id", "score_breakdown_json", "ai_summary", "risk_flags_json"} <= signal_columns
    assert "user_id" in trade_columns
    assert migration == ("production_core_schema",)


def test_postgresql_adapter_translates_parameters_and_returning_id():
    class FakeCursor:
        def __init__(self):
            self.sql = ""
            self.params = ()
            self.rowcount = 1

        def execute(self, sql, params):
            self.sql = sql
            self.params = params

        def fetchone(self):
            return {"id": 42}

        def fetchall(self):
            return []

    class FakeRaw:
        def __init__(self):
            self.cursors = []

        def cursor(self):
            cursor = FakeCursor()
            self.cursors.append(cursor)
            return cursor

        def commit(self):
            pass

        def rollback(self):
            pass

    raw = FakeRaw()
    connection = ConnectionAdapter(raw, "postgresql")
    cursor = connection.execute(
        "INSERT INTO users (name, email) VALUES (?, ?)",
        ("A", "a@example.com"),
    )
    assert raw.cursors[-1].sql.endswith("RETURNING id")
    assert "%s" in raw.cursors[-1].sql and "?" not in raw.cursors[-1].sql
    assert cursor.lastrowid == 42

    connection.execute("SELECT * FROM users WHERE id = ?", (42,))
    assert "RETURNING" not in raw.cursors[-1].sql
    assert raw.cursors[-1].params == (42,)


def test_postgresql_schema_uses_bigserial_and_idempotent_columns():
    class DummyCursor:
        rowcount = 0
        lastrowid = None

        def fetchone(self):
            return None

        def fetchall(self):
            return []

    class Collector:
        def __init__(self):
            self.statements = []

        def execute(self, sql, params=()):
            self.statements.append(sql)
            return DummyCursor()

    manager = DatabaseManager.__new__(DatabaseManager)
    manager.backend = "postgresql"
    collector = Collector()
    manager._apply_schema_v1(collector)
    ddl = "\n".join(collector.statements)
    assert "BIGSERIAL PRIMARY KEY" in ddl
    assert "AUTOINCREMENT" not in ddl
    assert "ADD COLUMN IF NOT EXISTS" in ddl
    assert "user_id BIGINT" in ddl


def test_auth_hashes_session_tokens_and_upgrades_legacy_password(tmp_path):
    db_path = tmp_path / "auth.db"
    auth = AuthService(db_path=str(db_path), seed_demo_user=False)
    registered = auth.register(
        AuthRegisterRequest(name="RC User", email="rc@example.com", password="StrongPass123!")
    )
    assert auth.get_user_by_token(registered.access_token).email == "rc@example.com"

    with sqlite3.connect(db_path) as conn:
        stored_token = conn.execute("SELECT token FROM sessions").fetchone()[0]
        stored_hash = conn.execute("SELECT password_hash FROM users").fetchone()[0]
    assert registered.access_token != stored_token
    assert stored_token == hashlib.sha256(registered.access_token.encode()).hexdigest()
    assert stored_hash.startswith("pbkdf2_sha256$310000$")

    salt = b"0123456789abcdef"
    digest = hashlib.pbkdf2_hmac("sha256", b"LegacyPass123!", salt, 100_000)
    legacy = f"{base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO users (name,email,password_hash,created_at) VALUES (?,?,?,?)",
            ("Legacy", "legacy@example.com", legacy, "2026-07-14T00:00:00+00:00"),
        )
        conn.commit()
    auth.login(AuthLoginRequest(email="legacy@example.com", password="LegacyPass123!"))
    with sqlite3.connect(db_path) as conn:
        upgraded = conn.execute(
            "SELECT password_hash FROM users WHERE email='legacy@example.com'"
        ).fetchone()[0]
    assert upgraded.startswith("pbkdf2_sha256$310000$")


def test_rate_limit_request_id_proxy_and_monitoring_are_deterministic(monkeypatch):
    clock = [1000.0]
    limiter = SlidingWindowRateLimiter(now_fn=lambda: clock[0])
    monkeypatch.setattr(settings, "rate_limit_auth_per_minute", 2)
    first = limiter.check("client", "/api/v1/auth/login")
    second = limiter.check("client", "/api/v1/auth/register")
    third = limiter.check("client", "/api/v1/auth/login")
    assert first.allowed and second.allowed
    assert third.allowed is False and third.retry_after_seconds == 60
    clock[0] += 61
    assert limiter.check("client", "/api/v1/auth/login").allowed is True

    assert request_id("valid_Request-123") == "valid_Request-123"
    assert request_id("bad id with spaces") != "bad id with spaces"
    monkeypatch.setattr(settings, "trust_proxy_headers", False)
    direct = client_identity("10.0.0.1", "203.0.113.5")
    monkeypatch.setattr(settings, "trust_proxy_headers", True)
    proxied = client_identity("10.0.0.1", "203.0.113.5")
    assert direct != proxied
    assert "203.0.113.5" not in proxied

    metrics = MonitoringService(now_fn=lambda: clock[0])
    metrics.record("/health", 200, 10)
    metrics.record("/api/v1/test", 500, 90)
    metrics.record_rate_limited()
    snapshot = metrics.snapshot()
    assert snapshot["requests_total"] == 2
    assert snapshot["server_errors_total"] == 1
    assert snapshot["rate_limited_total"] == 1
    assert snapshot["latency_p95_ms"] == 90


def test_readiness_blocks_sqlite_in_production(monkeypatch, tmp_path):
    database = DatabaseManager(db_path=str(tmp_path / "readiness.db"))
    monkeypatch.setattr(settings, "app_env", "production")
    item = ReadinessService(database)._database_persistence_check()
    assert item.status == "missing"
    assert item.key == "DATABASE_URL"


def test_sqlite_backup_and_restore_scripts_verify_manifest(tmp_path):
    source = tmp_path / "source.db"
    with sqlite3.connect(source) as conn:
        conn.execute("CREATE TABLE proof (value TEXT NOT NULL)")
        conn.execute("INSERT INTO proof VALUES ('rc-backup-ok')")
        conn.commit()

    output_dir = tmp_path / "backups"
    env = os.environ.copy()
    env.pop("DATABASE_URL", None)
    env["DATABASE_PATH"] = str(source)
    backup = subprocess.run(
        [sys.executable, "scripts/backup_database.py", "--output-dir", str(output_dir)],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    manifest = json.loads(backup.stdout.strip())
    backup_path = output_dir / manifest["file"]
    assert backup_path.exists()
    assert manifest["sha256"]
    assert manifest["contains_connection_string"] is False

    destination = tmp_path / "restored.db"
    restore_env = env.copy()
    restore_env["DATABASE_PATH"] = str(destination)
    subprocess.run(
        [
            sys.executable,
            "scripts/restore_database.py",
            str(backup_path),
            "--confirm",
            "RESTORE_APEX_DATABASE",
            "--sqlite-destination",
            str(destination),
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=restore_env,
        check=True,
        capture_output=True,
        text=True,
    )
    with sqlite3.connect(destination) as conn:
        value = conn.execute("SELECT value FROM proof").fetchone()[0]
    assert value == "rc-backup-ok"


def test_release_manifest_and_production_blueprint_are_traceable(tmp_path):
    root = Path(__file__).resolve().parents[2]
    apk = tmp_path / "apex.apk"
    apk.write_bytes(b"deterministic-test-apk")
    manifest_path = tmp_path / "release-manifest.json"
    env = os.environ.copy()
    env["GITHUB_SHA"] = "a" * 40
    subprocess.run(
        [
            sys.executable,
            "scripts/generate_release_manifest.py",
            "--apk",
            str(apk),
            "--output",
            str(manifest_path),
            "--version",
            "3.0.0-rc1",
        ],
        cwd=root / "backend",
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    manifest = json.loads(manifest_path.read_text())
    assert manifest["source_commit"] == "a" * 40
    assert manifest["artifact"]["sha256"] == hashlib.sha256(apk.read_bytes()).hexdigest()
    assert manifest["safety"]["live_execution_expected"] is False
    assert manifest["safety"]["deterministic_core_override_allowed"] is False

    render = (root / "render.yaml").read_text()
    assert "fromDatabase:" in render
    assert "healthCheckPath: /ready" in render
    assert "postgresMajorVersion: \"16\"" in render
    assert "ENABLE_LIVE_EXECUTION\n        value: false" in render
    assert "AI_EXTERNAL_ENABLED\n        value: false" in render
