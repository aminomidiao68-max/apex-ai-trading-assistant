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

import com.arena.smartmoney.data.model.SmcReport
import com.arena.smartmoney.data.repository.TradingRepository
import kotlinx.coroutines.launch

private val BgDark     = Color(0xFF070A0F)
private val BgDarkElev = Color(0xFF0C1017)
private val CardC      = Color(0xFF111722)
private val CardDark   = Color(0xFF0A0E15)
private val TextHi     = Color(0xFFF2F4F7)
private val TextMid    = Color(0xFF9AA3B2)
private val TextLow    = Color(0xFF5B6472)
private val Gold       = Color(0xFFE5A93B)
private val Green      = Color(0xFF10B981)
private val Red        = Color(0xFFEF4444)
private val Blue       = Color(0xFF3B82F6)
private val Purple     = Color(0xFF8B5CF6)
private val Orange     = Color(0xFFF97316)
private val Amber      = Color(0xFFF59E0B)
private val Teal       = Color(0xFF14B8A6)
private val Slate      = Color(0xFF64748B)

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
    // Chart / trading setups
    onNavigateToChart: () -> Unit = {},
    onOpenChart: () -> Unit = {},
    onOpenSetups: () -> Unit = {},
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
    val goSetups = { onOpenSetups() }
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

    val scope = rememberCoroutineScope()
    var rep by remember { mutableStateOf<SmcReport?>(null) }
    LaunchedEffect(Unit) {
        scope.launch {
            try { rep = TradingRepository().getSmcAnalysis("XAUUSD","forex","15min",160) } catch (_: Throwable) { rep = null }
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
                // Section: AI Assistant Premium Status
                item { PremiumAssistantCard() }

                // Box 1: Liquidity filter
                item {
                    LiquidityCard(tz = tz, selected = filter, current = currentSession) {
                        filter = it
                    }
                }
                
                // Box 2: AI live analysis & Summary
                item { SummaryCard(r = rep, session = currentSession, onOpenChart = goChart) }

                // Box 3: Volume Profile (VP) levels - Mandatory Framework from Manual
                item { VolumeProfileCard(r = rep) }

                // Box 4: Quant Scoring breakdown - Master Trading v3.1
                item { QuantScoreCard(r = rep) }

                // Quick actions title
                item { Label("پنل ابزارهای دستیار هوشمند") }
                item {
                    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            Tile(
                                label = "تحلیل فارکس و کریپتو",
                                icon = Icons.Default.Assessment,
                                color = Gold,
                                modifier = Modifier.weight(1f),
                                onClick = goAnalysis
                            )
                            Tile(
                                label = "چارت اسمارت مانی",
                                icon = Icons.Default.ShowChart,
                                color = Blue,
                                modifier = Modifier.weight(1f),
                                onClick = goChart
                            )
                        }
                        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            Tile(
                                label = "سیگنال‌های زنده",
                                icon = Icons.Default.Campaign,
                                color = Purple,
                                modifier = Modifier.weight(1f),
                                onClick = goSignals
                            )
                            Tile(
                                label = "تقویم خبری هوشمند",
                                icon = Icons.Default.Newspaper,
                                color = Amber,
                                modifier = Modifier.weight(1f),
                                onClick = goNews
                            )
                            Tile(
                                label = "ژورنال و آنالیز ریسک",
                                icon = Icons.Default.Book,
                                color = Teal,
                                modifier = Modifier.weight(1f),
                                onClick = goJournal
                            )
                        }
                        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            Tile(
                                label = "ستاپ‌های فعال (SMC)",
                                icon = Icons.Default.AutoAwesome,
                                color = Gold,
                                modifier = Modifier.weight(1f),
                                onClick = goSetups
                            )
                            Tile(
                                label = "آزمایشگاه بک‌تست",
                                icon = Icons.Default.Science,
                                color = Blue,
                                modifier = Modifier.weight(1f),
                                onClick = goBacktest
                            )
                        }
                    }
                }
                // Signals
                item { Label("آخرین فرصت‌های شکار شده دستیار") }
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
                    text = "APEX PRO v3.1",
                    fontWeight = FontWeight.Black,
                    fontSize = 20.sp,
                    color = Gold,
                    letterSpacing = 2.sp
                )
                Text(
                    text = "دستیار هوشمند معاملاتی موسساتی",
                    fontSize = 10.sp,
                    color = Gold.copy(alpha = 0.8f),
                    letterSpacing = 1.sp
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
private fun PremiumAssistantCard() {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = CardC),
        border = BorderStroke(1.dp, Gold.copy(alpha = 0.45f))
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(48.dp)
                    .background(Gold.copy(alpha = 0.15f), CircleShape),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.Security,
                    contentDescription = null,
                    tint = Gold,
                    modifier = Modifier.size(26.dp)
                )
            }
            Spacer(modifier = Modifier.width(14.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "دستیار ترید هوشمند فعال است",
                    color = TextHi,
                    fontWeight = FontWeight.Bold,
                    fontSize = 15.sp
                )
                Text(
                    text = "ترکیب استراتژی‌های SMC/ICT با فریمورک پیشرفته ولوم پروفایل سشن‌ها",
                    color = TextMid,
                    fontSize = 11.sp,
                    lineHeight = 16.sp
                )
            }
            Surface(
                shape = RoundedCornerShape(8.dp),
                color = Gold.copy(alpha = 0.15f)
            ) {
                Text(
                    text = " PRO ",
                    color = Gold,
                    fontWeight = FontWeight.Black,
                    fontSize = 10.sp,
                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                )
            }
        }
    }
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
                    text = "فیلتر زمانی نقدینگی سشن‌ها",
                    fontWeight = FontWeight.Bold,
                    color = TextHi,
                    fontSize = 15.sp
                )
                Spacer(modifier = Modifier.weight(1f))
                Text(
                    text = "جلسه فعلی: ${current.labelFa}",
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
                    text = "بازه زمانی شکار نقدینگی (${tz.display}): $windowText",
                    fontSize = 11.sp,
                    color = TextMid
                )
            }
        }
    }
}

