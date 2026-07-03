package com.arena.smartmoney.ui.dashboard

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
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
import androidx.compose.material3.Card
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
import com.arena.smartmoney.ui.i18n.rememberTranslator
import java.util.Locale
import kotlin.math.abs

@Composable
fun DashboardScreen(
    onOpenBacktest: () -> Unit,
    onOpenAnalytics: () -> Unit,
    viewModel: DashboardViewModel = viewModel()
) {
    val state by viewModel.uiState.collectAsState()
    val t = rememberTranslator()

    val listToShow = if (state.watchlist.isEmpty()) {
        state.watchlistSymbols.map {
            com.arena.smartmoney.data.model.MarketOverviewItem(
                symbol = it,
                market = if (it.endsWith("USDT")) "crypto" else "forex",
                last_price = null,
                change_pct = null,
                source = "offline",
                status = "waiting_for_backend"
            )
        }
    } else state.watchlist

    val strongestSymbol = listToShow.filter { it.change_pct != null }.maxByOrNull { abs(it.change_pct ?: 0.0) }
    val streamInFallbackMode = state.streamStatus.contains("404") || state.streamStatus.contains("error", ignoreCase = true)
    val missingForexFeeds = listToShow.any { it.status == "missing_api_key" }
    val stats = state.tradeStats

    val aiSummary = buildString {
        append(
            if (state.sessionScore >= 8.0) {
                t(
                    "AI market engine sees strong session quality and active movement.",
                    "موتور هوش مصنوعی کیفیت خوب سشن و حرکت فعال بازار را تشخیص می‌دهد."
                )
            } else {
                t(
                    "AI market engine sees moderate conditions; be more selective.",
                    "موتور هوش مصنوعی شرایط متوسط بازار را تشخیص می‌دهد؛ انتخاب معامله باید گزینشی‌تر باشد."
                )
            }
        )
        strongestSymbol?.let {
            append(" ")
            append(
                t(
                    "Focus symbol: ${it.symbol} (${String.format(Locale.US, "%.2f", it.change_pct ?: 0.0)}%).",
                    "نماد مهم فعلی: ${it.symbol} (${String.format(Locale.US, "%.2f", it.change_pct ?: 0.0)}%)."
                )
            )
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    listOf(
                        Color(0xFF050B14),
                        Color(0xFF08131F),
                        Color(0xFF0B1D2B),
                        Color(0xFF050B14)
                    )
                )
            )
    ) {
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            item {
                NeonPanel(
                    brush = Brush.linearGradient(
                        listOf(Color(0xFF0B1320), Color(0xFF11263B), Color(0xFF0B1320))
                    )
                ) {
                    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Text(
                            text = "APEX AI PREMIUM",
                            style = MaterialTheme.typography.headlineMedium,
                            color = Color(0xFF67ECFF),
                            fontWeight = FontWeight.ExtraBold
                        )
                        Text(
                            text = t("AI Market Command Center", "مرکز فرمان هوش مصنوعی بازار"),
                            color = Color.White,
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            text = "Created by Amin omidi",
                            color = Color(0xFF9BEFFF),
                            style = MaterialTheme.typography.titleSmall
                        )
                        Text(
                            text = aiSummary,
                            color = Color(0xFFE3F8FF),
                            style = MaterialTheme.typography.bodyMedium
                        )
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            InfoChip(t("Session", "سشن"), state.sessionName)
                            InfoChip(t("Quality", "کیفیت"), state.marketQuality)
                            InfoChip(t("Score", "امتیاز"), String.format(Locale.US, "%.1f", state.sessionScore))
                        }
                    }
                }
            }

            item {
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    MetricCard(
                        modifier = Modifier.weight(1f),
                        title = t("Win Rate", "نرخ برد"),
                        value = "${stats?.win_rate ?: 0.0}%",
                        accent = Color(0xFF33E6A6)
                    )
                    MetricCard(
                        modifier = Modifier.weight(1f),
                        title = t("Open Trades", "معاملات باز"),
                        value = "${stats?.open_trades ?: 0}",
                        accent = Color(0xFF59C7FF)
                    )
                    MetricCard(
                        modifier = Modifier.weight(1f),
                        title = t("Net PnL", "سود خالص"),
                        value = String.format(Locale.US, "%.2f", stats?.net_pnl ?: 0.0),
                        accent = if ((stats?.net_pnl ?: 0.0) >= 0) Color(0xFF67ECFF) else Color(0xFFFF7A7A)
                    )
                }
            }

            item {
                Text(
                    text = t("Premium AI Modules", "ماژول‌های پرمیوم هوش مصنوعی"),
                    style = MaterialTheme.typography.titleLarge,
                    color = Color.White,
                    fontWeight = FontWeight.Bold
                )
            }

            item {
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    ActionCard(
                        modifier = Modifier.weight(1f),
                        title = t("Backtest Lab", "آزمایشگاه بک‌تست"),
                        subtitle = t("Validate setup quality", "اعتبارسنجی کیفیت ستاپ"),
                        accent = listOf(Color(0xFF1B7CFF), Color(0xFF33D6FF)),
                        onClick = onOpenBacktest
                    )
                    ActionCard(
                        modifier = Modifier.weight(1f),
                        title = t("Analytics Center", "مرکز آنالیتیکس"),
                        subtitle = t("Review signal performance", "بررسی عملکرد سیگنال‌ها"),
                        accent = listOf(Color(0xFF00C78C), Color(0xFF67ECFF)),
                        onClick = onOpenAnalytics
                    )
                }
            }

            item {
                NeonPanel(
                    brush = Brush.linearGradient(
                        listOf(Color(0xFF111A29), Color(0xFF13263A), Color(0xFF111A29))
                    )
                ) {
                    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Text(
                            text = t("Live Market Stream", "استریم زنده بازار"),
                            style = MaterialTheme.typography.titleLarge,
                            color = Color.White,
                            fontWeight = FontWeight.Bold
                        )
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            StreamChip("BTC", onClick = { viewModel.selectStreamSymbol("BTCUSDT") })
                            StreamChip("ETH", onClick = { viewModel.selectStreamSymbol("ETHUSDT") })
                            StreamChip("EURUSD", onClick = { viewModel.selectStreamSymbol("EURUSD") })
                            StreamChip("XAU", onClick = { viewModel.selectStreamSymbol("XAUUSD") })
                        }
                        Button(onClick = { viewModel.reconnectStream() }, modifier = Modifier.fillMaxWidth()) {
                            Text(t("Reconnect Live Feed", "اتصال مجدد فید زنده"))
                        }
                        Text(
                            text = t("Focused symbol", "نماد انتخابی") + ": ${state.streamSymbol}",
                            color = Color(0xFFB9F3FF)
                        )
                        Text(
                            text = if (streamInFallbackMode) {
                                t(
                                    "Realtime websocket is unavailable right now. REST fallback is keeping the dashboard live.",
                                    "فعلاً وب‌سوکت لحظه‌ای در دسترس نیست اما حالت جایگزین REST داشبورد را زنده نگه داشته است."
                                )
                            } else {
                                t(
                                    "Realtime stream is connected and feeding the dashboard.",
                                    "استریم لحظه‌ای متصل است و داده را به داشبورد می‌رساند."
                                )
                            },
                            color = if (streamInFallbackMode) Color(0xFFFFD27A) else Color(0xFF67ECFF)
                        )
                        state.liveSnapshot?.let {
                            Text(
                                text = t("Live price", "قیمت لحظه‌ای") + ": ${it.last_price ?: "-"} • 24h: ${it.change_pct ?: "-"}%",
                                color = when {
                                    (it.change_pct ?: 0.0) > 0 -> Color(0xFF33E6A6)
                                    (it.change_pct ?: 0.0) < 0 -> Color(0xFFFF7A7A)
                                    else -> Color.White
                                },
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }
            }

            if (missingForexFeeds) {
                item {
                    NeonPanel(
                        brush = Brush.linearGradient(
                            listOf(Color(0xFF241915), Color(0xFF322216), Color(0xFF241915))
                        ),
                        borderColor = Color(0x55FFB657)
                    ) {
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text(
                                text = t("Forex Feed Notice", "هشدار فید فارکس"),
                                color = Color(0xFFFFD27A),
                                fontWeight = FontWeight.Bold,
                                style = MaterialTheme.typography.titleMedium
                            )
                            Text(
                                text = t(
                                    "Forex and gold remain limited until TwelveData API key is configured on the backend.",
                                    "داده فارکس و طلا تا زمان تنظیم کلید TwelveData روی بک‌اند محدود باقی می‌ماند."
                                ),
                                color = Color.White
                            )
                        }
                    }
                }
            }

            item {
                Text(
                    text = t("Live Watchlist", "واچ‌لیست زنده"),
                    style = MaterialTheme.typography.titleLarge,
                    color = Color.White,
                    fontWeight = FontWeight.Bold
                )
            }

            items(listToShow) { item ->
                WatchlistCard(item = item, t = t)
            }
        }
    }
}

