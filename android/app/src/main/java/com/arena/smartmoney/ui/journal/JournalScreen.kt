package com.arena.smartmoney.ui.journal

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
import com.arena.smartmoney.data.model.TradeJournalItemDto
import com.arena.smartmoney.ui.components.PremiumGlassCard
import com.arena.smartmoney.ui.components.PremiumScreenBackground
import com.arena.smartmoney.ui.components.PremiumSectionHeader
import com.arena.smartmoney.ui.i18n.formatDisplayTimestamp
import com.arena.smartmoney.ui.i18n.formatTradeNote
import com.arena.smartmoney.ui.i18n.rememberTranslator
import java.util.Locale
import kotlin.math.abs

@Composable
fun JournalScreen(viewModel: JournalViewModel = viewModel()) {
    val state by viewModel.uiState.collectAsState()
    val t = rememberTranslator()

    val filteredItems = when (state.filter) {
        "open" -> state.items.filter { it.status == "open" }
        "closed" -> state.items.filter { it.status == "closed" }
        "wins" -> state.items.filter { it.status == "closed" && (it.pnl_amount ?: 0.0) > 0.0 }
        "losses" -> state.items.filter { it.status == "closed" && (it.pnl_amount ?: 0.0) < 0.0 }
        else -> state.items
    }

    val stats = state.stats
    val closedItems = state.items.filter { it.status == "closed" }
    val openItems = state.items.filter { it.status == "open" }
    val winItems = closedItems.filter { (it.pnl_amount ?: 0.0) > 0.0 }
    val lossItems = closedItems.filter { (it.pnl_amount ?: 0.0) < 0.0 }
    val avgWin = if (winItems.isNotEmpty()) winItems.map { it.pnl_amount ?: 0.0 }.average() else 0.0
    val avgLossAbs = if (lossItems.isNotEmpty()) lossItems.map { abs(it.pnl_amount ?: 0.0) }.average() else 0.0
    val payoffRatio = if (avgLossAbs > 0) avgWin / avgLossAbs else 0.0
    val closureRate = if (state.items.isNotEmpty()) (closedItems.size.toDouble() / state.items.size.toDouble()) * 100.0 else 0.0
    val expectancy = if (closedItems.isNotEmpty()) (stats?.net_pnl ?: 0.0) / closedItems.size.toDouble() else 0.0
    val openRisk = openItems.sumOf { abs(it.entry_price - it.stop_loss) * it.size }
    val bestTrade = closedItems.maxByOrNull { it.pnl_amount ?: Double.NEGATIVE_INFINITY }
    val worstTrade = closedItems.minByOrNull { it.pnl_amount ?: Double.POSITIVE_INFINITY }
    val healthLabel = journalHealthLabel(stats?.win_rate ?: 0.0, stats?.net_pnl ?: 0.0, t)
    val coachMessage = journalCoachMessage(
        winRate = stats?.win_rate ?: 0.0,
        netPnl = stats?.net_pnl ?: 0.0,
        openTrades = stats?.open_trades ?: 0,
        payoffRatio = payoffRatio,
        t = t,
    )

    PremiumScreenBackground {
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                PremiumSectionHeader(
                    title = t("Trade Journal Pro", "ژورنال حرفه‌ای معاملات"),
                    subtitle = t(
                        "Execution tracking, performance intelligence and post-trade coaching from your AI signals.",
                        "ردیابی اجرا، هوش عملکرد و مربی‌گری پس از معامله بر پایه سیگنال‌های AI."
                    )
                )
            }
            item {
                PremiumGlassCard {
                    Text(t("Performance Intelligence", "هوش عملکرد"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        JournalChip(t("Health", "سلامت"), healthLabel, Modifier.weight(1f))
                        JournalChip(t("Win Rate", "نرخ برد"), "${stats?.win_rate ?: 0.0}%", Modifier.weight(1f))
                        JournalChip(t("Net PnL", "سود خالص"), (stats?.net_pnl ?: 0.0).toString(), Modifier.weight(1f))
                    }
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        JournalChip(t("Closure Rate", "نرخ بسته‌شدن"), String.format(Locale.US, "%.1f%%", closureRate), Modifier.weight(1f))
                        JournalChip(t("Payoff", "نسبت پاداش"), if (payoffRatio > 0) String.format(Locale.US, "%.2f", payoffRatio) else "-", Modifier.weight(1f))
                        JournalChip(t("Open Risk", "ریسک باز"), String.format(Locale.US, "%.2f", openRisk), Modifier.weight(1f))
                    }
                    MetricLine(t("Total Trades", "کل معاملات"), "${stats?.total_trades ?: 0}")
                    MetricLine(t("Open / Closed", "باز / بسته"), "${stats?.open_trades ?: 0} / ${stats?.closed_trades ?: 0}")
                    MetricLine(t("Wins / Losses", "برد / باخت"), "${stats?.wins ?: 0} / ${stats?.losses ?: 0}")
                    MetricLine(t("Average Win", "میانگین برد"), String.format(Locale.US, "%.2f", avgWin))
                    MetricLine(t("Average Loss", "میانگین باخت"), if (avgLossAbs > 0) String.format(Locale.US, "%.2f", avgLossAbs) else "-")
                    MetricLine(t("Expectancy / Trade", "امیدریاضی هر معامله"), String.format(Locale.US, "%.2f", expectancy))
                    bestTrade?.let {
                        MetricLine(t("Best Trade", "بهترین معامله"), "${it.symbol} • ${String.format(Locale.US, "%.2f", it.pnl_amount ?: 0.0)}")
                    }
                    worstTrade?.let {
                        MetricLine(t("Worst Trade", "بدترین معامله"), "${it.symbol} • ${String.format(Locale.US, "%.2f", it.pnl_amount ?: 0.0)}")
                    }
                    Text(t("Coach", "مربی") + ": $coachMessage", color = Color(0xFFFFD27A))
                    if (state.message.isNotBlank()) Text(state.message, color = Color(0xFF67ECFF))
                    state.error?.let { Text(t("Error", "خطا") + ": $it", color = MaterialTheme.colorScheme.error) }
                }
            }
            item {
                PremiumGlassCard(borderColor = Color(0x4059C7FF)) {
                    Text(t("Filter & Review", "فیلتر و بررسی"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        FilterButton(modifier = Modifier.weight(1f), title = t("All", "همه"), selected = state.filter == "all") { viewModel.setFilter("all") }
                        FilterButton(modifier = Modifier.weight(1f), title = t("Open", "باز"), selected = state.filter == "open") { viewModel.setFilter("open") }
                        FilterButton(modifier = Modifier.weight(1f), title = t("Closed", "بسته"), selected = state.filter == "closed") { viewModel.setFilter("closed") }
                    }
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        FilterButton(modifier = Modifier.weight(1f), title = t("Wins", "بردها"), selected = state.filter == "wins") { viewModel.setFilter("wins") }
                        FilterButton(modifier = Modifier.weight(1f), title = t("Losses", "باخت‌ها"), selected = state.filter == "losses") { viewModel.setFilter("losses") }
                        Button(onClick = { viewModel.refresh() }, modifier = Modifier.weight(1f)) {
                            Text(if (state.loading) t("Refreshing...", "در حال بروزرسانی...") else t("Refresh", "بروزرسانی"))
                        }
                    }
                    Text(t("Visible Trades", "معاملات قابل مشاهده") + ": ${filteredItems.size}", color = Color(0xFFBCEEFF))
                }
            }

            if (filteredItems.isEmpty()) {
                item {
                    PremiumGlassCard {
                        Text(t("No trades saved yet", "هنوز معامله‌ای ذخیره نشده است"), style = MaterialTheme.typography.titleMedium, color = Color.White, fontWeight = FontWeight.Bold)
                        Text(t("Add stronger signals to the journal to track execution quality.", "سیگنال‌های قوی‌تر را به ژورنال اضافه کن تا کیفیت اجرا را پیگیری کنی."), color = Color(0xFFBCEEFF))
                    }
                }
            }

            items(filteredItems) { trade ->
                JournalTradeCard(
                    trade = trade,
                    onCloseWin = { viewModel.closeTradeAsWin(trade) },
                    onCloseLoss = { viewModel.closeTradeAsLoss(trade) },
                    onDelete = { },
                    t = t,
                )
            }
        }
    }
}

