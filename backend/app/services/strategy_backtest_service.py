"""Deterministic walk-forward backtest of the classic strategy pack (v2).

Replays `strategy_pack_v2.scan_all()` over real historical candles exactly as
the live pipeline runs it (same window sizes, same detectors, no look-ahead)
and simulates every ACTIVE signal that carries a trade plan with the same
conservative fill rules as the PRIME backtest:
  * entry only on a later bar touching the entry price,
  * the entry bar itself only checks the stop (no same-bar TP),
  * in an ambiguous later bar the stop is assumed to fill first.

Plan conventions (documented, never hidden):
  * signals with entry+stop+target → simulated as given,
  * signals with entry+stop but no target → target = 2R (exit reason "tp_2r"),
  * signals without a stop → skipped and counted (no fabricated risk).

Books are per-strategy: while strategy X has an open trade, new X signals are
ignored; other strategies are simulated independently. Quality-bucket stats
answer the calibration question: does quality>=65 actually beat quality<55?

v3.14: every simulated trade is also tagged with three walk-forward-safe gate
flags computed ONLY from data available at the signal bar (no look-ahead):
  * gate_trend : close vs EMA50 agrees with the trade direction,
  * gate_votes : indicator_pack_v2 net vote (|net|>=15) agrees with direction,
  * gate_perf  : the strategy's own closed trades so far (>=3, total R > 0).
The response reports stats for each gate subset and the full combination, so
the claim "gating improves results" is measured, never assumed.
"""
from __future__ import annotations

import asyncio
from typing import Any

WARMUP = 200          # detectors need history (golden cross 210, KST 65, ...)
WINDOW = 300          # replay window fed to scan_all (live endpoints use ~220-300)
MIN_QUALITY_DEFAULT = 55

QUALITY_BUCKETS = (
    ("q<55", lambda q: q < 55),
    ("q55-64", lambda q: 55 <= q < 65),
    ("q65-74", lambda q: 65 <= q < 75),
    ("q75+", lambda q: q >= 75),
)

DISCLAIMER_FA = (
    "⚠️ این بک‌تست پک ۲۲ استراتژی کلاسیک را روی کندل‌های واقعی بازپخش می‌کند (walk-forward، بدون "
    "look-ahead، دقیقاً همان پنجره‌های اسکن زنده). قوانین پرکردن محافظه‌کارانه: ورود فقط در کندل "
    "بعدی، کندل ورود فقط SL را چک می‌کند و در کندل مبهم اول SL پر می‌شود. سیگنال‌های بدون target "
    "با هدف ۲R شبیه‌سازی شده‌اند (exit_reason=tp_2r) و سیگنال‌های بدون stop شمارش می‌شوند ولی "
    "شبیه‌سازی نمی‌شوند (ریسک جعل نمی‌شود). داده تاریخی L2/فوت‌پرینت وجود ندارد. سبد هر استراتژی "
    "مستقل است (بدون پوزیشن همپوشان برای یک استراتژی). نتایج گذشته تضمین آینده نیست؛ برای قضاوت "
    "هر استراتژی به نمونه بزرگ (دست‌کم ۳۰ معامله) نگاه کن."
)


def _simulate_plan(items: list[dict], i: int, direction: str, entry: float,
                   sl: float, target: float | None, exit_horizon: int,
                   fee_pct: float) -> dict | None:
    """Conservative bar-by-bar fill. Mirrors prime_backtest_service._simulate."""
    risk = abs(entry - sl)
    if risk <= 0:
        return None
    if direction == "long" and not sl < entry:
        return None
    if direction == "short" and not sl > entry:
        return None
    target_kind = "tp"
    if target is None:
        target = entry + 2 * risk if direction == "long" else entry - 2 * risk
        target_kind = "tp_2r"
    if direction == "long" and not entry < target:
        return None
    if direction == "short" and not entry > target:
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
        return {"triggered": False}

    exit_price = None
    exit_reason = "timeout"
    exit_index = last_j
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
                if float(bar["h"]) >= target:
                    exit_price, exit_reason, exit_index = target, target_kind, k
                    break
            else:
                if float(bar["h"]) >= sl:
                    exit_price, exit_reason, exit_index = sl, "sl", k
                    break
                if float(bar["l"]) <= target:
                    exit_price, exit_reason, exit_index = target, target_kind, k
                    break
        if exit_price is None:
            exit_price = float(items[last_j]["c"])
            exit_reason = "timeout"
            exit_index = last_j

    signed = (exit_price - entry) if direction == "long" else (entry - exit_price)
    r_multiple = signed / risk
    if fee_pct > 0:
        r_multiple -= (fee_pct / 100.0) * (entry + exit_price) / risk
    return {
        "triggered": True,
        "index": i,
        "time": items[i].get("t"),
        "direction": direction,
        "entry": entry,
        "sl": sl,
        "tp": target,
        "entry_time": items[entry_index].get("t"),
        "exit_time": items[exit_index].get("t"),
        "exit_price": round(exit_price, 8),
        "exit_reason": exit_reason,
        "bars_held": exit_index - entry_index,
        "r": round(r_multiple, 3),
    }


