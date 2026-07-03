package com.arena.smartmoney.ui.dashboard

import androidx.compose.foundation.background
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
import androidx.compose.foundation.layout.weight
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

    val missingForexFeeds = listToShow.any { it.status == "missing_api_key" }
    val streamInFallbackMode = state.streamStatus.contains("404") || state.streamStatus.contains("error", ignoreCase = true)
    val live = state.liveSnapshot
    val strongestSymbol = listToShow
        .filter { it.change_pct != null }
        .maxByOrNull { kotlin.math.abs(it.change_pct ?: 0.0) }
    val aiSummary = buildString {
        append(
            if (state.sessionScore >= 8.0)
                t("AI sees active market conditions in prime session hours.", "هوش مصنوعی شرایط فعال بازار را در ساعات مهم سشن تشخیص می‌دهد.")
            else
                t("AI sees calmer market conditions; select trades more conservatively.", "هوش مصنوعی شرایط آرام‌تری را در بازار تشخیص می‌دهد؛ انتخاب معامله باید محتاطانه‌تر باشد.")
        )
        strongestSymbol?.let {
            append(" ")
            append(
                t(
                    "Top mover: ${it.symbol} with ${String.format(Locale.US, "%.2f", it.change_pct ?: 0.0)}% move.",
                    "نماد برتر: ${it.symbol} با تغییر ${String.format(Locale.US, "%.2f", it.change_pct ?: 0.0)} درصد."
                )
            )
        }
        if (missingForexFeeds) {
            append(" ")
            append(t("Forex feeds are limited until TwelveData is configured.", "فید فارکس تا زمان تنظیم TwelveData محدود باقی می‌ماند."))
        }
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(
                        brush = Brush.linearGradient(
                            colors = listOf(Color(0xFF091A2F), Color(0xFF0E3150), Color(0xFF102038))
                        ),
                        shape = RoundedCornerShape(24.dp)
                    )
                    .padding(22.dp)
            ) {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("APEX AI", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
                    Text(
                        t("Advanced AI Trading Dashboard", "داشبورد پیشرفته هوش مصنوعی معاملات"),
                        style = MaterialTheme.typography.titleMedium,
                        color = Color(0xFFB9EFFF)
                    )
                    Text(
                        "Created by Amin omidi",
                        style = MaterialTheme.typography.labelLarge,
                        color = Color(0xFF9ADFFF)
                    )
                    Text(
                        aiSummary,
                        style = MaterialTheme.typography.bodyMedium,
                        color = Color(0xFFE5F8FF)
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        MetricChip(t("Session", "سشن"), state.sessionName)
                        MetricChip(t("Quality", "کیفیت"), state.marketQuality)
                        MetricChip(t("Score", "امتیاز"), state.sessionScore.toString())
                    }
                }
            }
        }
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(t("AI Market Pulse", "نبض بازار هوش مصنوعی"), style = MaterialTheme.typography.titleLarge)
                    Text(
                        t(
                            "The dashboard blends session timing, market movement, crypto watchlist behavior, and journal state to help prioritize stronger setups.",
                            "داشبورد با ترکیب زمان سشن، حرکت بازار، رفتار واچ‌لیست کریپتو و وضعیت ژورنال، به اولویت‌بندی ستاپ‌های قوی‌تر کمک می‌کند."
                        )
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.refreshAll() }) {
                            Text(if (state.loading) t("Refreshing...", "در حال بروزرسانی...") else t("Refresh Live Data", "بروزرسانی داده زنده"))
                        }
                        Button(onClick = onOpenBacktest) {
                            Text(t("Backtest Lab", "آزمایشگاه بک‌تست"))
                        }
                        Button(onClick = onOpenAnalytics) {
                            Text(t("Analytics", "آنالیتیکس"))
                        }
                    }
                    state.error?.let {
                        Text(
                            t("Dashboard fallback mode: $it", "حالت پشتیبان داشبورد: $it"),
                            color = MaterialTheme.colorScheme.error
                        )
                    }
                }
            }
        }
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(t("Live Market Stream", "جریان زنده بازار"), style = MaterialTheme.typography.titleLarge)
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.selectStreamSymbol("BTCUSDT") }) { Text("BTC") }
                        Button(onClick = { viewModel.selectStreamSymbol("ETHUSDT") }) { Text("ETH") }
                        Button(onClick = { viewModel.selectStreamSymbol("EURUSD") }) { Text("EURUSD") }
                        Button(onClick = { viewModel.selectStreamSymbol("XAUUSD") }) { Text("XAU") }
                    }
                    Button(onClick = { viewModel.reconnectStream() }) { Text(t("Reconnect Stream", "اتصال مجدد استریم")) }
                    Text(t("Focused Symbol", "نماد متمرکز") + ": ${state.streamSymbol}")
                    Text(
                        if (streamInFallbackMode)
                            t("Realtime websocket is unavailable; REST fallback is active.", "استریم لحظه‌ای در دسترس نیست؛ حالت جایگزین REST فعال است.")
                        else
                            t("Stream connected and updating.", "استریم متصل و در حال بروزرسانی است.")
                    )
                    live?.let {
                        Text(
                            t("Live Price", "قیمت لحظه‌ای") + ": ${it.last_price ?: "-"} • 24h: ${it.change_pct ?: "-"}%",
                            color = when {
                                (it.change_pct ?: 0.0) > 0 -> Color(0xFF2ECC71)
                                (it.change_pct ?: 0.0) < 0 -> Color(0xFFE74C3C)
                                else -> MaterialTheme.colorScheme.onSurface
                            }
                        )
                        it.error?.let { message ->
                            Text(t("Stream detail", "جزئیات استریم") + ": $message", color = MaterialTheme.colorScheme.primary)
                        }
                    }
                }
            }
        }
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(t("Trading Journal Summary", "خلاصه ژورنال معاملات"), style = MaterialTheme.typography.titleLarge)
                    val stats = state.tradeStats
                    Text(t("Total Trades", "کل معاملات") + ": ${stats?.total_trades ?: 0}")
                    Text(t("Open Trades", "معاملات باز") + ": ${stats?.open_trades ?: 0}")
                    Text(t("Closed Trades", "معاملات بسته") + ": ${stats?.closed_trades ?: 0}")
                    Text(t("Wins / Losses", "برد / باخت") + ": ${stats?.wins ?: 0} / ${stats?.losses ?: 0}")
                    Text(t("Win Rate", "نرخ برد") + ": ${stats?.win_rate ?: 0.0}%")
                    Text(t("Net PnL", "سود/زیان خالص") + ": ${stats?.net_pnl ?: 0.0}")
                }
            }
        }
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(t("Professional Risk Rules", "قوانین حرفه‌ای مدیریت ریسک"), style = MaterialTheme.typography.titleLarge)
                    Text("• " + t("Fixed risk per trade", "ریسک ثابت به ازای هر معامله"))
                    Text("• " + t("Daily loss limit", "حد ضرر روزانه"))
                    Text("• " + t("Maximum consecutive losses", "حداکثر ضررهای پیاپی"))
                    Text("• " + t("Maximum simultaneous positions", "حداکثر پوزیشن همزمان"))
                    Text("• " + t("Breakeven and partial TP planning", "برنامه‌ریزی بریک‌اون و تی‌پی پله‌ای"))
                }
            }
        }
        if (missingForexFeeds) {
            item {
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text(t("Forex Feed Notice", "اطلاعیه فید فارکس"), style = MaterialTheme.typography.titleLarge)
                        Text(t("Forex and gold quotes remain limited until a TwelveData API key is configured on the backend.", "تا زمانی که کلید TwelveData در بک‌اند تنظیم نشود، داده‌های فارکس و طلا محدود باقی می‌مانند."))
                    }
                }
            }
        }
        item {
            Text(t("Live Watchlist", "واچ‌لیست زنده"), style = MaterialTheme.typography.titleLarge)
        }

        items(listToShow) { item ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Row(modifier = Modifier.padding(16.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(item.symbol, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                        Text("${item.market.uppercase(Locale.getDefault())} • ${item.source}")
                        Text(t("Status", "وضعیت") + ": ${item.status}")
                    }
                    Spacer(Modifier.width(16.dp))
                    Column {
                        Text(t("Price", "قیمت") + ": ${item.last_price?.toString() ?: "-"}")
                        Text("24h: ${item.change_pct?.toString() ?: "-"}%")
                    }
                }
            }
        }
    }
}

@Composable
private fun MetricChip(label: String, value: String) {
    Box(
        modifier = Modifier
            .background(Color(0x1FFFFFFF), RoundedCornerShape(16.dp))
            .padding(horizontal = 12.dp, vertical = 8.dp)
    ) {
        Column {
            Text(label, color = Color(0xFF9ADFFF), style = MaterialTheme.typography.labelSmall)
            Text(value, color = Color.White, style = MaterialTheme.typography.labelLarge)
        }
    }
}
