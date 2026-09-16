"""Deterministic candle-based backtest of the SMC setup pipeline.

Replays the exact same `smc_engine.analyze()` detector that runs live
(including the resampled HTF bias, exactly like /api/v1/setups/scan) over
historical candles and simulates entry/SL/TP1 fills bar-by-bar with the
conservative rule: the entry bar only checks the stop (no same-bar TP), and
if both levels trade in one later bar the stop is assumed to fill first.

Buckets (mirroring the live pipeline):
- "all"         : graded setups — grade A+/A/B + long/short + entry/sl/tp1
                  (the widest honest candle-based tier).
- "prime_proxy" : the full live confirmed gate — omega_compliant
                  (RR>=2, confluence>=65, probability>=75, MTF alignment,
                  killzone session, confirming volume) + graded tier.

Honest scope notes (always embedded in the response, never hidden):
- Historical L2/footprint/microstructure data does not exist, so the strict
  decision engine's orderflow gates (applied after the scan layer in live)
  cannot be replayed; this backtest measures the scan/detector layer.
- Fees/slippage are optional (fee_pct per side, applied to R).

This service never touches the strict decision engine's live verdicts; it is
a research/verification tool that reports what the detector DID, not what
anyone should trade now.
"""
from __future__ import annotations

import asyncio
from typing import Any

GRADE_TIERS = ("A+", "A", "B")
MAX_ANALYZE_WINDOW = 260  # live analysis uses <=260 candles; keep replay equal

HTF_MAP = {"1m": "5m", "5m": "15m", "15m": "1h", "30m": "4h", "1h": "4h", "4h": "1d"}
TF_SECONDS = {
    "5m": 300, "15m": 900, "30m": 1800,
    "1h": 3600, "4h": 14400, "1d": 86400,
}

DISCLAIMER_FA = (
    "⚠️ این بک‌تست لایه آشکارساز/اسکن را روی کندل‌های واقعی بازپخش می‌کند (با HTF bias ریزنمونه‌شده، "
    "دقیقاً مثل اسکن زنده). داده تاریخی L2/فوت‌پرینت/خردساختار وجود ندارد، پس گیت‌های اردرفلوی موتور "
    "سخت‌گیر (لایه بعد از اسکن) قابل بازپخش نیستند. سبد prime_proxy اینجا = گیت کامل امگای زنده "
    "(گرید A+/A/B + RR≥2 + کانفلوئنس≥65 + احتمال≥75 + هم‌راستایی MTF + کیل‌زون + حجم تاییدکننده). "
    "قوانین پرکردن محافظه‌کارانه: کندل ورود فقط SL را چک می‌کند و در کندل مبهم، اول SL پر می‌شود. "
    "نتایج گذشته تضمین آینده نیست."
)


async def fetch_okx_deep_candles(symbol: str, timeframe: str, max_candles: int = 1200) -> list[dict]:
    """Paginate OKX public history-candles into normalized {t,o,h,l,c,v} items.

    Newest-first API is walked backwards with the `after` cursor. Returns an
    ascending, de-duplicated list (possibly shorter than max_candles).
    """
    import httpx
    from app.services.historical_data_service import _okx_bar, _okx_instrument

    inst = _okx_instrument(symbol)
    bar = _okx_bar(timeframe)
    rows: list[list] = []
    cursor: str | None = None
    pages = 0
    async with httpx.AsyncClient(timeout=20.0) as client:
        while len(rows) < max_candles and pages < 16:
            params: dict[str, str] = {"instId": inst, "bar": bar, "limit": "100"}
            if cursor:
                params["after"] = cursor
            response = await client.get(
                "https://www.okx.com/api/v5/market/history-candles", params=params
            )
            if not response.is_success:
                break
            data = (response.json() or {}).get("data") or []
            if not data:
                break
            rows.extend(data)
            cursor = str(data[-1][0])  # oldest ts in this page
            pages += 1
            if len(data) < 100:
                break
    by_t: dict[float, dict] = {}
    for row in rows:
        try:
            t = float(row[0]) / 1000.0
            by_t[t] = {
                "t": t,
                "o": float(row[1]),
                "h": float(row[2]),
                "l": float(row[3]),
                "c": float(row[4]),
                "v": float(row[5]),
            }
        except (IndexError, TypeError, ValueError):
            continue
    items = [by_t[t] for t in sorted(by_t)]
    return items[-max_candles:]


def resample(items: list[dict], tf_seconds: int) -> list[dict]:
    """Deterministic OHLCV bucketing (same spirit as the live HTF resample)."""
    if tf_seconds <= 0 or not items:
        return []
    buckets: dict[int, dict] = {}
    for item in items:
        try:
            t = int(item["t"])
        except (KeyError, TypeError, ValueError):
            continue
        key = t - (t % tf_seconds)
        row = buckets.get(key)
        if row is None:
            buckets[key] = {
                "t": float(key),
                "o": float(item["o"]),
                "h": float(item["h"]),
                "l": float(item["l"]),
                "c": float(item["c"]),
                "v": float(item["v"]),
            }
        else:
            row["h"] = max(row["h"], float(item["h"]))
            row["l"] = min(row["l"], float(item["l"]))
            row["c"] = float(item["c"])
            row["v"] += float(item["v"])
    return [buckets[k] for k in sorted(buckets)]


