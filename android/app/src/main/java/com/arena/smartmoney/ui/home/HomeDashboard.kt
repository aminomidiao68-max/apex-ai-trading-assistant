package com.arena.smartmoney.ui.home

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.arena.smartmoney.ui.aichat.AIChatScreen
import com.arena.smartmoney.ui.analytics.AnalyticsScreen
import com.arena.smartmoney.ui.analyze.AnalyzeScreen
import com.arena.smartmoney.ui.backtest.BacktestScreen
import com.arena.smartmoney.ui.broker.BrokerScreen
import com.arena.smartmoney.ui.chart.ChartScreen
import com.arena.smartmoney.ui.journal.JournalScreen
import com.arena.smartmoney.ui.news.NewsScreen
import com.arena.smartmoney.ui.readiness.ReadinessScreen
import com.arena.smartmoney.ui.risk.RiskCalculatorScreen
import com.arena.smartmoney.ui.setups.TradeSetupsScreen
import com.arena.smartmoney.ui.theme.CardBg
import com.arena.smartmoney.ui.theme.CyanAccent
import com.arena.smartmoney.ui.theme.DarkBg
import com.arena.smartmoney.ui.theme.SoftText
import java.time.DayOfWeek
import java.time.ZonedDateTime
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter

enum class HomeModule(val emoji: String, val en: String, val fa: String) {
    ANALYZE("🎯", "Analyze", "آنالیز نهادی"),
    CHAT("💬", "AI Chat", "چت هوشمند"),
    CHART("📈", "Charts", "چارت زنده"),
    SETUPS("🧩", "Setups", "ستاپ‌ها"),
    RISK("🧮", "Calc & Risk", "ماشین‌حساب و ریسک"),
    JOURNAL("📔", "Journal", "ژورنال معاملات"),
    NEWS("📰", "News Impact", "اخبار و اثر بازار"),
    SESSIONS("🕘", "Sessions", "سشن‌ها و کیل‌زون"),
    FORWARD("🧪", "Forward-Test", "آزمون واقعی دقت"),
    ANALYTICS("📊", "Analytics", "آنالیتیکس"),
    BACKTEST("🔄", "Backtest", "بک‌تست"),
    BROKER("🏦", "Broker", "بروکر"),
}

data class SessionInfo(
    val fa: String,
    val en: String,
    val killzone: Boolean,
    val weekend: Boolean,
)

fun sessionInfo(now: ZonedDateTime): SessionInfo {
    val h = now.hour
    return when {
        now.dayOfWeek == DayOfWeek.SATURDAY || now.dayOfWeek == DayOfWeek.SUNDAY ->
            SessionInfo("تعطیلی آخر هفته — وتوی نقدینگی", "Weekend — liquidity veto", false, true)
        h in 0..6 -> SessionInfo("سشن آسیا (سیدنی/توکیو)", "Asia (Sydney/Tokyo)", false, false)
        h in 7..11 -> SessionInfo("سشن لندن", "London", false, false)
        h in 12..15 -> SessionInfo("هم‌پوشانی لندن/نیویورک — کیل‌زون", "London/NY overlap — KILLZONE", true, false)
        h in 16..20 -> SessionInfo("سشن نیویورک", "New York", false, false)
        else -> SessionInfo("پایان نیویورک — نقدینگی کم", "Late NY — thin liquidity", false, false)
    }
}

private val TIME_FMT: DateTimeFormatter = DateTimeFormatter.ofPattern("HH:mm:ss")

@Composable
fun HomeDashboard(
    onOpenSettings: () -> Unit,
    onOpenAbout: () -> Unit,
) {
    var openModule by remember { mutableStateOf<HomeModule?>(null) }
    var chartArgs by remember { mutableStateOf<Triple<String, String, String>?>(null) }
    var menuOpen by remember { mutableStateOf(false) }
    var now by remember { mutableStateOf(ZonedDateTime.now(ZoneOffset.UTC)) }
    LaunchedEffect(Unit) {
        while (true) {
            kotlinx.coroutines.delay(1000)
            now = ZonedDateTime.now(ZoneOffset.UTC)
        }
    }
    val session = sessionInfo(now)

    Box(
        Modifier
            .fillMaxSize()
            .background(Brush.verticalGradient(listOf(Color(0xFF050B16), DarkBg)))
    ) {
        Column(Modifier.fillMaxSize()) {
            // ------------------------------------------------ header + 3-dot
            Row(
                Modifier
                    .fillMaxWidth()
                    .padding(PaddingValues(start = 18.dp, end = 6.dp, top = 14.dp)),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(Modifier.weight(1f)) {
                    Text(
                        "APEX MARKET AI",
                        color = CyanAccent,
                        fontSize = 21.sp,
                        fontWeight = FontWeight.ExtraBold,
                    )
                    Text(
                        "Institutional-grade AI trading companion",
                        color = SoftText.copy(alpha = 0.75f),
                        fontSize = 10.5.sp,
                    )
                }
                Box {
                    IconButton(onClick = { menuOpen = true }) {
                        Icon(
                            Icons.Default.MoreVert,
                            contentDescription = "Menu",
                            tint = SoftText,
                        )
                    }
                    DropdownMenu(expanded = menuOpen, onDismissRequest = { menuOpen = false }) {
                        DropdownMenuItem(
                            text = { Text("تنظیمات / Settings") },
                            onClick = { menuOpen = false; onOpenSettings() },
                        )
                        DropdownMenuItem(
                            text = { Text("درباره برنامه / About") },
                            onClick = { menuOpen = false; onOpenAbout() },
                        )
                    }
                }
            }

            // ------------------------------------------------ market clock
            MarketClockCard(now, session)

            // ------------------------------------------------ one-page modules
            Column(
                Modifier
                    .weight(1f)
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 14.dp, vertical = 10.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                for (rowItems in HomeModule.values().chunked(2)) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        ModuleCard(
                            module = rowItems[0],
                            modifier = Modifier.weight(1f),
                            onClick = { openModule = rowItems[0] },
                        )
                        if (rowItems.size > 1) {
                            ModuleCard(
                                module = rowItems[1],
                                modifier = Modifier.weight(1f),
                                onClick = { openModule = rowItems[1] },
                            )
                        } else {
                            Spacer(Modifier.weight(1f))
                        }
                    }
                }
                Spacer(Modifier.height(18.dp))
            }
        }
    }

    openModule?.let { module ->
        ModuleDialog(
            module = module,
            chartArgs = chartArgs,
            onOpenChart = { s, m, tf -> chartArgs = Triple(s, m, tf) },
            onClearChart = { chartArgs = null },
            onClose = { openModule = null; chartArgs = null },
        )
    }
}

