package com.arena.smartmoney.ui.signals

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.arena.smartmoney.ui.components.PremiumGlassCard
import com.arena.smartmoney.ui.components.PremiumScreenBackground
import com.arena.smartmoney.ui.components.PremiumSectionHeader
import com.arena.smartmoney.ui.i18n.formatDisplayTimestamp
import com.arena.smartmoney.ui.i18n.localizeSignalReason
import com.arena.smartmoney.ui.i18n.localizeSessionName
import com.arena.smartmoney.ui.i18n.rememberTranslator
import com.arena.smartmoney.util.NotificationHelper
import java.util.Locale

@Composable
fun SignalsScreen(
    onOpenJournal: () -> Unit,
    viewModel: SignalsViewModel = viewModel()
) {
    val state by viewModel.uiState.collectAsState()
    val context = LocalContext.current
    val t = rememberTranslator()

    LaunchedEffect(state.notificationSignal?.id) {
        val signal = state.notificationSignal ?: return@LaunchedEffect
        if (signal.direction.lowercase(Locale.getDefault()) != "neutral" && signal.score >= 70.0) {
            NotificationHelper.showSignalNotification(
                context = context,
                title = "${signal.symbol} ${signal.direction.uppercase(Locale.getDefault())}",
                body = "Score ${signal.score} • ${signal.session_name}",
                id = signal.id
            )
        }
        viewModel.consumeNotification()
    }

    PremiumScreenBackground {
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            item {
                PremiumSectionHeader(
                    title = t("Signal Center", "مرکز سیگنال"),
                    subtitle = t(
                        "AI live scan, confidence grading and TP1 / TP2 / TP3 workflow.",
                        "اسکن زنده هوش مصنوعی، درجه‌بندی اطمینان و جریان TP1 / TP2 / TP3."
                    )
                )
            }
            item {
                PremiumGlassCard {
                    Text(t("Quick Live Scan", "اسکن سریع زنده"), color = Color.White, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                    Text(t("Scan stronger setups and send only cleaner trade ideas to the journal.", "ستاپ‌های قوی‌تر را اسکن کن و فقط ایده‌های تمیزتر را به ژورنال بفرست."), color = Color(0xFFBCEEFF))
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.scanMarket("BTCUSDT", "crypto") }, modifier = Modifier.weight(1f)) { Text("BTC") }
                        Button(onClick = { viewModel.scanMarket("ETHUSDT", "crypto") }, modifier = Modifier.weight(1f)) { Text("ETH") }
                        OutlinedButton(onClick = { viewModel.scanMarket("EURUSD", "forex") }, modifier = Modifier.weight(1f)) { Text("EURUSD") }
                    }
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedButton(onClick = { viewModel.scanMarket("XAUUSD", "forex") }, modifier = Modifier.weight(1f)) { Text("XAUUSD") }
                        Button(onClick = { viewModel.loadHistory() }, modifier = Modifier.weight(1f)) {
                            Text(if (state.loading) t("Loading...", "در حال بارگذاری...") else t("Refresh", "بروزرسانی"))
                        }
                        Button(onClick = onOpenJournal, modifier = Modifier.weight(1f)) { Text(t("Journal", "ژورنال")) }
                    }
                    if (state.scanMessage.isNotBlank()) Text(state.scanMessage, color = Color(0xFF33E6A6))
                    if (state.journalMessage.isNotBlank()) Text(state.journalMessage, color = Color(0xFF67ECFF))
                    state.error?.let { Text(t("Error", "خطا") + ": $it", color = MaterialTheme.colorScheme.error) }
                    Text(t("Forex live scan still needs a TwelveData API key on the backend.", "اسکن زنده فارکس هنوز به کلید TwelveData روی بک‌اند نیاز دارد."), color = Color(0xFFFFD27A))
                }
            }
            items(state.items) { signal ->
                val grade = when {
                    signal.score >= 85 -> t("A+ elite setup", "ستاپ ممتاز A+")
                    signal.score >= 75 -> t("A grade setup", "ستاپ درجه A")
                    signal.score >= 65 -> t("B grade setup", "ستاپ درجه B")
                    else -> t("C / weak setup", "ستاپ ضعیف / C")
                }
                val confidence = when (signal.confidence.lowercase(Locale.getDefault())) {
                    "high" -> t("High", "بالا")
                    "medium" -> t("Medium", "متوسط")
                    else -> t("Low", "پایین")
                }
                val tp1 = signal.take_profits.getOrNull(0)
                val tp2 = signal.take_profits.getOrNull(1)
                val tp3 = signal.take_profits.getOrNull(2)
                val analysisSummary = signal.reasons.take(3).joinToString(separator = " • ") { localizeSignalReason(it, t) }
                val accent = when (signal.direction.lowercase(Locale.getDefault())) {
                    "buy" -> Color(0xFF33E6A6)
                    "sell" -> Color(0xFFFF7A7A)
                    else -> Color(0xFF67ECFF)
                }

                PremiumGlassCard(borderColor = accent.copy(alpha = 0.35f)) {
                    Text(signal.symbol, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.ExtraBold, color = Color.White)
                    Text("${signal.direction.uppercase(Locale.getDefault())} • ${t("Score", "امتیاز")} ${signal.score} • ${signal.timeframe}", color = accent, fontWeight = FontWeight.Bold)
                    Text(grade, color = Color(0xFFBCEEFF))
                    Text(t("Confidence", "اطمینان") + ": $confidence • ${t("Session", "سشن")}: ${localizeSessionName(signal.session_name, t)}", color = Color.White)
                    if (analysisSummary.isNotBlank()) {
                        Text(t("AI Analysis", "تحلیل هوش مصنوعی") + ": $analysisSummary", color = Color(0xFFDDF8FF))
                    }
                    Text(t("Entry Zone", "محدوده ورود") + ": ${signal.entry_low ?: "-"} - ${signal.entry_high ?: "-"}", color = Color.White)
                    Text(t("Stop Loss", "حد ضرر") + ": ${signal.stop_loss ?: "-"}", color = Color.White)
                    Text("TP1 • RR 1:1 = ${tp1 ?: "-"}", color = Color(0xFF67ECFF), fontWeight = FontWeight.Bold)
                    Text("TP2 • RR 1:2 = ${tp2 ?: "-"}", color = Color(0xFF67ECFF), fontWeight = FontWeight.Bold)
                    Text("TP3 • RR 1:3 = ${tp3 ?: "-"}", color = Color(0xFF67ECFF), fontWeight = FontWeight.Bold)
                    signal.risk_to_reward?.let {
                        Text(t("Max Target RR", "بیشترین نسبت بازده هدف") + ": 1:$it", color = Color(0xFFFFD27A))
                    }
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.createTradeFromSignal(signal) }, modifier = Modifier.weight(1f)) {
                            Text(t("Add to Journal", "افزودن به ژورنال"))
                        }
                        OutlinedButton(onClick = onOpenJournal, modifier = Modifier.weight(1f)) {
                            Text(t("Open Journal", "باز کردن ژورنال"))
                        }
                    }
                    Text(t("Saved At", "زمان ذخیره") + ": ${formatDisplayTimestamp(signal.created_at)}", color = Color(0xFF8EDFFF))
                }
            }
        }
    }
}