def _stats(trades: list[dict]) -> dict:
    if not trades:
        return {
            "trades": 0, "wins": 0, "losses": 0, "win_rate_pct": None,
            "avg_r": None, "total_r": None, "profit_factor": None,
            "max_consecutive_losses": 0, "best_r": None, "worst_r": None,
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
        "max_consecutive_losses": best_streak,
        "best_r": round(max(t["r"] for t in trades), 3),
        "worst_r": round(min(t["r"] for t in trades), 3),
        "exit_reasons": reasons,
    }


def _ema(values: list[float], span: int) -> float | None:
    """Deterministic EMA (SMA-seeded) — last value only."""
    if len(values) < span:
        return None
    alpha = 2.0 / (span + 1)
    ema = sum(values[:span]) / span
    for v in values[span:]:
        ema = alpha * v + (1 - alpha) * ema
    return ema


GATE_RULES_FA = {
    "trend": "هم‌جهتی با EMA50: لانگ فقط اگر close>EMA50، شورت فقط اگر close<EMA50 (در لحظه سیگنال)",
    "votes": "رأی پک ۲۲ اندیکاتور: خالص ≥۱۵+ برای لانگ، ≤۱۵− برای شورت (همان پنجره لحظه سیگنال)",
    "perf": "عملکرد گذشته خودِ استراتژی در همین بازپخش: دست‌کم ۳ معامله بسته‌شده با مجموع R مثبت",
    "combo": "هر سه گیت با هم (trend + votes + perf)",
}
GATE_VOTE_THRESHOLD = 15
GATE_PERF_MIN_TRADES = 3
GATE_SUBSETS = (
    ("trend", ("gate_trend",)),
    ("votes", ("gate_votes",)),
    ("perf", ("gate_perf",)),
    ("trend+votes", ("gate_trend", "gate_votes")),
    ("combo", ("gate_trend", "gate_votes", "gate_perf")),
)
GATE_CLAIM_MIN_TRADES = 30      # below this, no edge is claimed
GATE_CLAIM_MIN_DELTA_R = 0.15   # minimum avgR improvement to call it better


