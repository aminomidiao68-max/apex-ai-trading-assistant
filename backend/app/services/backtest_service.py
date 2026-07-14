from __future__ import annotations

from statistics import mean

from app.models import (
    BacktestExecutionSettings,
    BacktestRunRequest,
    BacktestSummary,
    BacktestSweepCandidate,
    BacktestSweepRequest,
    BacktestSweepSummary,
    BacktestTradeResult,
    Candle,
    MarketType,
    SignalDirection,
    SignalRequest,
    WalkForwardRequest,
    WalkForwardStepResult,
    WalkForwardSummary,
)
from app.services.signal_engine import SignalEngine


_EXECUTION_MODEL = "conservative_ohlc_v2"


def _timeframe_minutes(timeframe: str) -> int:
    value = timeframe.lower().strip().replace("min", "m")
    mapping = {
        "1m": 1,
        "3m": 3,
        "5m": 5,
        "15m": 15,
        "30m": 30,
        "1h": 60,
        "2h": 120,
        "4h": 240,
        "6h": 360,
        "12h": 720,
        "1d": 1440,
    }
    return mapping.get(value, 15)


def _resolved_costs(
    market: MarketType,
    execution: BacktestExecutionSettings,
) -> tuple[float, float, float, list[str]]:
    if market == MarketType.crypto:
        default_fee, default_spread, default_slippage = 4.0, 1.0, 1.0
    else:
        default_fee, default_spread, default_slippage = 1.0, 2.0, 0.75
    fee = default_fee if execution.fee_bps_per_side is None else execution.fee_bps_per_side
    spread = default_spread if execution.spread_bps is None else execution.spread_bps
    slippage = default_slippage if execution.slippage_bps is None else execution.slippage_bps
    assumptions = [
        f"fee_per_side_bps={fee:.4f}",
        f"spread_bps={spread:.4f}",
        f"slippage_per_fill_bps={slippage:.4f}",
        f"funding_bps_per_8h={execution.funding_bps_per_8h:.4f}",
        "entry_must_trade_before_expiry",
        "same_bar_stop_and_target_resolves_to_stop",
        "favorable_exit_gaps_receive_no_price_improvement",
        "signals_use_closed_candles_only",
    ]
    if execution.prevent_overlapping_trades:
        assumptions.append("overlapping_positions_prevented")
    if execution.mark_unclosed_to_market:
        assumptions.append("unclosed_positions_marked_to_market")
    return float(fee), float(spread), float(slippage), assumptions


