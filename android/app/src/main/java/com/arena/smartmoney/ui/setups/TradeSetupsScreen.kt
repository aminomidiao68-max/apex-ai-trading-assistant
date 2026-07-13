package com.arena.smartmoney.ui.setups

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.ShowChart
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.arena.smartmoney.data.model.TradeSetupDto
import com.arena.smartmoney.ui.components.PremiumGlassCard
import com.arena.smartmoney.ui.components.PremiumScreenBackground
import com.arena.smartmoney.ui.components.PremiumSectionHeader
import com.arena.smartmoney.ui.i18n.rememberTranslator

private val SetupGold = Color(0xFFD4AF37)
private val SetupGreen = Color(0xFF26A69A)
private val SetupRed = Color(0xFFEF5350)
private val SetupBlue = Color(0xFF67ECFF)
private val SetupMuted = Color(0xFF8D98AA)
private val SetupSurface = Color(0xFF171C2B)

@Composable
fun TradeSetupsScreen(
    onOpenChart: (symbol: String, market: String, timeframe: String) -> Unit,
    viewModel: TradeSetupsViewModel = viewModel(),
) {
    val state by viewModel.uiState.collectAsState()
    val t = rememberTranslator()
    val source = when (state.selectedStatus) {
        "forming" -> state.forming
        "invalidated" -> state.invalidated
        else -> state.confirmed
    }
    val filtered = source.filter { setup ->
        (state.selectedSymbol == "ALL" || setup.symbol == state.selectedSymbol) &&
            (state.selectedTimeframe == "ALL" || setup.timeframe == state.selectedTimeframe)
    }
    val symbols = listOf("ALL") + (state.confirmed + state.forming)
        .map { it.symbol }.distinct().sorted()
    val timeframes = listOf("ALL", "1m", "5m", "15m", "30m", "1h", "4h", "1d")

    PremiumScreenBackground {
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(horizontal = 14.dp),
            contentPadding = PaddingValues(vertical = 14.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            item {
                PremiumSectionHeader(
                    title = t("Trading Setups", "ستاپ‌های معاملاتی"),
                    subtitle = t(
                        "Confirmed and forming SMC/ICT setups across 10 symbols and 7 timeframes.",
                        "ستاپ‌های تأییدشده و درحال‌تشکیل SMC/ICT در ۱۰ نماد و ۷ تایم‌فریم.",
                    ),
                )
            }
            item {
                PremiumGlassCard(borderColor = SetupGold.copy(alpha = 0.35f)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween,
                    ) {
                        Column {
                            Text(
                                t("Live Setup Scanner", "اسکنر زنده ستاپ"),
                                color = Color.White,
                                style = MaterialTheme.typography.titleLarge,
                                fontWeight = FontWeight.Bold,
                            )
                            Text(
                                "${state.totalScanned}/70 • ${if (state.cached) t("Cached", "کش‌شده") else t("Live", "زنده")}",
                                color = SetupBlue,
                            )
                        }
                        IconButton(
                            onClick = { viewModel.load(force = true) },
                            enabled = !state.loading,
                        ) {
                            Icon(Icons.Default.Refresh, contentDescription = "refresh", tint = SetupGold)
                        }
                    }
                    Text(
                        t(
                            "Only real detected setups are listed. An empty list means no valid setup is present.",
                            "فقط ستاپ‌های واقعاً تشکیل‌شده نمایش داده می‌شوند؛ لیست خالی یعنی ستاپ معتبری وجود ندارد.",
                        ),
                        color = Color(0xFFFFD27A),
                    )
                }
            }
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(7.dp),
                ) {
                    StatusButton(
                        text = t("Confirmed", "تأییدشده") + " ${state.confirmed.size}",
                        selected = state.selectedStatus == "confirmed",
                        modifier = Modifier.weight(1f),
                    ) { viewModel.selectStatus("confirmed") }
                    StatusButton(
                        text = t("Forming", "درحال تشکیل") + " ${state.forming.size}",
                        selected = state.selectedStatus == "forming",
                        modifier = Modifier.weight(1f),
                    ) { viewModel.selectStatus("forming") }
                    StatusButton(
                        text = t("Invalid", "باطل") + " ${state.invalidated.size}",
                        selected = state.selectedStatus == "invalidated",
                        modifier = Modifier.weight(1f),
                    ) { viewModel.selectStatus("invalidated") }
                }
            }
            item {
                FilterRow(
                    title = t("Symbol", "نماد"),
                    options = symbols,
                    selected = state.selectedSymbol,
                    allLabel = t("All", "همه"),
                    onSelect = viewModel::selectSymbol,
                )
            }
            item {
                FilterRow(
                    title = t("Timeframe", "تایم‌فریم"),
                    options = timeframes,
                    selected = state.selectedTimeframe,
                    allLabel = t("All", "همه"),
                    onSelect = viewModel::selectTimeframe,
                )
            }

            if (state.loading) {
                item {
                    Box(
                        modifier = Modifier.fillMaxWidth().height(180.dp),
                        contentAlignment = Alignment.Center,
                    ) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            CircularProgressIndicator(color = SetupGold)
                            Spacer(Modifier.height(12.dp))
                            Text(
                                t(
                                    "Scanning 70 symbol/timeframe combinations...",
                                    "در حال بررسی ۷۰ ترکیب نماد و تایم‌فریم...",
                                ),
                                color = Color.White,
                            )
                        }
                    }
                }
            } else if (state.error != null) {
                item {
                    PremiumGlassCard(borderColor = SetupRed.copy(alpha = 0.5f)) {
                        Text(t("Scanner error", "خطای اسکنر"), color = SetupRed, fontWeight = FontWeight.Bold)
                        Text(state.error.orEmpty(), color = Color.White)
                        Button(onClick = { viewModel.load(force = false) }) {
                            Text(t("Retry", "تلاش دوباره"))
                        }
                    }
                }
            } else if (filtered.isEmpty()) {
                item {
                    PremiumGlassCard {
                        Text(
                            when (state.selectedStatus) {
                                "confirmed" -> t(
                                    "No confirmed setup right now. Do not force a trade.",
                                    "در حال حاضر ستاپ تأییدشده‌ای وجود ندارد؛ معامله را اجبار نکنید.",
                                )
                                "forming" -> t(
                                    "No setup is currently forming.",
                                    "در حال حاضر ستاپی در حال تشکیل نیست.",
                                )
                                else -> t("No invalidated setup.", "ستاپ باطل‌شده‌ای وجود ندارد.")
                            },
                            color = SetupMuted,
                            style = MaterialTheme.typography.titleMedium,
                        )
                    }
                }
            } else {
                items(filtered, key = { it.id }) { setup ->
                    TradeSetupCard(setup = setup, onOpenChart = {
                        onOpenChart(setup.symbol, setup.market, setup.timeframe)
                    })
                }
            }
            item { Spacer(Modifier.height(18.dp)) }
        }
    }
}

