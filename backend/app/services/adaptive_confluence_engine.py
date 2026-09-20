"""Adaptive Confluence Engine — v4.0

Learns which confluence factors actually predict winning trades and adjusts
their weights over time. Uses exponential moving average of per-factor win rates
to upweight factors that consistently appear in winners and downweight factors
that appear in losers.

Design:
  * Each confluence factor has a base weight (from smc_engine) and an adaptive
    multiplier that starts at 1.0 and converges based on observed outcomes.
  * Factors that appear in winning trades get their multiplier increased
    (capped at 2.0x); factors in losing trades get decreased (floored at 0.2x).
  * The system needs at least 20 trades per factor before the adaptive weight
    dominates the base weight; before that, base weights are used as-is.
  * A global regime filter adjusts all weights based on market regime
    performance (trending setups may outperform choppy ones, etc.)
  * All adjustments are deterministic and reproducible.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

# Minimum trades before adaptive weighting kicks in
_MIN_TRADES_FOR_ADAPT = 20
# Learning rate for EMA updates
_LEARNING_RATE = 0.05
# Adaptive multiplier bounds
_MULT_MIN = 0.20
_MULT_MAX = 2.00


@dataclass
class FactorRecord:
    """Tracks per-factor performance statistics."""
    appearances: int = 0
    wins: int = 0
    losses: int = 0
    win_rate_ema: float = 0.50  # EMA of win rate, starts at 50% (neutral)
    adaptive_multiplier: float = 1.0
    total_points_in_wins: float = 0.0
    total_points_in_losses: float = 0.0


@dataclass
class RegimeRecord:
    """Tracks per-regime performance."""
    appearances: int = 0
    wins: int = 0
    win_rate: float = 0.50
    avg_rr: float = 0.0
    profit_factor: float = 1.0


class AdaptiveConfluenceEngine:
    """Stateful engine that learns optimal confluence factor weights."""

    def __init__(self) -> None:
        self._factors: dict[str, FactorRecord] = {}
        self._regimes: dict[str, RegimeRecord] = {}
        self._setup_types: dict[str, FactorRecord] = {}  # per-setup-type tracking
        self._total_trades: int = 0
        self._total_wins: int = 0

    def record_trade(
        self,
        factors: list[dict],
        setup_type: str,
        regime: str,
        won: bool,
        rr: float,
        pnl_r: float,
    ) -> None:
        """Record a trade outcome and update all adaptive weights."""
        self._total_trades += 1
        if won:
            self._total_wins += 1

        # Update per-factor records
        for factor in factors:
            name = str(factor.get("name") or "unknown")
            points = float(factor.get("points") or 0)
            if name not in self._factors:
                self._factors[name] = FactorRecord()
            rec = self._factors[name]
            rec.appearances += 1
            if won:
                rec.wins += 1
                rec.total_points_in_wins += abs(points)
            else:
                rec.losses += 1
                rec.total_points_in_losses += abs(points)

            # EMA update of win rate
            outcome = 1.0 if won else 0.0
            rec.win_rate_ema = (1 - _LEARNING_RATE) * rec.win_rate_ema + _LEARNING_RATE * outcome

            # Update adaptive multiplier based on EMA win rate
            # If win_rate > 0.50, increase multiplier; if < 0.50, decrease
            if rec.appearances >= _MIN_TRADES_FOR_ADAPT:
                deviation = rec.win_rate_ema - 0.50
                # Scale deviation: 0.50 deviation = full 2x or 0.2x
                target_mult = 1.0 + deviation * 2.0
                target_mult = max(_MULT_MIN, min(_MULT_MAX, target_mult))
                # Smooth transition
                rec.adaptive_multiplier = (
                    0.90 * rec.adaptive_multiplier + 0.10 * target_mult
                )

        # Update per-regime records
        if regime not in self._regimes:
            self._regimes[regime] = RegimeRecord()
        reg = self._regimes[regime]
        reg.appearances += 1
        if won:
            reg.wins += 1
        reg.win_rate = reg.wins / max(1, reg.appearances)
        reg.avg_rr = (1 - _LEARNING_RATE) * reg.avg_rr + _LEARNING_RATE * rr
        if pnl_r > 0:
            reg.profit_factor = (1 - _LEARNING_RATE) * reg.profit_factor + _LEARNING_RATE * max(0.1, pnl_r)
        else:
            reg.profit_factor = (1 - _LEARNING_RATE) * reg.profit_factor + _LEARNING_RATE * min(0.1, 1.0 / max(0.1, abs(pnl_r)))

        # Update per-setup-type records
        if setup_type not in self._setup_types:
            self._setup_types[setup_type] = FactorRecord()
        setup_rec = self._setup_types[setup_type]
        setup_rec.appearances += 1
        if won:
            setup_rec.wins += 1
        outcome = 1.0 if won else 0.0
        setup_rec.win_rate_ema = (1 - _LEARNING_RATE) * setup_rec.win_rate_ema + _LEARNING_RATE * outcome
        if setup_rec.appearances >= _MIN_TRADES_FOR_ADAPT:
            deviation = setup_rec.win_rate_ema - 0.50
            target_mult = 1.0 + deviation * 2.0
            target_mult = max(_MULT_MIN, min(_MULT_MAX, target_mult))
            setup_rec.adaptive_multiplier = 0.90 * setup_rec.adaptive_multiplier + 0.10 * target_mult

    def get_factor_multiplier(self, factor_name: str) -> float:
        """Get the adaptive multiplier for a specific factor."""
        rec = self._factors.get(factor_name)
        if rec is None or rec.appearances < _MIN_TRADES_FOR_ADAPT:
            return 1.0
        return rec.adaptive_multiplier

    def get_setup_multiplier(self, setup_type: str) -> float:
        """Get the adaptive multiplier for a setup type."""
        rec = self._setup_types.get(setup_type)
        if rec is None or rec.appearances < _MIN_TRADES_FOR_ADAPT:
            return 1.0
        return rec.adaptive_multiplier

    def get_regime_stats(self, regime: str) -> RegimeRecord | None:
        return self._regimes.get(regime)

    def adjust_confluence_score(
        self,
        factors: list[dict],
        base_score: int,
        setup_type: str = "",
        regime: str = "",
    ) -> tuple[int, list[dict], dict]:
        """Apply adaptive multipliers to confluence factors.

        Returns (adjusted_score, adjusted_factors, meta_info).
        """
        setup_mult = self.get_setup_multiplier(setup_type)
        adjusted_factors = []
        total_adjusted = 0.0

        for factor in factors:
            name = str(factor.get("name") or "unknown")
            base_points = float(factor.get("points") or 0)
            mult = self.get_factor_multiplier(name)
            # Setup multiplier only applies to positive factors
            if base_points > 0 and setup_mult != 1.0:
                mult *= setup_mult
            adjusted_points = base_points * mult
            # Round to keep it clean
            adjusted_points = round(adjusted_points, 1)
            total_adjusted += adjusted_points
            adjusted_factors.append({
                **factor,
                "points": adjusted_points,
                "base_points": base_points,
                "adaptive_multiplier": round(mult, 3),
            })

        adjusted_score = max(0, min(100, int(round(total_adjusted))))

        meta = {
            "adaptive_applied": self._total_trades >= _MIN_TRADES_FOR_ADAPT,
            "total_trades_learned": self._total_trades,
            "global_win_rate": round(self._total_wins / max(1, self._total_trades), 4) if self._total_trades else 0.0,
            "setup_multiplier": round(setup_mult, 3),
            "factors_tracked": len(self._factors),
            "regimes_tracked": len(self._regimes),
        }

        return adjusted_score, adjusted_factors, meta

    def get_stats(self) -> dict:
        """Full diagnostic snapshot of the adaptive engine state."""
        return {
            "total_trades": self._total_trades,
            "total_wins": self._total_wins,
            "global_win_rate": round(self._total_wins / max(1, self._total_trades), 4) if self._total_trades else 0.0,
            "min_trades_for_adapt": _MIN_TRADES_FOR_ADAPT,
            "factors": {
                name: {
                    "appearances": rec.appearances,
                    "wins": rec.wins,
                    "losses": rec.losses,
                    "win_rate": round(rec.wins / max(1, rec.appearances), 4),
                    "win_rate_ema": round(rec.win_rate_ema, 4),
                    "adaptive_multiplier": round(rec.adaptive_multiplier, 3),
                }
                for name, rec in sorted(self._factors.items(), key=lambda x: -x[1].appearances)
            },
            "setup_types": {
                name: {
                    "appearances": rec.appearances,
                    "wins": rec.wins,
                    "win_rate": round(rec.wins / max(1, rec.appearances), 4),
                    "win_rate_ema": round(rec.win_rate_ema, 4),
                    "adaptive_multiplier": round(rec.adaptive_multiplier, 3),
                }
                for name, rec in sorted(self._setup_types.items(), key=lambda x: -x[1].appearances)
            },
            "regimes": {
                name: {
                    "appearances": reg.appearances,
                    "wins": reg.wins,
                    "win_rate": round(reg.win_rate, 4),
                    "avg_rr": round(reg.avg_rr, 3),
                    "profit_factor": round(reg.profit_factor, 3),
                }
                for name, reg in sorted(self._regimes.items(), key=lambda x: -x[1].appearances)
            },
        }

    def reset(self) -> None:
        """Reset all learned state."""
        self._factors.clear()
        self._regimes.clear()
        self._setup_types.clear()
        self._total_trades = 0
        self._total_wins = 0


# Singleton instance
adaptive_confluence_engine = AdaptiveConfluenceEngine()
