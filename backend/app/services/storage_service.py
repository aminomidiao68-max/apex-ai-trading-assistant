from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.config import settings
from app.models import (
    AnalyticsReport,
    AnalyticsSummary,
    AnalyticsSymbolCount,
    DeviceTokenItem,
    DeviceTokenRegisterRequest,
    MarketType,
    ScoreBreakdown,
    SignalDirection,
    SignalHistoryItem,
    SignalResponse,
    SignalSymbolStats,
    TradeJournalCloseRequest,
    TradeJournalCreateRequest,
    TradeJournalItem,
    TradeJournalStats,
    TradePerformanceBySymbol,
)


class StorageService:
    def __init__(self, db_path: str | None = None) -> None:
        root = Path(__file__).resolve().parents[2]
        data_dir = root / "app_data"
        data_dir.mkdir(parents=True, exist_ok=True)
        configured_path = settings.database_path.strip()
        self.db_path = db_path or configured_path or str(data_dir / "smartmoney.db")
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _column_exists(self, conn: sqlite3.Connection, table: str, column: str) -> bool:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return any(row["name"] == column for row in rows)

    def _ensure_column(self, conn: sqlite3.Connection, table: str, definition: str) -> None:
        column_name = definition.split()[0]
        if not self._column_exists(conn, table, column_name):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                    reasons_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            self._ensure_column(conn, "signals", "user_id INTEGER")
            self._ensure_column(conn, "signals", "score_breakdown_json TEXT NOT NULL DEFAULT '{}'")
            self._ensure_column(conn, "signals", "setup_grade TEXT NOT NULL DEFAULT 'C'")
            self._ensure_column(conn, "signals", "execution_label TEXT NOT NULL DEFAULT 'observe'")
            self._ensure_column(conn, "signals", "entry_model TEXT NOT NULL DEFAULT 'No Trade'")
            self._ensure_column(conn, "signals", "ai_summary TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "signals", "confluence_tags_json TEXT NOT NULL DEFAULT '[]'")
            self._ensure_column(conn, "signals", "risk_flags_json TEXT NOT NULL DEFAULT '[]'")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            self._ensure_column(conn, "trades", "user_id INTEGER")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_user_id_id ON signals(user_id, id DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_user_id_id ON trades(user_id, id DESC)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS device_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token TEXT NOT NULL UNIQUE,
                    platform TEXT NOT NULL,
                    device_name TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notification_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    sent_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def save_signal(self, signal: SignalResponse, user_id: int | None = None) -> SignalHistoryItem:
        created_at = self._now()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO signals (
                    user_id, symbol, market, timeframe, direction, score, confidence, session_name,
                    news_blocked, entry_low, entry_high, stop_loss, take_profits_json,
                    risk_to_reward, score_breakdown_json, setup_grade, execution_label,
                    entry_model, ai_summary, confluence_tags_json, risk_flags_json,
                    reasons_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    signal.symbol,
                    signal.market.value,
                    signal.timeframe,
                    signal.direction.value,
                    signal.score,
                    signal.confidence,
                    signal.session_name,
                    1 if signal.news_blocked else 0,
                    signal.entry_low,
                    signal.entry_high,
                    signal.stop_loss,
                    json.dumps(signal.take_profits),
                    signal.risk_to_reward,
                    json.dumps(signal.score_breakdown.model_dump()),
                    signal.setup_grade,
                    signal.execution_label,
                    signal.entry_model,
                    signal.ai_summary,
                    json.dumps(signal.confluence_tags),
                    json.dumps(signal.risk_flags),
                    json.dumps(signal.reasons),
                    created_at,
                ),
            )
            conn.commit()
            signal_id = int(cursor.lastrowid)

        return SignalHistoryItem(
            id=signal_id,
            symbol=signal.symbol,
            market=signal.market,
            timeframe=signal.timeframe,
            direction=signal.direction,
            score=signal.score,
            confidence=signal.confidence,
            session_name=signal.session_name,
            news_blocked=signal.news_blocked,
            entry_low=signal.entry_low,
            entry_high=signal.entry_high,
            stop_loss=signal.stop_loss,
            take_profits=signal.take_profits,
            risk_to_reward=signal.risk_to_reward,
            score_breakdown=signal.score_breakdown,
            setup_grade=signal.setup_grade,
            execution_label=signal.execution_label,
            entry_model=signal.entry_model,
            ai_summary=signal.ai_summary,
            confluence_tags=signal.confluence_tags,
            risk_flags=signal.risk_flags,
            reasons=signal.reasons,
            created_at=created_at,
        )

    def list_signals(self, limit: int = 30, user_id: int | None = None) -> list[SignalHistoryItem]:
        limit = max(1, min(limit, 200))
        with self._connect() as conn:
            if user_id is None:
                rows = conn.execute(
                    "SELECT * FROM signals ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM signals WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                    (user_id, limit),
                ).fetchall()
        return [self._signal_row_to_model(row) for row in rows]

    def create_trade(self, request: TradeJournalCreateRequest, user_id: int | None = None) -> TradeJournalItem:
        created_at = self._now()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO trades (
                    user_id, symbol, market, direction, entry_price, stop_loss, take_profit,
                    size, pnl_amount, status, notes, created_at, closed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    request.symbol,
                    request.market.value,
                    request.direction.value,
                    request.entry_price,
                    request.stop_loss,
                    request.take_profit,
                    request.size,
                    None,
                    "open",
                    request.notes,
                    created_at,
                    None,
                ),
            )
            conn.commit()
            trade_id = int(cursor.lastrowid)
            row = conn.execute("SELECT * FROM trades WHERE id = ?", (trade_id,)).fetchone()
        return self._trade_row_to_model(row)

    def list_trades(self, limit: int = 50, user_id: int | None = None) -> list[TradeJournalItem]:
        limit = max(1, min(limit, 200))
        with self._connect() as conn:
            if user_id is None:
                rows = conn.execute(
                    "SELECT * FROM trades ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM trades WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                    (user_id, limit),
                ).fetchall()
        return [self._trade_row_to_model(row) for row in rows]

    def close_trade(
        self,
        trade_id: int,
        request: TradeJournalCloseRequest,
        user_id: int | None = None,
    ) -> TradeJournalItem:
        closed_at = self._now()
        with self._connect() as conn:
            if user_id is None:
                row = conn.execute("SELECT * FROM trades WHERE id = ?", (trade_id,)).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM trades WHERE id = ? AND user_id = ?", (trade_id, user_id)
                ).fetchone()
            if row is None:
                raise ValueError(f"Trade {trade_id} not found")
            if row["status"] == "closed":
                raise ValueError(f"Trade {trade_id} is already closed")
            if user_id is None:
                where_sql = "id = ?"
                where_params = (trade_id,)
            else:
                where_sql = "id = ? AND user_id = ?"
                where_params = (trade_id, user_id)
            conn.execute(
                f"""
                UPDATE trades
                SET exit_price = ?, pnl_amount = ?, notes = ?, status = ?, closed_at = ?
                WHERE {where_sql}
                """,
                (
                    request.exit_price,
                    request.pnl_amount,
                    request.notes,
                    "closed",
                    closed_at,
                    *where_params,
                ),
            )
            conn.commit()
            row = conn.execute(
                f"SELECT * FROM trades WHERE {where_sql}", where_params
            ).fetchone()
        return self._trade_row_to_model(row)

    def delete_trade(self, trade_id: int, user_id: int | None = None) -> None:
        with self._connect() as conn:
            if user_id is None:
                cursor = conn.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
            else:
                cursor = conn.execute(
                    "DELETE FROM trades WHERE id = ? AND user_id = ?", (trade_id, user_id)
                )
            conn.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"Trade {trade_id} not found")

    def get_trade_stats(self, user_id: int | None = None) -> TradeJournalStats:
        where_sql = "" if user_id is None else "WHERE user_id = ?"
        params = () if user_id is None else (user_id,)
        with self._connect() as conn:
            row = conn.execute(
                f"""
                SELECT
                    COUNT(*) AS total_trades,
                    SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) AS open_trades,
                    SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) AS closed_trades,
                    SUM(CASE WHEN pnl_amount > 0 THEN 1 ELSE 0 END) AS wins,
                    SUM(CASE WHEN pnl_amount < 0 THEN 1 ELSE 0 END) AS losses,
                    COALESCE(SUM(pnl_amount), 0) AS net_pnl
                FROM trades
                {where_sql}
                """,
                params,
            ).fetchone()

        total_trades = int(row["total_trades"] or 0)
        open_trades = int(row["open_trades"] or 0)
        closed_trades = int(row["closed_trades"] or 0)
        wins = int(row["wins"] or 0)
        losses = int(row["losses"] or 0)
        net_pnl = float(row["net_pnl"] or 0.0)
        win_rate = round((wins / closed_trades) * 100, 2) if closed_trades else 0.0

        return TradeJournalStats(
            total_trades=total_trades,
            open_trades=open_trades,
            closed_trades=closed_trades,
            wins=wins,
            losses=losses,
            win_rate=win_rate,
            net_pnl=round(net_pnl, 2),
        )

    def get_analytics_summary(self, user_id: int | None = None) -> AnalyticsSummary:
        since_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        where_sql = "" if user_id is None else "WHERE user_id = ?"
        summary_params = (since_24h,) if user_id is None else (since_24h, user_id)
        top_params = () if user_id is None else (user_id,)
        with self._connect() as conn:
            row = conn.execute(
                f"""
                SELECT
                    COUNT(*) AS total_saved_signals,
                    SUM(CASE WHEN direction = 'buy' THEN 1 ELSE 0 END) AS buy_signals,
                    SUM(CASE WHEN direction = 'sell' THEN 1 ELSE 0 END) AS sell_signals,
                    SUM(CASE WHEN direction = 'neutral' THEN 1 ELSE 0 END) AS neutral_signals,
                    COALESCE(AVG(score), 0) AS average_signal_score,
                    SUM(CASE WHEN created_at >= ? THEN 1 ELSE 0 END) AS recent_signals_24h
                FROM signals
                {where_sql}
                """,
                summary_params,
            ).fetchone()
            top_rows = conn.execute(
                f"""
                SELECT symbol, COUNT(*) AS count
                FROM signals
                {where_sql}
                GROUP BY symbol
                ORDER BY count DESC, symbol ASC
                LIMIT 5
                """,
                top_params,
            ).fetchall()

        top_symbols = [AnalyticsSymbolCount(symbol=item["symbol"], count=int(item["count"])) for item in top_rows]
        return AnalyticsSummary(
            total_saved_signals=int(row["total_saved_signals"] or 0),
            buy_signals=int(row["buy_signals"] or 0),
            sell_signals=int(row["sell_signals"] or 0),
            neutral_signals=int(row["neutral_signals"] or 0),
            average_signal_score=round(float(row["average_signal_score"] or 0.0), 2),
            recent_signals_24h=int(row["recent_signals_24h"] or 0),
            top_signal_symbols=top_symbols,
            trade_stats=self.get_trade_stats(user_id=user_id),
        )

    def get_analytics_report(self, user_id: int | None = None) -> AnalyticsReport:
        since_7d = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        summary = self.get_analytics_summary(user_id=user_id)
        signal_where = "" if user_id is None else "WHERE user_id = ?"
        trade_where = "" if user_id is None else "WHERE user_id = ?"
        signal_params = () if user_id is None else (user_id,)
        trade_params = () if user_id is None else (user_id,)
        notification_where = "WHERE created_at >= ?"
        notification_params: tuple = (since_7d,)
        if user_id is not None:
            notification_where += " AND user_id = ?"
            notification_params = (since_7d, user_id)
        with self._connect() as conn:
            signal_rows = conn.execute(
                f"""
                SELECT symbol, COUNT(*) AS count, COALESCE(AVG(score), 0) AS average_score
                FROM signals
                {signal_where}
                GROUP BY symbol
                ORDER BY count DESC, symbol ASC
                LIMIT 10
                """,
                signal_params,
            ).fetchall()
            trade_rows = conn.execute(
                f"""
                SELECT
                    symbol,
                    COUNT(*) AS trade_count,
                    SUM(CASE WHEN pnl_amount > 0 THEN 1 ELSE 0 END) AS wins,
                    SUM(CASE WHEN pnl_amount < 0 THEN 1 ELSE 0 END) AS losses,
                    COALESCE(SUM(pnl_amount), 0) AS net_pnl,
                    SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) AS closed_trades
                FROM trades
                {trade_where}
                GROUP BY symbol
                ORDER BY net_pnl DESC, trade_count DESC, symbol ASC
                LIMIT 10
                """,
                trade_params,
            ).fetchall()
            notif_row = conn.execute(
                f"""
                SELECT COUNT(*) AS recent_notification_events_7d
                FROM notification_events
                {notification_where}
                """,
                notification_params,
            ).fetchone()

        signal_stats = [
            SignalSymbolStats(
                symbol=row["symbol"],
                count=int(row["count"]),
                average_score=round(float(row["average_score"] or 0.0), 2),
            )
            for row in signal_rows
        ]
        trade_perf = []
        for row in trade_rows:
            closed = int(row["closed_trades"] or 0)
            wins = int(row["wins"] or 0)
            losses = int(row["losses"] or 0)
            win_rate = round((wins / closed) * 100, 2) if closed else 0.0
            trade_perf.append(
                TradePerformanceBySymbol(
                    symbol=row["symbol"],
                    trade_count=int(row["trade_count"]),
                    wins=wins,
                    losses=losses,
                    win_rate=win_rate,
                    net_pnl=round(float(row["net_pnl"] or 0.0), 2),
                )
            )

        return AnalyticsReport(
            summary=summary,
            signal_stats_by_symbol=signal_stats,
            trade_performance_by_symbol=trade_perf,
            recent_notification_events_7d=int(notif_row["recent_notification_events_7d"] or 0),
        )

    def register_device_token(self, user_id: int, request: DeviceTokenRegisterRequest) -> DeviceTokenItem:
        created_at = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO device_tokens (user_id, token, platform, device_name, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(token) DO UPDATE SET
                    user_id = excluded.user_id,
                    platform = excluded.platform,
                    device_name = excluded.device_name
                """,
                (user_id, request.token, request.platform, request.device_name, created_at),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM device_tokens WHERE token = ?",
                (request.token,),
            ).fetchone()
        return self._device_row_to_model(row)

    def list_device_tokens(self, user_id: int) -> list[DeviceTokenItem]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM device_tokens WHERE user_id = ? ORDER BY id DESC",
                (user_id,),
            ).fetchall()
        return [self._device_row_to_model(row) for row in rows]

    def list_all_device_tokens(self) -> list[DeviceTokenItem]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM device_tokens ORDER BY id DESC"
            ).fetchall()
        return [self._device_row_to_model(row) for row in rows]

    def log_notification_event(self, user_id: int, title: str, body: str, mode: str, sent_count: int) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO notification_events (user_id, title, body, mode, sent_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, title, body, mode, sent_count, self._now()),
            )
            conn.commit()

    def _signal_row_to_model(self, row: sqlite3.Row) -> SignalHistoryItem:
        breakdown_raw = row["score_breakdown_json"] if "score_breakdown_json" in row.keys() else "{}"
        breakdown_data = json.loads(breakdown_raw or "{}")
        breakdown = (
            ScoreBreakdown(**breakdown_data)
            if breakdown_data and {"structure", "smc", "order_flow", "session", "news", "indicators", "total"} <= breakdown_data.keys()
            else None
        )
        confluence_tags = json.loads(row["confluence_tags_json"]) if "confluence_tags_json" in row.keys() and row["confluence_tags_json"] else []
        risk_flags = json.loads(row["risk_flags_json"]) if "risk_flags_json" in row.keys() and row["risk_flags_json"] else []

        return SignalHistoryItem(
            id=row["id"],
            symbol=row["symbol"],
            market=MarketType(row["market"]),
            timeframe=row["timeframe"],
            direction=SignalDirection(row["direction"]),
            score=row["score"],
            confidence=row["confidence"],
            session_name=row["session_name"],
            news_blocked=bool(row["news_blocked"]),
            entry_low=row["entry_low"],
            entry_high=row["entry_high"],
            stop_loss=row["stop_loss"],
            take_profits=json.loads(row["take_profits_json"]),
            risk_to_reward=row["risk_to_reward"],
            score_breakdown=breakdown,
            setup_grade=row["setup_grade"] if "setup_grade" in row.keys() and row["setup_grade"] else "C",
            execution_label=row["execution_label"] if "execution_label" in row.keys() and row["execution_label"] else "observe",
            entry_model=row["entry_model"] if "entry_model" in row.keys() and row["entry_model"] else "No Trade",
            ai_summary=row["ai_summary"] if "ai_summary" in row.keys() and row["ai_summary"] else "",
            confluence_tags=confluence_tags,
            risk_flags=risk_flags,
            reasons=json.loads(row["reasons_json"]),
            created_at=row["created_at"],
        )

    def _trade_row_to_model(self, row: sqlite3.Row) -> TradeJournalItem:
        return TradeJournalItem(
            id=row["id"],
            symbol=row["symbol"],
            market=MarketType(row["market"]),
            direction=SignalDirection(row["direction"]),
            entry_price=row["entry_price"],
            stop_loss=row["stop_loss"],
            take_profit=row["take_profit"],
            exit_price=row["exit_price"],
            size=row["size"],
            pnl_amount=row["pnl_amount"],
            status=row["status"],
            notes=row["notes"],
            created_at=row["created_at"],
            closed_at=row["closed_at"],
        )

    def _device_row_to_model(self, row: sqlite3.Row) -> DeviceTokenItem:
        return DeviceTokenItem(
            id=row["id"],
            user_id=row["user_id"],
            token=row["token"],
            platform=row["platform"],
            device_name=row["device_name"],
            created_at=row["created_at"],
        )
