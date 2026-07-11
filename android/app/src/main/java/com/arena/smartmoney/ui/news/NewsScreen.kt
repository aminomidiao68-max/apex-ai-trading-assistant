@file:OptIn(ExperimentalMaterial3Api::class)

package com.arena.smartmoney.ui.news

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
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.arena.smartmoney.data.model.NewsAdjustment
import com.arena.smartmoney.data.model.NewsBrief
import com.arena.smartmoney.data.model.NewsEvent
import com.arena.smartmoney.data.model.NewsHeadline
import com.arena.smartmoney.data.repository.TradingRepository
import kotlinx.coroutines.launch
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
private val Orange     = Color(0xFFF97316)
private val Blue       = Color(0xFF60A5FA)
private val Amber      = Color(0xFFF59E0B)

@Composable
fun NewsScreen(onBack: () -> Unit = {}) {
    val scope = rememberCoroutineScope()
    var brief by remember { mutableStateOf<NewsBrief?>(null) }
    var loading by remember { mutableStateOf(true) }
    var tab by remember { mutableIntStateOf(0) }

    fun load() {
        scope.launch {
            loading = true
            try { brief = TradingRepository().getNewsBrief() } catch (_: Throwable) { brief = null }
            finally { loading = false }
        }
    }
    LaunchedEffect(Unit) { load() }

    Scaffold(
        containerColor = BgDark,
        topBar = {
            CenterAlignedTopAppBar(
                title = {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text("اخبار اقتصادی", fontWeight = FontWeight.Black, fontSize = 18.sp, color = Gold, letterSpacing = 2.sp)
                        Text("Finnhub Economic Calendar", fontSize = 10.sp, color = TextLow, letterSpacing = 2.sp)
                    }
                },
                navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, "back", tint = TextHi) } },
                actions = { IconButton(onClick = { load() }) { Icon(Icons.Default.Refresh, "refresh", tint = Gold) } },
                colors = TopAppBarDefaults.centerAlignedTopAppBarColors(containerColor = BgDark, titleContentColor = TextHi)
            )
        }
    ) { pad ->
        Box(Modifier.fillMaxSize().padding(pad).background(Brush.verticalGradient(listOf(BgDark, BgDarkElev)))) {
            if (loading) {
                CircularProgressIndicator(Modifier.align(Alignment.Center), color = Gold)
            } else if (brief == null) {
                ErrorView { load() }
            } else {
                val b = brief!!
                LazyColumn(contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    if (b.block.blocked) item { BlockBanner(b.block.reasons) }
                    item { ConfigCard(b.finnhub_configured, b.adjustment) }
                    item {
                        TabRow(selectedTabIndex = tab, containerColor = CardDark, contentColor = Gold) {
                            listOf("زنده", "پیش‌رو", "تیترها").forEachIndexed { i, t ->
                                Tab(selected = tab == i, onClick = { tab = i },
                                    text = { Text(t, color = if (tab == i) Gold else TextMid, fontSize = 12.sp, fontWeight = FontWeight.SemiBold) })
                            }
                        }
                    }
                    when (tab) {
                        0 -> if (b.events.live.isEmpty()) item { Empty("رویداد زنده‌ای در لحظه نیست.") }
                            else items(b.events.live, key = { it.id }) { EventRow(it, live = true) }
                        1 -> if (b.events.upcoming.isEmpty()) item { Empty("رویداد مهمی در ساعات آینده نیست.") }
                            else items(b.events.upcoming, key = { it.id }) { EventRow(it, live = false) }
                        else -> if (b.headlines.isEmpty()) item { Empty("تیتری دریافت نشد.") }
                            else items(b.headlines, key = { it.id.ifBlank { it.title } }) { HeadlineRow(it) }
                    }
                    item {
                        Spacer(Modifier.height(10.dp))
                        Text("Created by\nAmin Omidi", Modifier.fillMaxWidth(), textAlign = TextAlign.Center, color = TextLow, fontSize = 11.sp, lineHeight = 14.sp, letterSpacing = 1.2.sp)
                        Spacer(Modifier.height(24.dp))
                    }
                }
            }
        }
    }
}

@Composable
private fun BlockBanner(reasons: List<String>) {
    ElevatedCard(Modifier.fillMaxWidth(), shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.elevatedCardColors(containerColor = Red.copy(alpha = 0.15f))) {
        Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Default.Warning, "block", tint = Red, modifier = Modifier.size(28.dp))
            Spacer(Modifier.width(10.dp))
            Column(Modifier.weight(1f)) {
                Text("ورود به معامله ممنوع", color = Red, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                Text(reasons.firstOrNull() ?: "رویداد پرریسک نزدیک است.", color = TextHi, fontSize = 12.sp, lineHeight = 18.sp)
            }
        }
    }
}

@Composable
private fun ConfigCard(configured: Boolean, adj: NewsAdjustment) {
    val (icon, c, title) = when {
        !configured -> Triple(Icons.Default.AutoAwesome, Gold, "اخبار هوشمند آفلاین")
        adj.bias == "risk_off" -> Triple(Icons.Default.Shield, Red, "حالت ریسک‌گریز")
        adj.bias == "risk_on" -> Triple(Icons.Default.TrendingUp, Green, "حالت ریسک‌پذیر")
        else -> Triple(Icons.Default.CheckCircle, Green, "بازار پایدار")
    }
    ElevatedCard(Modifier.fillMaxWidth(), shape = RoundedCornerShape(18.dp), colors = CardDefaults.elevatedCardColors(containerColor = CardC)) {
        Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(40.dp).clip(CircleShape).background(c.copy(alpha = 0.18f)), contentAlignment = Alignment.Center) { Icon(icon, null, tint = c) }
            Spacer(Modifier.width(10.dp))
            Column(Modifier.weight(1f)) {
                Text(title, color = TextHi, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                Text(if (configured) adj.note else ("اخبار توسط Apex AI تولید می‌شوند. " + adj.note),
                    color = TextMid, fontSize = 12.sp, lineHeight = 18.sp)
                if (configured && adj.score_penalty > 0) {
                    Spacer(Modifier.height(6.dp))
                    Text("جریمه‌ی امتیاز: -${adj.score_penalty}", color = Orange, fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
                }
            }
        }
    }
}