@Composable
private fun NeonPanel(
    brush: Brush,
    borderColor: Color = Color(0x4037E6FF),
    content: @Composable () -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .background(brush, RoundedCornerShape(28.dp))
            .border(1.dp, borderColor, RoundedCornerShape(28.dp))
            .padding(18.dp)
    ) {
        content()
    }
}

@Composable
private fun MetricCard(
    modifier: Modifier = Modifier,
    title: String,
    value: String,
    accent: Color
) {
    Box(
        modifier = modifier
            .background(Color(0xCC0E1724), RoundedCornerShape(22.dp))
            .border(1.dp, accent.copy(alpha = 0.35f), RoundedCornerShape(22.dp))
            .padding(vertical = 16.dp, horizontal = 12.dp)
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(title, color = Color(0xFFBEEFFF), style = MaterialTheme.typography.labelLarge)
            Text(value, color = accent, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.ExtraBold)
        }
    }
}

@Composable
private fun ActionCard(
    modifier: Modifier = Modifier,
    title: String,
    subtitle: String,
    accent: List<Color>,
    onClick: () -> Unit
) {
    Box(
        modifier = modifier
            .background(Brush.linearGradient(accent), RoundedCornerShape(24.dp))
            .padding(1.dp)
    ) {
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .clickable(onClick = onClick),
            shape = RoundedCornerShape(24.dp)
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(Color(0xFF0B1320))
                    .padding(16.dp)
            ) {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(title, color = Color.White, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                    Text(subtitle, color = Color(0xFFBEEFFF), style = MaterialTheme.typography.bodyMedium)
                }
            }
        }
    }
}