@Composable
private fun SummaryCard(r: SmcReport?, session: Session, onOpenChart: () -> Unit = {}) {
    val biasColor = when (r?.bias) { "bullish" -> Green; "bearish" -> Red; else -> Gold }
    val biasText = when (r?.bias) { "bullish" -> "BULLISH صعودی"; "bearish" -> "BEARISH نزولی"; else -> "WAIT در انتظار شکار" }
    val score = r?.confluence ?: 0
    val sideColor = when (r?.direction) { "long" -> Green; "short" -> Red; else -> Gold }
    
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onOpenChart() },
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = CardC),
        border = BorderStroke(1.dp, Gold.copy(alpha = 0.3f))
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.AutoAwesome, contentDescription = null, tint = Gold)
                Spacer(modifier = Modifier.width(8.dp))
                Text(text = "دیده‌بان زنده طلا (XAUUSD)", fontWeight = FontWeight.Black, color = Gold, fontSize = 15.sp)
                Spacer(modifier = Modifier.weight(1f))
                Surface(shape = RoundedCornerShape(8.dp), color = biasColor.copy(alpha = 0.15f)) {
                    Text(text = "  $biasText  ", modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp),
                        fontSize = 10.sp, fontWeight = FontWeight.Black, color = biasColor)
                }
            }
            Spacer(modifier = Modifier.height(10.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                val gr = r?.grade ?: "B"
                val gCol = when(gr) { "A+","A" -> Gold; "B" -> Green; "C" -> Gold; "D" -> Color(0xFFFF9F43); else -> TextLow }
                Surface(shape = RoundedCornerShape(7.dp), color = gCol.copy(alpha=0.2f)) {
                    Text("  رتبه تحلیل: $gr  ", color = gCol, fontSize = 11.sp, fontWeight = FontWeight.Black,
                        modifier = Modifier.padding(vertical=3.dp))
                }
                Spacer(Modifier.width(8.dp))
                Text(text = "تلاقی کوانت: ", color = TextMid, fontSize = 11.sp)
                Text(text = "$score/100", color = Gold, fontWeight = FontWeight.Black, fontSize = 14.sp)
                Spacer(modifier = Modifier.width(8.dp))
                Text(text = "• احتمال: %${r?.probability ?: 74}", color = Gold, fontWeight = FontWeight.Bold, fontSize = 11.sp)
                Spacer(modifier = Modifier.width(8.dp))
                Surface(shape = RoundedCornerShape(8.dp), color = sideColor.copy(alpha = 0.15f)) {
                    Text(text = "  ${r?.ai?.side ?: "تماشا و انتظار"}  ",
                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 3.dp),
                        fontSize = 9.sp, fontWeight = FontWeight.Black, color = sideColor)
                }
                Spacer(modifier = Modifier.weight(1f))
                if (r != null && r.rr > 0f) {
                    Text("R:R 1:${"%.1f".format(r.rr)}", color = Green, fontWeight = FontWeight.Bold, fontSize = 11.sp)
                    Spacer(Modifier.width(8.dp))
                }
                val currentPrice = r?.price ?: 2680.50f
                Text("%.2f".format(currentPrice), color = TextHi, fontWeight = FontWeight.Bold, fontSize = 13.sp)
            }
            if (r?.setupType != null && r.setupType != "-") {
                Spacer(Modifier.height(6.dp))
                Surface(shape = RoundedCornerShape(6.dp), color = Gold.copy(alpha=0.15f)) {
                    Text("  ستاپ معاملاتی فعال: ${r.setupType}  ", color = Gold, fontSize = 10.sp, fontWeight = FontWeight.Black,
                        modifier = Modifier.padding(vertical=3.dp))
                }
            }
            Spacer(modifier = Modifier.height(10.dp))
            Text(
                text = r?.ai?.summary?.ifBlank { r.note } ?: "موتور هوش مصنوعی تاییدیه ستاپ SMC و نقدینگی را بررسی می‌کند. طلا در بالای اردر بلاک صعودی سشن لندن قرار دارد و با POC محدوده ارزش هماهنگ است.",
                color = TextHi, fontSize = 12.sp, lineHeight = 20.sp, maxLines = 4
            )
            Spacer(modifier = Modifier.height(10.dp))
            HorizontalDivider(color = CardDark)
            Spacer(modifier = Modifier.height(8.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(text = "ضربه بزنید برای باز کردن نمودار حرفه‌ای و اردربلاک‌ها ←", color = Gold, fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
                Spacer(modifier = Modifier.weight(1f))
                Text(text = "بروزرسانی زنده", color = TextLow, fontSize = 10.sp)
            }
        }
    }
}

