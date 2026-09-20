"""Performance Tracker Service — v4.0

Records and analyzes trade outcomes to provide a real feedback loop.
Tracks every actionable signal from generation to resolution, computing
rolling win rates, profit factors, drawdowns, and per-factor performance.

This is the data pipeline that feeds:
  * calibrated_probability_engine — online logistic regression updates
  * adaptive_confluence_engine — factor weight adjustments
  * Risk engine — drawdown-based risk multipliers (already exists)

Storage: SQLite table `trade_outcomes` (auto-created, same DB as the app).
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from typing import Any

from app.services.database_service import DatabaseManager


_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS trade_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER DEFAULT 0,
    symbol TEXT NOT NULL,
    market TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    direction TEXT NOT NULL,
    setup_type TEXT DEFAULT '',
    entry_price REAL,
    exit_price REAL,
    stop_loss REAL,
    take_profit REAL,
    grade TEXT DEFAULT '',
    confluence INTEGER DEFAULT 0,
    probability INTEGER DEFAULT 0,
    rr REAL DEFAULT 0,
    calibrated_probability REAL,
    pnl_r REAL DEFAULT 0,
    won INTEGER DEFAULT 0,
    regime TEXT DEFAULT '',
    factors_json TEXT DEFAULT '[]',
    micro_aligned INTEGER DEFAULT 0,
    cost_fee_r REAL DEFAULT 0,
    status TEXT DEFAULT 'open',
    opened_at REAL DEFAULT 0,
    closed_at REAL DEFAULT 0,
    notes TEXT DEFAULT ''
)
"""

_CREATE_INDEX_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_trade_outcomes_symbol ON trade_outcomes(symbol)",
    "CREATE INDEX IF NOT EXISTS idx_trade_outcomes_status ON trade_outcomes(status)",
    "CREATE INDEX IF NOT EXISTS idx_trade_outcomes_direction ON trade_outcomes(direction)",
]


@dataclass
class TradeRecord:
    symbol: str
    market: str
    timeframe: str
    direction: str
    setup_type: str = ""
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    grade: str = ""
    confluence: int = 0
    probability: int = 0
    rr: float = 0.0
    calibrated_probability: float | None = None
    regime: str = ""
    factors: list[dict] = None
    micro_aligned: bool = False
    cost_fee_r: float = 0.0
    user_id: int = 0


