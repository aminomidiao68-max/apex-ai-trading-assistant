@file:OptIn(ExperimentalMaterial3Api::class)

package com.arena.smartmoney.ui.dashboard

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.text.SimpleDateFormat
import java.util.*

private val BgDark     = Color(0xFF0B0F14)
private val BgDarkElev = Color(0xFF10151C)
private val CardC      = Color(0xFF161C25)
private val CardDark   = Color(0xFF0E1319)
private val TextHi     = Color(0xFFF2F4F7)
private val TextMid    = Color(0xFF9AA3B2)
private val TextLow    = Color(0xFF5B6472)
private val Gold       = Color(0xFFD4AF37)
private val Green      = Color(0xFF22C55E)
private val Red        = Color(0xFFEF4444)
private val Blue       = Color(0xFF60A5FA)
private val Purple     = Color(0xFFA78BFA)
private val Orange     = Color(0xFFF97316)
private val Amber      = Color(0xFFF59E0B)
private val Teal       = Color(0xFF34D399)
private val Slate      = Color(0xFF94A3B8)

private enum class Tz(val display: String, val zoneId: String) {
    TEHRAN("تهران", "Asia/Tehran"),
    UTC("UTC", "UTC")
}

private enum class Session(val labelFa: String, val startTH: Int, val endTH: Int, val color: Color) {
    ASIA    ("نقدینگی آسیا",      4, 12, Slate),
    LONDON  ("نقدینگی لندن",     12, 17, Blue),
    NY      ("نقدینگی نیویورک",  17, 24, Orange),
    OVERLAP ("هم‌پوشانی طلایی",  16, 19, Gold)
}

private data class Dummy(
    val sym: String, val dir: String, val tf: String,
    val st: String, val tp: String, val sl: String
)

private val SAMPLE_SIGNALS = listOf(
    Dummy("XAUUSD", "LONG",  "15m", "SMC", "2685.00", "2675.00"),
    Dummy("EURUSD", "SHORT", "1H",  "OB",  "1.08000", "1.08650")
)

