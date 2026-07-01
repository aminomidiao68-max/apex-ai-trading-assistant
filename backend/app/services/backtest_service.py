from __future__ import annotations

from statistics import mean

from app.models import (
    BacktestRunRequest,
    BacktestSummary,
    BacktestSweepCandidate,
    BacktestSweepRequest,
    BacktestSweepSummary,
    BacktestTradeResult,
    Candle,
    SignalDirection,
    SignalRequest,
    WalkForwardRequest,
    WalkForwardStepResult,
    WalkForwardSummary,
)
from app.services.signal_engine import SignalEngine


class BacktestService:
    def __init__(self, engine: SignalEngine | None = None) -> None:
        self.engine = engine or SignalEngine()

    def run(self, request: BacktestRunRequest, candles: list[Candle]) -> BacktestSummary:
        results = self._generate_results(request, candles)
        return self._summarize_results(request.symbol.upper(), request.market, request.timeframe, len(candles), results)

    def run_sweep(self, request: BacktestSweepRequest, candles: list[Candle]) -> BacktestSweepSummary:
        candidates: list[BacktestSweepCandidate] = []
        combinations_tested = 0

        for window_size in self._unique_sorted_ints(request.window_sizes, minimum=20, maximum=120):
            for lookahead in self._unique_sorted_ints(request.lookahead_options, minimum=2, maximum=50):
                for threshold in self._unique_sorted_floats(request.score_thresholds, minimum=0.0, maximum=100.0):
                    for tp_index in self._unique_sorted_ints(request.take_profit_indices, minimum=0, maximum=2):
                        if len(candles) < window_size + lookahead + 5:
                            continue
                        combinations_tested += 1
                        summary = self.run(
                            BacktestRunRequest(
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
                            ),
                            candles,
                        )
                        if summary.evaluated_signals == 0:
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
                            )
                        )

        items = sorted(
            candidates,
            key=lambda item: (item.net_rr, item.expectancy_rr, item.win_rate, item.evaluated_signals),
            reverse=True,
        )[: request.max_results]
        best_by_net_rr = items[0] if items else None
        best_by_win_rate = None
        if candidates:
            best_by_win_rate = sorted(
                candidates,
                key=lambda item: (item.win_rate, item.net_rr, item.expectancy_rr, item.evaluated_signals),
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
                    client_timezone=request.client_timezone,
                    risk_settings=request.risk_settings,
                    trade_stats=request.trade_stats,
                ),
                training_candles,
            )
            if not sweep.best_by_net_rr:
                cursor += request.step_size
                step_index += 1
                continue

            selected = sweep.best_by_net_rr
            combined = candles[train_start:test_end]
            test_results = self._generate_results(
                BacktestRunRequest(
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
                ),
                combined,
                start_index=request.train_window,
                end_index=len(combined) - selected.lookahead_candles,
            )
            summary = self._summarize_results(
                request.symbol.upper(),
                request.market,
                request.timeframe,
                len(combined),
                test_results,
            )
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
        aggregate_net_rr = round(sum(item.test_net_rr for item in items), 2)
        closed = total_wins + total_losses
        aggregate_win_rate = round((total_wins / closed) * 100, 2) if closed else 0.0
        avg_expectancy = round(mean([item.test_expectancy_rr for item in items]), 2) if items else 0.0
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
        last_index = (end_index if end_index is not None else len(candles) - request.lookahead_candles)

        for index in range(start, last_index):
            if len(results) >= request.max_signals:
                break

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

            future = candles[index:index + request.lookahead_candles]
            entry = (signal.entry_low + signal.entry_high) / 2
            stop = signal.stop_loss
            tp = signal.take_profits[request.take_profit_index]
            outcome, rr, bars_held = self._evaluate_trade(signal.direction, future, entry, stop, tp)

            results.append(
                BacktestTradeResult(
                    signal_time=window[-1].timestamp.isoformat(),
                    direction=signal.direction,
                    score=signal.score,
                    entry_price=round(entry, 6),
                    stop_loss=round(stop, 6),
                    take_profit=round(tp, 6),
                    outcome=outcome,
                    rr_realized=round(rr, 2),
                    bars_held=bars_held,
                )
            )
        return results

    def _summarize_results(
        self,
        symbol: str,
        market,
        timeframe: str,
        tested_candles: int,
        results: list[BacktestTradeResult],
    ) -> BacktestSummary:
        wins = [item for item in results if item.outcome == "win"]
        losses = [item for item in results if item.outcome == "loss"]
        unclosed = [item for item in results if item.outcome == "unclosed"]
        avg_score = round(mean([item.score for item in results]), 2) if results else 0.0
        net_rr = round(sum(item.rr_realized for item in results), 2)
        closed_count = len(wins) + len(losses)
        win_rate = round((len(wins) / closed_count) * 100, 2) if closed_count else 0.0
        average_win_rr = round(mean([item.rr_realized for item in wins]), 2) if wins else 0.0
        average_loss_rr = round(mean([item.rr_realized for item in losses]), 2) if losses else 0.0
        expectancy_rr = round((net_rr / len(results)), 2) if results else 0.0
        positive_rr = sum(item.rr_realized for item in wins)
        negative_rr_abs = abs(sum(item.rr_realized for item in losses))
        profit_factor = round(positive_rr / negative_rr_abs, 2) if negative_rr_abs > 0 else round(positive_rr, 2)
        longest_win_streak, longest_loss_streak = self._streaks(results)

        return BacktestSummary(
            symbol=symbol,
            market=market,
            timeframe=timeframe,
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
            items=results,
        )

    def _evaluate_trade(
        self,
        direction: SignalDirection,
        future: list[Candle],
        entry: float,
        stop: float,
        take_profit: float,
    ) -> tuple[str, float, int]:
        risk = abs(entry - stop)
        reward = abs(take_profit - entry)
        rr = reward / risk if risk > 0 else 0.0

        for idx, candle in enumerate(future, start=1):
            if direction == SignalDirection.buy:
                hit_stop = candle.low <= stop
                hit_tp = candle.high >= take_profit
            else:
                hit_stop = candle.high >= stop
                hit_tp = candle.low <= take_profit

            if hit_stop and hit_tp:
                return "loss", -1.0, idx
            if hit_tp:
                return "win", rr, idx
            if hit_stop:
                return "loss", -1.0, idx

        return "unclosed", 0.0, len(future)

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
            else:
                current_win = 0
                current_loss = 0

            max_win = max(max_win, current_win)
            max_loss = max(max_loss, current_loss)

        return max_win, max_loss

    def _unique_sorted_ints(self, values: list[int], minimum: int, maximum: int) -> list[int]:
        return sorted({min(max(v, minimum), maximum) for v in values})

    def _unique_sorted_floats(self, values: list[float], minimum: float, maximum: float) -> list[float]:
        return sorted({float(min(max(v, minimum), maximum)) for v in values})