class PerformanceTrackerService:
    """Tracks real trade outcomes and feeds the learning engines."""

    def __init__(self, database: DatabaseManager) -> None:
        self._db = database
        self._ensure_table()

    def _ensure_table(self) -> None:
        try:
            with self._db.connection() as conn:
                conn.execute(_CREATE_TABLE_SQL)
                for sql in _CREATE_INDEX_SQL:
                    conn.execute(sql)
                conn.commit()
        except Exception:
            pass

    def record_entry(self, record: TradeRecord) -> int | None:
        """Record a new trade entry (status='open'). Returns the row ID."""
        try:
            now = time.time()
            factors_json = json.dumps(record.factors or [], ensure_ascii=False)
            with self._db.connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO trade_outcomes
                        (user_id, symbol, market, timeframe, direction, setup_type,
                         entry_price, stop_loss, take_profit, grade, confluence,
                         probability, rr, calibrated_probability, regime,
                         factors_json, micro_aligned, cost_fee_r, status, opened_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)
                    """,
                    (
                        record.user_id, record.symbol, record.market, record.timeframe,
                        record.direction, record.setup_type, record.entry_price,
                        record.stop_loss, record.take_profit, record.grade,
                        record.confluence, record.probability, record.rr,
                        record.calibrated_probability, record.regime,
                        factors_json, int(record.micro_aligned), record.cost_fee_r,
                        now,
                    ),
                )
                conn.commit()
                return cursor.lastrowid
        except Exception:
            return None

    def close_trade(
        self,
        trade_id: int,
        exit_price: float,
        pnl_r: float,
        won: bool,
        notes: str = "",
    ) -> bool:
        """Close a tracked trade and feed the learning engines."""
        try:
            now = time.time()
            with self._db.connection() as conn:
                conn.execute(
                    """
                    UPDATE trade_outcomes
                    SET exit_price = ?, pnl_r = ?, won = ?, status = 'closed',
                        closed_at = ?, notes = ?
                    WHERE id = ?
                    """,
                    (exit_price, pnl_r, int(won), now, notes, trade_id),
                )
                conn.commit()
                row = conn.execute(
                    "SELECT * FROM trade_outcomes WHERE id = ?",
                    (trade_id,),
                ).fetchone()
            if row:
                self._feed_learning_engines(row, won, pnl_r)
            return True
        except Exception:
            return False

    def _feed_learning_engines(self, row: Any, won: bool, pnl_r: float) -> None:
        """Feed the outcome to the calibrated probability and adaptive confluence engines."""
        try:
            # Convert sqlite3.Row to dict if needed
            if hasattr(row, "keys"):
                row_dict = {k: row[k] for k in row.keys()}
            else:
                row_dict = dict(row)

            factors = json.loads(row_dict.get("factors_json") or "[]")
            setup_type = str(row_dict.get("setup_type") or "")
            regime = str(row_dict.get("regime") or "")
            rr = float(row_dict.get("rr") or 0)

            # Feed adaptive confluence engine
            from app.services.adaptive_confluence_engine import adaptive_confluence_engine
            adaptive_confluence_engine.record_trade(
                factors=factors,
                setup_type=setup_type,
                regime=regime,
                won=won,
                rr=rr,
                pnl_r=pnl_r,
            )

            # Feed calibrated probability engine
            from app.services.calibrated_probability_engine import (
                update_with_outcome,
                CalibrationFeatures,
            )

            features = CalibrationFeatures(
                confluence_norm=min(1.0, float(row_dict.get("confluence") or 0) / 100.0),
                grade_a_plus=1.0 if row_dict.get("grade") == "A+" else 0.0,
                grade_a=1.0 if row_dict.get("grade") == "A" else 0.0,
                rr_norm=min(1.0, rr / 5.0),
                data_quality_norm=0.85,
                market_regime_trend=1.0 if regime == "trending" else 0.0,
                market_regime_balanced=1.0 if regime in ("balanced", "compressed") else 0.0,
                negative_evidence=0.0,
                cost_drag=min(1.0, float(row_dict.get("cost_fee_r") or 0) / 0.30),
                micro_aligned=1.0 if row_dict.get("micro_aligned") else 0.0,
            )
            update_with_outcome(features, won, learning_rate=0.01)
        except Exception:
            pass

    def get_stats(self, symbol: str | None = None, limit: int = 200) -> dict:
        """Compute rolling performance statistics."""
        try:
            with self._db.connection() as conn:
                where = "WHERE status = 'closed'"
                params: list[Any] = []
                if symbol:
                    where += " AND symbol = ?"
                    params.append(symbol.upper())
                where += f" ORDER BY closed_at DESC LIMIT {int(limit)}"
                cursor = conn.execute(
                    f"SELECT * FROM trade_outcomes {where}",
                    tuple(params),
                )
                rows = cursor.fetchall()

            if not rows:
                return self._empty_stats()

            # Convert rows to dicts
            records = []
            for r in rows:
                if hasattr(r, "keys"):
                    records.append({k: r[k] for k in r.keys()})
                else:
                    records.append(dict(r))

            total = len(records)
            wins = sum(1 for r in records if int(r.get("won") or 0))
            losses = total - wins
            pnl_sum = sum(float(r.get("pnl_r") or 0) for r in records)
            gross_profit = sum(float(r.get("pnl_r") or 0) for r in records if float(r.get("pnl_r") or 0) > 0)
            gross_loss = abs(sum(float(r.get("pnl_r") or 0) for r in records if float(r.get("pnl_r") or 0) < 0))
            profit_factor = gross_profit / max(gross_loss, 0.001)

            # Drawdown calculation
            cumulative = 0.0
            peak = 0.0
            max_dd = 0.0
            for r in reversed(records):
                cumulative += float(r.get("pnl_r") or 0)
                peak = max(peak, cumulative)
                dd = peak - cumulative
                max_dd = max(max_dd, dd)

            # Per-direction stats
            longs = [r for r in records if r.get("direction") == "long"]
            shorts = [r for r in records if r.get("direction") == "short"]
            long_wins = sum(1 for r in longs if int(r.get("won") or 0))
            short_wins = sum(1 for r in shorts if int(r.get("won") or 0))

            # Per-setup-type stats
            setup_stats: dict[str, dict] = {}
            for r in records:
                st = str(r.get("setup_type") or "unknown")
                if st not in setup_stats:
                    setup_stats[st] = {"total": 0, "wins": 0, "pnl_r": 0.0}
                setup_stats[st]["total"] += 1
                setup_stats[st]["wins"] += int(r.get("won") or 0)
                setup_stats[st]["pnl_r"] += float(r.get("pnl_r") or 0)

            # Per-grade stats
            grade_stats: dict[str, dict] = {}
            for r in records:
                g = str(r.get("grade") or "F")
                if g not in grade_stats:
                    grade_stats[g] = {"total": 0, "wins": 0, "pnl_r": 0.0}
                grade_stats[g]["total"] += 1
                grade_stats[g]["wins"] += int(r.get("won") or 0)
                grade_stats[g]["pnl_r"] += float(r.get("pnl_r") or 0)

            # Recent streak
            recent = records[:10]
            streak_wins = 0
            for r in recent:
                if int(r.get("won") or 0):
                    streak_wins += 1
                else:
                    break

            avg_rr = sum(float(r.get("rr") or 0) for r in records) / max(1, total)

            return {
                "total_trades": total,
                "wins": wins,
                "losses": losses,
                "win_rate": round(wins / max(1, total), 4),
                "profit_factor": round(profit_factor, 3),
                "total_pnl_r": round(pnl_sum, 2),
                "avg_rr": round(avg_rr, 3),
                "max_drawdown_r": round(max_dd, 2),
                "expectancy_r": round(pnl_sum / max(1, total), 4),
                "long_stats": {
                    "total": len(longs),
                    "wins": long_wins,
                    "win_rate": round(long_wins / max(1, len(longs)), 4),
                },
                "short_stats": {
                    "total": len(shorts),
                    "wins": short_wins,
                    "win_rate": round(short_wins / max(1, len(shorts)), 4),
                },
                "setup_stats": {
                    st: {
                        "total": s["total"],
                        "wins": s["wins"],
                        "win_rate": round(s["wins"] / max(1, s["total"]), 4),
                        "pnl_r": round(s["pnl_r"], 2),
                    }
                    for st, s in sorted(setup_stats.items(), key=lambda x: -x[1]["total"])
                },
                "grade_stats": {
                    g: {
                        "total": s["total"],
                        "wins": s["wins"],
                        "win_rate": round(s["wins"] / max(1, s["total"]), 4),
                        "pnl_r": round(s["pnl_r"], 2),
                    }
                    for g, s in sorted(grade_stats.items())
                },
                "current_win_streak": streak_wins,
                "recent_10_pnl_r": round(sum(float(r.get("pnl_r") or 0) for r in recent), 2),
            }
        except Exception:
            return self._empty_stats()

    def _empty_stats(self) -> dict:
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "total_pnl_r": 0.0,
            "avg_rr": 0.0,
            "max_drawdown_r": 0.0,
            "expectancy_r": 0.0,
            "long_stats": {"total": 0, "wins": 0, "win_rate": 0.0},
            "short_stats": {"total": 0, "wins": 0, "win_rate": 0.0},
            "setup_stats": {},
            "grade_stats": {},
            "current_win_streak": 0,
            "recent_10_pnl_r": 0.0,
        }

    def get_open_trades(self, symbol: str | None = None) -> list[dict]:
        where = "WHERE status = 'open'"
        params: list[Any] = []
        if symbol:
            where += " AND symbol = ?"
            params.append(symbol.upper())
        where += " ORDER BY opened_at DESC"
        try:
            with self._db.connection() as conn:
                cursor = conn.execute(
                    f"SELECT * FROM trade_outcomes {where}",
                    tuple(params),
                )
                rows = cursor.fetchall()
            result = []
            for r in rows:
                if hasattr(r, "keys"):
                    result.append({k: r[k] for k in r.keys()})
                else:
                    result.append(dict(r))
            return result
        except Exception:
            return []

    def auto_close_stale_trades(self, current_candles: list[dict], symbol: str) -> int:
        """Auto-close open trades that have hit their SL or TP.

        Returns the number of trades closed.
        """
        if not current_candles:
            return 0
        open_trades = self.get_open_trades(symbol)
        if not open_trades:
            return 0

        closed = 0
        last_candle = current_candles[-1]
        current_high = float(last_candle.get("h") or 0)
        current_low = float(last_candle.get("l") or 0)
        current_close = float(last_candle.get("c") or 0)

        for trade in open_trades:
            direction = str(trade.get("direction") or "")
            entry = float(trade.get("entry_price") or 0)
            sl = float(trade.get("stop_loss") or 0)
            tp = float(trade.get("take_profit") or 0)
            trade_id = int(trade.get("id") or 0)

            if entry <= 0 or sl <= 0:
                continue

            pnl_r = 0.0
            won = False
            exit_price = 0.0
            risk = abs(entry - sl)

            if direction == "long":
                if current_low <= sl:
                    exit_price = sl
                    pnl_r = -1.0
                    won = False
                elif tp > 0 and current_high >= tp:
                    exit_price = tp
                    pnl_r = float(trade.get("rr") or 2.0)
                    won = True
                else:
                    exit_price = current_close
                    pnl_r = (exit_price - entry) / max(risk, 1e-9)
                    won = pnl_r > 0
            elif direction == "short":
                if current_high >= sl:
                    exit_price = sl
                    pnl_r = -1.0
                    won = False
                elif tp > 0 and current_low <= tp:
                    exit_price = tp
                    pnl_r = float(trade.get("rr") or 2.0)
                    won = True
                else:
                    exit_price = current_close
                    pnl_r = (entry - exit_price) / max(risk, 1e-9)
                    won = pnl_r > 0

            # Only close if SL or TP was hit
            if (direction == "long" and current_low <= sl) or \
               (direction == "short" and current_high >= sl) or \
               (tp > 0 and ((direction == "long" and current_high >= tp) or
                            (direction == "short" and current_low <= tp))):
                if self.close_trade(trade_id, exit_price, round(pnl_r, 4), won):
                    closed += 1

        return closed