@Composable
fun DashboardScreen(
    // Signals
    onNavigateToSignals: () -> Unit = {},
    onOpenSignals: () -> Unit = {},
    // Journal
    onNavigateToJournal: () -> Unit = {},
    onOpenJournal: () -> Unit = {},
    // Market analysis / analytics / pro
    onNavigateToMarketAnalysis: () -> Unit = {},
    onOpenMarketAnalysis: () -> Unit = {},
    onNavigateToAnalytics: () -> Unit = {},
    onOpenAnalytics: () -> Unit = {},
    onOpenMarketPro: () -> Unit = {},
    onOpenProAnalysis: () -> Unit = {},
    // Chart
    onNavigateToChart: () -> Unit = {},
    onOpenChart: () -> Unit = {},
    // News
    onNavigateToNews: () -> Unit = {},
    onOpenNews: () -> Unit = {},
    // Backtest
    onNavigateToBacktest: () -> Unit = {},
    onOpenBacktest: () -> Unit = {},
    // Home / dashboard
    onNavigateToDashboard: () -> Unit = {},
    onOpenDashboard: () -> Unit = {},
    onNavigateToHome: () -> Unit = {},
    onOpenHome: () -> Unit = {},
    // Settings / profile (just in case)
    onNavigateToSettings: () -> Unit = {},
    onOpenSettings: () -> Unit = {},
    onNavigateToProfile: () -> Unit = {},
    onOpenProfile: () -> Unit = {}
) {
    val goSignals = {
        onNavigateToSignals(); onOpenSignals()
    }
    val goJournal = {
        onNavigateToJournal(); onOpenJournal()
    }
    val goAnalysis = {
        onNavigateToMarketAnalysis(); onOpenMarketAnalysis()
        onNavigateToAnalytics(); onOpenAnalytics()
        onOpenMarketPro(); onOpenProAnalysis()
    }
    val goChart = {
        onNavigateToChart(); onOpenChart()
    }
    val goNews = {
        onNavigateToNews(); onOpenNews()
    }
    val goBacktest = {
        onNavigateToBacktest(); onOpenBacktest()
    }

    var tz     by rememberSaveable { mutableStateOf(Tz.TEHRAN) }
    var filter by rememberSaveable { mutableStateOf(Session.ASIA) }
    var tzMenu by remember { mutableStateOf(false) }

    val fmt = remember(tz) {
        SimpleDateFormat("HH:mm", Locale.ENGLISH).apply {
            timeZone = TimeZone.getTimeZone(tz.zoneId)
        }
    }

    var clock by remember { mutableStateOf(fmt.format(Date())) }
    LaunchedEffect(tz) {
        while (true) {
            clock = fmt.format(Date())
            kotlinx.coroutines.delay(30_000L)
        }
    }

    val currentSession: Session = run {
        val h = Calendar.getInstance(TimeZone.getTimeZone(tz.zoneId))
            .get(Calendar.HOUR_OF_DAY)
        when {
            h in 16..18 -> Session.OVERLAP
            h in 4..11  -> Session.ASIA
            h in 12..16 -> Session.LONDON
            h in 17..23 -> Session.NY
            else        -> Session.ASIA
        }
    }

    Scaffold(
        containerColor = BgDark,
        topBar = { TopBar(tz, clock) { tzMenu = true } }
    ) { pad ->
        Box {
            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(pad)
                    .background(Brush.verticalGradient(listOf(BgDark, BgDarkElev))),
                contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                // Box 1: Liquidity filter
                item {
                    LiquidityCard(tz = tz, selected = filter, current = currentSession) {
                        filter = it
                    }
                }
                // Box 2: AI summary
                item { SummaryCard(session = currentSession) }
                // Quick actions title
                item { Label("دسترسی سریع") }
                item {
                    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            Tile(
                                label = "تحلیل بازار حرفه‌ای",
                                icon = Icons.Default.Assessment,
                                color = Gold,
                                modifier = Modifier.weight(1f),
                                onClick = goAnalysis
                            )
                            Tile(
                                label = "چارت",
                                icon = Icons.Default.ShowChart,
                                color = Blue,
                                modifier = Modifier.weight(1f),
                                onClick = goChart
                            )
                        }
                        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            Tile(
                                label = "سیگنال‌ها",
                                icon = Icons.Default.Campaign,
                                color = Purple,
                                modifier = Modifier.weight(1f),
                                onClick = goSignals
                            )
                            Tile(
                                label = "اخبار",
                                icon = Icons.Default.Newspaper,
                                color = Amber,
                                modifier = Modifier.weight(1f),
                                onClick = goNews
                            )
                            Tile(
                                label = "ژورنال",
                                icon = Icons.Default.Book,
                                color = Teal,
                                modifier = Modifier.weight(1f),
                                onClick = goJournal
                            )
                        }
                    }
                }
                // Signals
                item { Label("سیگنال‌های زنده") }
                items(SAMPLE_SIGNALS) { s ->
                    SignalCard(s = s, onClick = goChart)
                }
                // Footer branding
                item {
                    Spacer(modifier = Modifier.height(10.dp))
                    Text(
                        text = "Created by\nAmin Omidi",
                        modifier = Modifier.fillMaxWidth(),
                        textAlign = TextAlign.Center,
                        color = TextLow,
                        fontSize = 11.sp,
                        lineHeight = 14.sp,
                        letterSpacing = 1.2.sp
                    )
                    Spacer(modifier = Modifier.height(24.dp))
                }
            }

            DropdownMenu(
                expanded = tzMenu,
                onDismissRequest = { tzMenu = false }
            ) {
                Tz.values().forEach { m ->
                    DropdownMenuItem(
                        text = {
                            Text(
                                text = m.display,
                                color = if (m == tz) Gold else TextHi
                            )
                        },
                        leadingIcon = {
                            Icon(
                                imageVector = if (m == Tz.TEHRAN) Icons.Default.Language
                                              else Icons.Default.Public,
                                contentDescription = m.display,
                                tint = if (m == tz) Gold else TextMid,
                                modifier = Modifier.size(18.dp)
                            )
                        },
                        onClick = {
                            tz = m
                            tzMenu = false
                        }
                    )
                }
            }
        }
    }
}