def _htf_bias(window: list[dict], timeframe: str, analyze) -> str | None:
    """Reproduce the live scan's HTF bias (resample + analyze) for one window."""
    htf = HTF_MAP.get(str(timeframe).lower())
    seconds = TF_SECONDS.get(htf or "")
    if not htf or not seconds:
        return None
    try:
        higher = resample(window, seconds)
        if len(higher) < 30:
            return None
        return analyze(higher, timeframe=htf).get("bias")
    except Exception:
        return None


def _simulate(items: list[dict], i: int, report: dict, exit_horizon: int, fee_pct: float) -> dict | None:
    """Simulate one setup occurrence detected at bar i. Returns a trade row or None."""
    levels = report.get("levels") or {}
    try:
        entry = float(levels.get("entry") or 0)
        sl = float(levels.get("sl") or 0)
        tp = float(report.get("tp1") or 0)
    except (TypeError, ValueError):
        return None
    direction = str(report.get("direction") or "")
    if direction not in ("long", "short") or entry <= 0 or sl <= 0 or tp <= 0:
        return None
    risk = abs(entry - sl)
    if risk <= 0:
        return None
    if direction == "long" and not (sl < entry < tp):
        return None
    if direction == "short" and not (tp < entry < sl):
        return None

    last_j = min(i + exit_horizon, len(items) - 1)
    entry_index = None
    for j in range(i + 1, last_j + 1):
        bar = items[j]
        if direction == "long" and float(bar["l"]) <= entry:
            entry_index = j
            break
        if direction == "short" and float(bar["h"]) >= entry:
            entry_index = j
            break
    if entry_index is None:
        return {"triggered": False, "index": i}

    exit_price = None
    exit_reason = "timeout"
    exit_index = last_j
    # conservative: entry bar only checks the stop
    first_bar = items[entry_index]
    if direction == "long" and float(first_bar["l"]) <= sl:
        exit_price, exit_reason, exit_index = sl, "sl", entry_index
    elif direction == "short" and float(first_bar["h"]) >= sl:
        exit_price, exit_reason, exit_index = sl, "sl", entry_index
    if exit_price is None:
        for k in range(entry_index + 1, last_j + 1):
            bar = items[k]
            if direction == "long":
                if float(bar["l"]) <= sl:
                    exit_price, exit_reason, exit_index = sl, "sl", k
                    break
                if float(bar["h"]) >= tp:
                    exit_price, exit_reason, exit_index = tp, "tp1", k
                    break
            else:
                if float(bar["h"]) >= sl:
                    exit_price, exit_reason, exit_index = sl, "sl", k
                    break
                if float(bar["l"]) <= tp:
                    exit_price, exit_reason, exit_index = tp, "tp1", k
                    break
        if exit_price is None:
            exit_price = float(items[last_j]["c"])
            exit_reason = "timeout"
            exit_index = last_j

    signed = (exit_price - entry) if direction == "long" else (entry - exit_price)
    r_multiple = signed / risk
    fee_r = (fee_pct / 100.0) * (entry + exit_price) / risk if fee_pct > 0 else 0.0
    r_multiple -= fee_r
    omega = bool(report.get("omega_compliant"))
    return {
        "triggered": True,
        "index": i,
        "time": items[i].get("t"),
        "direction": direction,
        "setup_type": str(report.get("setup_type") or "-"),
        "grade": str(report.get("grade") or "-"),
        "confluence": int(report.get("confluence") or 0),
        "omega_compliant": omega,
        "entry": entry,
        "sl": sl,
        "tp1": tp,
        "entry_time": items[entry_index].get("t"),
        "exit_time": items[exit_index].get("t"),
        "exit_price": round(exit_price, 8),
        "exit_reason": exit_reason,
        "bars_held": exit_index - entry_index,
        "r": round(r_multiple, 3),
        "prime": omega,  # live-confirmed gate (full Omega rule set)
    }


def _stats(trades: list[dict]) -> dict:
    if not trades:
        return {
            "trades": 0, "wins": 0, "losses": 0, "win_rate_pct": None,
            "avg_r": None, "total_r": None, "profit_factor": None,
            "expectancy_r": None, "max_consecutive_losses": 0,
            "best_r": None, "worst_r": None,
            "exit_reasons": {},
        }
    wins = [t for t in trades if t["r"] > 0]
    losses = [t for t in trades if t["r"] <= 0]
    gross_win = sum(t["r"] for t in wins)
    gross_loss = abs(sum(t["r"] for t in losses))
    streak = best_streak = 0
    for t in trades:
        if t["r"] <= 0:
            streak += 1
            best_streak = max(best_streak, streak)
        else:
            streak = 0
    reasons: dict[str, int] = {}
    for t in trades:
        reasons[t["exit_reason"]] = reasons.get(t["exit_reason"], 0) + 1
    return {
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(len(wins) / len(trades) * 100, 1),
        "avg_r": round(sum(t["r"] for t in trades) / len(trades), 3),
        "total_r": round(sum(t["r"] for t in trades), 3),
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss > 0 else None,
        "expectancy_r": round(sum(t["r"] for t in trades) / len(trades), 3),
        "max_consecutive_losses": best_streak,
        "best_r": round(max(t["r"] for t in trades), 3),
        "worst_r": round(min(t["r"] for t in trades), 3),
        "exit_reasons": reasons,
    }