@Composable
private fun JournalTradeCard(
    trade: TradeJournalItemDto,
    onCloseWin: () -> Unit,
    onCloseLoss: () -> Unit,
    onDelete: () -> Unit,
    t: (String, String) -> String,
) {
    val pnl = trade.pnl_amount ?: 0.0
    val statusLabel = when (trade.status.lowercase(Locale.getDefault())) {
        "open" -> t("Open", "باز")
        "closed" -> t("Closed", "بسته")
        else -> trade.status
    }
    val directionLabel = when (trade.direction.lowercase(Locale.getDefault())) {
        "buy" -> t("BUY", "خرید")
        "sell" -> t("SELL", "فروش")
        else -> trade.direction.uppercase(Locale.getDefault())
    }
    val accent = if (trade.direction.lowercase(Locale.getDefault()) == "buy") Color(0xFF33E6A6) else Color(0xFFFF7A7A)
    val riskAmount = abs(trade.entry_price - trade.stop_loss) * trade.size
    val realizedMultiple = if (riskAmount > 0.0 && trade.status == "closed") pnl / riskAmount else 0.0
    val tradeQuality = when {
        trade.status == "open" -> t("Live", "زنده")
        pnl > 0 -> t("Winner", "برنده")
        pnl < 0 -> t("Loser", "بازنده")
        else -> t("Flat", "خنثی")
    }

    PremiumGlassCard(borderColor = accent.copy(alpha = 0.35f)) {
        Text("${trade.symbol} • $directionLabel", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.ExtraBold, color = Color.White)
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            JournalChip(t("Status", "وضعیت"), statusLabel, Modifier.weight(1f))
            JournalChip(t("Quality", "کیفیت"), tradeQuality, Modifier.weight(1f))
            JournalChip(t("R-Multiple", "آر مولتیپل"), if (trade.status == "closed") String.format(Locale.US, "%.2fR", realizedMultiple) else "-", Modifier.weight(1f))
        }
        Text(t("Entry", "ورود") + ": ${trade.entry_price}", color = Color.White)
        Text(t("Stop Loss", "حد ضرر") + ": ${trade.stop_loss}", color = Color.White)
        Text(t("Take Profit", "حد سود") + ": ${trade.take_profit ?: "-"}", color = Color.White)
        Text(t("Size", "حجم") + ": ${trade.size}", color = Color.White)
        Text(t("Risk Budget", "بودجه ریسک") + ": ${String.format(Locale.US, "%.2f", riskAmount)}", color = Color(0xFFFFD27A))
        Text(
            t("PnL", "سود/زیان") + ": ${String.format(Locale.US, "%.2f", pnl)}",
            color = when {
                pnl > 0 -> Color(0xFF33E6A6)
                pnl < 0 -> Color(0xFFFF7A7A)
                else -> Color.White
            },
            fontWeight = FontWeight.Bold
        )
        Text(t("Created At", "زمان ایجاد") + ": ${formatDisplayTimestamp(trade.created_at)}", color = Color(0xFF8EDFFF))
        trade.closed_at?.let { Text(t("Closed At", "زمان بسته شدن") + ": ${formatDisplayTimestamp(it)}", color = Color(0xFF8EDFFF)) }
        if (trade.notes.isNotBlank()) {
            Text(t("Notes", "یادداشت") + ": ${formatTradeNote(trade.notes, t)}", color = Color(0xFFDDF8FF))
        }
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            if (trade.status == "open") {
                if (trade.take_profit != null) {
                    Button(onClick = onCloseWin, modifier = Modifier.weight(1f)) {
                        Text(t("Close at TP", "بستن با حد سود"))
                    }
                }
                OutlinedButton(onClick = onCloseLoss, modifier = Modifier.weight(1f)) {
                    Text(t("Close at SL", "بستن با حد ضرر"))
                }
            }
        }
        OutlinedButton(onClick = onDelete, modifier = Modifier.fillMaxWidth()) {
            Text(t("Delete Trade", "حذف معامله"))
        }
    }
}