@Composable
private fun TopBar(tz: Tz, clock: String, onTzClick: () -> Unit) {
    CenterAlignedTopAppBar(
        title = {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(
                    text = "APEX AI",
                    fontWeight = FontWeight.Black,
                    fontSize = 20.sp,
                    color = Gold,
                    letterSpacing = 2.sp
                )
                Text(
                    text = "Trading Assistant",
                    fontSize = 10.sp,
                    color = TextLow,
                    letterSpacing = 3.sp
                )
            }
        },
        actions = {
            Surface(
                modifier = Modifier
                    .clickable(onClick = onTzClick)
                    .padding(end = 12.dp),
                shape = RoundedCornerShape(50),
                color = CardC,
                border = BorderStroke(1.dp, Gold.copy(alpha = 0.35f))
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        Icons.Default.Schedule,
                        contentDescription = null,
                        tint = Gold,
                        modifier = Modifier.size(14.dp)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = "${tz.display} · $clock",
                        color = TextHi,
                        fontSize = 11.sp
                    )
                }
            }
        },
        colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
            containerColor = BgDark,
            titleContentColor = TextHi
        )
    )
}

@Composable
private fun LiquidityCard(
    tz: Tz,
    selected: Session,
    current: Session,
    onSelect: (Session) -> Unit
) {
    ElevatedCard(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.elevatedCardColors(containerColor = CardC),
        elevation = CardDefaults.elevatedCardElevation(defaultElevation = 6.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(10.dp)
                        .background(current.color, CircleShape)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "فیلتر زمانی نقدینگی",
                    fontWeight = FontWeight.Bold,
                    color = TextHi,
                    fontSize = 15.sp
                )
                Spacer(modifier = Modifier.weight(1f))
                Text(
                    text = "جلسه: ${current.labelFa}",
                    fontSize = 11.sp,
                    color = current.color,
                    fontWeight = FontWeight.SemiBold
                )
            }

            Spacer(modifier = Modifier.height(12.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Session.values().forEach { s ->
                    val sel = s == selected
                    FilterChip(
                        selected = sel,
                        onClick = { onSelect(s) },
                        label = {
                            Text(
                                text = s.labelFa,
                                fontSize = 10.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = if (sel) Color.Black else TextHi,
                                maxLines = 1
                            )
                        },
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(12.dp),
                        colors = FilterChipDefaults.filterChipColors(
                            selectedContainerColor = s.color,
                            containerColor = CardDark,
                            selectedLabelColor = Color.Black,
                            labelColor = TextMid
                        )
                    )
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            val windowText = when (tz) {
                Tz.TEHRAN -> {
                    val sh = String.format("%02d:00", selected.startTH)
                    val eh = if (selected.endTH == 24) "00:00"
                             else String.format("%02d:00", selected.endTH)
                    "$sh – $eh"
                }
                Tz.UTC -> {
                    val sh = (selected.startTH - 4 + 24) % 24
                    val eh = (selected.endTH - 4 + 24) % 24
                    val shs = String.format("%02d:00", sh)
                    val ehs = if (eh == 0) "00:00"
                             else String.format("%02d:00", eh)
                    "$shs – $ehs"
                }
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    Icons.Default.AccessTime,
                    contentDescription = null,
                    tint = selected.color,
                    modifier = Modifier.size(14.dp)
                )
                Spacer(modifier = Modifier.width(6.dp))
                Text(
                    text = "بازه (${tz.display}): $windowText",
                    fontSize = 11.sp,
                    color = TextMid
                )
            }
        }
    }
}

