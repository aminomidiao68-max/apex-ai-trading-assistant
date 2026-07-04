package com.arena.smartmoney.ui.analytics

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
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

@Composable
fun AnalyticsScreen(viewModel: AnalyticsViewModel = viewModel()) {
    val state by viewModel.uiState.collectAsState()
    val report = state.report
    val summary = report?.summary
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
                    title = t("Analytics Center", "مرکز آنالیتیکس"),
                    subtitle = t(
                        "Luxury signal intelligence, activity overview and journal performance.",
                        "هوش سیگنال، نمای کلی فعالیت و عملکرد ژورنال در قالب پرمیوم."
                    )
                )
            }
            item {
                PremiumGlassCard {
                    Text(t("AI Overview", "نمای کلی هوش مصنوعی"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
                    Button(onClick = { viewModel.load() }, modifier = Modifier.fillMaxWidth()) {
                        Text(if (state.loading) t("Refreshing...", "در حال بروزرسانی...") else t("Refresh Analytics", "بروزرسانی آنالیتیکس"))
                    }
                    state.error?.let {
                        Text(t("Error", "خطا") + ": $it", color = MaterialTheme.colorScheme.error)
                    }
                    if (summary != null) {
                        MetricLine(t("Saved Signals", "سیگنال‌های ذخیره‌شده"), summary.total_saved_signals.toString())
                        MetricLine(t("Last 24h Signals", "سیگنال‌های ۲۴ ساعت اخیر"), summary.recent_signals_24h.toString())
                        MetricLine(t("Average Signal Score", "میانگین امتیاز سیگنال"), summary.average_signal_score.toString())
                        MetricLine(
                            t("Buy / Sell / Neutral", "خرید / فروش / خنثی"),
                            "${summary.buy_signals} / ${summary.sell_signals} / ${summary.neutral_signals}"
                        )
                        MetricLine(
                            t("Notification Events 7d", "رویدادهای نوتیفیکیشن ۷ روز اخیر"),
                            report.recent_notification_events_7d.toString()
                        )
                    }
                }
            }

            summary?.let { data ->
                item {
                    PremiumGlassCard(borderColor = Color(0x4033E6A6)) {
                        Text(t("Journal Performance", "عملکرد ژورنال"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
                        MetricLine(t("Total Trades", "کل معاملات"), data.trade_stats.total_trades.toString())
                        MetricLine(t("Open / Closed", "باز / بسته"), "${data.trade_stats.open_trades} / ${data.trade_stats.closed_trades}")
                        MetricLine(t("Win Rate", "نرخ برد"), "${data.trade_stats.win_rate}%")
                        MetricLine(t("Net PnL", "سود/زیان خالص"), data.trade_stats.net_pnl.toString())
                    }
                }
                item {
                    SectionLabel(t("Top Signal Symbols", "برترین نمادهای سیگنال"))
                }
                items(data.top_signal_symbols) { item ->
                    PremiumGlassCard {
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text(item.symbol, style = MaterialTheme.typography.titleMedium, color = Color.White, fontWeight = FontWeight.Bold)
                            Text(t("Count", "تعداد") + ": ${item.count}", color = Color(0xFF67ECFF))
                        }
                    }
                }
                item {
                    SectionLabel(t("Signal Stats by Symbol", "آمار سیگنال بر اساس نماد"))
                }
                items(report.signal_stats_by_symbol) { item ->
                    PremiumGlassCard {
                        Text(item.symbol, style = MaterialTheme.typography.titleMedium, color = Color.White, fontWeight = FontWeight.Bold)
                        MetricLine(t("Signals", "سیگنال‌ها"), item.count.toString())
                        MetricLine(t("Average Score", "میانگین امتیاز"), item.average_score.toString())
                    }
                }
                item {
                    SectionLabel(t("Trade Performance by Symbol", "عملکرد معاملات بر اساس نماد"))
                }
                items(report.trade_performance_by_symbol) { item ->
                    PremiumGlassCard(borderColor = Color(0x4059C7FF)) {
                        Text(item.symbol, style = MaterialTheme.typography.titleMedium, color = Color.White, fontWeight = FontWeight.Bold)
                        MetricLine(t("Trades", "معاملات"), item.trade_count.toString())
                        MetricLine(t("Wins / Losses", "برد / باخت"), "${item.wins} / ${item.losses}")
                        MetricLine(t("Win Rate", "نرخ برد"), "${item.win_rate}%")
                        MetricLine(t("Net PnL", "سود/زیان خالص"), item.net_pnl.toString())
                    }
                }
            }
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
