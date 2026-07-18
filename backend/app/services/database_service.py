from __future__ import annotations

import os
import re
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from app.config import settings


LATEST_SCHEMA_VERSION = 13
_INSERT_ID_TABLES = {"users", "signals", "trades"}
_INSERT_TABLE_RE = re.compile(r"^\s*INSERT\s+INTO\s+(?:[A-Za-z_][\w]*\.)?([A-Za-z_][\w]*)", re.I)


class CursorAdapter:
    def __init__(self, cursor: Any, lastrowid: int | None = None) -> None:
        self._cursor = cursor
        self._lastrowid = lastrowid

    @property
    def lastrowid(self) -> int | None:
        if self._lastrowid is not None:
            return self._lastrowid
        return getattr(self._cursor, "lastrowid", None)

    @property
    def rowcount(self) -> int:
        return int(getattr(self._cursor, "rowcount", 0))

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()


class ConnectionAdapter:
    def __init__(self, raw: Any, backend: str) -> None:
        self.raw = raw
        self.backend = backend

    def execute(self, sql: str, params: tuple | list = ()) -> CursorAdapter:
        if self.backend == "sqlite":
            return CursorAdapter(self.raw.execute(sql, tuple(params)))

        # psycopg interprets every percent sign as a client-side placeholder.
        # Escape literal SQL percent signs (for example LIKE '%USD%') before
        # translating the portable qmark placeholders used by this adapter.
        translated = sql.replace("%", "%%").replace("?", "%s")
        match = _INSERT_TABLE_RE.match(translated)
        should_return_id = (
            match is not None
            and match.group(1).lower() in _INSERT_ID_TABLES
            and "RETURNING" not in translated.upper()
        )
        if should_return_id:
            translated = translated.rstrip().rstrip(";") + " RETURNING id"
        cursor = self.raw.cursor()
        cursor.execute(translated, tuple(params))
        lastrowid = None
        if should_return_id:
            row = cursor.fetchone()
            if row is not None:
                lastrowid = int(row["id"] if isinstance(row, dict) else row[0])
        return CursorAdapter(cursor, lastrowid=lastrowid)

    def commit(self) -> None:
        self.raw.commit()

    def rollback(self) -> None:
        self.raw.rollback()


