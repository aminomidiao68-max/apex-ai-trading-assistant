package com.arena.smartmoney.ui.signals

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
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

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item {
            Text(t("Signal Center", "مرکز سیگنال"), style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
            Text(t("AI live scan, saved history and TP1 / TP2 / TP3 workflow.", "اسکن زنده هوش مصنوعی، تاریخچه ذخیره‌شده و جریان تی‌پی ۱ / ۲ / ۳."))
        }
        item {
            Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(22.dp)) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(t("Quick Live Scan", "اسکن سریع زنده"), style = MaterialTheme.typography.titleLarge)
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.scanMarket("BTCUSDT", "crypto") }) { Text("BTC") }
                        Button(onClick = { viewModel.scanMarket("ETHUSDT", "crypto") }) { Text("ETH") }
                        Button(onClick = { viewModel.scanMarket("EURUSD", "forex") }) { Text("EURUSD") }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.scanMarket("XAUUSD", "forex") }) { Text("XAUUSD") }
                        Button(onClick = { viewModel.loadHistory() }) { Text(if (state.loading) t("Loading...", "در حال بارگذاری...") else t("Refresh", "بروزرسانی")) }
                        Button(onClick = onOpenJournal) { Text(t("Journal", "ژورنال")) }
                    }
                    if (state.scanMessage.isNotBlank()) Text(state.scanMessage, color = Color(0xFF2ECC71))
                    if (state.journalMessage.isNotBlank()) Text(state.journalMessage, color = MaterialTheme.colorScheme.primary)
                    state.error?.let { Text(t("Error", "خطا") + ": $it", color = MaterialTheme.colorScheme.error) }
                    Text(t("Forex live scan needs a TwelveData API key on the backend.", "برای اسکن زنده فارکس باید کلید TwelveData روی بک‌اند تنظیم شود."))
                }
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
            val analysisSummary = signal.reasons.take(3).joinToString(separator = " • ")
            Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(22.dp)) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(signal.symbol, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                    Text("${signal.direction.uppercase(Locale.getDefault())} • ${t("Score", "امتیاز")} ${signal.score} • ${signal.timeframe}")
                    Text(grade)
                    Text(t("Confidence", "اطمینان") + ": $confidence • " + t("Session", "سشن") + ": ${signal.session_name}")
                    if (analysisSummary.isNotBlank()) {
                        Text(t("AI Analysis", "تحلیل هوش مصنوعی") + ": $analysisSummary")
                    }
                    Text(t("Entry Zone", "محدوده ورود") + ": ${signal.entry_low ?: "-"} - ${signal.entry_high ?: "-"}")
                    Text(t("Stop Loss", "حد ضرر") + ": ${signal.stop_loss ?: "-"}")
                    Text("TP1: ${tp1 ?: "-"}")
                    Text("TP2: ${tp2 ?: "-"}")
                    Text("TP3: ${tp3 ?: "-"}")
                    signal.risk_to_reward?.let {
                        Text(t("Target RR", "نسبت ریسک به بازده هدف") + ": $it")
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.createTradeFromSignal(signal) }) {
                            Text(t("Add to Journal", "افزودن به ژورنال"))
                        }
                        Button(onClick = onOpenJournal) {
                            Text(t("Open Journal", "باز کردن ژورنال"))
                        }
                    }
                    Text(t("Saved At", "زمان ذخیره") + ": ${signal.created_at}")
                }
            }
        }
    }
}