@Composable
private fun JournalChip(title: String, value: String, modifier: Modifier = Modifier) {
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
private fun FilterButton(
    modifier: Modifier = Modifier,
    title: String,
    selected: Boolean,
    onClick: () -> Unit
) {
    if (selected) {
        Button(onClick = onClick, modifier = modifier) { Text(title) }
    } else {
        OutlinedButton(onClick = onClick, modifier = modifier) { Text(title) }
    }
}

@Composable
private fun MetricLine(label: String, value: String) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, color = Color(0xFFDDF8FF))
        Text(value, color = Color(0xFF67ECFF), fontWeight = FontWeight.Bold)
    }
}

private fun journalHealthLabel(winRate: Double, netPnl: Double, t: (String, String) -> String): String {
    return when {
        winRate >= 60.0 && netPnl > 0 -> t("Elite", "ممتاز")
        winRate >= 50.0 && netPnl >= 0 -> t("Strong", "قوی")
        winRate >= 40.0 -> t("Developing", "در حال شکل‌گیری")
        else -> t("Weak", "ضعیف")
    }
}

private fun journalCoachMessage(
    winRate: Double,
    netPnl: Double,
    openTrades: Int,
    payoffRatio: Double,
    t: (String, String) -> String,
): String {
    return when {
        openTrades >= 3 -> t("Too many open trades are reducing focus. Manage exposure before adding more positions.", "تعداد معاملات باز زیاد شده و تمرکز را کم می‌کند. قبل از افزودن پوزیشن جدید، اکسپوژر را مدیریت کن.")
        winRate >= 58.0 && netPnl > 0 && payoffRatio >= 1.2 -> t("Execution quality is strong. Keep the same discipline and avoid forcing extra trades.", "کیفیت اجرا قوی است. همین نظم را حفظ کن و معامله اضافه و اجباری نزن.")
        winRate >= 45.0 && netPnl >= 0 -> t("You are stable but still improving. Focus on cleaner A/B setups and tighter exit discipline.", "عملکردت پایدار است اما هنوز جای رشد دارد. روی ستاپ‌های تمیزتر A/B و نظم بهتر در خروج تمرکز کن.")
        else -> t("Performance is under pressure. Reduce frequency, review losses and only take high-confluence setups.", "عملکرد تحت فشار است. تعداد معاملات را کم کن، باخت‌ها را مرور کن و فقط ستاپ‌های با همگرایی بالا بگیر.")
    }
}
