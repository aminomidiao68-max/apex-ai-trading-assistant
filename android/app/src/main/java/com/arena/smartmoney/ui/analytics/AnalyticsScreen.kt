package com.arena.smartmoney.ui.analytics

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
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
import com.arena.smartmoney.ui.components.PremiumGlassCard
import com.arena.smartmoney.ui.components.PremiumScreenBackground
import com.arena.smartmoney.ui.components.PremiumSectionHeader
import com.arena.smartmoney.ui.i18n.rememberTranslator

@Composable
fun AnalyticsScreen(viewModel: AnalyticsViewModel = viewModel()) {
    val state by viewModel.uiState.collectAsState()
    val report = state.report
    val summary = report?.summary
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
                    title = t("Analytics Center", "مرکز آنالیتیکس"),
                    subtitle = t(
                        "Institutional dashboard for signal quality, journal efficiency and symbol leadership.",
                        "داشبورد حرفه‌ای برای کیفیت سیگنال، کارایی ژورنال و رهبری نمادها."
                    )
                )
            }
            item {
                PremiumGlassCard {
                    Text(t("Institutional Snapshot", "نمای نهادی"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
                    Button(onClick = { viewModel.load() }, modifier = Modifier.fillMaxWidth()) {
                        Text(if (state.loading) t("Refreshing...", "در حال بروزرسانی...") else t("Refresh Analytics", "بروزرسانی آنالیتیکس"))
                    }
                    state.error?.let {
                        Text(t("Error", "خطا") + ": $it", color = MaterialTheme.colorScheme.error)
                    }
                    if (summary != null && report != null) {
                        val health = analyticsHealth(summary.average_signal_score, summary.trade_stats.win_rate)
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            AnalyticsChip(t("Health", "سلامت"), health, Modifier.weight(1f))
                            AnalyticsChip(t("Signals 24h", "سیگنال ۲۴ساعت"), summary.recent_signals_24h.toString(), Modifier.weight(1f))
                            AnalyticsChip(t("Notifications 7d", "نوتیفیکیشن ۷روزه"), report.recent_notification_events_7d.toString(), Modifier.weight(1f))
                        }
                        MetricLine(t("Saved Signals", "سیگنال‌های ذخیره‌شده"), summary.total_saved_signals.toString())
                        MetricLine(t("Average Signal Score", "میانگین امتیاز سیگنال"), summary.average_signal_score.toString())
                        MetricLine(t("Buy / Sell / Neutral", "خرید / فروش / خنثی"), "${summary.buy_signals} / ${summary.sell_signals} / ${summary.neutral_signals}")
                    }
                }
            }

            summary?.let { data ->
                item {
                    PremiumGlassCard(borderColor = Color(0x4033E6A6)) {
                        Text(t("Journal Performance", "عملکرد ژورنال"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            AnalyticsChip(t("Win Rate", "نرخ برد"), "${data.trade_stats.win_rate}%", Modifier.weight(1f))
                            AnalyticsChip(t("Net PnL", "سود خالص"), data.trade_stats.net_pnl.toString(), Modifier.weight(1f))
                            AnalyticsChip(t("Closed Trades", "معاملات بسته"), data.trade_stats.closed_trades.toString(), Modifier.weight(1f))
                        }
                        MetricLine(t("Total Trades", "کل معاملات"), data.trade_stats.total_trades.toString())
                        MetricLine(t("Open / Closed", "باز / بسته"), "${data.trade_stats.open_trades} / ${data.trade_stats.closed_trades}")
                        MetricLine(t("Wins / Losses", "برد / باخت"), "${data.trade_stats.wins} / ${data.trade_stats.losses}")
                    }
                }
                item { SectionLabel(t("Top Signal Symbols", "برترین نمادهای سیگنال")) }
                items(data.top_signal_symbols) { item ->
                    PremiumGlassCard {
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text(item.symbol, style = MaterialTheme.typography.titleMedium, color = Color.White, fontWeight = FontWeight.Bold)
                            Text(t("Count", "تعداد") + ": ${item.count}", color = Color(0xFF67ECFF))
                        }
                    }
                }
                item { SectionLabel(t("Signal Stats by Symbol", "آمار سیگنال بر اساس نماد")) }
                items(report.signal_stats_by_symbol) { item ->
                    PremiumGlassCard {
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            AnalyticsChip(item.symbol, item.count.toString(), Modifier.weight(1f))
                            AnalyticsChip(t("Avg Score", "میانگین امتیاز"), item.average_score.toString(), Modifier.weight(1f))
                        }
                    }
                }
                item { SectionLabel(t("Trade Performance by Symbol", "عملکرد معاملات بر اساس نماد")) }
                items(report.trade_performance_by_symbol) { item ->
                    PremiumGlassCard(borderColor = Color(0x4059C7FF)) {
                        Text(item.symbol, style = MaterialTheme.typography.titleMedium, color = Color.White, fontWeight = FontWeight.Bold)
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            AnalyticsChip(t("Trades", "معاملات"), item.trade_count.toString(), Modifier.weight(1f))
                            AnalyticsChip(t("WR", "نرخ برد"), "${item.win_rate}%", Modifier.weight(1f))
                            AnalyticsChip(t("Net", "خالص"), item.net_pnl.toString(), Modifier.weight(1f))
                        }
                        MetricLine(t("Wins / Losses", "برد / باخت"), "${item.wins} / ${item.losses}")
                    }
                }
            }
        }
    }
}

@Composable
private fun AnalyticsChip(title: String, value: String, modifier: Modifier = Modifier) {
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
private fun SectionLabel(text: String) {
    Text(
        text = text,
        style = MaterialTheme.typography.titleLarge,
        color = Color.White,
        fontWeight = FontWeight.Bold
    )
}

@Composable
private fun MetricLine(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(label, color = Color(0xFFDDF8FF))
        Text(value, color = Color(0xFF67ECFF), fontWeight = FontWeight.Bold)
    }
}

private fun analyticsHealth(avgScore: Double, winRate: Double): String {
    return when {
        avgScore >= 78.0 && winRate >= 58.0 -> "Elite"
        avgScore >= 68.0 && winRate >= 50.0 -> "Strong"
        avgScore >= 58.0 -> "Developing"
        else -> "Weak"
    }
}
