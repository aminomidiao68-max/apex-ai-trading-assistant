package com.arena.smartmoney.ui.journal

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
fun JournalScreen(viewModel: JournalViewModel = viewModel()) {
    val state by viewModel.uiState.collectAsState()
    val t = rememberTranslator()

    val filteredItems = when (state.filter) {
        "open" -> state.items.filter { it.status == "open" }
        "closed" -> state.items.filter { it.status == "closed" }
        else -> state.items
    }

    PremiumScreenBackground {
        androidx.compose.foundation.lazy.LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                PremiumSectionHeader(
                    title = t("Trade Journal", "ژورنال معاملات"),
                    subtitle = t(
                        "Track open and closed positions created from AI signals.",
                        "پوزیشن‌های باز و بسته‌ای که از سیگنال‌های AI ساخته شده‌اند را دنبال کن."
                    )
                )
            }
            item {
                val stats = state.stats
                PremiumGlassCard {
                    Text(t("Performance Snapshot", "نمای کلی عملکرد"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
                    Text(t("Total Trades", "کل معاملات") + ": ${stats?.total_trades ?: 0}", color = Color.White)
                    Text(t("Open / Closed", "باز / بسته") + ": ${stats?.open_trades ?: 0} / ${stats?.closed_trades ?: 0}", color = Color.White)
                    Text(t("Wins / Losses", "برد / باخت") + ": ${stats?.wins ?: 0} / ${stats?.losses ?: 0}", color = Color.White)
                    Text(t("Win Rate", "نرخ برد") + ": ${stats?.win_rate ?: 0.0}%", color = Color(0xFF67ECFF), fontWeight = FontWeight.Bold)
                    Text(
                        t("Net PnL", "سود/زیان خالص") + ": ${stats?.net_pnl ?: 0.0}",
                        color = when {
                            (stats?.net_pnl ?: 0.0) > 0 -> Color(0xFF33E6A6)
                            (stats?.net_pnl ?: 0.0) < 0 -> Color(0xFFFF7A7A)
                            else -> Color.White
                        },
                        fontWeight = FontWeight.Bold
                    )
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        FilterButton(modifier = Modifier.weight(1f), title = t("All", "همه"), selected = state.filter == "all") { viewModel.setFilter("all") }
                        FilterButton(modifier = Modifier.weight(1f), title = t("Open", "باز"), selected = state.filter == "open") { viewModel.setFilter("open") }
                        FilterButton(modifier = Modifier.weight(1f), title = t("Closed", "بسته"), selected = state.filter == "closed") { viewModel.setFilter("closed") }
                    }
                    Button(onClick = { viewModel.refresh() }, modifier = Modifier.fillMaxWidth()) {
                        Text(if (state.loading) t("Refreshing...", "در حال بروزرسانی...") else t("Refresh Journal", "بروزرسانی ژورنال"))
                    }
                    if (state.message.isNotBlank()) Text(state.message, color = Color(0xFF67ECFF))
                    state.error?.let { Text(t("Error", "خطا") + ": $it", color = MaterialTheme.colorScheme.error) }
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

                PremiumGlassCard(borderColor = accent.copy(alpha = 0.35f)) {
                    Text("${trade.symbol} • $directionLabel", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.ExtraBold, color = Color.White)
                    Text(t("Status", "وضعیت") + ": $statusLabel", color = Color(0xFFBCEEFF))
                    Text(t("Entry", "ورود") + ": ${trade.entry_price}", color = Color.White)
                    Text(t("Stop Loss", "حد ضرر") + ": ${trade.stop_loss}", color = Color.White)
                    Text(t("Take Profit", "حد سود") + ": ${trade.take_profit ?: "-"}", color = Color.White)
                    Text(t("Size", "حجم") + ": ${trade.size}", color = Color.White)
                    Text(
                        t("PnL", "سود/زیان") + ": $pnl",
                        color = when {
                            pnl > 0 -> Color(0xFF33E6A6)
                            pnl < 0 -> Color(0xFFFF7A7A)
                            else -> Color.White
                        },
                        fontWeight = FontWeight.Bold
                    )
                    Text(t("Created At", "زمان ایجاد") + ": ${trade.created_at}", color = Color(0xFF8EDFFF))
                    trade.closed_at?.let { Text(t("Closed At", "زمان بسته شدن") + ": $it", color = Color(0xFF8EDFFF)) }
                    if (trade.notes.isNotBlank()) Text(t("Notes", "یادداشت") + ": ${trade.notes}", color = Color(0xFFDDF8FF))
                    if (trade.status == "open") {
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            if (trade.take_profit != null) {
                                Button(onClick = { viewModel.closeTradeAsWin(trade) }, modifier = Modifier.weight(1f)) {
                                    Text(t("Close at TP", "بستن با حد سود"))
                                }
                            }
                            OutlinedButton(onClick = { viewModel.closeTradeAsLoss(trade) }, modifier = Modifier.weight(1f)) {
                                Text(t("Close at SL", "بستن با حد ضرر"))
                            }
                        }
                    }
                }
            }
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