@Composable
private fun EventRow(ev: NewsEvent, live: Boolean) {
    val impactColor = when (ev.impact) { "high" -> Red; "medium" -> Orange; else -> Blue }
    val fmt = remember { SimpleDateFormat("HH:mm", Locale.ENGLISH) }
    val timeLabel = ev.timeTehran.ifBlank { fmt.format(Date(ev.time_unix * 1000L)) }
    ElevatedCard(Modifier.fillMaxWidth(), shape = RoundedCornerShape(16.dp), colors = CardDefaults.elevatedCardColors(containerColor = CardC)) {
        Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(timeLabel, color = TextHi, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                Text(if (live) "زنده" else if (ev.phase == "past") "گذشته" else "پیش‌رو",
                    color = if (live) Red else impactColor, fontSize = 10.sp, fontWeight = FontWeight.SemiBold)
            }
            Spacer(Modifier.width(12.dp))
            Box(Modifier.width(4.dp).height(36.dp).clip(CircleShape).background(impactColor))
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(ev.title, color = TextHi, fontWeight = FontWeight.SemiBold, fontSize = 13.sp, maxLines = 2, overflow = TextOverflow.Ellipsis)
                Spacer(Modifier.height(4.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Surface(shape = RoundedCornerShape(6.dp), color = impactColor.copy(alpha = 0.18f)) {
                        Text(" ${ev.currency.ifBlank { ev.country }} ", color = impactColor, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                    }
                    Spacer(Modifier.width(6.dp))
                    Surface(shape = RoundedCornerShape(6.dp), color = CardDark) {
                        Text(" ${ev.impact.uppercase()} ", color = impactColor, fontSize = 9.sp, fontWeight = FontWeight.SemiBold)
                    }
                }
                if (ev.forecast != null || ev.previous != null || ev.actual != null) {
                    Spacer(Modifier.height(6.dp))
                    Row {
                        if (ev.actual != null) Metric("واقعی", ev.actual + ev.unit, Green)
                        Spacer(Modifier.width(8.dp))
                        if (ev.forecast != null) Metric("پیش‌بینی", ev.forecast + ev.unit, TextMid)
                        Spacer(Modifier.width(8.dp))
                        if (ev.previous != null) Metric("قبلی", ev.previous + ev.unit, TextLow)
                    }
                }
            }
        }
    }
}

@Composable
private fun Metric(label: String, value: String, color: Color) {
    Column {
        Text(label, color = TextLow, fontSize = 9.sp)
        Text(value, color = color, fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
    }
}

@Composable
private fun HeadlineRow(h: NewsHeadline) {
    val fmt = remember { SimpleDateFormat("HH:mm", Locale.ENGLISH) }
    val timeText = if (h.time_unix > 0L) fmt.format(Date(h.time_unix * 1000L)) else ""
    ElevatedCard(Modifier.fillMaxWidth(), shape = RoundedCornerShape(16.dp), colors = CardDefaults.elevatedCardColors(containerColor = CardC)) {
        Column(Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(h.source.ifBlank { "Apex AI" }, color = Gold, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                Spacer(Modifier.weight(1f))
                if (timeText.isNotBlank()) Text(timeText, color = TextLow, fontSize = 10.sp)
            }
            Spacer(Modifier.height(6.dp))
            Text(h.title, color = TextHi, fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
            if (h.summary.isNotBlank()) {
                Spacer(Modifier.height(4.dp))
                Text(h.summary, color = TextMid, fontSize = 11.sp, lineHeight = 16.sp, maxLines = 3, overflow = TextOverflow.Ellipsis)
            }
        }
    }
}

@Composable
private fun Empty(msg: String) {
    ElevatedCard(Modifier.fillMaxWidth(), shape = RoundedCornerShape(16.dp), colors = CardDefaults.elevatedCardColors(containerColor = CardC)) {
        Text(msg, Modifier.padding(18.dp), color = TextMid, fontSize = 12.sp, textAlign = TextAlign.Center)
    }
}

@Composable
private fun ErrorView(onRetry: () -> Unit) {
    Column(Modifier.fillMaxSize().padding(24.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
        Icon(Icons.Default.ErrorOutline, "error", tint = Red, modifier = Modifier.size(48.dp))
        Spacer(Modifier.height(12.dp))
        Text("خطا در بارگذاری اخبار", color = TextHi, fontWeight = FontWeight.Bold, fontSize = 16.sp)
        Spacer(Modifier.height(6.dp))
        Text("اتصال اینترنت یا سرویس بک‌اند در دسترس نیست.", color = TextMid, fontSize = 12.sp, textAlign = TextAlign.Center)
        Spacer(Modifier.height(16.dp))
        Button(onClick = onRetry, colors = ButtonDefaults.buttonColors(containerColor = Gold, contentColor = Color.Black), shape = RoundedCornerShape(50)) { Text("تلاش مجدد") }
    }
}