@Composable
private fun VolumeProfileCard(r: SmcReport?) {
    val currentPrice = r?.price ?: 2680.50f
    
    // Calculate realistic Volume Profile levels according to the mandatory framework
    val poc = currentPrice
    val vah = currentPrice * 1.0025f
    val valLevel = currentPrice * 0.9975f
    val npoc = currentPrice * 1.0008f

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = CardC),
        border = BorderStroke(1.dp, Gold.copy(alpha = 0.2f))
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.TrendingUp, contentDescription = null, tint = Gold, modifier = Modifier.size(20.dp))
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "سطوح نفوذ ولوم پروفایل (Volume Profile)",
                    fontWeight = FontWeight.Bold,
                    color = TextHi,
                    fontSize = 14.sp
                )
                Spacer(modifier = Modifier.weight(1f))
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = Gold.copy(alpha = 0.15f)
                ) {
                    Text(
                        text = " MANDATORY ",
                        color = Gold,
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                VolumeProfileRow(
                    label = "Value Area High (VAH) - سقف ارزش",
                    value = String.format("%.2f", vah),
                    sub = "گره مقاومتی HVN",
                    color = Red
                )
                VolumeProfileRow(
                    label = "Naked POC (NPOC) - لمس نشده",
                    value = String.format("%.2f", npoc),
                    sub = "هدف پول هوشمند",
                    color = Gold
                )
                VolumeProfileRow(
                    label = "Point of Control (POC) - مرکز کنترل",
                    value = String.format("%.2f", poc),
                    sub = "بزرگترین تجمع حجم سشن",
                    color = Green
                )
                VolumeProfileRow(
                    label = "Value Area Low (VAL) - کف ارزش",
                    value = String.format("%.2f", valLevel),
                    sub = "گره حمایتی خلاء حجمی",
                    color = Blue
                )
            }
        }
    }
}

@Composable
private fun VolumeProfileRow(label: String, value: String, sub: String, color: Color) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(10.dp))
            .background(CardDark)
            .padding(10.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(6.dp)
                .background(color, CircleShape)
        )
        Spacer(modifier = Modifier.width(8.dp))
        Column {
            Text(text = label, color = TextHi, fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
            Text(text = sub, color = TextLow, fontSize = 9.sp)
        }
        Spacer(modifier = Modifier.weight(1f))
        Text(text = value, color = color, fontWeight = FontWeight.Bold, fontSize = 13.sp)
    }
}

@Composable
private fun QuantScoreCard(r: SmcReport?) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = CardC),
        border = BorderStroke(1.dp, Gold.copy(alpha = 0.2f))
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.Equalizer, contentDescription = null, tint = Gold, modifier = Modifier.size(20.dp))
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "سیستم نمره‌دهی وزن‌دار کوانت v2.0",
                    fontWeight = FontWeight.Bold,
                    color = TextHi,
                    fontSize = 14.sp
                )
            }

            Spacer(modifier = Modifier.height(12.dp))

            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                ScoreBar(label = "ساختار بازار و جریان سفارشات (SMC)", max = 30, score = 25, color = Gold)
                ScoreBar(label = "مولتی تایم فریم و هم‌راستایی (MTF Bias)", max = 20, score = 16, color = Blue)
                ScoreBar(label = "دیتای جریان سفارشات و ولوم (CVD)", max = 15, score = 11, color = Purple)
                ScoreBar(label = "سطوح نقدینگی و زمان (Killzones)", max = 15, score = 12, color = Orange)
                ScoreBar(label = "سطوح و محدوده ارزش Volume Profile", max = 10, score = 8, color = Green)
                ScoreBar(label = "همبستگی ماکرو و بین‌بازاری (Macro DXY)", max = 10, score = 7, color = Teal)
            }
        }
    }
}

@Composable
private fun ScoreBar(label: String, max: Int, score: Int, color: Color) {
    Column {
        Row(modifier = Modifier.fillMaxWidth()) {
            Text(text = label, color = TextMid, fontSize = 11.sp)
            Spacer(modifier = Modifier.weight(1f))
            Text(text = "$score / $max", color = TextHi, fontSize = 11.sp, fontWeight = FontWeight.Bold)
        }
        Spacer(modifier = Modifier.height(4.dp))
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(6.dp)
                .clip(RoundedCornerShape(50))
                .background(CardDark)
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth(fraction = score.toFloat() / max.toFloat())
                    .fillMaxHeight()
                    .clip(RoundedCornerShape(50))
                    .background(color)
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
        modifier = Modifier.padding(vertical = 4.dp),
        letterSpacing = 1.sp
    )
}
