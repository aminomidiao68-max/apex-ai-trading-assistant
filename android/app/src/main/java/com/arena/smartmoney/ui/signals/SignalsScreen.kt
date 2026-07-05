package com.arena.smartmoney.ui.signals

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.arena.smartmoney.data.model.SignalHistoryItemDto
import com.arena.smartmoney.ui.components.PremiumGlassCard
import com.arena.smartmoney.ui.components.PremiumScreenBackground
import com.arena.smartmoney.ui.components.PremiumSectionHeader
import com.arena.smartmoney.ui.i18n.formatDisplayTimestamp
import com.arena.smartmoney.ui.i18n.localizeConfluenceTag
import com.arena.smartmoney.ui.i18n.localizeEntryModel
import com.arena.smartmoney.ui.i18n.localizeExecutionLabel
import com.arena.smartmoney.ui.i18n.localizeRiskFlag
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
                        "AI live scan, confluence grading, execution labels and TP1 / TP2 / TP3 workflow.",
                        "اسکن زنده هوش مصنوعی، گرید همگرایی، برچسب اجرای معامله و جریان TP1 / TP2 / TP3."
                    )
                )
            }
            item {
                PremiumGlassCard {
                    Text(
                        t("Quick Live Scan", "اسکن سریع زنده"),
                        color = Color.White,
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        t(
                            "Scan stronger setups and send only cleaner trade ideas to the journal.",
                            "ستاپ‌های قوی‌تر را اسکن کن و فقط ایده‌های تمیزتر را به ژورنال بفرست."
                        ),
                        color = Color(0xFFBCEEFF)
                    )
                    Text(
                        t("Selected timeframe", "تایم‌فریم انتخابی") + ": ${state.selectedTimeframe}",
                        color = Color(0xFF67ECFF),
                        fontWeight = FontWeight.Bold
                    )

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        TimeframeButton("1m", state.selectedTimeframe == "1m", modifier = Modifier.weight(1f)) { viewModel.selectTimeframe("1m") }
                        TimeframeButton("5m", state.selectedTimeframe == "5m", modifier = Modifier.weight(1f)) { viewModel.selectTimeframe("5m") }
                        TimeframeButton("15m", state.selectedTimeframe == "15m", modifier = Modifier.weight(1f)) { viewModel.selectTimeframe("15m") }
                        TimeframeButton("1h", state.selectedTimeframe == "1h", modifier = Modifier.weight(1f)) { viewModel.selectTimeframe("1h") }
                    }

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Button(onClick = { viewModel.scanMarket("BTCUSDT", "crypto") }, modifier = Modifier.weight(1f)) { Text("BTC") }
                        Button(onClick = { viewModel.scanMarket("ETHUSDT", "crypto") }, modifier = Modifier.weight(1f)) { Text("ETH") }
                        OutlinedButton(onClick = { viewModel.scanMarket("EURUSD", "forex") }, modifier = Modifier.weight(1f)) { Text("EURUSD") }
                    }

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        OutlinedButton(onClick = { viewModel.scanMarket("XAUUSD", "forex") }, modifier = Modifier.weight(1f)) { Text("XAUUSD") }
                        Button(onClick = { viewModel.loadHistory() }, modifier = Modifier.weight(1f)) {
                            Text(if (state.loading) t("Loading...", "در حال بارگذاری...") else t("Refresh", "بروزرسانی"))
                        }
                        Button(onClick = onOpenJournal, modifier = Modifier.weight(1f)) { Text(t("Journal", "ژورنال")) }
                    }

                    if (state.scanMessage.isNotBlank()) Text(state.scanMessage, color = Color(0xFF33E6A6))
                    if (state.journalMessage.isNotBlank()) Text(state.journalMessage, color = Color(0xFF67ECFF))
                    state.error?.let { Text(t("Error", "خطا") + ": $it", color = MaterialTheme.colorScheme.error) }

                    Text(
                        t(
                            "Live engine now exposes institutional grade, entry model and confluence tags.",
                            "موتور زنده حالا گرید حرفه‌ای، مدل ورود و تگ‌های همگرایی را هم نشان می‌دهد."
                        ),
                        color = Color(0xFFFFD27A)
                    )
                }
            }

            items(state.items) { signal ->
                SignalCard(
                    signal = signal,
                    onOpenJournal = onOpenJournal,
                    onAddToJournal = { viewModel.createTradeFromSignal(signal) },
                    t = t
                )
            }
        }
    }
}

