package com.arena.smartmoney.ui.backtest

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import java.util.Locale

@Composable
fun BacktestScreen(viewModel: BacktestViewModel = viewModel()) {
    val state by viewModel.uiState.collectAsState()

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Text("Backtest Lab", style = MaterialTheme.typography.headlineSmall)
            Text("Run historical simulations on live-fetched candles")
        }
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.selectAsset("BTCUSDT", "crypto") }) { Text("BTC") }
                        Button(onClick = { viewModel.selectAsset("ETHUSDT", "crypto") }) { Text("ETH") }
                        Button(onClick = { viewModel.selectAsset("EURUSD", "forex") }) { Text("EURUSD") }
                        Button(onClick = { viewModel.selectAsset("XAUUSD", "forex") }) { Text("XAU") }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.selectTimeframe("15m") }) { Text("15m") }
                        Button(onClick = { viewModel.selectTimeframe("1h") }) { Text("1h") }
                        Button(onClick = { viewModel.runBacktest() }) { Text(if (state.loading) "Running..." else "Run") }
                        Button(onClick = { viewModel.runSweep() }) { Text("Sweep") }
                        Button(onClick = { viewModel.runWalkForward() }) { Text("Walk") }
                    }
                    Text("Asset: ${state.symbol} • ${state.timeframe}")
                    ParameterRow(
                        label = "Window Size",
                        value = state.windowSize.toString(),
                        onMinus = { viewModel.adjustWindowSize(-5) },
                        onPlus = { viewModel.adjustWindowSize(5) }
                    )
                    ParameterRow(
                        label = "Lookahead",
                        value = state.lookaheadCandles.toString(),
                        onMinus = { viewModel.adjustLookahead(-1) },
                        onPlus = { viewModel.adjustLookahead(1) }
                    )
                    ParameterRow(
                        label = "Max Signals",
                        value = state.maxSignals.toString(),
                        onMinus = { viewModel.adjustMaxSignals(-5) },
                        onPlus = { viewModel.adjustMaxSignals(5) }
                    )
                    ParameterRow(
                        label = "Score Threshold",
                        value = String.format(Locale.US, "%.1f", state.scoreThreshold),
                        onMinus = { viewModel.adjustScoreThreshold(-2.5) },
                        onPlus = { viewModel.adjustScoreThreshold(2.5) }
                    )
                    ParameterRow(
                        label = "Train Window",
                        value = state.trainWindow.toString(),
                        onMinus = { viewModel.adjustTrainWindow(-10) },
                        onPlus = { viewModel.adjustTrainWindow(10) }
                    )
                    ParameterRow(
                        label = "Test Window",
                        value = state.testWindow.toString(),
                        onMinus = { viewModel.adjustTestWindow(-5) },
                        onPlus = { viewModel.adjustTestWindow(5) }
                    )
                    ParameterRow(
                        label = "Step Size",
                        value = state.stepSize.toString(),
                        onMinus = { viewModel.adjustStepSize(-5) },
                        onPlus = { viewModel.adjustStepSize(5) }
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.cycleTakeProfit() }) { Text("TP Target") }
                        Text("Using TP${state.takeProfitIndex + 1}")
                    }
                    state.error?.let { Text("Error: $it", color = MaterialTheme.colorScheme.error) }
                }
            }
        }
        state.analytics?.let { analytics ->
            item {
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text("App Analytics", style = MaterialTheme.typography.titleMedium)
                        Text("Saved Signals: ${analytics.total_saved_signals}")
                        Text("Recent 24h Signals: ${analytics.recent_signals_24h}")
                        Text("Buy/Sell/Neutral: ${analytics.buy_signals} / ${analytics.sell_signals} / ${analytics.neutral_signals}")
                        Text("Avg Signal Score: ${analytics.average_signal_score}")
                        Text("Journal Win Rate: ${analytics.trade_stats.win_rate}%")
                        Text("Journal Net PnL: ${analytics.trade_stats.net_pnl}")
                    }
                }
            }
        }
        state.summary?.let { summary ->
            item {
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text("Backtest Summary", style = MaterialTheme.typography.titleMedium)
                        Text("Signals: ${summary.evaluated_signals} • Tested candles: ${summary.tested_candles}")
                        Text("Wins/Losses/Unclosed: ${summary.wins} / ${summary.losses} / ${summary.unclosed}")
                        Text("Win Rate: ${summary.win_rate}%")
                        Text("Average Score: ${summary.average_score}")
                        Text("Net RR: ${summary.net_rr}")
                        Text("Avg Win RR: ${summary.average_win_rr} • Avg Loss RR: ${summary.average_loss_rr}")
                        Text("Expectancy RR: ${summary.expectancy_rr} • Profit Factor: ${summary.profit_factor}")
                        Text("Win/Loss Streak: ${summary.longest_win_streak} / ${summary.longest_loss_streak}")
                    }
                }
            }
            items(summary.items) { item ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text("${item.direction.uppercase(Locale.getDefault())} • ${item.score}", style = MaterialTheme.typography.titleMedium)
                        Text("Signal Time: ${item.signal_time}")
                        Text("Entry: ${item.entry_price} • SL: ${item.stop_loss} • TP: ${item.take_profit}")
                        Text("Outcome: ${item.outcome} • RR: ${item.rr_realized} • Bars held: ${item.bars_held}")
                    }
                }
            }
        }
        state.sweepSummary?.let { sweep ->
            item {
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text("Parameter Sweep", style = MaterialTheme.typography.titleMedium)
                        Text("Combinations tested: ${sweep.combinations_tested}")
                        sweep.best_by_net_rr?.let {
                            Text("Best Net RR → W:${it.window_size} L:${it.lookahead_candles} T:${it.score_threshold} TP${it.take_profit_index + 1} RR:${it.net_rr}")
                        }
                        sweep.best_by_win_rate?.let {
                            Text("Best Win Rate → W:${it.window_size} L:${it.lookahead_candles} T:${it.score_threshold} TP${it.take_profit_index + 1} WR:${it.win_rate}%")
                        }
                    }
                }
            }
            items(sweep.items) { item ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(
                            "W:${item.window_size} • L:${item.lookahead_candles} • T:${item.score_threshold} • TP${item.take_profit_index + 1}",
                            style = MaterialTheme.typography.titleMedium
                        )
                        Text("Signals: ${item.evaluated_signals} • Wins/Losses: ${item.wins}/${item.losses} • Unclosed: ${item.unclosed}")
                        Text("Win Rate: ${item.win_rate}% • Net RR: ${item.net_rr} • Expectancy: ${item.expectancy_rr}")
                        Text("Profit Factor: ${item.profit_factor} • Streak W/L: ${item.longest_win_streak}/${item.longest_loss_streak}")
                    }
                }
            }
        }
        state.walkForwardSummary?.let { wf ->
            item {
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text("Walk-Forward Summary", style = MaterialTheme.typography.titleMedium)
                        Text("Steps: ${wf.steps_executed} • Test Signals: ${wf.total_test_signals}")
                        Text("Wins/Losses/Unclosed: ${wf.total_wins}/${wf.total_losses}/${wf.total_unclosed}")
                        Text("Aggregate Win Rate: ${wf.aggregate_win_rate}%")
                        Text("Aggregate Net RR: ${wf.aggregate_net_rr}")
                        Text("Average Step Expectancy: ${wf.average_step_expectancy_rr}")
                        Text("Best/Worst Step: ${wf.best_step_index ?: "-"}/${wf.worst_step_index ?: "-"}")
                    }
                }
            }
            items(wf.items) { item ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text("Step ${item.step_index}", style = MaterialTheme.typography.titleMedium)
                        Text("Train: ${item.train_start_time} → ${item.train_end_time}")
                        Text("Test: ${item.test_start_time} → ${item.test_end_time}")
                        Text("Params: W${item.selected_window_size} / L${item.selected_lookahead_candles} / T${item.selected_score_threshold} / TP${item.selected_take_profit_index + 1}")
                        Text("Training RR: ${item.training_net_rr} • Training WR: ${item.training_win_rate}%")
                        Text("Test Signals: ${item.test_evaluated_signals} • W/L/U: ${item.test_wins}/${item.test_losses}/${item.test_unclosed}")
                        Text("Test WR: ${item.test_win_rate}% • Net RR: ${item.test_net_rr} • Exp: ${item.test_expectancy_rr}")
                    }
                }
            }
        }
    }
}

@Composable
private fun ParameterRow(
    label: String,
    value: String,
    onMinus: () -> Unit,
    onPlus: () -> Unit
) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(label, modifier = Modifier.weight(1f))
        Button(onClick = onMinus) { Text("-") }
        Text(value, modifier = Modifier.padding(horizontal = 4.dp))
        Button(onClick = onPlus) { Text("+") }
    }
}