class DatabaseManager:
    _pools: dict[str, Any] = {}
    _pool_lock = threading.Lock()

    def __init__(self, db_path: str | None = None, database_url: str | None = None) -> None:
        root = Path(__file__).resolve().parents[2]
        data_dir = root / "app_data"
        data_dir.mkdir(parents=True, exist_ok=True)

        # An explicit db_path is used by isolated tests and always means SQLite.
        if db_path is not None:
            configured = db_path
        else:
            configured = (
                (database_url or "").strip()
                or os.getenv("DATABASE_URL", "").strip()
                or settings.database_url.strip()
                or os.getenv("DATABASE_PATH", "").strip()
                or settings.database_path.strip()
            )
        if configured.startswith(("postgresql://", "postgres://")):
            self.backend = "postgresql"
            self.database_url = configured
            self.sqlite_path = None
            self.persistent = True
        else:
            self.backend = "sqlite"
            self.database_url = None
            self.sqlite_path = configured or str(data_dir / "smartmoney.db")
            self.persistent = bool(configured)
        self.migrate()

    @property
    def safe_descriptor(self) -> str:
        if self.backend == "postgresql":
            return "postgresql"
        return "sqlite_explicit" if self.persistent else "sqlite_ephemeral_default"

    def _pool(self):
        if self.backend != "postgresql" or not self.database_url:
            return None
        try:
            from psycopg.rows import dict_row
            from psycopg_pool import ConnectionPool
        except ImportError as exc:
            raise RuntimeError("PostgreSQL driver is not installed") from exc

        with self._pool_lock:
            pool = self._pools.get(self.database_url)
            if pool is None:
                pool = ConnectionPool(
                    conninfo=self.database_url,
                    min_size=0,
                    max_size=max(1, settings.database_pool_max_size),
                    timeout=max(1.0, settings.database_connect_timeout_seconds),
                    kwargs={"row_factory": dict_row},
                    open=False,
                    name="apex-db-pool",
                )
                pool.open(
                    wait=True,
                    timeout=max(1.0, settings.database_connect_timeout_seconds),
                )
                self._pools[self.database_url] = pool
            return pool

    @contextmanager
    def connection(self) -> Iterator[ConnectionAdapter]:
        if self.backend == "sqlite":
            assert self.sqlite_path is not None
            raw = sqlite3.connect(
                self.sqlite_path,
                timeout=max(1.0, settings.database_connect_timeout_seconds),
            )
            raw.row_factory = sqlite3.Row
            raw.execute("PRAGMA foreign_keys = ON")
            raw.execute("PRAGMA busy_timeout = 5000")
            try:
                yield ConnectionAdapter(raw, "sqlite")
            except Exception:
                raw.rollback()
                raise
            finally:
                raw.close()
            return

        pool = self._pool()
        assert pool is not None
        with pool.connection(
            timeout=max(1.0, settings.database_connect_timeout_seconds)
        ) as raw:
            yield ConnectionAdapter(raw, "postgresql")

    def migrate(self) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TEXT NOT NULL
                )
                """
            )
            applied = {
                int(row["version"])
                for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
            }
            if 1 not in applied:
                self._apply_schema_v1(conn)
                conn.execute(
                    """
                    INSERT INTO schema_migrations (version, name, applied_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(version) DO NOTHING
                    """,
                    (1, "production_core_schema", datetime.now(timezone.utc).isoformat()),
                )
            if 2 not in applied:
                self._apply_schema_v2(conn)
                conn.execute(
                    """
                    INSERT INTO schema_migrations (version, name, applied_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(version) DO NOTHING
                    """,
                    (2, "historical_quant_dataset_registry", datetime.now(timezone.utc).isoformat()),
                )
            if 3 not in applied:
                self._apply_schema_v3(conn)
                conn.execute(
                    """
                    INSERT INTO schema_migrations (version, name, applied_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(version) DO NOTHING
                    """,
                    (3, "immutable_research_experiment_locks", datetime.now(timezone.utc).isoformat()),
                )
            if 4 not in applied:
                self._apply_schema_v4(conn)
                conn.execute(
                    """
                    INSERT INTO schema_migrations (version, name, applied_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(version) DO NOTHING
                    """,
                    (4, "encrypted_user_provider_secret_vault", datetime.now(timezone.utc).isoformat()),
                )
            if 5 not in applied:
                self._apply_schema_v5(conn)
                conn.execute(
                    """
                    INSERT INTO schema_migrations (version, name, applied_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(version) DO NOTHING
                    """,
                    (5, "paper_oms_event_ledger", datetime.now(timezone.utc).isoformat()),
                )
            if 6 not in applied:
                self._apply_schema_v6(conn)
                conn.execute(
                    """
                    INSERT INTO schema_migrations (version, name, applied_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(version) DO NOTHING
                    """,
                    (6, "paper_portfolio_equity_ledger", datetime.now(timezone.utc).isoformat()),
                )
            if 7 not in applied:
                self._apply_schema_v7(conn)
                conn.execute(
                    """
                    INSERT INTO schema_migrations (version, name, applied_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(version) DO NOTHING
                    """,
                    (7, "paper_automated_market_feed", datetime.now(timezone.utc).isoformat()),
                )
            if 8 not in applied:
                self._apply_schema_v8(conn)
                conn.execute(
                    """
                    INSERT INTO schema_migrations (version, name, applied_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(version) DO NOTHING
                    """,
                    (8, "paper_margin_funding_liquidation_ledger", datetime.now(timezone.utc).isoformat()),
                )
            if 9 not in applied:
                self._apply_schema_v9(conn)
                conn.execute(
                    """
                    INSERT INTO schema_migrations (version, name, applied_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(version) DO NOTHING
                    """,
                    (9, "paper_recovery_concentration_shadow_reconciliation", datetime.now(timezone.utc).isoformat()),
                )
            if 10 not in applied:
                self._apply_schema_v10(conn)
                conn.execute(
                    """
                    INSERT INTO schema_migrations (version, name, applied_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(version) DO NOTHING
                    """,
                    (10, "paper_statistical_correlation_snapshots", datetime.now(timezone.utc).isoformat()),
                )
            if 11 not in applied:
                self._apply_schema_v11(conn)
                conn.execute(
                    """
                    INSERT INTO schema_migrations (version, name, applied_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(version) DO NOTHING
                    """,
                    (11, "paper_private_testnet_readonly_reconciliation", datetime.now(timezone.utc).isoformat()),
                )
            if 12 not in applied:
                self._apply_schema_v12(conn)
                conn.execute(
                    """
                    INSERT INTO schema_migrations (version, name, applied_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(version) DO NOTHING
                    """,
                    (12, "paper_chaos_recovery_snapshots", datetime.now(timezone.utc).isoformat()),
                )
            if 13 not in applied:
                self._apply_schema_v13(conn)
                conn.execute(
                    """
                    INSERT INTO schema_migrations (version, name, applied_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(version) DO NOTHING
                    """,
                    (13, "paper_testnet_execution_safety", datetime.now(timezone.utc).isoformat()),
                )
            conn.commit()

    def _id_column(self) -> str:
        return "BIGSERIAL PRIMARY KEY" if self.backend == "postgresql" else "INTEGER PRIMARY KEY AUTOINCREMENT"

    def _apply_schema_v1(self, conn: ConnectionAdapter) -> None:
        id_column = self._id_column()
        user_id_type = "BIGINT" if self.backend == "postgresql" else "INTEGER"
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS users (
                id {id_column},
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id {user_id_type} NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS signals (
                id {id_column},
                user_id {user_id_type},
                symbol TEXT NOT NULL,
                market TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                direction TEXT NOT NULL,
                score REAL NOT NULL,
                confidence TEXT NOT NULL,
                session_name TEXT NOT NULL,
                news_blocked INTEGER NOT NULL,
                entry_low REAL,
                entry_high REAL,
                stop_loss REAL,
                take_profits_json TEXT NOT NULL,
                risk_to_reward REAL,
                score_breakdown_json TEXT NOT NULL DEFAULT '{{}}',
                setup_grade TEXT NOT NULL DEFAULT 'C',
                execution_label TEXT NOT NULL DEFAULT 'observe',
                entry_model TEXT NOT NULL DEFAULT 'No Trade',
                ai_summary TEXT NOT NULL DEFAULT '',
                confluence_tags_json TEXT NOT NULL DEFAULT '[]',
                risk_flags_json TEXT NOT NULL DEFAULT '[]',
                reasons_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS trades (
                id {id_column},
                user_id {user_id_type},
                symbol TEXT NOT NULL,
                market TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                stop_loss REAL NOT NULL,
                take_profit REAL,
                exit_price REAL,
                size REAL NOT NULL,
                pnl_amount REAL,
                status TEXT NOT NULL,
                notes TEXT NOT NULL,
                created_at TEXT NOT NULL,
                closed_at TEXT
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS device_tokens (
                id {id_column},
                user_id {user_id_type} NOT NULL,
                token TEXT NOT NULL UNIQUE,
                platform TEXT NOT NULL,
                device_name TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS notification_events (
                id {id_column},
                user_id {user_id_type} NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                mode TEXT NOT NULL,
                sent_count INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        # Upgrade pre-RC SQLite databases in-place. PostgreSQL uses IF NOT EXISTS
        # to remain safe across concurrent deployment instances.
        self._ensure_columns(
            conn,
            "signals",
            [
                f"user_id {user_id_type}",
                "score_breakdown_json TEXT NOT NULL DEFAULT '{}'",
                "setup_grade TEXT NOT NULL DEFAULT 'C'",
                "execution_label TEXT NOT NULL DEFAULT 'observe'",
                "entry_model TEXT NOT NULL DEFAULT 'No Trade'",
                "ai_summary TEXT NOT NULL DEFAULT ''",
                "confluence_tags_json TEXT NOT NULL DEFAULT '[]'",
                "risk_flags_json TEXT NOT NULL DEFAULT '[]'",
            ],
        )
        self._ensure_columns(conn, "trades", [f"user_id {user_id_type}"])
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_user_id_id ON signals(user_id, id DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_user_id_id ON trades(user_id, id DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user_created ON notification_events(user_id, created_at DESC)")

    def _apply_schema_v2(self, conn: ConnectionAdapter) -> None:
        id_column = self._id_column()
        user_id_type = "BIGINT" if self.backend == "postgresql" else "INTEGER"
        binary_type = "BYTEA" if self.backend == "postgresql" else "BLOB"
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS quant_datasets (
                id {id_column},
                user_id {user_id_type} NOT NULL,
                dataset_id TEXT NOT NULL,
                version TEXT NOT NULL,
                source TEXT NOT NULL,
                symbol TEXT NOT NULL,
                market TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                sample_count INTEGER NOT NULL,
                source_sha256 TEXT NOT NULL,
                canonical_sha256 TEXT NOT NULL,
                data_quality_score REAL NOT NULL,
                manifest_json TEXT NOT NULL,
                candles_gzip {binary_type} NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, dataset_id, version)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_quant_datasets_user_symbol_timeframe "
            "ON quant_datasets(user_id, symbol, timeframe, created_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_quant_datasets_created "
            "ON quant_datasets(created_at DESC)"
        )

    def _apply_schema_v3(self, conn: ConnectionAdapter) -> None:
        id_column = self._id_column()
        user_id_type = "BIGINT" if self.backend == "postgresql" else "INTEGER"
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS research_experiments (
                id {id_column},
                user_id {user_id_type} NOT NULL,
                experiment_id TEXT NOT NULL,
                version TEXT NOT NULL,
                dataset_id TEXT NOT NULL,
                dataset_version TEXT NOT NULL,
                dataset_sha256 TEXT NOT NULL,
                request_sha256 TEXT NOT NULL,
                development_end_index INTEGER NOT NULL,
                holdout_start_index INTEGER NOT NULL,
                holdout_end_index INTEGER NOT NULL,
                status TEXT NOT NULL,
                result_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, experiment_id, version)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_research_experiments_user_created "
            "ON research_experiments(user_id, created_at DESC)"
        )

    def _apply_schema_v4(self, conn: ConnectionAdapter) -> None:
        id_column = self._id_column()
        user_id_type = "BIGINT" if self.backend == "postgresql" else "INTEGER"
        binary_type = "BYTEA" if self.backend == "postgresql" else "BLOB"
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS user_provider_secrets (
                id {id_column},
                user_id {user_id_type} NOT NULL,
                provider TEXT NOT NULL,
                ciphertext {binary_type} NOT NULL,
                nonce {binary_type} NOT NULL,
                key_version INTEGER NOT NULL,
                enabled INTEGER NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{{}}',
                last_test_status TEXT,
                last_tested_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, provider)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_user_provider_secrets_user "
            "ON user_provider_secrets(user_id, provider)"
        )

    def _apply_schema_v5(self, conn: ConnectionAdapter) -> None:
        id_column = self._id_column()
        user_id_type = "BIGINT" if self.backend == "postgresql" else "INTEGER"
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS paper_execution_controls (
                user_id {user_id_type} PRIMARY KEY,
                paper_trading_enabled INTEGER NOT NULL,
                kill_switch_engaged INTEGER NOT NULL,
                max_open_orders INTEGER NOT NULL,
                max_order_notional REAL NOT NULL,
                default_fee_bps REAL NOT NULL,
                default_slippage_bps REAL NOT NULL,
                max_daily_drawdown_pct REAL NOT NULL DEFAULT 3.0,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS paper_orders (
                order_id TEXT PRIMARY KEY,
                user_id {user_id_type} NOT NULL,
                idempotency_key TEXT NOT NULL,
                request_hash TEXT NOT NULL,
                symbol TEXT NOT NULL,
                market TEXT NOT NULL,
                side TEXT NOT NULL,
                order_type TEXT NOT NULL,
                quantity REAL NOT NULL,
                limit_price REAL,
                time_in_force TEXT NOT NULL,
                status TEXT NOT NULL,
                filled_quantity REAL NOT NULL,
                average_fill_price REAL,
                total_fees REAL NOT NULL,
                reference_bid REAL NOT NULL,
                reference_ask REAL NOT NULL,
                max_slippage_bps REAL NOT NULL,
                fee_bps REAL NOT NULL,
                signal_score REAL NOT NULL,
                risk_approved INTEGER NOT NULL,
                strategy_id TEXT,
                setup_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                terminal_at TEXT,
                UNIQUE(user_id, idempotency_key)
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS paper_fills (
                fill_id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                user_id {user_id_type} NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                fee_amount REAL NOT NULL,
                liquidity TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS paper_order_events (
                event_id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                user_id {user_id_type} NOT NULL,
                sequence INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                from_status TEXT,
                to_status TEXT NOT NULL,
                reason TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(order_id, sequence)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_paper_orders_user_status "
            "ON paper_orders(user_id, status, created_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_paper_fills_order ON paper_fills(order_id, created_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_paper_events_order ON paper_order_events(order_id, sequence)"
        )

    def _apply_schema_v6(self, conn: ConnectionAdapter) -> None:
        user_id_type = "BIGINT" if self.backend == "postgresql" else "INTEGER"
        self._ensure_columns(
            conn,
            "paper_execution_controls",
            ["max_daily_drawdown_pct REAL NOT NULL DEFAULT 3.0"],
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS paper_accounts (
                user_id {user_id_type} PRIMARY KEY,
                initial_cash REAL NOT NULL,
                cash_balance REAL NOT NULL,
                realized_pnl REAL NOT NULL,
                total_fees REAL NOT NULL,
                peak_equity REAL NOT NULL,
                daily_start_equity REAL NOT NULL,
                trading_day TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS paper_positions (
                user_id {user_id_type} NOT NULL,
                symbol TEXT NOT NULL,
                market TEXT NOT NULL,
                quantity REAL NOT NULL,
                average_entry_price REAL,
                mark_price REAL,
                realized_pnl REAL NOT NULL,
                total_fees REAL NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(user_id, symbol)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_paper_positions_user ON paper_positions(user_id, symbol)"
        )

    def _apply_schema_v7(self, conn: ConnectionAdapter) -> None:
        user_id_type = "BIGINT" if self.backend == "postgresql" else "INTEGER"
        self._ensure_columns(
            conn,
            "paper_execution_controls",
            [
                "automated_feed_enabled INTEGER NOT NULL DEFAULT 0",
                "max_tick_age_seconds INTEGER NOT NULL DEFAULT 30",
            ],
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS paper_feed_subscriptions (
                user_id {user_id_type} NOT NULL,
                symbol TEXT NOT NULL,
                market TEXT NOT NULL,
                provider TEXT NOT NULL,
                enabled INTEGER NOT NULL,
                poll_interval_seconds INTEGER NOT NULL,
                next_poll_at TEXT NOT NULL,
                last_attempt_at TEXT,
                last_success_at TEXT,
                last_provider_timestamp TEXT,
                last_event_id TEXT,
                consecutive_failures INTEGER NOT NULL DEFAULT 0,
                last_error_code TEXT,
                lease_owner TEXT,
                lease_until TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(user_id, symbol)
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS paper_market_ticks (
                tick_id TEXT PRIMARY KEY,
                user_id {user_id_type} NOT NULL,
                event_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                source TEXT NOT NULL,
                bid REAL NOT NULL,
                ask REAL NOT NULL,
                available_quantity REAL NOT NULL,
                provider_timestamp TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                affected_order_ids_json TEXT NOT NULL,
                received_at TEXT NOT NULL,
                processed_at TEXT NOT NULL,
                UNIQUE(user_id, event_id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_paper_feed_due "
            "ON paper_feed_subscriptions(enabled, next_poll_at, lease_until)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_paper_ticks_user_symbol "
            "ON paper_market_ticks(user_id, symbol, processed_at DESC)"
        )

    def _apply_schema_v8(self, conn: ConnectionAdapter) -> None:
        user_id_type = "BIGINT" if self.backend == "postgresql" else "INTEGER"
        self._ensure_columns(
            conn,
            "paper_execution_controls",
            [
                "max_leverage REAL NOT NULL DEFAULT 10.0",
                "default_maintenance_margin_rate REAL NOT NULL DEFAULT 0.005",
                "liquidation_fee_bps REAL NOT NULL DEFAULT 20.0",
                "max_margin_utilization_pct REAL NOT NULL DEFAULT 70.0",
            ],
        )
        self._ensure_columns(
            conn,
            "paper_orders",
            [
                "leverage REAL NOT NULL DEFAULT 1.0",
                "margin_mode TEXT NOT NULL DEFAULT 'isolated'",
                "maintenance_margin_rate REAL NOT NULL DEFAULT 0.005",
            ],
        )
        self._ensure_columns(
            conn,
            "paper_accounts",
            [
                "total_funding REAL NOT NULL DEFAULT 0.0",
                "liquidation_count INTEGER NOT NULL DEFAULT 0",
            ],
        )
        self._ensure_columns(
            conn,
            "paper_positions",
            [
                "leverage REAL NOT NULL DEFAULT 1.0",
                "margin_mode TEXT NOT NULL DEFAULT 'isolated'",
                "initial_margin REAL NOT NULL DEFAULT 0.0",
                "maintenance_margin_rate REAL NOT NULL DEFAULT 0.005",
                "liquidation_price REAL",
                "accumulated_funding REAL NOT NULL DEFAULT 0.0",
                "position_status TEXT NOT NULL DEFAULT 'flat'",
                "liquidated_at TEXT",
            ],
        )
        conn.execute(
            """
            UPDATE paper_positions
            SET initial_margin = ABS(quantity * COALESCE(average_entry_price, mark_price, 0.0))
            WHERE ABS(quantity) > 0.0 AND initial_margin <= 0.0
            """
        )
        conn.execute(
            """
            UPDATE paper_positions
            SET position_status = CASE WHEN ABS(quantity) > 0.0 THEN 'open' ELSE 'flat' END
            WHERE position_status IS NULL OR position_status = 'flat'
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS paper_margin_events (
                event_id TEXT NOT NULL,
                user_id {user_id_type} NOT NULL,
                event_type TEXT NOT NULL,
                symbol TEXT NOT NULL,
                amount REAL NOT NULL,
                funding_rate REAL,
                mark_price REAL,
                realized_pnl REAL NOT NULL DEFAULT 0.0,
                source TEXT NOT NULL,
                is_real_rate INTEGER NOT NULL DEFAULT 0,
                payload_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(user_id, event_id),
                UNIQUE(user_id, event_type, payload_hash)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_paper_margin_events_user_created "
            "ON paper_margin_events(user_id, created_at DESC)"
        )

    def _apply_schema_v9(self, conn: ConnectionAdapter) -> None:
        user_id_type = "BIGINT" if self.backend == "postgresql" else "INTEGER"
        self._ensure_columns(
            conn,
            "paper_execution_controls",
            [
                "max_symbol_margin_pct REAL NOT NULL DEFAULT 30.0",
                "max_risk_group_margin_pct REAL NOT NULL DEFAULT 50.0",
                "max_directional_notional_multiple REAL NOT NULL DEFAULT 3.0",
            ],
        )
        self._ensure_columns(
            conn,
            "paper_orders",
            ["risk_group TEXT NOT NULL DEFAULT 'unclassified'"],
        )
        self._ensure_columns(
            conn,
            "paper_positions",
            ["risk_group TEXT NOT NULL DEFAULT 'unclassified'"],
        )
        for table in ("paper_orders", "paper_positions"):
            conn.execute(
                f"""
                UPDATE {table}
                SET risk_group = CASE
                    WHEN market = 'crypto' AND (UPPER(symbol) LIKE 'BTC%' OR UPPER(symbol) LIKE 'ETH%')
                        THEN 'crypto_major_structural_proxy'
                    WHEN market = 'crypto' AND (UPPER(symbol) LIKE 'USDT%' OR UPPER(symbol) LIKE 'USDC%' OR UPPER(symbol) LIKE 'DAI%')
                        THEN 'crypto_stable_structural_proxy'
                    WHEN market = 'crypto' THEN 'crypto_alt_structural_proxy'
                    WHEN UPPER(symbol) LIKE 'XAU%' OR UPPER(symbol) LIKE 'XAG%'
                        THEN 'metals_usd_structural_proxy'
                    WHEN UPPER(symbol) LIKE '%USD%' THEN 'forex_usd_structural_proxy'
                    WHEN UPPER(symbol) LIKE '%EUR%' THEN 'forex_eur_structural_proxy'
                    ELSE 'other_structural_proxy'
                END
                WHERE risk_group = 'unclassified'
                """
            )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS paper_connector_checkpoints (
                user_id {user_id_type} NOT NULL,
                connector TEXT NOT NULL,
                state TEXT NOT NULL,
                consecutive_failures INTEGER NOT NULL DEFAULT 0,
                backoff_until TEXT,
                latency_ms INTEGER,
                server_time_offset_ms INTEGER,
                last_probe_at TEXT,
                last_success_at TEXT,
                last_error_code TEXT,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(user_id, connector)
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS paper_shadow_reconciliations (
                user_id {user_id_type} NOT NULL,
                run_id TEXT NOT NULL,
                connector TEXT NOT NULL,
                snapshot_id TEXT NOT NULL,
                request_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                matched_orders INTEGER NOT NULL,
                mismatched_orders INTEGER NOT NULL,
                missing_local_orders INTEGER NOT NULL,
                missing_external_orders INTEGER NOT NULL,
                issues_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(user_id, run_id),
                UNIQUE(user_id, connector, snapshot_id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_paper_connector_state "
            "ON paper_connector_checkpoints(user_id, state)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_paper_shadow_reconcile_created "
            "ON paper_shadow_reconciliations(user_id, created_at DESC)"
        )

    def _apply_schema_v10(self, conn: ConnectionAdapter) -> None:
        user_id_type = "BIGINT" if self.backend == "postgresql" else "INTEGER"
        for table in ("paper_orders", "paper_positions"):
            self._ensure_columns(
                conn,
                table,
                [
                    "correlation_source TEXT NOT NULL DEFAULT 'structural_proxy'",
                    "correlation_snapshot_id TEXT",
                ],
            )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS paper_correlation_snapshots (
                user_id {user_id_type} NOT NULL,
                snapshot_id TEXT NOT NULL,
                request_hash TEXT NOT NULL,
                dataset_refs_json TEXT NOT NULL,
                symbols_json TEXT NOT NULL,
                observations INTEGER NOT NULL,
                matrix_json TEXT NOT NULL,
                clusters_json TEXT NOT NULL,
                cluster_threshold REAL NOT NULL,
                shrinkage_weight REAL NOT NULL,
                canonical_sha256 TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(user_id, snapshot_id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_paper_correlation_created "
            "ON paper_correlation_snapshots(user_id, created_at DESC)"
        )

    def _apply_schema_v11(self, conn: ConnectionAdapter) -> None:
        user_id_type = "BIGINT" if self.backend == "postgresql" else "INTEGER"
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS paper_private_testnet_reconciliations (
                user_id {user_id_type} NOT NULL,
                reconciliation_id TEXT NOT NULL,
                connector TEXT NOT NULL,
                status TEXT NOT NULL,
                external_order_count INTEGER NOT NULL,
                external_fill_count INTEGER NOT NULL,
                matched_orders INTEGER NOT NULL,
                mismatched_orders INTEGER NOT NULL,
                issues_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(user_id, reconciliation_id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_private_testnet_reconcile_created "
            "ON paper_private_testnet_reconciliations(user_id, created_at DESC)"
        )

    def _apply_schema_v12(self, conn: ConnectionAdapter) -> None:
        user_id_type = "BIGINT" if self.backend == "postgresql" else "INTEGER"
        binary_type = "BYTEA" if self.backend == "postgresql" else "BLOB"
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS paper_recovery_snapshots (
                user_id {user_id_type} NOT NULL,
                snapshot_id TEXT NOT NULL,
                canonical_sha256 TEXT NOT NULL,
                payload_gzip {binary_type} NOT NULL,
                row_counts_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(user_id, snapshot_id)
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS paper_chaos_runs (
                user_id {user_id_type} NOT NULL,
                run_id TEXT NOT NULL,
                request_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(user_id, run_id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_paper_recovery_snapshots_created "
            "ON paper_recovery_snapshots(user_id, created_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_paper_chaos_runs_created "
            "ON paper_chaos_runs(user_id, created_at DESC)"
        )

    def _apply_schema_v13(self, conn: ConnectionAdapter) -> None:
        user_id_type = "BIGINT" if self.backend == "postgresql" else "INTEGER"
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS paper_testnet_execution_controls (
                user_id {user_id_type} PRIMARY KEY,
                enabled INTEGER NOT NULL,
                kill_switch_engaged INTEGER NOT NULL,
                max_order_notional REAL NOT NULL,
                max_open_orders INTEGER NOT NULL,
                allowed_symbols_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS paper_testnet_orders (
                order_id TEXT PRIMARY KEY,
                user_id {user_id_type} NOT NULL,
                idempotency_key TEXT NOT NULL,
                request_hash TEXT NOT NULL,
                client_order_id TEXT NOT NULL,
                connector TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                reference_price REAL NOT NULL,
                reduce_only INTEGER NOT NULL,
                status TEXT NOT NULL,
                external_order_id TEXT,
                last_error_code TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, idempotency_key),
                UNIQUE(user_id, client_order_id)
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_testnet_orders_user_status ON paper_testnet_orders(user_id, status, created_at DESC)")

    def _ensure_columns(
        self,
        conn: ConnectionAdapter,
        table: str,
        definitions: list[str],
    ) -> None:
        if self.backend == "postgresql":
            for definition in definitions:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {definition}")
            return
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        existing = {str(row["name"]) for row in rows}
        for definition in definitions:
            column = definition.split()[0]
            if column not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")

    def schema_version(self) -> int:
        with self.connection() as conn:
            row = conn.execute("SELECT COALESCE(MAX(version), 0) AS version FROM schema_migrations").fetchone()
        return int(row["version"] if row else 0)

    def health(self) -> dict[str, Any]:
        started = time.monotonic()
        try:
            with self.connection() as conn:
                conn.execute("SELECT 1 AS ok").fetchone()
                row = conn.execute(
                    "SELECT COALESCE(MAX(version), 0) AS version FROM schema_migrations"
                ).fetchone()
            return {
                "connected": True,
                "backend": self.backend,
                "descriptor": self.safe_descriptor,
                "persistent": self.persistent,
                "schema_version": int(row["version"] if row else 0),
                "latest_schema_version": LATEST_SCHEMA_VERSION,
                "migration_current": int(row["version"] if row else 0) == LATEST_SCHEMA_VERSION,
                "latency_ms": max(0, int((time.monotonic() - started) * 1000)),
            }
        except Exception:
            return {
                "connected": False,
                "backend": self.backend,
                "descriptor": self.safe_descriptor,
                "persistent": self.persistent,
                "schema_version": 0,
                "latest_schema_version": LATEST_SCHEMA_VERSION,
                "migration_current": False,
                "latency_ms": max(0, int((time.monotonic() - started) * 1000)),
            }

    def sqlite_integrity_check(self) -> str:
        if self.backend != "sqlite":
            return "not_applicable"
        with self.connection() as conn:
            row = conn.execute("PRAGMA integrity_check").fetchone()
        return str(row[0] if not hasattr(row, "keys") else row[0])

    def backup_sqlite(self, destination: str) -> str:
        if self.backend != "sqlite" or not self.sqlite_path:
            raise RuntimeError("SQLite backup is available only for the SQLite backend")
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        source = sqlite3.connect(self.sqlite_path)
        backup = sqlite3.connect(str(target))
        try:
            source.backup(backup)
        finally:
            backup.close()
            source.close()
        return str(target)