@Composable
private fun SignalCard(
    signal: SignalHistoryItemDto,
    onOpenJournal: () -> Unit,
    onAddToJournal: () -> Unit,
    t: (String, String) -> String,
) {
    val grade = signal.setup_grade ?: when {
        signal.score >= 88 -> "A+"
        signal.score >= 78 -> "A"
        signal.score >= 68 -> "B"
        else -> "C"
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

    val confidenceProgress = when (signal.confidence.lowercase(Locale.getDefault())) {
        "high" -> 0.92f
        "medium" -> 0.68f
        else -> 0.35f
    }

    val executionLabel = localizeExecutionLabel(signal.execution_label ?: "observe", t)
    val entryModel = localizeEntryModel(signal.entry_model ?: "No Trade", t)
    val confluenceTags = (signal.confluence_tags ?: emptyList()).take(6)
    val riskFlags = signal.risk_flags ?: emptyList()

    PremiumGlassCard(borderColor = accent.copy(alpha = 0.35f)) {
        Text(
            signal.symbol,
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.ExtraBold,
            color = Color.White
        )

        Text(
            "${signal.direction.uppercase(Locale.getDefault())} • ${t("Score", "امتیاز")} ${signal.score} • ${signal.timeframe}",
            color = accent,
            fontWeight = FontWeight.Bold
        )

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            InfoChip(
                label = "Grade $grade",
                background = accent.copy(alpha = 0.18f),
                color = accent
            )
            InfoChip(
                label = executionLabel,
                background = Color(0x2611D9FF),
                color = Color(0xFF8EEBFF)
            )
        }

        Text(
            t("Confidence", "اطمینان") + ": $confidence • ${t("Session", "سشن")}: ${localizeSessionName(signal.session_name, t)}",
            color = Color.White
        )

        Text(
            t("Entry Model", "مدل ورود") + ": $entryModel",
            color = Color(0xFFFFD27A),
            fontWeight = FontWeight.SemiBold
        )

        ConfidenceBar(progress = confidenceProgress, accent = accent, t = t)

        signal.ai_summary?.takeIf { it.isNotBlank() }?.let {
            Text(t("AI Summary", "خلاصه هوش مصنوعی") + ": $it", color = Color(0xFFDDF8FF))
        }

        if (analysisSummary.isNotBlank()) {
            Text(t("AI Analysis", "تحلیل هوش مصنوعی") + ": $analysisSummary", color = Color(0xFFBCEEFF))
        }

        if (confluenceTags.isNotEmpty()) {
            Text(t("Confluence Tags", "تگ‌های همگرایی"), color = Color.White, fontWeight = FontWeight.Bold)
            SignalTagRows(tags = confluenceTags.map { localizeConfluenceTag(it, t) }, accent = accent)
        }

        signal.score_breakdown?.let { breakdown ->
            Text(t("Institutional Breakdown", "شکست امتیاز نهادی"), color = Color.White, fontWeight = FontWeight.Bold)
            BreakdownMeter(t("Structure", "ساختار"), breakdown.structure.toFloat(), 25f, accent)
            BreakdownMeter(t("SMC", "اسمارت‌مانی"), breakdown.smc.toFloat(), 25f, accent)
            BreakdownMeter(t("Order Flow", "جریان سفارش"), breakdown.order_flow.toFloat(), 20f, accent)
            BreakdownMeter(t("Session", "سشن"), breakdown.session.toFloat(), 10f, accent)
            BreakdownMeter(t("News", "خبر"), breakdown.news.toFloat(), 10f, accent)
            BreakdownMeter(t("Indicators", "اندیکاتورها"), breakdown.indicators.toFloat(), 10f, accent)
        }

        Text(t("Entry Zone", "محدوده ورود") + ": ${signal.entry_low ?: "-"} - ${signal.entry_high ?: "-"}", color = Color.White)
        Text(t("Stop Loss", "حد ضرر") + ": ${signal.stop_loss ?: "-"}", color = Color.White)
        Text("TP1 • RR 1:1 = ${tp1 ?: "-"}", color = Color(0xFF67ECFF), fontWeight = FontWeight.Bold)
        Text("TP2 • RR 1:2 = ${tp2 ?: "-"}", color = Color(0xFF67ECFF), fontWeight = FontWeight.Bold)
        Text("TP3 • RR 1:3 = ${tp3 ?: "-"}", color = Color(0xFF67ECFF), fontWeight = FontWeight.Bold)

        signal.risk_to_reward?.let {
            Text(t("Max Target RR", "بیشترین نسبت بازده هدف") + ": 1:$it", color = Color(0xFFFFD27A))
        }

        if (riskFlags.isNotEmpty()) {
            Text(t("Risk Flags", "هشدارهای ریسک"), color = Color(0xFFFFD27A), fontWeight = FontWeight.Bold)
            Text(riskFlags.joinToString(" • ") { localizeRiskFlag(it, t) }, color = Color(0xFFFFD27A))
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Button(onClick = onAddToJournal, modifier = Modifier.weight(1f)) {
                Text(t("Add to Journal", "افزودن به ژورنال"))
            }
            OutlinedButton(onClick = onOpenJournal, modifier = Modifier.weight(1f)) {
                Text(t("Open Journal", "باز کردن ژورنال"))
            }
        }

        Text(t("Saved At", "زمان ذخیره") + ": ${formatDisplayTimestamp(signal.created_at)}", color = Color(0xFF8EDFFF))
    }
}

