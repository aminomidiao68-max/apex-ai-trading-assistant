package com.arena.smartmoney.ui.backtest

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.arena.smartmoney.ui.components.PremiumGlassCard
import com.arena.smartmoney.ui.components.PremiumScreenBackground
import com.arena.smartmoney.ui.components.PremiumSectionHeader
import com.arena.smartmoney.ui.i18n.rememberTranslator
import java.util.Locale

@Composable
fun BacktestScreen(viewModel: BacktestViewModel = viewModel()) {
    val state by viewModel.uiState.collectAsState()
    val t = rememberTranslator()

    PremiumScreenBackground {
        androidx.compose.foundation.lazy.LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                PremiumSectionHeader(
                    title = t("Backtest Lab", "آزمایشگاه بک‌تست"),
                    subtitle = t(
                        "Run historical simulations, parameter sweep and walk-forward validation on live-fetched candles.",
                        "شبیه‌سازی تاریخی، سوییپ پارامترها و اعتبارسنجی واک‌فوروارد را روی کندل‌های زنده اجرا کن."
                    )
                )
            }
            item {
                PremiumGlassCard {
                    Text(t("Scenario Setup", "تنظیم سناریو"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.selectAsset("BTCUSDT", "crypto") }, modifier = Modifier.weight(1f)) { Text("BTC") }
                        Button(onClick = { viewModel.selectAsset("ETHUSDT", "crypto") }, modifier = Modifier.weight(1f)) { Text("ETH") }
                    }
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedButton(onClick = { viewModel.selectAsset("EURUSD", "forex") }, modifier = Modifier.weight(1f)) { Text("EURUSD") }
                        OutlinedButton(onClick = { viewModel.selectAsset("XAUUSD", "forex") }, modifier = Modifier.weight(1f)) { Text("XAUUSD") }
                    }
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.selectTimeframe("15m") }, modifier = Modifier.weight(1f)) { Text("15m") }
                        OutlinedButton(onClick = { viewModel.selectTimeframe("1h") }, modifier = Modifier.weight(1f)) { Text("1h") }
                    }
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.runBacktest() }, modifier = Modifier.weight(1f)) {
                            Text(if (state.loading) t("Running...", "در حال اجرا...") else t("Run", "اجرا"))
                        }
                        OutlinedButton(onClick = { viewModel.runSweep() }, modifier = Modifier.weight(1f)) {
                            Text(t("Sweep", "سوییپ"))
                        }
                        OutlinedButton(onClick = { viewModel.runWalkForward() }, modifier = Modifier.weight(1f)) {
                            Text(t("Walk", "واک"))
                        }
                    }
                    Text(t("Asset", "دارایی") + ": ${state.symbol} • ${state.timeframe}", color = Color(0xFF67ECFF), fontWeight = FontWeight.Bold)
                    ParameterRow(t("Window Size", "اندازه پنجره"), state.windowSize.toString(), { viewModel.adjustWindowSize(-5) }, { viewModel.adjustWindowSize(5) })
                    ParameterRow(t("Lookahead", "تعداد کندل آینده"), state.lookaheadCandles.toString(), { viewModel.adjustLookahead(-1) }, { viewModel.adjustLookahead(1) })
                    ParameterRow(t("Max Signals", "حداکثر سیگنال‌ها"), state.maxSignals.toString(), { viewModel.adjustMaxSignals(-5) }, { viewModel.adjustMaxSignals(5) })
                    ParameterRow(t("Score Threshold", "آستانه امتیاز"), String.format(Locale.US, "%.1f", state.scoreThreshold), { viewModel.adjustScoreThreshold(-2.5) }, { viewModel.adjustScoreThreshold(2.5) })
                    ParameterRow(t("Train Window", "پنجره آموزش"), state.trainWindow.toString(), { viewModel.adjustTrainWindow(-10) }, { viewModel.adjustTrainWindow(10) })
                    ParameterRow(t("Test Window", "پنجره تست"), state.testWindow.toString(), { viewModel.adjustTestWindow(-5) }, { viewModel.adjustTestWindow(5) })
                    ParameterRow(t("Step Size", "اندازه گام"), state.stepSize.toString(), { viewModel.adjustStepSize(-5) }, { viewModel.adjustStepSize(5) })
                    Button(onClick = { viewModel.cycleTakeProfit() }, modifier = Modifier.fillMaxWidth()) {
                        Text(t("Take Profit Target", "هدف حد سود") + " • TP${state.takeProfitIndex + 1}")
                    }
                    state.error?.let { Text(t("Error", "خطا") + ": $it", color = MaterialTheme.colorScheme.error) }
                }
            }
            state.analytics?.let { analytics ->
                item {
                    PremiumGlassCard(borderColor = Color(0x4059C7FF)) {
                        Text(t("App Analytics Snapshot", "اسنپ‌شات آنالیتیکس برنامه"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
                        MetricLine(t("Saved Signals", "سیگنال‌های ذخیره‌شده"), analytics.total_saved_signals.toString())
                        MetricLine(t("Recent 24h Signals", "سیگنال‌های ۲۴ ساعت اخیر"), analytics.recent_signals_24h.toString())
                        MetricLine(t("Buy / Sell / Neutral", "خرید / فروش / خنثی"), "${analytics.buy_signals} / ${analytics.sell_signals} / ${analytics.neutral_signals}")
                        MetricLine(t("Avg Signal Score", "میانگین امتیاز سیگنال"), analytics.average_signal_score.toString())
                        MetricLine(t("Journal Win Rate", "نرخ برد ژورنال"), "${analytics.trade_stats.win_rate}%")
                        MetricLine(t("Journal Net PnL", "سود/زیان خالص ژورنال"), analytics.trade_stats.net_pnl.toString())
                    }
                }
            }
            state.summary?.let { summary ->
                item {
                    PremiumGlassCard(borderColor = Color(0x4033E6A6)) {
                        Text(t("Backtest Summary", "خلاصه بک‌تست"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
                        MetricLine(t("Signals / Tested Candles", "سیگنال‌ها / کندل‌های تست‌شده"), "${summary.evaluated_signals} / ${summary.tested_candles}")
                        MetricLine(t("Wins / Losses / Unclosed", "برد / باخت / بازمانده"), "${summary.wins} / ${summary.losses} / ${summary.unclosed}")
                        MetricLine(t("Win Rate", "نرخ برد"), "${summary.win_rate}%")
                        MetricLine(t("Average Score", "میانگین امتیاز"), summary.average_score.toString())
                        MetricLine(t("Net RR", "RR خالص"), summary.net_rr.toString())
                        MetricLine(t("Expectancy RR", "امیدریاضی RR"), summary.expectancy_rr.toString())
                        MetricLine(t("Profit Factor", "فاکتور سود"), summary.profit_factor.toString())
                    }
                }
                items(summary.items) { item ->
                    PremiumGlassCard {
                        Text("${item.direction.uppercase(Locale.getDefault())} • ${item.score}", style = MaterialTheme.typography.titleMedium, color = Color.White, fontWeight = FontWeight.Bold)
                        Text(t("Signal Time", "زمان سیگنال") + ": ${item.signal_time}", color = Color(0xFFDDF8FF))
                        Text(t("Entry / SL / TP", "ورود / حد ضرر / حد سود") + ": ${item.entry_price} / ${item.stop_loss} / ${item.take_profit}", color = Color.White)
                        Text(t("Outcome", "نتیجه") + ": ${item.outcome}", color = Color.White)
                        Text(t("Realized RR", "RR محقق‌شده") + ": ${item.rr_realized}", color = Color(0xFF67ECFF))
                        Text(t("Bars Held", "تعداد کندل نگهداری") + ": ${item.bars_held}", color = Color.White)
                    }
                }
            }
            state.sweepSummary?.let { sweep ->
                item {
                    PremiumGlassCard(borderColor = Color(0x40FFC857)) {
                        Text(t("Parameter Sweep", "سوییپ پارامترها"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
                        MetricLine(t("Combinations Tested", "ترکیب‌های تست‌شده"), sweep.combinations_tested.toString())
                        sweep.best_by_net_rr?.let {
                            Text(t("Best Net RR", "بهترین RR خالص") + " → W:${it.window_size} • L:${it.lookahead_candles} • T:${it.score_threshold} • TP${it.take_profit_index + 1} • RR:${it.net_rr}", color = Color(0xFFDDF8FF))
                        }
                        sweep.best_by_win_rate?.let {
                            Text(t("Best Win Rate", "بهترین نرخ برد") + " → W:${it.window_size} • L:${it.lookahead_candles} • T:${it.score_threshold} • TP${it.take_profit_index + 1} • WR:${it.win_rate}%", color = Color(0xFFDDF8FF))
                        }
                    }
                }
                items(sweep.items) { item ->
                    PremiumGlassCard {
                        Text("W:${item.window_size} • L:${item.lookahead_candles} • T:${item.score_threshold} • TP${item.take_profit_index + 1}", style = MaterialTheme.typography.titleMedium, color = Color.White, fontWeight = FontWeight.Bold)
                        Text(t("Signals", "سیگنال‌ها") + ": ${item.evaluated_signals}", color = Color.White)
                        Text(t("Wins / Losses / Unclosed", "برد / باخت / بازمانده") + ": ${item.wins} / ${item.losses} / ${item.unclosed}", color = Color.White)
                        Text(t("Win Rate", "نرخ برد") + ": ${item.win_rate}%", color = Color(0xFF67ECFF))
                        Text(t("Net RR", "RR خالص") + ": ${item.net_rr}", color = Color(0xFF67ECFF))
                        Text(t("Expectancy", "امیدریاضی") + ": ${item.expectancy_rr}", color = Color.White)
                    }
                }
            }
            state.walkForwardSummary?.let { wf ->
                item {
                    PremiumGlassCard(borderColor = Color(0x4059C7FF)) {
                        Text(t("Walk-Forward Summary", "خلاصه واک‌فوروارد"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
                        MetricLine(t("Steps / Test Signals", "گام‌ها / سیگنال‌های تست"), "${wf.steps_executed} / ${wf.total_test_signals}")
                        MetricLine(t("Wins / Losses / Unclosed", "برد / باخت / بازمانده"), "${wf.total_wins} / ${wf.total_losses} / ${wf.total_unclosed}")
                        MetricLine(t("Aggregate Win Rate", "نرخ برد تجمیعی"), "${wf.aggregate_win_rate}%")
                        MetricLine(t("Aggregate Net RR", "RR خالص تجمیعی"), wf.aggregate_net_rr.toString())
                        MetricLine(t("Average Step Expectancy", "میانگین امیدریاضی هر گام"), wf.average_step_expectancy_rr.toString())
                    }
                }
                items(wf.items) { item ->
                    PremiumGlassCard {
                        Text(t("Step", "گام") + " ${item.step_index}", style = MaterialTheme.typography.titleMedium, color = Color.White, fontWeight = FontWeight.Bold)
                        Text(t("Train", "آموزش") + ": ${item.train_start_time} → ${item.train_end_time}", color = Color.White)
                        Text(t("Test", "تست") + ": ${item.test_start_time} → ${item.test_end_time}", color = Color.White)
                        Text(t("Selected Params", "پارامترهای انتخاب‌شده") + ": W${item.selected_window_size} / L${item.selected_lookahead_candles} / T${item.selected_score_threshold} / TP${item.selected_take_profit_index + 1}", color = Color(0xFFDDF8FF))
                        Text(t("Training RR / WR", "RR / WR آموزش") + ": ${item.training_net_rr} / ${item.training_win_rate}%", color = Color(0xFF67ECFF))
                        Text(t("Test WR / Net RR / Exp", "WR / RR خالص / امیدریاضی تست") + ": ${item.test_win_rate}% / ${item.test_net_rr} / ${item.test_expectancy_rr}", color = Color.White)
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
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(label, modifier = Modifier.weight(1f), color = Color(0xFFDDF8FF))
        OutlinedButton(onClick = onMinus) { Text("-") }
        Text(value, modifier = Modifier.padding(horizontal = 4.dp), color = Color.White, fontWeight = FontWeight.Bold)
        OutlinedButton(onClick = onPlus) { Text("+") }
    }
}

@Composable
private fun MetricLine(label: String, value: String) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, color = Color(0xFFDDF8FF))
        Text(value, color = Color(0xFF67ECFF), fontWeight = FontWeight.Bold)
    }
}