def run(
    items: list[dict],
    symbol: str = "",
    timeframe: str = "",
    warmup: int = 130,
    step: int = 3,
    exit_horizon: int | None = None,
    fee_pct: float = 0.0,
    cost_gate: bool = True,
) -> dict:
    """Walk-forward replay of the live detector over `items` (ascending).

    cost_gate=True applies the v3.20 trade-cost/geometry gate (same rules as
    the live strict engine) so only fee-survivable plans are replayed. The
    gate evaluates at real taker cost even when fee_pct=0 (audit mode).
    """
    n = len(items)
    if n < warmup + 20:
        return {
            "ok": False,
            "detail": "insufficient_candles",
            "candles": n,
            "required": warmup + 20,
        }
    from app.services.smc_engine import analyze

    exit_horizon = int(exit_horizon or max(24, min(96, n // 4)))
    trades: list[dict] = []
    not_triggered = 0
    detected = 0
    cost_gated = 0
    i = warmup
    while i < n - 5:
        window_start = max(0, i + 1 - MAX_ANALYZE_WINDOW)
        window = items[window_start:i + 1]
        try:
            htf_bias = _htf_bias(window, timeframe, analyze)
            report = analyze(window, symbol=symbol, timeframe=timeframe, htf_bias=htf_bias)
        except Exception:
            i += step
            continue
        eligible = (
            str(report.get("grade")) in GRADE_TIERS
            and str(report.get("direction")) in ("long", "short")
            and bool((report.get("levels") or {}).get("entry"))
        )
        if eligible:
            detected += 1
            if cost_gate:
                from app.services import trade_cost_gate
                lv = report.get("levels") or {}
                cg = trade_cost_gate.evaluate(
                    lv.get("entry"), lv.get("sl"), report.get("tp1"),
                    str(report.get("direction") or ""),
                    fee_pct=fee_pct if fee_pct > 0 else trade_cost_gate.DEFAULT_FEE_PCT,
                    atr=report.get("atr"),
                )
                if cg["applicable"] and not cg["passed"]:
                    cost_gated += 1
                    i += step
                    continue
            outcome = _simulate(items, i, report, exit_horizon, fee_pct)
            if outcome is None:
                i += step
                continue
            if not outcome.get("triggered"):
                not_triggered += 1
                i += step
                continue
            trades.append({k: v for k, v in outcome.items() if k != "triggered"})
            # skip ahead: no overlapping positions (single-thread book)
            exit_t = outcome.get("exit_time")
            jumped = False
            if exit_t is not None:
                for j in range(i + 1, n):
                    if items[j].get("t") == exit_t:
                        i = max(i + step, j + 1)
                        jumped = True
                        break
            if not jumped:
                i += step
            continue
        i += step

    prime_trades = [t for t in trades if t.get("prime")]
    by_setup: dict[str, list[dict]] = {}
    for t in trades:
        by_setup.setdefault(t["setup_type"], []).append(t)

    period_start = items[0].get("t")
    period_end = items[-1].get("t")
    return {
        "ok": True,
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "htf": HTF_MAP.get(str(timeframe).lower()),
        "candles": n,
        "period": {"start_ts": period_start, "end_ts": period_end},
        "settings": {
            "warmup": warmup,
            "step": step,
            "exit_horizon": exit_horizon,
            "fee_pct": fee_pct,
            "target": "tp1",
            "fill_rule": "conservative_sl_first_no_same_bar_tp",
            "analyze_window": MAX_ANALYZE_WINDOW,
            "htf_bias_replayed": True,
            "cost_gate": {
                "enabled": cost_gate,
                "gate_fee_pct": fee_pct if fee_pct > 0 else 0.05,
                "max_fee_r": 0.30, "min_risk_atr": 0.35, "min_net_rr": 1.5,
                "source": "trade_cost_gate v3.20 — same rules as live strict engine",
            },
        },
        "setups_detected": detected,
        "setups_cost_gated": cost_gated,
        "setups_not_triggered": not_triggered,
        "all": _stats(trades),
        "prime_proxy": _stats(prime_trades),
        "by_setup_type": {name: _stats(rows) for name, rows in sorted(by_setup.items())},
        "trades": trades[-40:],
        "disclaimer_fa": DISCLAIMER_FA,
        "created_by": "Amin Omidi",
    }


async def run_async(items: list[dict], **kwargs: Any) -> dict:
    """Thread-pool wrapper so heavy replays never block the event loop."""
    return await asyncio.to_thread(run, items, **kwargs)
