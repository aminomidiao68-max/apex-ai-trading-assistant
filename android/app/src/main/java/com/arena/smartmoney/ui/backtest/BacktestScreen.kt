package com.arena.smartmoney.ui.backtest

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.arena.smartmoney.data.model.BacktestSummaryDto
import com.arena.smartmoney.data.model.PrimeBacktestStatsDto
import com.arena.smartmoney.data.model.BacktestSweepSummaryDto
import com.arena.smartmoney.data.model.WalkForwardSummaryDto
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
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                PremiumSectionHeader(
                    title = t("Backtest Pro Lab", "لابراتوار حرفه‌ای بک‌تست"),
                    subtitle = t(
                        "Run historical simulations, parameter sweep and walk-forward validation with institutional reporting.",
                        "بک‌تست تاریخی، سوییپ پارامترها و واک‌فوروارد را با گزارش حرفه‌ای و نهادی اجرا کن."
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
                        BacktestTimeframeButton("1m", state.timeframe == "1m", modifier = Modifier.weight(1f)) { viewModel.selectTimeframe("1m") }
                        BacktestTimeframeButton("15m", state.timeframe == "15m", modifier = Modifier.weight(1f)) { viewModel.selectTimeframe("15m") }
                        BacktestTimeframeButton("1h", state.timeframe == "1h", modifier = Modifier.weight(1f)) { viewModel.selectTimeframe("1h") }
                    }
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.runBacktest() }, modifier = Modifier.weight(1f)) {
                            Text(if (state.loading) t("Running...", "در حال اجرا...") else t("Run", "اجرا"))
                        }
                        OutlinedButton(onClick = { viewModel.runSweep() }, modifier = Modifier.weight(1f)) { Text(t("Sweep", "سوییپ")) }
                        OutlinedButton(onClick = { viewModel.runWalkForward() }, modifier = Modifier.weight(1f)) { Text(t("Walk", "واک")) }
                    }
                    Text(t("Asset", "دارایی") + ": ${state.symbol} • ${state.timeframe} • TP${state.takeProfitIndex + 1}", color = Color(0xFF67ECFF), fontWeight = FontWeight.Bold)
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
            item {
                BulkPrimeCard(viewModel)
            }
            item {
                StrategyCoachCard(
                    summary = state.summary,
                    sweep = state.sweepSummary,
                    walkForward = state.walkForwardSummary,
                    t = t,
                )
            }
            item {
                PremiumGlassCard(borderColor = Color(0x40D4AF37)) {
                    Text(
                        t("PRIME Backtest (Live Detector Replay)", "بک‌تست PRIME (بازپخش آشکارساز زنده)"),
                        style = MaterialTheme.typography.titleLarge,
                        color = Color.White,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        t(
                            "Replays the exact live setup detector over real exchange history with conservative fills. No login needed.",
                            "آشکارساز زنده ستاپ‌ها را روی تاریخچه واقعی صرافی با قوانین پرکردن محافظه‌کارانه بازپخش می‌کند. بدون نیاز به ورود."
                        ),
                        color = Color(0xFFDDF8FF)
                    )
                    Button(onClick = { viewModel.runPrimeBacktest() }, modifier = Modifier.fillMaxWidth()) {
                        Text(
                            if (state.primeLoading) t("Running on real history...", "در حال اجرا روی تاریخچه واقعی...")
                            else t("Run PRIME Backtest", "اجرای بک‌تست PRIME") + " • ${state.symbol} • ${state.timeframe}"
                        )
                    }
                    state.primeError?.let { Text(t("Error", "خطا") + ": $it", color = MaterialTheme.colorScheme.error) }
                    state.primeResult?.let { res ->
                        if (!res.ok) {
                            Text(res.detail ?: t("Not enough historical data", "داده تاریخی کافی نیست"), color = Color(0xFFFFD27A))
                        } else {
                            MetricLine(
                                t("Candles / Source", "کندل‌ها / منبع"),
                                "${res.candles} • ${res.dataSource}" + (res.htf?.let { " • HTF $it" } ?: "")
                            )
                            MetricLine(
                                t("Setups Detected / Not Triggered", "ستاپ‌های شناسایی / فعال‌نشده"),
                                "${res.setupsDetected} / ${res.setupsNotTriggered}"
                            )
                            PrimeStatsBlock(t("All Graded Setups (A+/A/B)", "همه ستاپ‌های گریددار (A+/A/B)"), res.all, t)
                            PrimeStatsBlock(t("PRIME Proxy (Full Omega Gate)", "پروکسی PRIME (گیت کامل امگا)"), res.primeProxy, t)
                            if (res.trades.isNotEmpty()) {
                                Text(t("Recent Trades", "معاملات اخیر"), color = Color.White, fontWeight = FontWeight.Bold)
                                res.trades.takeLast(6).reversed().forEach { tr ->
                                    Text(
                                        "${tr.direction.uppercase(Locale.getDefault())} • ${tr.setupType} • ${tr.grade}" +
                                            (if (tr.prime) " ★PRIME" else "") +
                                            " → R=${tr.r} (${tr.exitReason})",
                                        color = if (tr.r > 0) Color(0xFF67ECFF) else Color(0xFFFFD27A)
                                    )
                                }
                            }
                            Text(res.disclaimerFa, color = Color(0xFF9AA7BD), style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }
            item {
                PremiumGlassCard(borderColor = Color(0x40B08CFF)) {
                    Text(
                        t("Classic Strategy Backtest (34 Strategies)", "بک‌تست استراتژی‌های کلاسیک (۳۴ استراتژی)"),
                        style = MaterialTheme.typography.titleLarge,
                        color = Color.White,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        t(
                            "Replays all 22 classic strategies from the scanner over real history and grades them by quality bucket. Answers: does higher quality actually win more?",
                            "هر ۳۴ استراتژی کلاسیک/ICT اسکنر را روی تاریخچه واقعی بازپخش و بر اساس سبد کیفی ارزیابی می‌کند. پاسخ می‌دهد: آیا کیفیت بالاتر واقعاً برد بیشتری دارد؟"
                        ),
                        color = Color(0xFFE7DEFF)
                    )
                    Button(onClick = { viewModel.runStrategyBacktest() }, modifier = Modifier.fillMaxWidth()) {
                        Text(
                            if (state.stratLoading) t("Running on real history...", "در حال اجرا روی تاریخچه واقعی...")
                            else t("Run Strategy Backtest", "اجرای بک‌تست استراتژی‌ها") + " • ${state.symbol} • ${state.timeframe}"
                        )
                    }
                    state.stratError?.let {
                        Text(t("Error", "خطا") + ": $it", color = MaterialTheme.colorScheme.error)
                    }
                    state.stratResult?.let { res ->
                        if (!res.ok) {
                            Text(
                                res.detail ?: t("Not enough historical data", "داده تاریخی کافی نیست"),
                                color = Color(0xFFFFD27A)
                            )
                        } else {
                            MetricLine(t("Candles / Source", "کندل‌ها / منبع"), "${res.candles} • ${res.dataSource}")
                            MetricLine(
                                t("Signals Detected / Trades", "سیگنال‌های شناسایی / معاملات"),
                                "${res.signalsDetected} / ${res.all.trades}"
                            )
                            PrimeStatsBlock(t("All Traded Signals", "همه سیگنال‌های معامله‌شده"), res.all, t)
                            Text(
                                t("By Quality Bucket", "بر اساس سبد کیفی"),
                                color = Color.White,
                                fontWeight = FontWeight.Bold
                            )
                            listOf("q75+", "q65-74", "q55-64", "q<55").forEach { key ->
                                res.byQualityBucket[key]?.let { b ->
                                    MetricLine(
                                        key,
                                        "${b.trades} • WR=${b.winRatePct ?: "—"}٪ • avgR=${b.avgR ?: "—"} • PF=${b.profitFactor ?: "—"}"
                                    )
                                }
                            }
                            if (res.byStrategy.isNotEmpty()) {
                                Text(
                                    t("By Strategy (≥1 trade)", "به تفکیک استراتژی (≥۱ معامله)"),
                                    color = Color.White,
                                    fontWeight = FontWeight.Bold
                                )
                                res.byStrategy.values.sortedByDescending { it.trades }.take(10).forEach { s ->
                                    Text(
                                        "${s.nameFa} [${s.family}] → ${s.trades} • WR=${s.winRatePct ?: "—"}٪ • avgR=${s.avgR ?: "—"}",
                                        color = if ((s.avgR ?: 0.0) > 0) Color(0xFF9BFFC8) else Color(0xFFFFD27A)
                                    )
                                }
                            }
                            if (res.gates != null && res.gates.subsets.isNotEmpty()) {
                                Text(
                                    t("Measured Gates (walk-forward safe)", "گیت‌های اندازه‌گیری‌شده (بدون look-ahead)"),
                                    color = Color.White,
                                    fontWeight = FontWeight.Bold
                                )
                                listOf("trend+votes", "combo", "votes", "trend", "perf").forEach { key ->
                                    res.gates.subsets[key]?.let { g ->
                                        MetricLine(
                                            key,
                                            "${g.trades} • WR=${g.winRatePct ?: "—"}٪ • avgR=${g.avgR ?: "—"} • PF=${g.profitFactor ?: "—"}"
                                        )
                                    }
                                }
                            }
                            Text(res.verdictFa, color = Color(0xFFB08CFF))
                            Text(res.disclaimerFa, color = Color(0xFF9AA7BD), style = MaterialTheme.typography.bodySmall)
                        }
                    }
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
                item { BacktestSummaryCard(summary = summary, t = t) }
                items(summary.items) { item ->
                    PremiumGlassCard {
                        Text("${item.direction.uppercase(Locale.getDefault())} • ${item.score}", style = MaterialTheme.typography.titleMedium, color = Color.White, fontWeight = FontWeight.Bold)
                        Text(t("Signal Time", "زمان سیگنال") + ": ${item.signal_time}", color = Color(0xFFDDF8FF))
                        Text(t("Entry / SL / TP", "ورود / حد ضرر / حد سود") + ": ${item.entry_price} / ${item.stop_loss} / ${item.take_profit}", color = Color.White)
                        Text(t("Outcome", "نتیجه") + ": ${localizeOutcome(item.outcome, t)}", color = Color.White)
                        Text(t("Entry Activated", "ورود فعال شد") + ": ${if (item.activated) t("Yes", "بله") else t("No", "خیر")}", color = Color.White)
                        Text(t("Gross / Costs / Net RR", "RR ناخالص / هزینه / خالص") + ": ${item.gross_rr} / ${item.costs_rr} / ${item.rr_realized}", color = Color(0xFF67ECFF))
                        Text(t("Entry Wait / Bars Held", "انتظار ورود / کندل نگهداری") + ": ${item.bars_to_entry} / ${item.bars_held}", color = Color.White)
                        if (item.exit_reason.isNotBlank()) {
                            Text(t("Exit Reason", "علت خروج") + ": ${item.exit_reason}", color = Color(0xFFFFD27A))
                        }
                    }
                }
            }
            state.sweepSummary?.let { sweep ->
                item { SweepInsightCard(sweep = sweep, t = t) }
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
                item { WalkForwardInsightCard(wf = wf, t = t) }
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
private fun StrategyCoachCard(
    summary: BacktestSummaryDto?,
    sweep: BacktestSweepSummaryDto?,
    walkForward: WalkForwardSummaryDto?,
    t: (String, String) -> String,
) {
    val headline = when {
        walkForward != null && walkForward.aggregate_net_rr > 0 && walkForward.aggregate_win_rate >= 55 -> t("Walk-forward passed this sample, but remains a research candidate—not live approval.", "واک‌فوروارد در این نمونه پذیرفته شد، اما فقط کاندید تحقیق است و مجوز اجرای زنده نیست.")
        sweep?.best_by_net_rr != null && sweep.best_by_net_rr.net_rr > 0 -> t("Parameter sweep found a positive sample. Validate it out-of-sample before drawing conclusions.", "سوییپ پارامترها یک نمونه مثبت یافته است؛ پیش از نتیجه‌گیری باید خارج از نمونه اعتبارسنجی شود.")
        summary != null && summary.net_rr > 0 -> t("Backtest is net-positive after modeled costs, but it does not guarantee future performance.", "بک‌تست پس از هزینه‌های مدل‌شده خالصاً مثبت است، اما عملکرد آینده را تضمین نمی‌کند.")
        else -> t("Current setup is still exploratory. Tighten thresholds or move to a stronger session.", "ستاپ فعلی هنوز اکتشافی است. آستانه‌ها را سخت‌تر کن یا به سشن قوی‌تر برو.")
    }

    PremiumGlassCard(borderColor = Color(0x40FFC857)) {
        Text(t("Strategy Coach", "مربی استراتژی"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
        Text(headline, color = Color(0xFFFFE6A3))
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            InsightChip(
                title = t("Backtest", "بک‌تست"),
                value = summary?.let { if (it.net_rr > 0) t("Positive", "مثبت") else t("Weak", "ضعیف") } ?: t("Idle", "بدون داده"),
                modifier = Modifier.weight(1f)
            )
            InsightChip(
                title = t("Sweep", "سوییپ"),
                value = sweep?.best_by_net_rr?.let { "RR ${it.net_rr}" } ?: t("Idle", "بدون داده"),
                modifier = Modifier.weight(1f)
            )
            InsightChip(
                title = t("Walk", "واک"),
                value = walkForward?.let { "WR ${it.aggregate_win_rate}%" } ?: t("Idle", "بدون داده"),
                modifier = Modifier.weight(1f)
            )
        }
    }
}

@Composable
private fun BacktestSummaryCard(summary: BacktestSummaryDto, t: (String, String) -> String) {
    PremiumGlassCard(borderColor = Color(0x4033E6A6)) {
        Text(t("Backtest Summary", "خلاصه بک‌تست"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            InsightChip(t("Win Rate", "نرخ برد"), "${summary.win_rate}%", Modifier.weight(1f))
            InsightChip(t("Net RR", "RR خالص"), summary.net_rr.toString(), Modifier.weight(1f))
            InsightChip(t("Profit Factor", "فاکتور سود"), summary.profit_factor.toString(), Modifier.weight(1f))
        }
        MetricLine(t("Evaluated / Activated / No Entry", "بررسی‌شده / فعال / بدون ورود"), "${summary.evaluated_signals} / ${summary.activated_signals} / ${summary.no_entry}")
        MetricLine(t("Wins / Losses / Unclosed", "برد / باخت / بازمانده"), "${summary.wins} / ${summary.losses} / ${summary.unclosed}")
        MetricLine(t("Gross / Cost / Net RR", "RR ناخالص / هزینه / خالص"), "${summary.gross_rr} / ${summary.total_costs_rr} / ${summary.net_rr}")
        MetricLine(t("Fees / Funding RR", "RR کارمزد / فاندینگ"), "${summary.total_fee_rr} / ${summary.total_funding_rr}")
        MetricLine(t("Maximum Drawdown RR", "حداکثر دراودان RR"), summary.max_drawdown_rr.toString())
        MetricLine(t("Average Score", "میانگین امتیاز"), summary.average_score.toString())
        MetricLine(t("Average Win / Loss RR", "میانگین RR برد / باخت"), "${summary.average_win_rr} / ${summary.average_loss_rr}")
        MetricLine(t("Expectancy RR", "امیدریاضی RR"), summary.expectancy_rr.toString())
        MetricLine(t("Win / Loss Streak", "رشته برد / باخت"), "${summary.longest_win_streak} / ${summary.longest_loss_streak}")
        MetricLine(t("Execution Model", "مدل اجرا"), summary.execution_model)
        MetricLine(t("Anti Look-Ahead", "ضد نگاه‌به‌آینده"), if (summary.anti_lookahead_enforced) t("Enforced", "فعال") else t("Off", "خاموش"))
    }
}

@Composable
private fun SweepInsightCard(sweep: BacktestSweepSummaryDto, t: (String, String) -> String) {
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

@Composable
private fun WalkForwardInsightCard(wf: WalkForwardSummaryDto, t: (String, String) -> String) {
    PremiumGlassCard(borderColor = Color(0x4059C7FF)) {
        Text(t("Walk-Forward Summary", "خلاصه واک‌فوروارد"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            InsightChip(t("Steps", "گام‌ها"), wf.steps_executed.toString(), Modifier.weight(1f))
            InsightChip(t("WR", "نرخ برد"), "${wf.aggregate_win_rate}%", Modifier.weight(1f))
            InsightChip(t("Net RR", "RR خالص"), wf.aggregate_net_rr.toString(), Modifier.weight(1f))
        }
        MetricLine(t("Total Test Signals", "کل سیگنال‌های تست"), wf.total_test_signals.toString())
        MetricLine(t("Wins / Losses / Unclosed", "برد / باخت / بازمانده"), "${wf.total_wins} / ${wf.total_losses} / ${wf.total_unclosed}")
        MetricLine(t("Average Step Expectancy", "میانگین امیدریاضی هر گام"), wf.average_step_expectancy_rr.toString())
        MetricLine(t("Best / Worst Step", "بهترین / بدترین گام"), "${wf.best_step_index ?: "-"} / ${wf.worst_step_index ?: "-"}")
    }
}

@Composable
private fun BacktestTimeframeButton(
    label: String,
    selected: Boolean,
    modifier: Modifier = Modifier,
    onClick: () -> Unit,
) {
    if (selected) {
        Button(onClick = onClick, modifier = modifier) { Text(label) }
    } else {
        OutlinedButton(onClick = onClick, modifier = modifier) { Text(label) }
    }
}

@Composable
private fun InsightChip(title: String, value: String, modifier: Modifier = Modifier) {
    Box(
        modifier = modifier
            .background(
                Brush.linearGradient(listOf(Color(0x2611D9FF), Color(0x2217FFB3))),
                RoundedCornerShape(16.dp)
            )
            .padding(horizontal = 12.dp, vertical = 10.dp)
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(title, color = Color(0xFFBCEEFF), style = MaterialTheme.typography.bodySmall)
            Text(value, color = Color.White, fontWeight = FontWeight.Bold)
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

private fun localizeOutcome(value: String, t: (String, String) -> String): String {
    return when (value.lowercase(Locale.getDefault())) {
        "win" -> t("Win", "برد")
        "loss" -> t("Loss", "باخت")
        "unclosed" -> t("Unclosed", "بازمانده")
        "no_entry" -> t("No Entry", "ورود فعال نشد")
        else -> value
    }
}

@Composable
private fun PrimeStatsBlock(title: String, stats: PrimeBacktestStatsDto, t: (String, String) -> String) {
    Text(title, color = Color(0xFF67ECFF), fontWeight = FontWeight.Bold)
    if (stats.trades == 0) {
        Text(t("No trades in this window", "در این بازه معامله‌ای ثبت نشد"), color = Color(0xFFDDF8FF))
        return
    }
    MetricLine(t("Trades / Wins / Losses", "معاملات / برد / باخت"), "${stats.trades} / ${stats.wins} / ${stats.losses}")
    MetricLine(t("Win Rate", "نرخ برد"), stats.winRatePct?.let { "$it%" } ?: "—")
    MetricLine(t("Avg R / Total R", "میانگین R / کل R"), "${stats.avgR ?: "—"} / ${stats.totalR ?: "—"}")
    MetricLine(t("Profit Factor / Expectancy", "ضریب سود / امیدریاضی"), "${stats.profitFactor ?: "—"} / ${stats.expectancyR ?: "—"}")
    MetricLine(t("Max Consecutive Losses", "حداکثر باخت پیاپی"), stats.maxConsecutiveLosses.toString())
    MetricLine(t("Best / Worst R", "بهترین / بدترین R"), "${stats.bestR ?: "—"} / ${stats.worstR ?: "—"}")
}

@Composable
private fun BulkPrimeCard(viewModel: BacktestViewModel) {
    val state by viewModel.uiState.collectAsState()
    val t = rememberTranslator()
    PremiumGlassCard(borderColor = Color(0xFF33E6A6).copy(alpha = 0.35f)) {
        Text("⚡ بک‌تست سریع ۲۰ نماد — Prime 1h (1000 کندل)", style = MaterialTheme.typography.titleMedium, color = Color.White, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(4.dp))
        Text("یک‌کلیک، ۲۰ درخواست موازی به بک‌اند قطعی — بدون تغییر هیچ پارامتری. فقط Prime (ساده‌ترین سناریو).", color = Color(0xFFDDF8FF).copy(alpha = 0.75f), style = MaterialTheme.typography.bodySmall)
        Spacer(Modifier.height(10.dp))
        Button(onClick = { viewModel.runBulkPrime20() }, modifier = Modifier.fillMaxWidth(), enabled = !state.bulkPrimeLoading) {
            Text(if (state.bulkPrimeLoading) "در حال اجرای ۲۰ بک‌تست…" else "اجرای بک‌تست ۲۰ نماد")
        }
        state.bulkPrimeError?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }
        if (state.bulkPrimeResults.isNotEmpty()) {
            Spacer(Modifier.height(10.dp))
            // summary
            val withTrades = state.bulkPrimeResults.filter { (it.result?.all?.trades ?: 0) > 0 }
            Text("نتیجه: ${withTrades.size} از ۲۰ نماد معامله داشتند • ${state.bulkPrimeResults.size} اسکن شد", color = Color(0xFF67ECFF), style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(8.dp))
            for (item in state.bulkPrimeResults) {
                val r = item.result
                val stats = r?.all
                Row(modifier = Modifier.fillMaxWidth().padding(vertical = 3.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(item.symbol, color = Color.White, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f))
                    if (stats != null) {
                        val wr = stats.winRatePct ?: 0.0
                        val pf = stats.profitFactor ?: 0.0
                        Text("${stats.trades} ت • برد ${"%.0f".format(wr)}٪ • PF ${"%.2f".format(pf)}", color = if (wr >= 50.0) Color(0xFF33E6A6) else Color(0xFFFFC857), style = MaterialTheme.typography.bodySmall)
                    } else {
                        Text(item.error ?: "—", color = Color(0xFFFF7A7A), style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
            Spacer(Modifier.height(10.dp))
            Text("🗺 هیت‌مپ برد — سبز ≥55٪، زرد 45–55٪، قرمز <45٪، خاکستری بدون معامله", color = Color.White.copy(alpha = 0.55f), style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(6.dp))
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                for (row in state.bulkPrimeResults.chunked(4)) {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        for (item in row) {
                            val w = item.result?.all?.winRatePct
                            val trades = item.result?.all?.trades ?: 0
                            val bg = when {
                                trades == 0 -> Color(0xFF1A2535)
                                w == null -> Color(0xFF1A2535)
                                w >= 55.0 -> Color(0xFF33E6A6).copy(alpha = 0.22f)
                                w >= 45.0 -> Color(0xFFFFC857).copy(alpha = 0.20f)
                                else -> Color(0xFFFF7A7A).copy(alpha = 0.18f)
                            }
                            val borderColor = when {
                                trades == 0 -> Color.White.copy(alpha = 0.06f)
                                w == null -> Color.White.copy(alpha = 0.06f)
                                w >= 55.0 -> Color(0xFF33E6A6).copy(alpha = 0.5f)
                                w >= 45.0 -> Color(0xFFFFC857).copy(alpha = 0.5f)
                                else -> Color(0xFFFF7A7A).copy(alpha = 0.5f)
                            }
                            val wrText = if (trades == 0) "—" else "${"%.0f".format(w ?: 0.0)}٪"
                            Column(
                                modifier = Modifier.weight(1f)
                                    .background(bg, RoundedCornerShape(10.dp))
                                    .border(1.dp, borderColor, RoundedCornerShape(10.dp))
                                    .padding(horizontal = 6.dp, vertical = 7.dp),
                                horizontalAlignment = androidx.compose.ui.Alignment.CenterHorizontally
                            ) {
                                Text(item.symbol, color = Color.White, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold, maxLines = 1)
                                Spacer(Modifier.height(3.dp))
                                Text(wrText, color = if (trades==0) Color.White.copy(alpha=0.45f) else borderColor, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold)
                                Text(if (trades==0) "بدون معامله" else "${trades} ت", color = Color.White.copy(alpha=0.55f), style = MaterialTheme.typography.labelSmall)
                            }
                        }
                        repeat(4 - row.size) { Spacer(Modifier.weight(1f)) }
                    }
                }
            }
            Spacer(Modifier.height(6.dp))
            Text("Prime = ساده‌ترین بک‌تست؛ برای سوییپ/واک‌فوروارد از بالا استفاده کنید.", color = Color.White.copy(alpha = 0.45f), style = MaterialTheme.typography.bodySmall)
        }
    }
}