@Composable
private fun SummaryCard(session: Session) {
    ElevatedCard(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.elevatedCardColors(containerColor = CardC)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.AutoAwesome, contentDescription = null, tint = Gold)
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "جمع‌بندی هوش مصنوعی",
                    fontWeight = FontWeight.Bold,
                    color = TextHi,
                    fontSize = 15.sp
                )
            }

            Spacer(modifier = Modifier.height(10.dp))

            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(text = "امتیاز روز: ", color = TextMid, fontSize = 13.sp)
                Text(text = "7/10", color = Gold, fontWeight = FontWeight.Black, fontSize = 18.sp)
                Spacer(modifier = Modifier.width(8.dp))
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = Green.copy(alpha = 0.15f)
                ) {
                    Text(
                        text = "BULLISH BIAS",
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp),
                        fontSize = 11.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Green
                    )
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = "روند کلی در جلسهٔ فعلی صعودی است. تمرکز روی نقدینگی سمت فروش و تایید روی تایم‌فریم‌های بالاتر باشد. مدیریت ریسک را رعایت کنید.",
                color = TextHi,
                fontSize = 13.sp,
                lineHeight = 20.sp
            )

            Spacer(modifier = Modifier.height(10.dp))
            HorizontalDivider(color = CardDark)
            Spacer(modifier = Modifier.height(10.dp))

            Text(
                text = "تمرکز پیشنهادی برای جلسهٔ ${session.labelFa}:",
                color = TextMid,
                fontSize = 11.sp,
                fontWeight = FontWeight.SemiBold
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = "ورود فقط در صورت تایید ساختار (BOS/CHoCH) و تشکیل Order Block معتبر. در زمان اخبار پرریسک ورود جدید نگیرید.",
                color = TextHi,
                fontSize = 12.sp,
                lineHeight = 18.sp
            )
        }
    }
}

@Composable
private fun Tile(
    label: String,
    icon: ImageVector,
    color: Color,
    modifier: Modifier = Modifier,
    onClick: () -> Unit
) {
    ElevatedCard(
        modifier = modifier
            .height(82.dp)
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.elevatedCardColors(containerColor = CardC)
    ) {
        Box(
            modifier = Modifier.fillMaxSize(),
            contentAlignment = Alignment.Center
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Icon(
                    imageVector = icon,
                    contentDescription = label,
                    tint = color,
                    modifier = Modifier.size(24.dp)
                )
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = label,
                    color = TextHi,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.SemiBold,
                    textAlign = TextAlign.Center
                )
            }
        }
    }
}

@Composable
private fun SignalCard(s: Dummy, onClick: () -> Unit) {
    val isLong = s.dir.equals("LONG", ignoreCase = true)
    val c = if (isLong) Green else Red

    ElevatedCard(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.elevatedCardColors(containerColor = CardC)
    ) {
        Row(
            modifier = Modifier.padding(14.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(42.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(c.copy(alpha = 0.15f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = if (isLong) Icons.Default.TrendingUp
                                  else Icons.Default.TrendingDown,
                    contentDescription = s.dir,
                    tint = c
                )
            }

            Spacer(modifier = Modifier.width(12.dp))

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = s.sym,
                    color = TextHi,
                    fontWeight = FontWeight.Bold,
                    fontSize = 15.sp
                )
                Text(
                    text = "${s.tf} · ${s.st}",
                    color = TextMid,
                    fontSize = 11.sp
                )
            }

            Column(horizontalAlignment = Alignment.End) {
                Text(
                    text = if (isLong) "LONG" else "SHORT",
                    color = c,
                    fontWeight = FontWeight.Black,
                    fontSize = 12.sp
                )
                Text(
                    text = "TP ${s.tp}  SL ${s.sl}",
                    color = TextLow,
                    fontSize = 10.sp
                )
            }
        }
    }
}

@Composable
private fun Label(text: String) {
    Text(
        text = text,
        color = TextMid,
        fontSize = 12.sp,
        fontWeight = FontWeight.Bold,
        letterSpacing = 1.sp
    )
}