@Composable
private fun MarketClockCard(now: ZonedDateTime, session: SessionInfo) {
    val badgeColor = when {
        session.weekend -> Color(0xFFE85B5B)
        session.killzone -> CyanAccent
        else -> Color(0xFF2E7BFF)
    }
    Column(
        Modifier
            .fillMaxWidth()
            .padding(horizontal = 14.dp, vertical = 6.dp)
            .border(1.dp, badgeColor.copy(alpha = 0.55f), RoundedCornerShape(20.dp))
            .background(Color(0xFF0B1626), RoundedCornerShape(20.dp))
            .padding(16.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(
                    now.format(TIME_FMT) + "  UTC",
                    color = Color.White,
                    fontSize = 30.sp,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    now.dayOfWeek.name.lowercase().replaceFirstChar { it.uppercase() } +
                        " · " + now.toLocalDate().toString(),
                    color = SoftText.copy(alpha = 0.7f),
                    fontSize = 11.sp,
                )
            }
            Text("🌍", fontSize = 30.sp)
        }
        Spacer(Modifier.height(10.dp))
        Row(
            Modifier
                .background(badgeColor.copy(alpha = 0.16f), RoundedCornerShape(12.dp))
                .padding(horizontal = 12.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                if (session.killzone) "🔥 " else if (session.weekend) "⛔ " else "🕘 ",
                fontSize = 15.sp,
            )
            Spacer(Modifier.width(6.dp))
            Column {
                Text(session.fa, color = badgeColor, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                Text(session.en, color = SoftText.copy(alpha = 0.65f), fontSize = 10.sp)
            }
        }
        Spacer(Modifier.height(8.dp))
        Text(
            "کیل‌زون سیگنال‌دهی: هم‌پوشانی لندن/نیویورک 12:00–16:00 UTC · آخر هفته وتو",
            color = SoftText.copy(alpha = 0.6f),
            fontSize = 10.sp,
        )
    }
}

@Composable
private fun ModuleCard(module: HomeModule, modifier: Modifier, onClick: () -> Unit) {
    Column(
        Modifier
            .then(modifier)
            .border(1.dp, Color(0xFF22364F), RoundedCornerShape(18.dp))
            .background(CardBg, RoundedCornerShape(18.dp))
            .clickable(onClick = onClick)
            .padding(14.dp),
    ) {
        Text(module.emoji, fontSize = 24.sp)
        Spacer(Modifier.height(8.dp))
        Text(module.fa, color = Color.White, fontSize = 13.5.sp, fontWeight = FontWeight.Bold)
        Text(module.en, color = SoftText.copy(alpha = 0.6f), fontSize = 10.sp)
    }
}

@Composable
private fun ModuleDialog(
    module: HomeModule,
    chartArgs: Triple<String, String, String>?,
    onOpenChart: (String, String, String) -> Unit,
    onClearChart: () -> Unit,
    onClose: () -> Unit,
) {
    Dialog(onDismissRequest = onClose, properties = DialogProperties(usePlatformDefaultWidth = false)) {
        Box(
            Modifier
                .fillMaxSize()
                .background(DarkBg)
        ) {
            Column(Modifier.fillMaxSize()) {
                Row(
                    Modifier
                        .fillMaxWidth()
                        .padding(PaddingValues(start = 10.dp, end = 10.dp, top = 10.dp)),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        module.emoji + "  " + module.fa,
                        color = CyanAccent,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.weight(1f).padding(PaddingValues(start = 8.dp)),
                    )
                    IconButton(onClick = onClose) {
                        Icon(Icons.Default.Close, contentDescription = "Close", tint = SoftText)
                    }
                }
                Box(Modifier.weight(1f)) {
                    when (module) {
                        HomeModule.ANALYZE -> AnalyzeScreen()
                        HomeModule.CHAT -> AIChatScreen()
                        HomeModule.CHART -> ChartScreen()
                        HomeModule.SETUPS -> {
                            val args = chartArgs
                            if (args != null) {
                                ChartScreen(
                                    onBack = onClearChart,
                                    initialSymbol = args.first,
                                    initialMarket = args.second,
                                    initialTimeframe = args.third,
                                )
                            } else {
                                TradeSetupsScreen(onOpenChart = onOpenChart)
                            }
                        }
                        HomeModule.RISK -> RiskCalculatorScreen()
                        HomeModule.JOURNAL -> JournalScreen()
                        HomeModule.NEWS -> NewsScreen(onBack = onClose)
                        HomeModule.SESSIONS -> SessionsScreen()
                        HomeModule.FORWARD -> ReadinessScreen()
                        HomeModule.ANALYTICS -> AnalyticsScreen()
                        HomeModule.BACKTEST -> BacktestScreen()
                        HomeModule.BROKER -> BrokerScreen()
                    }
                }
            }
        }
    }
}
