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
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.arena.smartmoney.ui.components.PremiumGlassCard
import com.arena.smartmoney.ui.components.PremiumScreenBackground
import com.arena.smartmoney.ui.components.PremiumSectionHeader
import com.arena.smartmoney.ui.i18n.localizeBackendStatus
import com.arena.smartmoney.ui.i18n.localizeMarketQuality
import com.arena.smartmoney.ui.i18n.localizeSessionName
import com.arena.smartmoney.ui.i18n.rememberTranslator
import java.time.Duration
import java.time.LocalTime
import java.time.ZoneId
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import java.util.Locale
import kotlin.math.abs

@Composable
fun DashboardScreen(
    onOpenBacktest: () -> Unit,
    onOpenAnalytics: () -> Unit,
    onOpenMarketAnalysis: () -> Unit,
    viewModel: DashboardViewModel = viewModel()
) {
    val state by viewModel.uiState.collectAsState()
    val t = rememberTranslator()
    val liquidityTimezone = remember { mutableStateOf("tehran") }

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
    val strongestMove = abs(strongestSymbol?.change_pct ?: 0.0)
    val streamInFallbackMode = state.streamStatus.contains("404") || state.streamStatus.contains("error", ignoreCase = true)
    val missingForexFeeds = listToShow.any { it.status == "missing_api_key" }
    val stats = state.tradeStats

    val focusHealth = when {
        state.sessionScore >= 8.0 && strongestMove >= 0.75 && !streamInFallbackMode -> t("Elite", "ممتاز")
        state.sessionScore >= 6.5 && strongestMove >= 0.35 -> t("Strong", "قوی")
        state.sessionScore >= 5.0 -> t("Developing", "در حال شکل‌گیری")
        else -> t("Weak", "ضعیف")
    }

    val liquidityFilter = buildLiquidityTimeFilter(timezoneMode = liquidityTimezone.value, t = t)

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

    PremiumScreenBackground {
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
                            text = t("Mission Control", "مرکز عملیات"),
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
                        LiquidityTimeFilterBox(model = liquidityFilter, t = t)
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            InfoChip(t("Session", "سشن"), localizeSessionName(state.sessionName, t))
                            InfoChip(t("Quality", "کیفیت"), localizeMarketQuality(state.marketQuality, t))
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
                PremiumGlassCard(borderColor = Color(0x40FFC857)) {
                    Text(t("Market Focus Board", "برد تمرکز بازار"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
                    Text(
                        strongestSymbol?.let {
                            t(
                                "Highest active displacement is coming from ${it.symbol} with ${String.format(Locale.US, "%.2f", it.change_pct ?: 0.0)}% movement.",
                                "بیشترین جابه‌جایی فعال فعلاً از ${it.symbol} با حرکت ${String.format(Locale.US, "%.2f", it.change_pct ?: 0.0)}٪ می‌آید."
                            )
                        } ?: t(
                            "Focus board is waiting for fresh market movement data.",
                            "برد تمرکز بازار منتظر داده تازه برای تشخیص حرکت است."
                        ),
                        color = Color(0xFFE7FAFF)
                    )
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        FocusChip(t("Health", "سلامت"), focusHealth, Modifier.weight(1f))
                        FocusChip(t("Stream", "استریم"), if (streamInFallbackMode) t("Fallback", "جایگزین") else t("Realtime", "لحظه‌ای"), Modifier.weight(1f))
                        FocusChip(t("Forex", "فارکس"), if (missingForexFeeds) t("Limited", "محدود") else t("Ready", "آماده"), Modifier.weight(1f))
                    }
                }
            }

            item {
                PremiumGlassCard(borderColor = Color(0x4059C7FF)) {
                    Text(t("Smart Alerts Pro", "اسمارت الرتس پرو"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        FocusChip(t("Scalp", "اسکالپ"), if (state.sessionScore >= 8.0 && strongestMove >= 0.75 && !streamInFallbackMode) t("Armed", "مسلح") else t("Standby", "آماده‌باش"), Modifier.weight(1f))
                        FocusChip(t("Intraday", "درون‌روزی"), if (state.sessionScore >= 6.5 && strongestMove >= 0.35) t("Armed", "مسلح") else t("Standby", "آماده‌باش"), Modifier.weight(1f))
                        FocusChip(t("Macro", "ماکرو"), if (strongestMove >= 1.0 || missingForexFeeds) t("Armed", "مسلح") else t("Standby", "آماده‌باش"), Modifier.weight(1f))
                    }
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
    ActionCard(
        modifier = Modifier.fillMaxWidth(),
        title = t("Market Analysis Pro", "تحلیل بازار حرفه‌ای"),
        subtitle = t("Open the dedicated precision workspace", "ورود به فضای اختصاصی تحلیل دقیق بازار"),
        accent = listOf(Color(0xFF7A5CFF), Color(0xFF3BE7FF)),
        onClick = onOpenMarketAnalysis
    )
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
                                text = t("Live price", "قیمت لحظه‌ای") + ": ${it.last_price ?: "-"} • 24h: ${it.change_pct ?: "-"}% • ${localizeBackendStatus(it.status, t)}",
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
private fun MissionControlBoard(
    missionStatus: String,
    commandPriority: String,
    executionClimate: String,
    t: (String, String) -> String,
) {
    PremiumGlassCard(borderColor = Color(0x40FFC857)) {
        Text(t("Mission Control Board", "برد مرکز عملیات"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FocusChip(t("Status", "وضعیت"), missionStatus, Modifier.weight(1f))
            FocusChip(t("Priority", "اولویت"), commandPriority, Modifier.weight(1f))
            FocusChip(t("Climate", "فضای اجرا"), executionClimate, Modifier.weight(1f))
        }
    }
}

@Composable
private fun SupremeLayerBoard(
    supremeState: String,
    pulseState: String,
    allocationBias: String,
    t: (String, String) -> String,
) {
    PremiumGlassCard(borderColor = Color(0x4059C7FF)) {
        Text(t("Supreme Control Layer", "لایه کنترل برتر"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FocusChip(t("Supreme", "برتر"), supremeState, Modifier.weight(1f))
            FocusChip(t("Pulse", "پالس"), pulseState, Modifier.weight(1f))
            FocusChip(t("Bias", "سوگیری"), allocationBias, Modifier.weight(1f))
        }
    }
}

@Composable
private fun PortfolioBoard(
    cryptoAssets: Int,
    forexAssets: Int,
    risingAssets: Int,
    fallingAssets: Int,
    neutralAssets: Int,
    portfolioHealth: String,
    riskPressure: String,
    breadthHealth: String,
    t: (String, String) -> String,
) {
    PremiumGlassCard(borderColor = Color(0x4033E6A6)) {
        Text(t("Portfolio Command", "فرماندهی پرتفوی"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FocusChip(t("Health", "سلامت"), portfolioHealth, Modifier.weight(1f))
            FocusChip(t("Risk", "ریسک"), riskPressure, Modifier.weight(1f))
            FocusChip(t("Breadth", "پهنای بازار"), breadthHealth, Modifier.weight(1f))
        }
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FocusChip(t("Crypto", "کریپتو"), cryptoAssets.toString(), Modifier.weight(1f))
            FocusChip(t("Forex", "فارکس"), forexAssets.toString(), Modifier.weight(1f))
            FocusChip(t("R/F/N", "ص/ن/خ"), "$risingAssets/$fallingAssets/$neutralAssets", Modifier.weight(1f))
        }
    }
}

@Composable
private fun SmartAlertsBoard(
    scalpAlert: String,
    intradayAlert: String,
    macroAlert: String,
    t: (String, String) -> String,
) {
    PremiumGlassCard(borderColor = Color(0x4059C7FF)) {
        Text(t("Smart Alerts Pro", "اسمارت الرتس پرو"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FocusChip(t("Scalp", "اسکالپ"), scalpAlert, Modifier.weight(1f))
            FocusChip(t("Intraday", "درون‌روزی"), intradayAlert, Modifier.weight(1f))
            FocusChip(t("Macro", "ماکرو"), macroAlert, Modifier.weight(1f))
        }
    }
}

private data class LiquidityWindowSlot(
    val title: String,
    val priority: Int,
    val start: ZonedDateTime,
    val end: ZonedDateTime,
)

private data class LiquidityTimeFilterModel(
    val currentLabel: String,
    val primeRange: String,
    val nextRange: String,
    val guidance: String,
)

@Composable
private fun LiquidityTimeFilterBox(
    model: LiquidityTimeFilterModel,
    t: (String, String) -> String,
) {
    PremiumGlassCard(borderColor = Color(0x40FFC857)) {
        Text(
            t("Liquidity Time Filter", "فیلتر زمانی نقدینگی"),
            style = MaterialTheme.typography.titleMedium,
            color = Color.White,
            fontWeight = FontWeight.Bold
        )
        Text(model.guidance, color = Color(0xFFDDF8FF))
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FocusChip(t("Now", "الان"), model.currentLabel, Modifier.weight(1f))
            FocusChip(t("Prime Window", "اوج نقدینگی"), model.primeRange, Modifier.weight(1f))
            FocusChip(t("Next Window", "پنجره بعدی"), model.nextRange, Modifier.weight(1f))
        }
    }
}

private fun buildLiquidityTimeFilter(t: (String, String) -> String): LiquidityTimeFilterModel {
    val displayZone = if (timezoneMode == "utc") ZoneId.of("UTC") else ZoneId.of("Asia/Tehran")
    val now = ZonedDateTime.now(displayZone)
    val formatter = DateTimeFormatter.ofPattern("HH:mm", Locale.US)

    fun buildWindow(
        zoneId: String,
        titleEn: String,
        titleFa: String,
        startHour: Int,
        startMinute: Int,
        endHour: Int,
        endMinute: Int,
        priority: Int,
    ): LiquidityWindowSlot {
        val sourceNow = now.withZoneSameInstant(ZoneId.of(zoneId))
        var startSource = sourceNow.with(LocalTime.of(startHour, startMinute)).withSecond(0).withNano(0)
        var endSource = sourceNow.with(LocalTime.of(endHour, endMinute)).withSecond(0).withNano(0)
        if (!endSource.isAfter(startSource)) endSource = endSource.plusDays(1)
        return LiquidityWindowSlot(
            title = t(titleEn, titleFa),
            priority = priority,
            start = startSource.withZoneSameInstant(displayZone),
            end = endSource.withZoneSameInstant(displayZone),
        )
    }

    val windows = listOf(
        buildWindow(
            zoneId = "Europe/London",
            titleEn = "London Open Drive",
            titleFa = "موج آغاز لندن",
            startHour = 8,
            startMinute = 0,
            endHour = 10,
            endMinute = 30,
            priority = 2,
        ),
        buildWindow(
            zoneId = "America/New_York",
            titleEn = "New York Open Drive",
            titleFa = "موج آغاز نیویورک",
            startHour = 8,
            startMinute = 0,
            endHour = 10,
            endMinute = 30,
            priority = 2,
        ),
        buildWindow(
            zoneId = "America/New_York",
            titleEn = "London-New York Overlap",
            titleFa = "همپوشانی لندن-نیویورک",
            startHour = 8,
            startMinute = 0,
            endHour = 11,
            endMinute = 30,
            priority = 3,
        ),
    )

    val activeWindow = windows
        .filter { !now.isBefore(it.start) && now.isBefore(it.end) }
        .maxByOrNull { it.priority }

    val nextWindow = windows
        .filter { now.isBefore(it.start) }
        .minByOrNull { Duration.between(now, it.start).toMinutes() }
        ?: windows.minByOrNull { it.start }?.let { it.copy(start = it.start.plusDays(1), end = it.end.plusDays(1)) }

    val primeWindow = windows.maxByOrNull { it.priority }

    val currentLabel = when (activeWindow?.priority) {
        3 -> t("Peak liquidity live", "اوج نقدینگی فعال")
        2 -> t("Strong liquidity live", "نقدینگی قوی فعال")
        else -> t("Outside prime liquidity", "خارج از اوج نقدینگی")
    }

    val guidance = when (activeWindow?.priority) {
        3 -> t(
            "Highest liquidity is live now. This is the best window for signal confirmation and fast execution.",
            "بیشترین حجم نقدینگی همین حالا فعال است. این بهترین بازه برای تأیید سیگنال و اجرای سریع است."
        )
        2 -> t(
            "Liquidity is strong now, but the overlap window remains the most powerful time for premium signals.",
            "الان نقدینگی قوی است، اما بازه همپوشانی همچنان قدرتمندترین زمان برای سیگنال‌های ممتاز است."
        )
        else -> t(
            "You are outside the prime liquidity window. Wait for the next institutional wave before trusting aggressive signals.",
            "الان خارج از پنجره اصلی نقدینگی هستی. برای سیگنال‌های تهاجمی بهتر است تا موج بعدی نقدینگی صبر کنی."
        )
    }

    fun formatRange(slot: LiquidityWindowSlot?): String {
        return slot?.let { "${it.title} • ${it.start.format(formatter)}-${it.end.format(formatter)}" } ?: "-"
    }

    return LiquidityTimeFilterModel(
        currentLabel = currentLabel,
        primeRange = formatRange(primeWindow),
        nextRange = formatRange(nextWindow),
        guidance = guidance,
    )
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
private fun FocusChip(label: String, value: String, modifier: Modifier = Modifier) {
    Box(
        modifier = modifier
            .background(
                Brush.linearGradient(listOf(Color(0x2611D9FF), Color(0x2217FFB3))),
                RoundedCornerShape(16.dp)
            )
            .padding(horizontal = 12.dp, vertical = 10.dp)
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            Text(label, color = Color(0xFFBCEEFF), style = MaterialTheme.typography.bodySmall)
            Text(value, color = Color.White, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun StreamChip(title: String, modifier: Modifier = Modifier, onClick: () -> Unit) {
    Button(onClick = onClick, modifier = modifier) {
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
                Text(t("Status", "وضعیت") + ": ${localizeBackendStatus(item.status, t)}", color = Color(0xFF8EDFFF))
            }
            Spacer(Modifier.width(12.dp))
            Column(horizontalAlignment = Alignment.End) {
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

private fun focusHealthLabel(sessionScore: Double, strongestMove: Double, streamFallback: Boolean, t: (String, String) -> String): String {
    return when {
        sessionScore >= 8.0 && strongestMove >= 0.75 && !streamFallback -> t("Elite", "ممتاز")
        sessionScore >= 6.5 && strongestMove >= 0.35 -> t("Strong", "قوی")
        sessionScore >= 5.0 -> t("Developing", "در حال شکل‌گیری")
        else -> t("Weak", "ضعیف")
    }
}

private fun alertStateLabel(isReady: Boolean, t: (String, String) -> String): String {
    return if (isReady) t("Armed", "مسلح") else t("Standby", "آماده‌باش")
}