class BacktestService:
    def __init__(self, engine: SignalEngine | None = None) -> None:
        self.engine = engine or SignalEngine()

    def run(self, request: BacktestRunRequest, candles: list[Candle]) -> BacktestSummary:
        self._validate_candles(candles)
        results = self._generate_results(request, candles)
        return self._summarize_results(request, len(candles), results)

    def run_sweep(self, request: BacktestSweepRequest, candles: list[Candle]) -> BacktestSweepSummary:
        self._validate_candles(candles)
        candidates: list[BacktestSweepCandidate] = []
        combinations_tested = 0

        for window_size in self._unique_sorted_ints(request.window_sizes, minimum=20, maximum=120):
            for lookahead in self._unique_sorted_ints(request.lookahead_options, minimum=2, maximum=50):
                for threshold in self._unique_sorted_floats(request.score_thresholds, minimum=0.0, maximum=100.0):
                    for tp_index in self._unique_sorted_ints(request.take_profit_indices, minimum=0, maximum=2):
                        if len(candles) < window_size + lookahead + 5:
                            continue
                        combinations_tested += 1
                        run_request = BacktestRunRequest(
                            symbol=request.symbol,
                            market=request.market,
                            timeframe=request.timeframe,
                            window_size=window_size,
                            lookahead_candles=lookahead,
                            score_threshold=threshold,
                            max_signals=request.max_signals,
                            take_profit_index=tp_index,
                            client_timezone=request.client_timezone,
                            risk_settings=request.risk_settings,
                            trade_stats=request.trade_stats,
                            execution=request.execution,
                        )
                        summary = self.run(run_request, candles)
                        if summary.activated_signals < request.minimum_activated_trades:
                            continue
                        candidates.append(
                            BacktestSweepCandidate(
                                window_size=window_size,
                                lookahead_candles=lookahead,
                                score_threshold=threshold,
                                take_profit_index=tp_index,
                                evaluated_signals=summary.evaluated_signals,
                                wins=summary.wins,
                                losses=summary.losses,
                                unclosed=summary.unclosed,
                                win_rate=summary.win_rate,
                                net_rr=summary.net_rr,
                                expectancy_rr=summary.expectancy_rr,
                                profit_factor=summary.profit_factor,
                                longest_win_streak=summary.longest_win_streak,
                                longest_loss_streak=summary.longest_loss_streak,
                                activated_signals=summary.activated_signals,
                                no_entry=summary.no_entry,
                                total_costs_rr=summary.total_costs_rr,
                                max_drawdown_rr=summary.max_drawdown_rr,
                            )
                        )

        items = sorted(
            candidates,
            key=lambda item: (
                item.net_rr,
                item.expectancy_rr,
                -item.max_drawdown_rr,
                item.activated_signals,
            ),
            reverse=True,
        )[: request.max_results]
        best_by_net_rr = items[0] if items else None
        best_by_win_rate = None
        if candidates:
            best_by_win_rate = sorted(
                candidates,
                key=lambda item: (
                    item.win_rate,
                    item.net_rr,
                    item.expectancy_rr,
                    -item.max_drawdown_rr,
                    item.activated_signals,
                ),
                reverse=True,
            )[0]

        return BacktestSweepSummary(
            symbol=request.symbol.upper(),
            market=request.market,
            timeframe=request.timeframe,
            combinations_tested=combinations_tested,
            best_by_net_rr=best_by_net_rr,
            best_by_win_rate=best_by_win_rate,
            items=items,
        )

    def run_walk_forward(self, request: WalkForwardRequest, candles: list[Candle]) -> WalkForwardSummary:
        self._validate_candles(candles)
        items: list[WalkForwardStepResult] = []
        cursor = 0
        step_index = 0

        while step_index < request.max_steps:
            train_start = cursor
            train_end = train_start + request.train_window
            test_end = train_end + request.test_window
            if test_end > len(candles):
                break

            training_candles = candles[train_start:train_end]
            sweep = self.run_sweep(
                BacktestSweepRequest(
                    symbol=request.symbol,
                    market=request.market,
                    timeframe=request.timeframe,
                    window_sizes=request.window_sizes,
                    lookahead_options=request.lookahead_options,
                    score_thresholds=request.score_thresholds,
                    take_profit_indices=request.take_profit_indices,
                    max_signals=request.max_signals,
                    max_results=3,
                    minimum_activated_trades=request.minimum_activated_trades,
                    client_timezone=request.client_timezone,
                    risk_settings=request.risk_settings,
                    trade_stats=request.trade_stats,
                    execution=request.execution,
                ),
                training_candles,
            )
            if not sweep.best_by_net_rr:
                cursor += request.step_size
                step_index += 1
                continue

            selected = sweep.best_by_net_rr
            combined = candles[train_start:test_end]
            test_request = BacktestRunRequest(
                symbol=request.symbol,
                market=request.market,
                timeframe=request.timeframe,
                window_size=selected.window_size,
                lookahead_candles=selected.lookahead_candles,
                score_threshold=selected.score_threshold,
                max_signals=request.max_signals,
                take_profit_index=selected.take_profit_index,
                client_timezone=request.client_timezone,
                risk_settings=request.risk_settings,
                trade_stats=request.trade_stats,
                execution=request.execution,
            )
            test_results = self._generate_results(
                test_request,
                combined,
                start_index=request.train_window,
                end_index=len(combined) - selected.lookahead_candles + 1,
            )
            summary = self._summarize_results(test_request, len(combined), test_results)
            items.append(
                WalkForwardStepResult(
                    step_index=step_index + 1,
                    train_start_time=combined[0].timestamp.isoformat(),
                    train_end_time=combined[request.train_window - 1].timestamp.isoformat(),
                    test_start_time=combined[request.train_window].timestamp.isoformat(),
                    test_end_time=combined[-1].timestamp.isoformat(),
                    selected_window_size=selected.window_size,
                    selected_lookahead_candles=selected.lookahead_candles,
                    selected_score_threshold=selected.score_threshold,
                    selected_take_profit_index=selected.take_profit_index,
                    training_net_rr=selected.net_rr,
                    training_win_rate=selected.win_rate,
                    test_evaluated_signals=summary.evaluated_signals,
                    test_wins=summary.wins,
                    test_losses=summary.losses,
                    test_unclosed=summary.unclosed,
                    test_win_rate=summary.win_rate,
                    test_net_rr=summary.net_rr,
                    test_expectancy_rr=summary.expectancy_rr,
                )
            )
            cursor += request.step_size
            step_index += 1

        total_test_signals = sum(item.test_evaluated_signals for item in items)
        total_wins = sum(item.test_wins for item in items)
        total_losses = sum(item.test_losses for item in items)
        total_unclosed = sum(item.test_unclosed for item in items)
        aggregate_net_rr = round(sum(item.test_net_rr for item in items), 4)
        closed = total_wins + total_losses
        aggregate_win_rate = round((total_wins / closed) * 100, 2) if closed else 0.0
        avg_expectancy = round(mean([item.test_expectancy_rr for item in items]), 4) if items else 0.0
        best_step = max(items, key=lambda x: x.test_net_rr).step_index if items else None
        worst_step = min(items, key=lambda x: x.test_net_rr).step_index if items else None

        return WalkForwardSummary(
            symbol=request.symbol.upper(),
            market=request.market,
            timeframe=request.timeframe,
            steps_executed=len(items),
            total_test_signals=total_test_signals,
            total_wins=total_wins,
            total_losses=total_losses,
            total_unclosed=total_unclosed,
            aggregate_win_rate=aggregate_win_rate,
            aggregate_net_rr=aggregate_net_rr,
            average_step_expectancy_rr=avg_expectancy,
            best_step_index=best_step,
            worst_step_index=worst_step,
            items=items,
        )

    def _generate_results(
        self,
        request: BacktestRunRequest,
        candles: list[Candle],
        start_index: int | None = None,
        end_index: int | None = None,
    ) -> list[BacktestTradeResult]:
        results: list[BacktestTradeResult] = []
        start = max(request.window_size, start_index or request.window_size)
        natural_end = len(candles) - request.lookahead_candles + 1
        last_index = min(end_index if end_index is not None else natural_end, natural_end)
        next_eligible_index = start

        for index in range(start, max(start, last_index)):
            if len(results) >= request.max_signals:
                break
            if request.execution.prevent_overlapping_trades and index < next_eligible_index:
                continue

            # The signal engine receives only candles closed before `index`.
            # The first candle that can activate the entry is candles[index].
            window = candles[index - request.window_size:index]
            signal = self.engine.analyze(
                SignalRequest(
                    symbol=request.symbol.upper(),
                    market=request.market,
                    timeframe=request.timeframe,
                    candles=window,
                    risk_settings=request.risk_settings,
                    trade_stats=request.trade_stats,
                    client_timezone=request.client_timezone,
                )
            )

            if signal.direction == SignalDirection.neutral:
                continue
            if signal.score < request.score_threshold:
                continue
            if signal.entry_low is None or signal.entry_high is None or signal.stop_loss is None:
                continue
            if len(signal.take_profits) <= request.take_profit_index:
                continue

            entry = (signal.entry_low + signal.entry_high) / 2.0
            stop = signal.stop_loss
            take_profit = signal.take_profits[request.take_profit_index]
            if not self._valid_geometry(signal.direction, entry, stop, take_profit):
                continue

            future = candles[index:index + request.lookahead_candles]
            evaluated = self._evaluate_trade(
                direction=signal.direction,
                future=future,
                entry=entry,
                stop=stop,
                take_profit=take_profit,
                market=request.market,
                timeframe=request.timeframe,
                execution=request.execution,
            )
            consumed_bars = int(evaluated.pop("consumed_bars"))
            result = BacktestTradeResult(
                signal_time=window[-1].timestamp.isoformat(),
                direction=signal.direction,
                score=signal.score,
                entry_price=round(entry, 8),
                stop_loss=round(stop, 8),
                take_profit=round(take_profit, 8),
                **evaluated,
            )
            results.append(result)

            if request.execution.prevent_overlapping_trades and result.activated:
                next_eligible_index = max(index + consumed_bars, index + 1)

        return results

    def _summarize_results(
        self,
        request: BacktestRunRequest,
        tested_candles: int,
        results: list[BacktestTradeResult],
    ) -> BacktestSummary:
        wins = [item for item in results if item.outcome == "win"]
        losses = [item for item in results if item.outcome == "loss"]
        unclosed = [item for item in results if item.outcome == "unclosed"]
        no_entry = [item for item in results if item.outcome == "no_entry"]
        activated = [item for item in results if item.activated]
        avg_score = round(mean([item.score for item in results]), 2) if results else 0.0
        net_rr = round(sum(item.rr_realized for item in activated), 4)
        gross_rr = round(sum(item.gross_rr for item in activated), 4)
        total_costs = round(sum(item.costs_rr for item in activated), 4)
        total_fees = round(sum(item.fee_rr for item in activated), 4)
        total_funding = round(sum(item.funding_rr for item in activated), 4)
        closed_count = len(wins) + len(losses)
        win_rate = round((len(wins) / closed_count) * 100, 2) if closed_count else 0.0
        average_win_rr = round(mean([item.rr_realized for item in wins]), 4) if wins else 0.0
        average_loss_rr = round(mean([item.rr_realized for item in losses]), 4) if losses else 0.0
        expectancy_rr = round((net_rr / len(activated)), 4) if activated else 0.0
        positive_rr = sum(max(item.rr_realized, 0.0) for item in activated)
        negative_rr_abs = abs(sum(min(item.rr_realized, 0.0) for item in activated))
        profit_factor = round(positive_rr / negative_rr_abs, 4) if negative_rr_abs > 0 else round(positive_rr, 4)
        longest_win_streak, longest_loss_streak = self._streaks(results)
        max_drawdown_rr = self._max_drawdown_rr(activated)
        _, _, _, assumptions = _resolved_costs(request.market, request.execution)

        return BacktestSummary(
            symbol=request.symbol.upper(),
            market=request.market,
            timeframe=request.timeframe,
            tested_candles=tested_candles,
            evaluated_signals=len(results),
            wins=len(wins),
            losses=len(losses),
            unclosed=len(unclosed),
            win_rate=win_rate,
            average_score=avg_score,
            net_rr=net_rr,
            average_win_rr=average_win_rr,
            average_loss_rr=average_loss_rr,
            expectancy_rr=expectancy_rr,
            profit_factor=profit_factor,
            longest_win_streak=longest_win_streak,
            longest_loss_streak=longest_loss_streak,
            activated_signals=len(activated),
            no_entry=len(no_entry),
            closed_trades=closed_count,
            gross_rr=gross_rr,
            total_costs_rr=total_costs,
            total_fee_rr=total_fees,
            total_funding_rr=total_funding,
            max_drawdown_rr=max_drawdown_rr,
            execution_model=_EXECUTION_MODEL,
            intrabar_policy=request.execution.intrabar_policy,
            anti_lookahead_enforced=True,
            assumptions=assumptions,
            items=results,
        )

    def _evaluate_trade(
        self,
        direction: SignalDirection,
        future: list[Candle],
        entry: float,
        stop: float,
        take_profit: float,
        market: MarketType,
        timeframe: str,
        execution: BacktestExecutionSettings,
    ) -> dict:
        risk = abs(entry - stop)
        if risk <= 0 or not future:
            return {
                "outcome": "no_entry",
                "rr_realized": 0.0,
                "bars_held": 0,
                "activated": False,
                "activation_time": None,
                "bars_to_entry": 0,
                "exit_price": None,
                "exit_reason": "invalid_or_empty_path",
                "gross_rr": 0.0,
                "costs_rr": 0.0,
                "fee_rr": 0.0,
                "funding_rr": 0.0,
                "consumed_bars": 1,
            }

        fee_bps, spread_bps, slippage_bps, _ = _resolved_costs(market, execution)
        adverse_entry_bps = spread_bps / 2.0 + slippage_bps
        adverse_exit_bps = spread_bps / 2.0 + slippage_bps
        if direction == SignalDirection.buy:
            entry_fill = entry * (1.0 + adverse_entry_bps / 10_000.0)
        else:
            entry_fill = entry * (1.0 - adverse_entry_bps / 10_000.0)

        entry_bar_number = 0
        activation_time: str | None = None
        expiry = min(execution.entry_expiry_bars, len(future))
        outcome = "no_entry"
        raw_exit: float | None = None
        exit_fill: float | None = None
        exit_reason = "entry_not_traded_before_expiry"
        exit_bar_number = 0

        for bar_number, candle in enumerate(future, start=1):
            if not entry_bar_number:
                if bar_number > expiry:
                    break
                if not (candle.low <= entry <= candle.high):
                    continue
                entry_bar_number = bar_number
                activation_time = candle.timestamp.isoformat()

            if direction == SignalDirection.buy:
                gap_stop = candle.open <= stop and bar_number > entry_bar_number
                gap_target = candle.open >= take_profit and bar_number > entry_bar_number
                hit_stop = candle.low <= stop
                hit_target = candle.high >= take_profit
            else:
                gap_stop = candle.open >= stop and bar_number > entry_bar_number
                gap_target = candle.open <= take_profit and bar_number > entry_bar_number
                hit_stop = candle.high >= stop
                hit_target = candle.low <= take_profit

            # Gaps after activation are handled first. Adverse stop gaps receive
            # the worse open; favorable target gaps receive no improvement.
            if gap_stop:
                outcome = "loss"
                raw_exit = candle.open
                exit_reason = "stop_gap"
            elif gap_target:
                outcome = "win"
                raw_exit = take_profit
                exit_reason = "target_gap_no_improvement"
            elif hit_stop and hit_target:
                outcome = "loss"
                raw_exit = stop
                exit_reason = "ambiguous_bar_stop_first"
            elif hit_stop:
                outcome = "loss"
                raw_exit = stop
                exit_reason = "stop"
            elif hit_target:
                outcome = "win"
                raw_exit = take_profit
                exit_reason = "target"

            if raw_exit is not None:
                exit_bar_number = bar_number
                break

        if not entry_bar_number:
            return {
                "outcome": "no_entry",
                "rr_realized": 0.0,
                "bars_held": 0,
                "activated": False,
                "activation_time": None,
                "bars_to_entry": 0,
                "exit_price": None,
                "exit_reason": exit_reason,
                "gross_rr": 0.0,
                "costs_rr": 0.0,
                "fee_rr": 0.0,
                "funding_rr": 0.0,
                "consumed_bars": max(1, expiry),
            }

        if raw_exit is None:
            outcome = "unclosed"
            exit_bar_number = len(future)
            if execution.mark_unclosed_to_market:
                raw_exit = future[-1].close
                exit_reason = "marked_to_market"
            else:
                exit_reason = "left_unrealized"

        bars_held = max(1, exit_bar_number - entry_bar_number + 1)
        if raw_exit is not None:
            if direction == SignalDirection.buy:
                exit_fill = raw_exit * (1.0 - adverse_exit_bps / 10_000.0)
                gross_rr = (raw_exit - entry) / risk
                execution_rr = (exit_fill - entry_fill) / risk
            else:
                exit_fill = raw_exit * (1.0 + adverse_exit_bps / 10_000.0)
                gross_rr = (entry - raw_exit) / risk
                execution_rr = (entry_fill - exit_fill) / risk
            fee_rr = (entry_fill + exit_fill) * (fee_bps / 10_000.0) / risk
            friction_rr = max(0.0, gross_rr - execution_rr)
        else:
            gross_rr = 0.0
            entry_friction = abs(entry_fill - entry) / risk
            fee_rr = entry_fill * (fee_bps / 10_000.0) / risk
            friction_rr = entry_friction
            execution_rr = -entry_friction

        hours_held = bars_held * _timeframe_minutes(timeframe) / 60.0
        funding_rr = (
            entry_fill
            * (execution.funding_bps_per_8h / 10_000.0)
            * (hours_held / 8.0)
            / risk
        )
        costs_rr = max(0.0, friction_rr + fee_rr + funding_rr)
        net_rr = gross_rr - costs_rr

        return {
            "outcome": outcome,
            "rr_realized": round(net_rr, 6),
            "bars_held": bars_held,
            "activated": True,
            "activation_time": activation_time,
            "bars_to_entry": entry_bar_number,
            "exit_price": round(exit_fill, 8) if exit_fill is not None else None,
            "exit_reason": exit_reason,
            "gross_rr": round(gross_rr, 6),
            "costs_rr": round(costs_rr, 6),
            "fee_rr": round(fee_rr, 6),
            "funding_rr": round(funding_rr, 6),
            "consumed_bars": max(1, exit_bar_number),
        }

    def _validate_candles(self, candles: list[Candle]) -> None:
        for previous, current in zip(candles, candles[1:]):
            if current.timestamp <= previous.timestamp:
                raise ValueError("Backtest candles must have strictly increasing timestamps")

    def _valid_geometry(
        self,
        direction: SignalDirection,
        entry: float,
        stop: float,
        take_profit: float,
    ) -> bool:
        if direction == SignalDirection.buy:
            return stop < entry < take_profit
        if direction == SignalDirection.sell:
            return take_profit < entry < stop
        return False

    def _max_drawdown_rr(self, results: list[BacktestTradeResult]) -> float:
        equity = 0.0
        peak = 0.0
        maximum = 0.0
        for item in results:
            equity += item.rr_realized
            peak = max(peak, equity)
            maximum = max(maximum, peak - equity)
        return round(maximum, 4)

    def _streaks(self, results: list[BacktestTradeResult]) -> tuple[int, int]:
        max_win = 0
        max_loss = 0
        current_win = 0
        current_loss = 0

        for item in results:
            if item.outcome == "win":
                current_win += 1
                current_loss = 0
            elif item.outcome == "loss":
                current_loss += 1
                current_win = 0
            elif item.outcome != "no_entry":
                current_win = 0
                current_loss = 0

            max_win = max(max_win, current_win)
            max_loss = max(max_loss, current_loss)

        return max_win, max_loss

    def _unique_sorted_ints(self, values: list[int], minimum: int, maximum: int) -> list[int]:
        return sorted({min(max(v, minimum), maximum) for v in values})

    def _unique_sorted_floats(self, values: list[float], minimum: float, maximum: float) -> list[float]:
        return sorted({float(min(max(v, minimum), maximum)) for v in values})
