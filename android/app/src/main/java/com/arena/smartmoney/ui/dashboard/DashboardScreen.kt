package com.arena.smartmoney.ui.dashboard

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

private val BgDark        = Color(0xFF0B0F14)
private val BgDarkElev    = Color(0xFF10151C)
private val Card          = Color(0xFF161C25)
private val CardDark      = Color(0xFF0E1319)
private val TextHi        = Color(0xFFF2F4F7)
private val TextMid       = Color(0xFF9AA3B2)
private val TextLow       = Color(0xFF5B6472)
private val Gold          = Color(0xFFD4AF37)
private val Green         = Color(0xFF22C55E)
private val Red           = Color(0xFFEF4444)
private val Blue          = Color(0xFF60A5FA)
private val Purple        = Color(0xFFA78BFA)
private val Orange        = Color(0xFFF97316)
private val Amber         = Color(0xFFF59E0B)
private val Teal          = Color(0xFF34D399)
private val Slate         = Color(0xFF94A3B8)

private enum class Tz(val display: String, val zoneId: String) {
    TEHRAN("تهران", "Asia/Tehran"),
    UTC("UTC", "UTC")
}

private enum class Session(
    val labelFa: String,
    val startHourTehran: Int,
    val endHourTehran: Int,
    val color: Color
) {
    ASIA    ("نقدینگی آسیا",      4, 12, Slate),
    LONDON  ("نقدینگی لندن",     12, 17, Blue),
    NY      ("نقدینگی نیویورک",  17, 24, Orange),
    OVERLAP ("هم‌پوشانی طلایی",  16, 19, Gold)
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(
    onNavigateToSignals: () -> Unit = {},
    onNavigateToJournal: () -> Unit = {},
    onNavigateToMarketAnalysis: () -> Unit = {},
    onNavigateToChart: () -> Unit = {},
    onNavigateToNews: () -> Unit = {}
) {
    var tz by rememberSaveable { mutableStateOf(Tz.TEHRAN) }
    var filter by rememberSaveable { mutableStateOf(Session.ASIA) }
    var tzMenuOpen by remember { mutableStateOf(false) }

    val fmt = remember(tz) {
        SimpleDateFormat("HH:mm", Locale.ENGLISH).apply {
            timeZone = TimeZone.getTimeZone(tz.zoneId)
        }
    }
    var now by remember { mutableStateOf(System.currentTimeMillis()) }
    LaunchedEffect(Unit) {
        while (true) {
            now = System.currentTimeMillis()
            kotlinx.coroutines.delay(30_000L)
        }
    }

    val current = remember(tz, now) {
        val h = Calendar.getInstance(TimeZone.getTimeZone(tz.zoneId)).get(Calendar.HOUR_OF_DAY)
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
        topBar = { ApexTopBar(tz, fmt.format(Date(now))) { tzMenuOpen = true } }
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
                item { LiquidityBox(tz, filter, current) { filter = it } }
                item { SummaryBox(current) }
                item { Section("دسترسی سریع") }
                item {
                    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            Action("تحلیل بازار حرفه‌ای", Icons.Default.Assessment, Gold, Modifier.weight(1f), onNavigateToMarketAnalysis)
                            Action("چارت", Icons.Default.ShowChart, Blue, Modifier.weight(1f), onNavigateToChart)
                        }
                        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            Action("سیگنال‌ها", Icons.Default.Campaign, Purple, Modifier.weight(1f), onNavigateToSignals)
                            Action("اخبار", Icons.Default.MenuBook, Amber, Modifier.weight(1f), onNavigateToNews)
                            Action("ژورنال", Icons.Default.Book, Teal, Modifier.weight(1f), onNavigateToJournal)
                        }
                    }
                }
                item { Section("سیگنال‌های زنده") }
                val demoSignals = remember {
                    listOf(
                        DemoSignal("XAUUSD", "LONG",  "15m", "SMC", "2685.00", "2675.00"),
                        DemoSignal("EURUSD", "SHORT", "1H",  "OB",  "1.08000", "1.08650")
                    )
                }
                items(demoSignals) { s -> SignalItem(s, onNavigateToChart) }
                item {
                    Spacer(Modifier.height(10.dp))
                    Text(
                        "Created by\nAmin Omidi",
                        Modifier.fillMaxWidth(),
                        textAlign = TextAlign.Center,
                        color = TextLow,
                        fontSize = 11.sp,
                        lineHeight = 14.sp,
                        letterSpacing = 1.2.sp
                    )
                    Spacer(Modifier.height(24.dp))
                }
            }
            DropdownMenu(expanded = tzMenuOpen, onDismissRequest = { tzMenuOpen = false }) {
                Tz.values().forEach { m ->
                    DropdownMenuItem(
                        text = { Text(m.display, color = if (m == tz) Gold else TextHi) },
                        leadingIcon = {
                            Icon(
                                if (m == Tz.TEHRAN) Icons.Default.Language else Icons.Default.Public,
                                null, tint = if (m == tz) Gold else TextMid,
                                modifier = Modifier.size(18.dp)
                            )
                        },
                        onClick = { tz = m; tzMenuOpen = false }
                    )
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ApexTopBar(tz: Tz, clock: String, onTzClick: () -> Unit) {
    CenterAlignedTopAppBar(
        title = {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text("APEX AI", fontWeight = FontWeight.Black, fontSize = 20.sp, color = Gold, letterSpacing = 2.sp)
                Text("Trading Assistant", fontSize = 10.sp, color = TextLow, letterSpacing = 3.sp)
            }
        },
        actions = {
            AssistChip(
                onClick = onTzClick,
                label = { Text("${tz.display} · $clock", color = TextHi, fontSize = 11.sp) },
                leadingIcon = { Icon(Icons.Default.Schedule, null, tint = Gold, modifier = Modifier.size(14.dp)) },
                shape = RoundedCornerShape(50),
                colors = AssistChipDefaults.assistChipColors(containerColor = Card),
                border = AssistChipDefaults.assistChipBorder(borderColor = Gold.copy(alpha = 0.35f))
            )
            Spacer(Modifier.width(8.dp))
        },
        colors = TopAppBarDefaults.centerAlignedTopAppBarColors(containerColor = BgDark, titleContentColor = TextHi)
    )
}

@Composable
private fun LiquidityBox(tz: Tz, selected: Session, current: Session, onSelect: (Session) -> Unit) {
    ElevatedCard(
        Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.elevatedCardColors(containerColor = Card),
        elevation = CardDefaults.elevatedCardElevation(6.dp)
    ) {
        Column(Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(10.dp).background(current.color, CircleShape))
                Spacer(Modifier.width(8.dp))
                Text("فیلتر زمانی نقدینگی", fontWeight = FontWeight.Bold, color = TextHi, fontSize = 15.sp)
                Spacer(Modifier.weight(1f))
                Text("جلسه: ${current.labelFa}", fontSize = 11.sp, color = current.color, fontWeight = FontWeight.SemiBold)
            }
            Spacer(Modifier.height(12.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Session.values().forEach { s ->
                    val sel = s == selected
                    FilterChip(
                        selected = sel,
                        onClick = { onSelect(s) },
                        label = {
                            Text(s.labelFa, fontSize = 10.sp, fontWeight = FontWeight.SemiBold,
                                color = if (sel) Color.Black else TextHi, maxLines = 1)
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
            Spacer(Modifier.height(12.dp))
            val windowText = when (tz) {
                Tz.TEHRAN -> {
                    val sh = String.format("%02d:00", selected.startHourTehran)
                    val eh = if (selected.endHourTehran == 24) "00:00" else String.format("%02d:00", selected.endHourTehran)
                    "$sh – $eh"
                }
                Tz.UTC -> {
                    val sh = (selected.startHourTehran - 4 + 24) % 24
                    val eh = (selected.endHourTehran - 4 + 24) % 24
                    val shs = String.format("%02d:00", sh)
                    val ehs = if (eh == 0) "00:00" else String.format("%02d:00", eh)
                    "$shs – $ehs"
                }
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.AccessTime, null, tint = selected.color, modifier = Modifier.size(14.dp))
                Spacer(Modifier.width(6.dp))
                Text("بازه (${tz.display}): $windowText", fontSize = 11.sp, color = TextMid)
            }
        }
    }
}

@Composable
private fun SummaryBox(session: Session) {
    ElevatedCard(
        Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.elevatedCardColors(containerColor = Card)
    ) {
        Column(Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.AutoAwesome, null, tint = Gold)
                Spacer(Modifier.width(8.dp))
                Text("جمع‌بندی هوش مصنوعی", fontWeight = FontWeight.Bold, color = TextHi, fontSize = 15.sp)
            }
            Spacer(Modifier.height(10.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("امتیاز روز: ", color = TextMid, fontSize = 13.sp)
                Text("7/10", color = Gold, fontWeight = FontWeight.Black, fontSize = 18.sp)
                Spacer(Modifier.width(8.dp))
                Surface(shape = RoundedCornerShape(8.dp), color = Green.copy(alpha = 0.15f)) {
                    Text("BULLISH BIAS", Modifier.padding(horizontal = 8.dp, vertical = 3.dp),
                        fontSize = 11.sp, fontWeight = FontWeight.SemiBold, color = Green)
                }
            }
            Spacer(Modifier.height(8.dp))
            Text("روند کلی در جلسهٔ فعلی صعودی است. تمرکز روی نقدینگی سمت فروش و تایید روی تایم فریم‌های بالاتر باشد. مدیریت ریسک را رعایت کنید.",
                color = TextHi, fontSize = 13.sp, lineHeight = 20.sp)
            Spacer(Modifier.height(10.dp))
            HorizontalDivider(color = CardDark)
            Spacer(Modifier.height(10.dp))
            Text("تمرکز پیشنهادی برای جلسهٔ ${session.labelFa}:",
                color = TextMid, fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(4.dp))
            Text("ورود فقط در صورت تایید ساختار (BOS/CHoCH) و تشکیل Order Block معتبر. در زمان اخبار پرریسک ورود جدید نگیرید.",
                color = TextHi, fontSize = 12.sp, lineHeight = 18.sp)
        }
    }
}

@Composable
private fun Action(label: String, icon: ImageVector, color: Color, modifier: Modifier = Modifier, onClick: () -> Unit) {
    ElevatedCard(
        modifier = modifier.height(82.dp).clickable(onClick = onClick),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.elevatedCardColors(containerColor = Card)
    ) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Icon(icon, null, tint = color, modifier = Modifier.size(24.dp))
                Spacer(Modifier.height(6.dp))
                Text(label, color = TextHi, fontSize = 11.sp, fontWeight = FontWeight.SemiBold, textAlign = TextAlign.Center)
            }
        }
    }
}

