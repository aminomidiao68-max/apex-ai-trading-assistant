package com.arena.smartmoney.ui.backtest

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.arena.smartmoney.ui.i18n.rememberTranslator
import java.util.Locale

@Composable
fun BacktestScreen(viewModel: BacktestViewModel = viewModel()) {
    val state by viewModel.uiState.collectAsState()
    val t = rememberTranslator()

    androidx.compose.foundation.lazy.LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Text(
                t("Backtest Lab", "آزمایشگاه بک‌تست"),
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold
            )
            Text(
                t(
                    "Run historical simulations, parameter sweep and walk-forward validation on live-fetched candles.",
                    "شبیه‌سازی تاریخی، سوییپ پارامترها و اعتبارسنجی واک‌فوروارد را روی کندل‌های زنده اجرا کن."
                )
            )
        }
        item {
            Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(22.dp)) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Text(t("Scenario Setup", "تنظیم سناریو"), style = MaterialTheme.typography.titleLarge)
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.selectAsset("BTCUSDT", "crypto") }, modifier = Modifier.weight(1f)) { Text("BTC") }
                        Button(onClick = { viewModel.selectAsset("ETHUSDT", "crypto") }, modifier = Modifier.weight(1f)) { Text("ETH") }
                    }
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.selectAsset("EURUSD", "forex") }, modifier = Modifier.weight(1f)) { Text("EURUSD") }
                        Button(onClick = { viewModel.selectAsset("XAUUSD", "forex") }, modifier = Modifier.weight(1f)) { Text("XAUUSD") }
                    }
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.selectTimeframe("15m") }, modifier = Modifier.weight(1f)) { Text("15m") }
                        Button(onClick = { viewModel.selectTimeframe("1h") }, modifier = Modifier.weight(1f)) { Text("1h") }
                    }
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.runBacktest() }, modifier = Modifier.weight(1f)) {
                            Text(if (state.loading) t("Running...", "در حال اجرا...") else t("Run", "اجرا"))
                        }
                        Button(onClick = { viewModel.runSweep() }, modifier = Modifier.weight(1f)) {
                            Text(t("Sweep", "سوییپ"))
                        }
                        Button(onClick = { viewModel.runWalkForward() }, modifier = Modifier.weight(1f)) {
                            Text(t("Walk", "واک"))
                        }
                    }
                    Text(t("Asset", "دارایی") + ": ${state.symbol} • ${state.timeframe}")
                    ParameterRow(
                        label = t("Window Size", "اندازه پنجره"),
                        value = state.windowSize.toString(),
                        onMinus = { viewModel.adjustWindowSize(-5) },
                        onPlus = { viewModel.adjustWindowSize(5) }
                    )
                    ParameterRow(
                        label = t("Lookahead", "تعداد کندل آینده"),
                        value = state.lookaheadCandles.toString(),
                        onMinus = { viewModel.adjustLookahead(-1) },
                        onPlus = { viewModel.adjustLookahead(1) }
                    )
                    ParameterRow(
                        label = t("Max Signals", "حداکثر سیگنال‌ها"),
                        value = state.maxSignals.toString(),
                        onMinus = { viewModel.adjustMaxSignals(-5) },
                        onPlus = { viewModel.adjustMaxSignals(5) }
                    )
                    ParameterRow(
                        label = t("Score Threshold", "آستانه امتیاز"),
                        value = String.format(Locale.US, "%.1f", state.scoreThreshold),
                        onMinus = { viewModel.adjustScoreThreshold(-2.5) },
                        onPlus = { viewModel.adjustScoreThreshold(2.5) }
                    )
                    ParameterRow(
                        label = t("Train Window", "پنجره آموزش"),
                        value = state.trainWindow.toString(),
                        onMinus = { viewModel.adjustTrainWindow(-10) },
                        onPlus = { viewModel.adjustTrainWindow(10) }
                    )
                    ParameterRow(
                        label = t("Test Window", "پنجره تست"),
                        value = state.testWindow.toString(),
                        onMinus = { viewModel.adjustTestWindow(-5) },
                        onPlus = { viewModel.adjustTestWindow(5) }
                    )
                    ParameterRow(
                        label = t("Step Size", "اندازه گام"),
                        value = state.stepSize.toString(),
                        onMinus = { viewModel.adjustStepSize(-5) },
                        onPlus = { viewModel.adjustStepSize(5) }
                    )
                    Button(onClick = { viewModel.cycleTakeProfit() }, modifier = Modifier.fillMaxWidth()) {
                        Text(t("Take Profit Target", "هدف حد سود") + " • TP${state.takeProfitIndex + 1}")
                    }
                    state.error?.let {
                        Text(t("Error", "خطا") + ": $it", color = MaterialTheme.colorScheme.error)
                    }
                }
            }
        }
        state.analytics?.let { analytics ->
            item {
                Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(22.dp)) {
                    Column(
                        modifier = Modifier.padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        Text(t("App Analytics Snapshot", "اسنپ‌شات آنالیتیکس برنامه"), style = MaterialTheme.typography.titleLarge)
                        MetricLine(t("Saved Signals", "سیگنال‌های ذخیره‌شده"), analytics.total_saved_signals.toString())
                        MetricLine(t("Recent 24h Signals", "سیگنال‌های ۲۴ ساعت اخیر"), analytics.recent_signals_24h.toString())
                        MetricLine(
                            t("Buy / Sell / Neutral", "خرید / فروش / خنثی"),
                            "${analytics.buy_signals} / ${analytics.sell_signals} / ${analytics.neutral_signals}"
                        )
                        MetricLine(t("Avg Signal Score", "میانگین امتیاز سیگنال"), analytics.average_signal_score.toString())
                        MetricLine(t("Journal Win Rate", "نرخ برد ژورنال"), "${analytics.trade_stats.win_rate}%")
                        MetricLine(t("Journal Net PnL", "سود/زیان خالص ژورنال"), analytics.trade_stats.net_pnl.toString())
                    }
                }
            }
        }
        state.summary?.let { summary ->
            item {
                Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(22.dp)) {
                    Column(
                        modifier = Modifier.padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        Text(t("Backtest Summary", "خلاصه بک‌تست"), style = MaterialTheme.typography.titleLarge)
                        MetricLine(t("Signals / Tested Candles", "سیگنال‌ها / کندل‌های تست‌شده"), "${summary.evaluated_signals} / ${summary.tested_candles}")
                        MetricLine(t("Wins / Losses / Unclosed", "برد / باخت / بازمانده"), "${summary.wins} / ${summary.losses} / ${summary.unclosed}")
                        MetricLine(t("Win Rate", "نرخ برد"), "${summary.win_rate}%")
                        MetricLine(t("Average Score", "میانگین امتیاز"), summary.average_score.toString())
                        MetricLine(t("Net RR", "RR خالص"), summary.net_rr.toString())
                        MetricLine(t("Avg Win RR", "میانگین RR برد"), summary.average_win_rr.toString())
                        MetricLine(t("Avg Loss RR", "میانگین RR باخت"), summary.average_loss_rr.toString())
                        MetricLine(t("Expectancy RR", "امیدریاضی RR"), summary.expectancy_rr.toString())
                        MetricLine(t("Profit Factor", "فاکتور سود"), summary.profit_factor.toString())
                        MetricLine(t("Win / Loss Streak", "استریک برد / باخت"), "${summary.longest_win_streak} / ${summary.longest_loss_streak}")
                    }
                }
            }
            items(summary.items.size) { index ->
                val item = summary.items[index]
                Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(18.dp)) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(
                            "${item.direction.uppercase(Locale.getDefault())} • ${item.score}",
                            style = MaterialTheme.typography.titleMedium
                        )
                        Text(t("Signal Time", "زمان سیگنال") + ": ${item.signal_time}")
                        Text(t("Entry / SL / TP", "ورود / حد ضرر / حد سود") + ": ${item.entry_price} / ${item.stop_loss} / ${item.take_profit}")
                        Text(t("Outcome", "نتیجه") + ": ${item.outcome}")
                        Text(t("Realized RR", "RR محقق‌شده") + ": ${item.rr_realized}")
                        Text(t("Bars Held", "تعداد کندل نگهداری") + ": ${item.bars_held}")
                    }
                }
            }
        }
        state.sweepSummary?.let { sweep ->
            item {
                Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(22.dp)) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text(t("Parameter Sweep", "سوییپ پارامترها"), style = MaterialTheme.typography.titleLarge)
                        MetricLine(t("Combinations Tested", "ترکیب‌های تست‌شده"), sweep.combinations_tested.toString())
                        sweep.best_by_net_rr?.let {
                            Text(t("Best Net RR", "بهترین RR خالص") + " → W:${it.window_size} • L:${it.lookahead_candles} • T:${it.score_threshold} • TP${it.take_profit_index + 1} • RR:${it.net_rr}")
                        }
                        sweep.best_by_win_rate?.let {
                            Text(t("Best Win Rate", "بهترین نرخ برد") + " → W:${it.window_size} • L:${it.lookahead_candles} • T:${it.score_threshold} • TP${it.take_profit_index + 1} • WR:${it.win_rate}%")
                        }
                    }
                }
            }
            items(sweep.items.size) { index ->
                val item = sweep.items[index]
                Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(18.dp)) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(
                            "W:${item.window_size} • L:${item.lookahead_candles} • T:${item.score_threshold} • TP${item.take_profit_index + 1}",
                            style = MaterialTheme.typography.titleMedium
                        )
                        Text(t("Signals", "سیگنال‌ها") + ": ${item.evaluated_signals}")
                        Text(t("Wins / Losses / Unclosed", "برد / باخت / بازمانده") + ": ${item.wins} / ${item.losses} / ${item.unclosed}")
                        Text(t("Win Rate", "نرخ برد") + ": ${item.win_rate}%")
                        Text(t("Net RR", "RR خالص") + ": ${item.net_rr}")
                        Text(t("Expectancy", "امیدریاضی") + ": ${item.expectancy_rr}")
                        Text(t("Profit Factor", "فاکتور سود") + ": ${item.profit_factor}")
                        Text(t("Streak W/L", "استریک برد/باخت") + ": ${item.longest_win_streak}/${item.longest_loss_streak}")
                    }
                }
            }
        }
        state.walkForwardSummary?.let { wf ->
            item {
                Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(22.dp)) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text(t("Walk-Forward Summary", "خلاصه واک‌فوروارد"), style = MaterialTheme.typography.titleLarge)
                        MetricLine(t("Steps / Test Signals", "گام‌ها / سیگنال‌های تست"), "${wf.steps_executed} / ${wf.total_test_signals}")
                        MetricLine(t("Wins / Losses / Unclosed", "برد / باخت / بازمانده"), "${wf.total_wins} / ${wf.total_losses} / ${wf.total_unclosed}")
                        MetricLine(t("Aggregate Win Rate", "نرخ برد تجمیعی"), "${wf.aggregate_win_rate}%")
                        MetricLine(t("Aggregate Net RR", "RR خالص تجمیعی"), wf.aggregate_net_rr.toString())
                        MetricLine(t("Average Step Expectancy", "میانگین امیدریاضی هر گام"), wf.average_step_expectancy_rr.toString())
                        MetricLine(t("Best / Worst Step", "بهترین / بدترین گام"), "${wf.best_step_index ?: "-"} / ${wf.worst_step_index ?: "-"}")
                    }
                }
            }
            items(wf.items.size) { index ->
                val item = wf.items[index]
                Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(18.dp)) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(t("Step", "گام") + " ${item.step_index}", style = MaterialTheme.typography.titleMedium)
                        Text(t("Train", "آموزش") + ": ${item.train_start_time} → ${item.train_end_time}")
                        Text(t("Test", "تست") + ": ${item.test_start_time} → ${item.test_end_time}")
                        Text(t("Selected Params", "پارامترهای انتخاب‌شده") + ": W${item.selected_window_size} / L${item.selected_lookahead_candles} / T${item.selected_score_threshold} / TP${item.selected_take_profit_index + 1}")
                        Text(t("Training RR / WR", "RR / WR آموزش") + ": ${item.training_net_rr} / ${item.training_win_rate}%")
                        Text(t("Test Signals W/L/U", "سیگنال‌های تست برد/باخت/بازمانده") + ": ${item.test_evaluated_signals} • ${item.test_wins}/${item.test_losses}/${item.test_unclosed}")
                        Text(t("Test WR / Net RR / Exp", "WR / RR خالص / امیدریاضی تست") + ": ${item.test_win_rate}% / ${item.test_net_rr} / ${item.test_expectancy_rr}")
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
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Text(label, modifier = Modifier.weight(1f))
        Button(onClick = onMinus) { Text("-") }
        Text(value, modifier = Modifier.padding(horizontal = 4.dp))
        Button(onClick = onPlus) { Text("+") }
    }
}

@Composable
private fun MetricLine(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(label)
        Text(value, color = MaterialTheme.colorScheme.primary)
    }
}