@Composable
private fun InfoChip(label: String, value: String) {
    Box(
        modifier = Modifier
            .background(Color(0x3318D7F0), RoundedCornerShape(18.dp))
            .border(1.dp, Color(0x4437E6FF), RoundedCornerShape(18.dp))
            .padding(horizontal = 12.dp, vertical = 8.dp)
    ) {
        Column {
            Text(label, color = Color(0xFF92EFFF), style = MaterialTheme.typography.labelSmall)
            Text(value, color = Color.White, style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun StreamChip(title: String, onClick: () -> Unit) {
    Button(onClick = onClick) {
        Text(title)
    }
}

@Composable
private fun WatchlistCard(
    item: com.arena.smartmoney.data.model.MarketOverviewItem,
    t: (String, String) -> String
) {
    val accent = when {
        (item.change_pct ?: 0.0) > 0 -> Color(0xFF33E6A6)
        (item.change_pct ?: 0.0) < 0 -> Color(0xFFFF7A7A)
        else -> Color(0xFF59C7FF)
    }

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .background(Color(0xCC0E1724), RoundedCornerShape(24.dp))
            .border(1.dp, accent.copy(alpha = 0.35f), RoundedCornerShape(24.dp))
            .padding(16.dp)
    ) {
        Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.weight(1f)) {
                Text(item.symbol, color = Color.White, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(4.dp))
                Text("${item.market.uppercase(Locale.getDefault())} • ${item.source}", color = Color(0xFFBEEFFF))
                Text(t("Status", "وضعیت") + ": ${item.status}", color = Color(0xFF8EDFFF))
            }
            Spacer(Modifier.width(12.dp))
            Column(horizontalAlignment = androidx.compose.ui.Alignment.End) {
                Text(
                    t("Price", "قیمت") + ": ${item.last_price?.toString() ?: "-"}",
                    color = Color.White,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    "24h: ${item.change_pct?.toString() ?: "-"}%",
                    color = accent,
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}