private data class DemoSignal(val symbol: String, val direction: String, val timeframe: String, val strategy: String, val tp: String, val sl: String)

@Composable
private fun SignalItem(s: DemoSignal, onClick: () -> Unit) {
    val isLong = s.direction.equals("LONG", ignoreCase = true)
    val c = if (isLong) Green else Red
    ElevatedCard(
        Modifier.fillMaxWidth().clickable(onClick = onClick),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.elevatedCardColors(containerColor = Card)
    ) {
        Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(42.dp).clip(RoundedCornerShape(12.dp)).background(c.copy(alpha = 0.15f)), contentAlignment = Alignment.Center) {
                Icon(if (isLong) Icons.Default.TrendingUp else Icons.Default.TrendingDown, null, tint = c)
            }
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(s.symbol, color = TextHi, fontWeight = FontWeight.Bold, fontSize = 15.sp)
                Text("${s.timeframe} · ${s.strategy}", color = TextMid, fontSize = 11.sp)
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(if (isLong) "LONG" else "SHORT", color = c, fontWeight = FontWeight.Black, fontSize = 12.sp)
                Text("TP ${s.tp}  SL ${s.sl}", color = TextLow, fontSize = 10.sp)
            }
        }
    }
}

@Composable
private fun Section(text: String) {
    Text(text, color = TextMid, fontSize = 12.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.sp)
}