@Composable
private fun ConfidenceBar(progress: Float, accent: Color, t: (String, String) -> String) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(t("AI Confidence Meter", "نوار اطمینان هوش مصنوعی"), color = Color(0xFFBCEEFF))
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(10.dp)
                .background(Color(0x331B2B3E), RoundedCornerShape(50))
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth(progress.coerceIn(0f, 1f))
                    .height(10.dp)
                    .background(Brush.horizontalGradient(listOf(accent, Color(0xFF67ECFF))), RoundedCornerShape(50))
            )
        }
    }
}

@Composable
private fun BreakdownMeter(title: String, value: Float, maxValue: Float, accent: Color) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text("$title • ${"%.1f".format(value)}", color = Color(0xFFBCEEFF))
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(8.dp)
                .background(Color(0x331B2B3E), RoundedCornerShape(50))
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth((value / maxValue).coerceIn(0f, 1f))
                    .height(8.dp)
                    .background(Brush.horizontalGradient(listOf(accent, Color(0xFF67ECFF))), RoundedCornerShape(50))
            )
        }
    }
}

@Composable
private fun SignalTagRows(tags: List<String>, accent: Color) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        tags.chunked(3).forEach { rowItems ->
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                rowItems.forEach { label ->
                    InfoChip(
                        label = label,
                        background = accent.copy(alpha = 0.14f),
                        color = Color.White,
                        modifier = Modifier.weight(1f)
                    )
                }
            }
        }
    }
}

@Composable
private fun InfoChip(
    label: String,
    background: Color,
    color: Color,
    modifier: Modifier = Modifier,
) {
    Box(
        modifier = modifier
            .background(background, RoundedCornerShape(14.dp))
            .padding(horizontal = 12.dp, vertical = 8.dp)
    ) {
        Text(
            label,
            color = color,
            style = MaterialTheme.typography.bodySmall,
            fontWeight = FontWeight.Bold
        )
    }
}

@Composable
private fun TimeframeButton(
    label: String,
    selected: Boolean,
    modifier: Modifier = Modifier,
    onClick: () -> Unit
) {
    if (selected) {
        Button(onClick = onClick, modifier = modifier) { Text(label) }
    } else {
        OutlinedButton(onClick = onClick, modifier = modifier) { Text(label) }
    }
}