def run(
    items: list[dict],
    symbol: str = "",
    timeframe: str = "15m",
    step: int = 3,
    min_quality: int = MIN_QUALITY_DEFAULT,
    exit_horizon: int | None = None,
    fee_pct: float = 0.0,
    gates: bool = True,
) -> dict:
    """Walk-forward replay of strategy_pack_v2 over ascending candles."""
    from app.services import strategy_pack_v2
    if gates:
        from app.services import indicator_pack_v2

    n = len(items)
    if n < WARMUP + 20:
        return {"ok": False, "detail": "insufficient_candles", "candles": n, "required": WARMUP + 20}

    exit_horizon = int(exit_horizon or max(24, min(96, n // 4)))
    open_until: dict[str, int] = {}   # strategy id -> index until which the book is busy
    trades: list[dict] = []
    signals_detected = 0
    signals_skipped_busy = 0
    signals_no_plan = 0
    signals_not_triggered = 0
    names: dict[str, str] = {}
    families: dict[str, str] = {}
    perf_count: dict[str, int] = {}   # closed trades per strategy so far (walk-forward)
    perf_total: dict[str, float] = {}

    i = WARMUP
    while i < n - 5:
        start = max(0, i + 1 - WINDOW)
        window = items[start:i + 1]
        try:
            scan = strategy_pack_v2.scan_all(window, timeframe)
        except Exception:
            i += step
            continue
        # gate context for this step — computed once, only from bars <= i
        net_votes: int | None = None
        ema50: float | None = None
        close_i: float | None = None
        if gates:
            closes = [float(b["c"]) for b in window]
            close_i = closes[-1] if closes else None
            ema50 = _ema(closes, 50)
            try:
                net_votes = int(indicator_pack_v2.summarize(indicator_pack_v2.compute_all(window)).get("net") or 0)
            except Exception:
                net_votes = None
        for sig in scan.get("active") or []:
            direction = str(sig.get("direction"))
            if direction not in ("long", "short"):
                continue
            quality = int(sig.get("quality") or 0)
            if quality < min_quality:
                continue
            sid = str(sig.get("id"))
            names[sid] = str(sig.get("name_fa") or sid)
            families[sid] = str(sig.get("family") or "")
            signals_detected += 1
            if open_until.get(sid, -1) >= i:
                signals_skipped_busy += 1
                continue
            entry = sig.get("entry")
            sl = sig.get("stop")
            target = sig.get("target")
            if not entry or not sl:
                signals_no_plan += 1
                continue
            outcome = _simulate_plan(items, i, direction, float(entry), float(sl),
                                     float(target) if target else None, exit_horizon, fee_pct)
            if outcome is None:
                signals_no_plan += 1
                continue
            if not outcome.get("triggered"):
                signals_not_triggered += 1
                continue
            row = {k: v for k, v in outcome.items() if k != "triggered"}
            row["strategy_id"] = sid
            row["name_fa"] = names[sid]
            row["family"] = families[sid]
            row["quality"] = quality
            if gates:
                row["gate_trend"] = bool(
                    ema50 is not None and close_i is not None and
                    (close_i > ema50 if direction == "long" else close_i < ema50)
                )
                row["gate_votes"] = bool(
                    net_votes is not None and
                    (net_votes >= GATE_VOTE_THRESHOLD if direction == "long"
                     else net_votes <= -GATE_VOTE_THRESHOLD)
                )
                row["gate_perf"] = bool(
                    perf_count.get(sid, 0) >= GATE_PERF_MIN_TRADES and
                    perf_total.get(sid, 0.0) > 0
                )
            trades.append(row)
            perf_count[sid] = perf_count.get(sid, 0) + 1
            perf_total[sid] = perf_total.get(sid, 0.0) + float(row["r"])
            exit_t = outcome.get("exit_time")
            busy_until = i + step
            if exit_t is not None:
                for j in range(i + 1, n):
                    if items[j].get("t") == exit_t:
                        busy_until = max(busy_until, j + 1)
                        break
            open_until[sid] = busy_until
        i += step

    by_strategy: dict[str, list[dict]] = {}
    for t in trades:
        by_strategy.setdefault(t["strategy_id"], []).append(t)
    by_bucket = {label: _stats([t for t in trades if pred(t["quality"])])
                 for label, pred in QUALITY_BUCKETS}
    by_direction = {
        "long": _stats([t for t in trades if t["direction"] == "long"]),
        "short": _stats([t for t in trades if t["direction"] == "short"]),
    }
    gate_section: dict[str, Any] = {}
    gate_subsets: dict[str, list[dict]] = {}
    if gates:
        gate_subsets = {
            gname: [t for t in trades if all(t.get(k) for k in keys)]
            for gname, keys in GATE_SUBSETS
        }
        gate_section = {
            "rules_fa": GATE_RULES_FA,
            "vote_threshold": GATE_VOTE_THRESHOLD,
            "perf_min_trades": GATE_PERF_MIN_TRADES,
            "claim_min_trades": GATE_CLAIM_MIN_TRADES,
            "subsets": {gname: _stats(rows) for gname, rows in gate_subsets.items()},
        }

    # honest, data-driven calibration verdict (no edge claimed under N=10)
    verdict_parts: list[str] = []
    hi = by_bucket["q65-74"]["trades"] + by_bucket["q75+"]["trades"]
    hi_trades = [t for t in trades if t["quality"] >= 65]
    lo_trades = [t for t in trades if t["quality"] < 65]
    if len(hi_trades) >= 10 and len(lo_trades) >= 10:
        hi_wr = sum(1 for t in hi_trades if t["r"] > 0) / len(hi_trades) * 100
        lo_wr = sum(1 for t in lo_trades if t["r"] > 0) / len(lo_trades) * 100
        hi_r = sum(t["r"] for t in hi_trades) / len(hi_trades)
        lo_r = sum(t["r"] for t in lo_trades) / len(lo_trades)
        verdict_parts.append(
            f"کیفیت ≥۶۵: {len(hi_trades)} معامله، WR={hi_wr:.0f}٪، avgR={hi_r:+.2f} | "
            f"کیفیت <۶۵: {len(lo_trades)} معامله، WR={lo_wr:.0f}٪، avgR={lo_r:+.2f}"
        )
        if hi_r > lo_r + 0.1:
            verdict_parts.append("→ امتیاز کیفیت با عملکرد همبستگی مثبت دارد (کالیبراسیون معتبر).")
        elif lo_r > hi_r + 0.1:
            verdict_parts.append("→ ⚠️ امتیاز کیفیت فعلاً با عملکرد همبستگی ندارد؛ به آن اتکا نکن تا بازکالیبره شود.")
        else:
            verdict_parts.append("→ تفاوت معناداری بین سبدهای کیفی دیده نشد.")
    else:
        verdict_parts.append(f"نمونه کافی برای سنجش کالیبراسیون کیفیت نیست (≥۶۵: {len(hi_trades)}، <۶۵: {len(lo_trades)} معامله؛ حداقل ۱۰+۱۰ لازم است).")
    if gates and trades:
        all_r = sum(t["r"] for t in trades) / len(trades)
        best_gate: str | None = None
        best_gate_r = 0.0
        best_gate_n = 0
        for gname, rows in gate_subsets.items():
            if len(rows) >= GATE_CLAIM_MIN_TRADES:
                sub_r = sum(t["r"] for t in rows) / len(rows)
                if best_gate is None or sub_r > best_gate_r:
                    best_gate, best_gate_r, best_gate_n = gname, sub_r, len(rows)
        if best_gate is None:
            verdict_parts.append(
                f"گیت‌ها: هیچ زیرمجموعه‌ای به نمونه ≥{GATE_CLAIM_MIN_TRADES} معامله نرسید — قضاوت درباره گیت ممکن نیست."
            )
        elif best_gate_r > all_r + GATE_CLAIM_MIN_DELTA_R:
            verdict_parts.append(
                f"بهترین گیت اندازه‌گیری‌شده «{best_gate}»: {best_gate_n} معامله با avgR={best_gate_r:+.2f} "
                f"(WR={sum(1 for t in gate_subsets[best_gate] if t['r'] > 0) / best_gate_n * 100:.0f}٪) "
                f"در برابر بدون گیت {len(trades)} معامله با avgR={all_r:+.2f} "
                f"→ روی این بازه گیت‌کردن بهبود واقعی داد (تضمین آینده نیست)."
            )
        else:
            verdict_parts.append(
                f"گیت‌ها: بهترین زیرمجموعه «{best_gate}» با avgR={best_gate_r:+.2f} در برابر بدون گیت "
                f"avgR={all_r:+.2f} → روی این بازه بهبود معناداری از گیت‌کردن دیده نشد."
            )

    ranked = sorted(
        ((sid, _stats(rows)) for sid, rows in by_strategy.items() if len(rows) >= 10),
        key=lambda kv: -(kv[1]["avg_r"] or 0),
    )
    if ranked:
        best_sid, best = ranked[0]
        worst_sid, worst = ranked[-1]
        verdict_parts.append(
            f"بهترین استراتژی (نمونه ≥۱۰): {names.get(best_sid, best_sid)} با {best['trades']} معامله، "
            f"WR={best['win_rate_pct']}٪، avgR={best['avg_r']:+.2f}"
        )
        if worst_sid != best_sid:
            verdict_parts.append(
                f"ضعیف‌ترین: {names.get(worst_sid, worst_sid)} با {worst['trades']} معامله، "
                f"WR={worst['win_rate_pct']}٪، avgR={worst['avg_r']:+.2f}"
            )
    else:
        verdict_parts.append("هیچ استراتژی در این بازه به نمونه ≥۱۰ معامله نرسید — قضاوت ممکن نیست.")

    return {
        "ok": True,
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "candles": n,
        "period": {"start_ts": items[0].get("t"), "end_ts": items[-1].get("t")},
        "settings": {
            "warmup": WARMUP, "window": WINDOW, "step": step,
            "min_quality": min_quality, "exit_horizon": exit_horizon,
            "fee_pct": fee_pct, "no_target_rule": "tp_2r",
            "fill_rule": "conservative_sl_first_no_same_bar_tp",
            "books": "per_strategy_no_overlap",
            "gates_enabled": gates,
        },
        "signals_detected": signals_detected,
        "signals_skipped_busy": signals_skipped_busy,
        "signals_no_plan": signals_no_plan,
        "signals_not_triggered": signals_not_triggered,
        "all": _stats(trades),
        "by_quality_bucket": by_bucket,
        "by_direction": by_direction,
        "gates": gate_section,
        "by_strategy": {
            sid: {"name_fa": names.get(sid, sid), "family": families.get(sid, ""), **_stats(rows)}
            for sid, rows in sorted(by_strategy.items())
        },
        "verdict_fa": " ".join(verdict_parts),
        "trades": trades[-40:],
        "disclaimer_fa": DISCLAIMER_FA,
        "created_by": "Amin Omidi",
    }


async def run_async(items: list[dict], **kwargs: Any) -> dict:
    return await asyncio.to_thread(run, items, **kwargs)