@Composable
private fun TradeSetupCard(setup: TradeSetupDto, onOpenChart: () -> Unit) {
    val directionColor = if (setup.direction == "long") SetupGreen else SetupRed
    val directionLabel = if (setup.direction == "long") "LONG • خرید" else "SHORT • فروش"
    Card(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onOpenChart),
        colors = CardDefaults.cardColors(containerColor = SetupSurface),
        shape = RoundedCornerShape(16.dp),
        border = BorderStroke(
            1.dp,
            (if (setup.status == "confirmed") SetupGold else directionColor).copy(alpha = 0.45f),
        ),
    ) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column {
                    Text(setup.symbol, color = Color.White, fontWeight = FontWeight.Black, style = MaterialTheme.typography.titleLarge)
                    Text("${setup.timeframe} • ${setup.market.uppercase()} • ${setup.setupFamily}", color = SetupMuted)
                }
                Surface(
                    color = directionColor.copy(alpha = 0.17f),
                    shape = RoundedCornerShape(8.dp),
                ) {
                    Text(
                        directionLabel,
                        color = directionColor,
                        fontWeight = FontWeight.Black,
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 7.dp),
                    )
                }
            }
            Text(setup.setupType, color = SetupGold, fontWeight = FontWeight.Bold)
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                SetupChip("Grade ${setup.grade}", SetupGold)
                SetupChip("Conf ${setup.confluence}", SetupBlue)
                SetupChip("Est %${setup.probability}", directionColor)
                SetupChip("RR 1:${"%.1f".format(setup.rr)}", SetupGreen)
            }
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                SetupChip("Q ${"%.0f".format(setup.dataQuality.score)}", SetupBlue)
                SetupChip(setup.marketRegime.name.uppercase(), SetupGold)
                SetupChip(
                    "Gates ${setup.decision.hardGatesPassed}/${setup.decision.hardGatesTotal}",
                    if (setup.decision.strictOmegaCompliant) SetupGreen else SetupRed,
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                PriceBox("Entry", setup.entry, SetupGold, Modifier.weight(1f))
                PriceBox("Safe SL", setup.stopLoss, SetupRed, Modifier.weight(1f))
                PriceBox("TP1", setup.tp1, SetupGreen, Modifier.weight(1f))
            }
            if (setup.status == "forming" && setup.missingConfirmations.isNotEmpty()) {
                Text(
                    "نیاز به تأیید: ${setup.missingConfirmations.joinToString(" • ")}",
                    color = Color(0xFFFFD27A),
                    style = MaterialTheme.typography.bodySmall,
                )
            }
            if (setup.factors.isNotEmpty()) {
                Text(
                    setup.factors.take(3).joinToString(" • "),
                    color = Color(0xFFBCEEFF),
                    style = MaterialTheme.typography.bodySmall,
                )
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.End,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(Icons.Default.ShowChart, contentDescription = null, tint = SetupBlue)
                Text("  مشاهده روی چارت زنده", color = SetupBlue, fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Composable
private fun FilterRow(
    title: String,
    options: List<String>,
    selected: String,
    allLabel: String,
    onSelect: (String) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(title, color = SetupMuted, fontWeight = FontWeight.Bold)
        CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Ltr) {
            LazyRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                items(options) { option ->
                    val isSelected = option == selected
                    Surface(
                        color = if (isSelected) SetupGold else SetupSurface,
                        shape = RoundedCornerShape(9.dp),
                        modifier = Modifier.clickable { onSelect(option) },
                    ) {
                        Text(
                            if (option == "ALL") allLabel else option,
                            color = if (isSelected) Color.Black else Color.White,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(horizontal = 13.dp, vertical = 8.dp),
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun StatusButton(text: String, selected: Boolean, modifier: Modifier, onClick: () -> Unit) {
    if (selected) {
        Button(onClick = onClick, modifier = modifier) { Text(text) }
    } else {
        OutlinedButton(onClick = onClick, modifier = modifier) { Text(text) }
    }
}

@Composable
private fun SetupChip(text: String, color: Color) {
    Box(
        modifier = Modifier
            .background(color.copy(alpha = 0.14f), RoundedCornerShape(50))
            .padding(horizontal = 8.dp, vertical = 5.dp),
    ) {
        Text(text, color = color, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun PriceBox(label: String, value: Float?, color: Color, modifier: Modifier) {
    Box(
        modifier = modifier.background(Color(0xFF101622), RoundedCornerShape(10.dp)).padding(9.dp),
    ) {
        Column {
            Text(label, color = SetupMuted, style = MaterialTheme.typography.bodySmall)
            Text(
                value?.let { formatSetupPrice(it) } ?: "-",
                color = color,
                fontWeight = FontWeight.Bold,
            )
        }
    }
}

private fun formatSetupPrice(value: Float): String = when {
    value >= 1000f -> "%.2f".format(value)
    value >= 100f -> "%.3f".format(value)
    else -> "%.5f".format(value)
}
