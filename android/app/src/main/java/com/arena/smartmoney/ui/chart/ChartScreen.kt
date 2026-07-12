@file:OptIn(ExperimentalMaterial3Api::class)
package com.arena.smartmoney.ui.chart

import android.graphics.Paint as NativePaint
import android.graphics.Rect
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.*
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.arena.smartmoney.data.model.SmcCandle
import com.arena.smartmoney.data.model.SmcReport
import com.arena.smartmoney.data.model.SmcSignal
import com.arena.smartmoney.data.model.SmcZone
import com.arena.smartmoney.data.repository.TradingRepository
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

// ========================== رنگ‌بندی دقیق TradingView ==========================
private val BgDark   = Color(0xFF0B0E17)
private val ChartBg  = Color(0xFF131722)   // پس‌زمینه چارت TV
private val ChartGrid= Color(0xFF1E2736)   // خطوط گرید ریز TV
private val Surf     = Color(0xFF171C2B)
private val Surf2    = Color(0xFF1E2538)
private val Gold     = Color(0xFFD4AF37)
private val GoldDim  = Color(0xFF8C7630)
private val GoldSoft = Color(0xFF2E2714)
private val TH       = Color(0xFFF5F0DC)
private val TL       = Color(0xFF788296)
private val UpC      = Color(0xFF26A69A)   // سبز تیل TV
private val DnC      = Color(0xFFEF5350)   // قرمز TV
private val BullOB   = Color(0xFF26A69A)   // بلوک سفارش خرید فیروزه‌ای
private val BearOB   = Color(0xFFFF9800)   // بلوک سفارش فروش نارنجی
private val FvgC     = Color(0xFFB388FF)
private val iFvgC    = Color(0xFF7C4DFF)
private val BrkC     = Color(0xFFFFB74D)
private val LiqC     = Color(0xFF42A5F5)
private val IdmColor = Color(0xFFFDD835)   // IDM زرد TV
private val AxisBg   = Color(0xFF131722)   // پس‌زمینه برچسب قیمت
private val KzAsia   = Color(0x265C89CF)   // آسیا — آبی کم‌رنگ
private val KzLon    = Color(0x3390CAF9)   // London Killzone — آبی روشن TV
private val KzNy     = Color(0x33EF5350)   // New York — قرمز روشن TV
private val KzOver   = Color(0x44D4AF37)   // Overlap — طلایی
private val VwapC    = Color(0xFFF5F0DC)
private val VolUp    = Color(0x6626A69A)
private val VolDn    = Color(0x66EF5350)

private val SYMBOLS = listOf("XAUUSD","EURUSD","GBPUSD","USDJPY","AUDUSD","BTCUSDT","ETHUSDT","SOLUSDT","US30","NAS100")
private val TIMEFRAMES = listOf("1m","5m","15m","30m","1h","4h","1d")

@Composable
fun ChartScreen(onBack: (() -> Unit)? = null) {
    val repo = remember { TradingRepository() }
    val scope = rememberCoroutineScope()
    var r by remember { mutableStateOf(SmcReport()) }
    var loading by remember { mutableStateOf(true) }
    var sym by remember { mutableStateOf("XAUUSD") }
    var mkt by remember { mutableStateOf("") }
    var tf  by remember { mutableStateOf("15m") }
    var scale by remember { mutableStateOf(defaultChartScale("15m")) }
    var signals by remember { mutableStateOf<List<SmcSignal>>(emptyList()) }
    var scanLoading by remember { mutableStateOf(false) }
    var refreshNonce by remember { mutableIntStateOf(0) }

    fun scan() {
        scope.launch {
            scanLoading = true
            try { signals = repo.scanSignals(40).signals }
            finally { scanLoading = false }
        }
    }

    // LaunchedEffect cancels the previous Retrofit call when symbol/timeframe
    // changes. Clearing the old report prevents a stale 5m chart from being
    // shown under a newly selected 15m chip.
    LaunchedEffect(sym, tf, refreshNonce) {
        val requestedSymbol = sym
        val requestedTimeframe = tf
        val requestedMarket = mkt
        loading = true
        scale = defaultChartScale(requestedTimeframe)
        r = SmcReport(
            symbol = requestedSymbol,
            timeframe = requestedTimeframe,
            market = if (requestedMarket.isBlank()) "auto" else requestedMarket,
            status = "loading"
        )
        delay(120)
        val response = repo.getSmcAnalysis(
            requestedSymbol, requestedMarket, requestedTimeframe, 260
        )
        if (sym == requestedSymbol && tf == requestedTimeframe) {
            r = response
            loading = false
        }
    }
    LaunchedEffect(Unit) {
        delay(2500)
        scan()
    }

    Scaffold(
        containerColor = BgDark,
        topBar = {
            TopAppBar(
                title = { Text("تحلیل هوشمند SMC", color = Gold, fontWeight = FontWeight.Black, fontSize = 19.sp) },
                navigationIcon = { if (onBack != null) IconButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, "back", tint = Gold) } },
                actions = {
                    IconButton(onClick = { refreshNonce++; scan() }) { Icon(Icons.Default.Refresh, "refresh", tint = Gold) }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = BgDark)
            )
        }
    ) { pad ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(pad).padding(horizontal = 10.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            item {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Label("نماد")
                    ChipRow(SYMBOLS, sym) { sym = it; mkt = "" }
                    Label("تایم‌فریم")
                    ChipRow(TIMEFRAMES, tf) { tf = it; scale = defaultChartScale(it) }
                }
            }
            item { HeaderCard(r, sym, mkt, tf, loading) }
            item {
                Card(colors = CardDefaults.cardColors(containerColor = ChartBg), shape = RoundedCornerShape(6.dp)) {
                    Column(modifier = Modifier.padding(0.dp)) {
                        // تولبار ساده بالای چارت (مثل TV)
                        Row(
                            modifier = Modifier.fillMaxWidth().padding(horizontal = 8.dp, vertical = 6.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text("APEX Smart Money Concepts", color = TL, fontSize = 10.sp, fontWeight = FontWeight.SemiBold)
                            Text("(با دو انگشت زوم کنید)", color = TL.copy(alpha = 0.6f), fontSize = 9.sp)
                        }
                        if (r.candles.isNotEmpty()) {
                            SmcCanvas(
                                modifier = Modifier.fillMaxWidth().height(390.dp),
                                report = r, scale = scale,
                                onScale = { scale = (scale * it).coerceIn(0.6f, 4f) }
                            )
                        } else {
                            Box(Modifier.fillMaxWidth().height(390.dp), contentAlignment = Alignment.Center) {
                                Text(if (loading) "در حال بارگذاری..." else "داده کافی نیست", color = TL, fontSize = 12.sp)
                            }
                        }
                        // پایین چارت
                        LazyRow(
                            modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp),
                            contentPadding = PaddingValues(horizontal = 8.dp),
                            horizontalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            item { LegendDot(BullOB, "Bullish OB") }
                            item { LegendDot(BearOB, "Bearish OB") }
                            item { LegendDot(FvgC, "FVG") }
                            item { LegendDot(BrkC.copy(alpha = 0.55f), "Breaker") }
                            item { LegendDot(LiqC, "BSL / SSL") }
                            item { LegendDot(UpC, "BOS / CHoCH") }
                            item { LegendDot(KzLon.copy(alpha=0.7f), "Sessions") }
                        }
                    }
                }
            }
            item { AiCard(r, loading) }
            item { LevelsCard(r) }
            if (r.watching.isNotEmpty()) item { WatchingCard(r) }
            // === اسکن زنده سیگنال‌ها ===
            item {
                Card(colors = CardDefaults.cardColors(containerColor = Surf), shape = RoundedCornerShape(14.dp),
                    border = androidx.compose.foundation.BorderStroke(1.dp, Gold.copy(alpha = 0.25f))) {
                    Column(Modifier.padding(14.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.AutoAwesome, "ai", tint = Gold)
                            Spacer(Modifier.width(8.dp))
                            Text("سیگنال‌های زنده بازار", color = Gold, fontWeight = FontWeight.Black, fontSize = 14.sp)
                            Spacer(Modifier.weight(1f))
                            androidx.compose.material3.IconButton(onClick = { scan() }, modifier = Modifier.size(28.dp)) {
                                Icon(Icons.Default.Refresh, "refresh", tint = Gold, modifier = Modifier.size(18.dp))
                            }
                        }
                        Spacer(Modifier.height(6.dp))
                        if (scanLoading) {
                            Text("در حال اسکن...", color = TL, fontSize = 12.sp)
                        } else {
                            val actionable = signals.filter { it.grade in listOf("A+","A","B") }
                            if (actionable.isEmpty()) {
                                Text("در حال حاضر سیگنال با درجه بالا پیدا نشد.", color = TL, fontSize = 12.sp)
                            } else {
                                Text("${actionable.size} سیگنال معتبر یافت شد (A+/A/B)", color = TH, fontSize = 11.sp)
                                Spacer(Modifier.height(8.dp))
                                actionable.take(6).forEach { s ->
                                    SignalRow(s)
                                }
                            }
                        }
                    }
                }
            }
            if (r.killzones.isNotEmpty()) item { Section("سشن‌ها و Killzoneها", Gold) }
            if (r.killzones.isNotEmpty()) items(r.killzones.take(4)) { kz -> KzRow(kz) }
            val liqSweeps = r.inducements.filter { it.kind.contains("liq") || it.kind.startsWith("eq") || it.kind.contains("recent") }
            if (liqSweeps.isNotEmpty()) item { Section("لایکوئیدیتی BSL / SSL", LiqC) }
            if (liqSweeps.isNotEmpty()) items(liqSweeps.take(6)) { LiqRow(it.kind, it.price) }
            if (r.orderBlocks.isNotEmpty()) item { Section("Order Blockها", Gold) }
            if (r.orderBlocks.isNotEmpty()) items(r.orderBlocks.take(5)) { Zc(it, "OB", if (it.kind == "bullish" || it.side == "bullish") BullOB else BearOB) }
            if (r.events.isNotEmpty()) item { Section("وقایع ساختاری BOS / CHoCH", Gold) }
            if (r.events.isNotEmpty()) items(r.events.takeLast(6)) { ev -> EventRow(ev.kind, ev.dir, ev.price) }
            item { Spacer(Modifier.height(40.dp)) }
            item { Text("Created by Amin Omidi", color = GoldDim, fontSize = 11.sp,
                modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Center)
                Spacer(Modifier.height(18.dp)) }
        }
    }
}

@Composable
private fun SignalRow(s: SmcSignal) {
    val col = when {
        s.direction == "long" -> UpC
        s.direction == "short" -> DnC
        else -> TL
    }
    val side = when(s.direction) { "long"->"خرید (LONG)";"short"->"فروش (SHORT)";else->"انتظار" }
    Surface(shape = RoundedCornerShape(10.dp), color = col.copy(alpha = 0.08f),
        modifier = Modifier.fillMaxWidth().padding(vertical = 3.dp)) {
        Row(Modifier.padding(10.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("${s.symbol} · ${s.timeframe}", color = TH, fontSize = 13.sp, fontWeight = FontWeight.Black)
                Text(s.note, color = TL, fontSize = 11.sp, maxLines = 1)
            }
            Column(horizontalAlignment = Alignment.End) {
                Surface(shape = RoundedCornerShape(6.dp), color = col.copy(alpha = 0.22f)) {
                    Text("  $side  ", color = col, fontSize = 10.sp, fontWeight = FontWeight.Black)
                }
                Spacer(Modifier.height(3.dp))
                Text("${s.grade} · conf ${s.confluence} · %${s.probability} · RR 1:${"%.1f".format(s.rr)}",
                    color = col, fontSize = 9.sp, fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Composable
private fun HeaderCard(r: SmcReport, sym: String, mkt: String, tf: String, loading: Boolean) {
    Card(colors = CardDefaults.cardColors(containerColor = Surf), shape = RoundedCornerShape(12.dp)) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                Column {
                    Text(r.symbol.ifBlank { sym }, color = TH, fontSize = 22.sp, fontWeight = FontWeight.Black)
                    val tflbl = r.timeframe.ifBlank { tf }
                    val mklbl = r.market.ifBlank { if (mkt.isBlank()) "auto" else mkt }.uppercase()
                    Text("$tflbl  •  $mklbl", color = TL, fontSize = 11.sp)
                    r.htf.bias?.let { hb ->
                        r.htf.timeframe?.let { htf ->
                            val hc = when(hb){"bullish"->UpC;"bearish"->DnC;else->GoldDim}
                            Spacer(Modifier.height(4.dp))
                            Surface(shape=RoundedCornerShape(5.dp), color=hc.copy(alpha=0.15f)){
                                Text("  HTF $htf: ${hb.uppercase()}  ", color=hc, fontSize=9.sp, fontWeight=FontWeight.Black)
                            }
                        }
                    }
                }
                Column(horizontalAlignment = Alignment.End) {
                    val p = r.price
                    Text(if (p > 0f) fmt(p) else "-", color = Gold, fontSize = 22.sp, fontWeight = FontWeight.Black)
                    val bc = when (r.bias) { "bullish" -> UpC; "bearish" -> DnC; else -> GoldDim }
                    val bl = when (r.bias) {
                        "bullish" -> "BULLISH • صعودی"
                        "bearish" -> "BEARISH • نزولی"
                        else -> "NEUTRAL • خنثی"
                    }
                    Surface(shape = RoundedCornerShape(5.dp), color = bc.copy(alpha = 0.15f)) {
                        Text("  $bl  ", color = bc, fontSize = 10.sp, fontWeight = FontWeight.Black)
                    }
                }
            }
            Spacer(Modifier.height(8.dp))
            LazyRow(horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                item {
                    val gradeC = when(r.grade) { "A+","A" -> Gold; "B" -> UpC; "C" -> GoldDim; "D" -> BrkC; else -> TL }
                    ChipS("درجه ${r.grade}", gradeC)
                }
                item { ChipS("conf ${r.confluence}", when { r.confluence>=70->Gold; r.confluence>=40->GoldDim; else->TL }) }
                item { ChipS(if(r.probability>0) "%${r.probability}" else "احتمال -", when { r.probability>=75->UpC; r.probability>=55->GoldDim; else->TL }) }
                item { ChipS(if (r.rr > 0f) "RR 1:%.1f".format(r.rr) else "RR -", if(r.rr>=2f) UpC else TL) }
                item { ChipS("TS ${r.trendStrength}", when{r.trendStrength>=60->UpC;r.trendStrength<30->DnC;else->TL}) }
            }
            Spacer(Modifier.height(4.dp))
            LazyRow(horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                item {
                    val pr = r.orderflow.pressure
                    ChipS(when(pr){"buy"->"OF+";"sell"->"OF−";else->"OF"}, when(pr){"buy"->UpC;"sell"->DnC;else->TL})
                }
                if (r.orderflow.volumeSpike) item { ChipS("VOL↑", Gold) }
                if (r.orderflow.absorption) item { ChipS("ABSRB", BrkC) }
                r.orderflow.cvdDivergence?.let {
                    item {
                        val divArrow = if (it == "bullish") "▲" else "▼"
                        val divCol = if (it == "bullish") UpC else DnC
                        ChipS("DIV$divArrow", divCol)
                    }
                }
                item { ChipS(when(r.premiumZone){"premium"->"پرِمیوم";"discount"->"دیسکانت";else->"تعادل"}, GoldDim) }
                if (r.newsBlocked) item { ChipS("⚠️اخبار", DnC) }
                if (r.mtfAligned) item { ChipS("MTF✓", UpC) }
                val actLbl = when(r.actionLabel) {
                    "STRONG_BUY/SELL" -> "STRONG"
                    "BUY/SELL" -> "BUY/SELL"
                    "CONSIDER" -> "CONSIDER"
                    "CAUTION" -> "CAUTION"
                    "HALF_SIZE" -> "HALF"
                    "WATCH" -> "WATCH"
                    "AVOID" -> "AVOID"
                    else -> r.actionLabel
                }
                val actCol = when(r.actionLabel) {
                    "STRONG_BUY/SELL","BUY/SELL" -> UpC
                    "CONSIDER" -> Gold
                    "WATCH","CAUTION" -> GoldDim
                    "HALF_SIZE" -> BrkC
                    "AVOID" -> DnC
                    else -> TL
                }
                item { ChipS(actLbl, actCol) }
            }
            if (r.setupType != "-" && r.setupType.isNotBlank()) {
                Spacer(Modifier.height(6.dp))
                Surface(shape=RoundedCornerShape(7.dp), color=Gold.copy(alpha=0.18f)) {
                    Text("  ستاپ: ${r.setupType}  ", color=Gold, fontSize=11.sp, fontWeight=FontWeight.Black)
                }
            }
            Spacer(Modifier.height(6.dp))
            Text(
                if (loading) "در حال بارگذاری..." else safeChartMessage(r.note),
                color = TH,
                fontSize = 12.sp,
                lineHeight = 18.sp
            )
            if (r.sessionActive != "-") {
                Spacer(Modifier.height(4.dp))
                Text("سشن فعال: ${r.sessionActive}  •  VWAP ${fmt(r.vwap)}", color = TL, fontSize = 11.sp)
            }
        }
    }
}

@Composable
private fun AiCard(r: SmcReport, loading: Boolean) {
    val sideC = when (r.direction) { "long" -> UpC; "short" -> DnC; else -> GoldDim }
    Card(colors = CardDefaults.cardColors(containerColor = GoldSoft), shape = RoundedCornerShape(14.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, GoldDim.copy(alpha = 0.3f))) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.AutoAwesome, "ai", tint = Gold)
                Spacer(Modifier.width(8.dp))
                Text("تحلیل هوشمند Apex AI", color = Gold, fontWeight = FontWeight.Black, fontSize = 14.sp)
                Spacer(Modifier.weight(1f))
                Surface(shape = RoundedCornerShape(5.dp), color = sideC.copy(alpha = 0.20f)) {
                    Text("  ${r.ai.side}  ", color = sideC, fontSize = 10.sp, fontWeight = FontWeight.Black)
                }
            }
            Spacer(Modifier.height(6.dp))
            Text(
                if (loading) "در حال تحلیل..." else safeChartMessage(r.ai.summary.ifBlank { r.note }),
                color = TH,
                fontSize = 12.sp,
                lineHeight = 20.sp
            )
            Spacer(Modifier.height(4.dp))
            Text(if (loading) "" else r.ai.recommendation, color = Gold, fontSize = 12.sp, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun WatchingCard(r: SmcReport) {
    Card(colors = CardDefaults.cardColors(containerColor = Surf2), shape = RoundedCornerShape(14.dp)) {
        Column(Modifier.padding(14.dp)) {
            Text("👀 ستاپ‌های زیر نظر", color = Gold, fontSize = 13.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(8.dp))
            r.watching.take(3).forEach { w ->
                val col = if (w.direction == "long") UpC else if (w.direction == "short") DnC else TL
                val lbl = if (w.direction == "long") "خرید" else if (w.direction == "short") "فروش" else "خنثی"
                val distPct = if (w.atr > 0f) (w.distance/w.atr) else 0f
                val statusLbl = when(w.status) { "in_zone" -> "✅ داخل ناحیه"; "approaching" -> "🟡 نزدیک"; else -> "🔴 دور" }
                Surface(shape = RoundedCornerShape(10.dp), color = col.copy(alpha=0.07f),
                    modifier = Modifier.fillMaxWidth().padding(vertical=3.dp)) {
                    Column(Modifier.padding(10.dp)) {
                        Row(horizontalArrangement=Arrangement.SpaceBetween, modifier=Modifier.fillMaxWidth()) {
                            Text(lbl, color=col, fontSize=12.sp, fontWeight=FontWeight.Black)
                            Text(statusLbl, color=col, fontSize=11.sp, fontWeight=FontWeight.Bold)
                        }
                        Spacer(Modifier.height(4.dp))
                        Text("فاصله: %.2f ATR • ورود: %s • SL: %s • TP: %s".format(distPct, fmt(w.entry), fmt(w.sl), fmt(w.tp)),
                            color=TL, fontSize=10.sp)
                        if (w.reasons.isNotEmpty()) {
                            Spacer(Modifier.height(3.dp))
                            Text("دلایل: " + w.reasons.joinToString(" / "), color=GoldDim, fontSize=10.sp)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun LevelsCard(r: SmcReport) {
    Card(colors = CardDefaults.cardColors(containerColor = Surf2), shape = RoundedCornerShape(14.dp)) {
        Column(modifier = Modifier.padding(14.dp)) {
            Text("طرح معامله (Entry / SL / TP1 / TP2 / TP3)", color = Gold, fontSize = 13.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(10.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                Lvl("Inval", r.invalidation, GoldDim)
                Lvl("SL",    r.levels.sl,    DnC)
                Lvl("Entry", r.levels.entry, Gold)
                Lvl("TP1",   r.tp1,          UpC.copy(alpha=0.8f))
                Lvl("TP2",   r.levels.tp,    UpC)
                Lvl("TP3",   r.tp3,          UpC.copy(alpha=0.6f))
            }
            Spacer(Modifier.height(6.dp))
            Text("⚖ Ω قانون ۱۰۰ اُمگا: حداکثر ۱% ریسک، RR≥1:2، بدون مارتینگل",
                color = GoldDim, fontSize = 10.sp, fontWeight = FontWeight.SemiBold)
        }
    }
}

private fun defaultChartScale(timeframe: String): Float = when (timeframe) {
    "1d" -> 2.8f
    "4h" -> 2.3f
    "1h" -> 1.8f
    "30m" -> 1.6f
    else -> 1.4f
}

// ======================== بوم چارت دقیقاً به سبک TradingView ========================
@Composable
private fun SmcCanvas(modifier: Modifier = Modifier, report: SmcReport, scale: Float, onScale: (Float)->Unit) {
    Canvas(modifier = modifier
        .background(ChartBg)
        .pointerInput(Unit) { detectTransformGestures { _, _, zoom, _ -> onScale(zoom) } }
    ) {
        val w = size.width; val h = size.height
        val candles = report.candles
        if (candles.isEmpty()) return@Canvas

        val totalCandles = candles.size
        val minimumVisible = min(40, totalCandles)
        val visibleCount = (totalCandles / scale).toInt()
            .coerceIn(minimumVisible, totalCandles)
        val startIdx = (totalCandles - visibleCount).coerceAtLeast(0)
        val visible = if (startIdx == 0) candles else candles.subList(startIdx, totalCandles)

        // Scale exclusively from candles that are actually visible. The API may
        // analyse more history than it returns; using the older global range was
        // compressing current candles into a flat line or giant vertical bars.
        var hi = visible.maxOf { it.h }
        var lo = visible.minOf { it.l }
        val range = (hi - lo).takeIf { it > 0f } ?: max(abs(hi) * 0.001f, 0.0001f)
        val pricePad = range * 0.07f
        hi += pricePad
        lo -= pricePad
        val nr = (hi - lo).coerceAtLeast(0.0000001f)

        val maxVisibleVolume = visible.maxOfOrNull { abs(it.v) } ?: 0f
        val hasVolume = maxVisibleVolume > 0f

        // Wider right axis prevents Forex and high-price crypto labels clipping.
        val axisW = 78f
        val chartL = 3f
        val chartR = w - axisW
        val volH = if (hasVolume) 40f else 0f
        val chartT = 24f
        val chartB = h - volH - 4f
        val chartW = chartR - chartL
        val chartH = chartB - chartT
        val volT = chartB + 4f
        val volB = h - 2f
        val cw = chartW / visible.size.toFloat()
        val bw = (cw * 0.70f).coerceAtLeast(1.3f)

        fun priceY(p: Float) = chartT + (hi - p)/nr * chartH
        fun idxX(i: Int) = chartL + (i - startIdx)*cw + cw/2

        // پس‌زمینه پنل حجم جدا
        drawRect(Color(0xFF0F1420), topLeft = Offset(chartL, volT-2f), size = Size(chartW+axisW, h - volT))

        // گرید افقی
        val gridN = 6
        for (i in 0..gridN) {
            val y = chartT + chartH*i/gridN
            drawLine(ChartGrid, Offset(chartL, y), Offset(chartR, y), strokeWidth=0.6f)
        }
        // محور عمودی قیمت (راست)
        drawRect(Color(0xFF0F1420), topLeft = Offset(chartR, chartT), size = Size(axisW, h-chartT))
        drawLine(ChartGrid, Offset(chartR, chartT), Offset(chartR, h), strokeWidth = 1f)

        val df = java.text.DecimalFormat(
            when {
                hi >= 1000f -> "0.00"
                hi >= 100f -> "0.000"
                else -> "0.00000"
            }
        )
        val axisText = NativePaint().apply {
            color = TL.toArgb()
            textSize = 15f
            isAntiAlias = true
            textAlign = NativePaint.Align.LEFT
        }
        for (i in 0..gridN) {
            val y = chartT + chartH*i/gridN
            val p = hi - nr*i/gridN
            drawContext.canvas.nativeCanvas.drawText(df.format(p), chartR+6f, y+6f, axisText)
        }

        // ======== Recent intraday Killzones only ========
        var lastKillzoneLabelRight = -1f
        val showKillzones = report.timeframe !in listOf("4h", "1d")
        if (showKillzones) {
            for (kz in report.killzones.takeLast(6)) {
                val zoneStart = kz.startIdx.coerceAtLeast(startIdx)
                val zoneEnd = kz.endIdx.coerceAtMost(totalCandles - 1)
                if (zoneEnd < startIdx || zoneStart > totalCandles - 1) continue
                val x1 = (idxX(zoneStart) - cw / 2).coerceIn(chartL, chartR)
                val x2 = (idxX(zoneEnd) + cw / 2).coerceIn(chartL, chartR)
                if (x2 <= x1) continue
                val kzCol = when {
                    kz.name.contains("لندن") && kz.name.contains("نیویورک") -> KzOver.copy(alpha = 0.16f)
                    kz.name.contains("نیویورک") -> KzNy.copy(alpha = 0.13f)
                    kz.name.contains("لندن") -> KzLon.copy(alpha = 0.13f)
                    else -> KzAsia.copy(alpha = 0.10f)
                }
                drawRect(kzCol, topLeft = Offset(x1, chartT), size = Size(x2 - x1, chartH))

                // Draw a single short label only when the zone is wide enough
                // and it cannot collide with the previous label.
                val zoneWidth = x2 - x1
                val labelX = (x1 + x2) / 2f
                if (zoneWidth >= 72f && x1 > lastKillzoneLabelRight + 8f) {
                    val label = when {
                        kz.name.contains("لندن") && kz.name.contains("نیویورک") -> "Overlap"
                        kz.name.contains("نیویورک") -> "New York"
                        kz.name.contains("لندن") -> "London"
                        else -> "Asia"
                    }
                    val paint = NativePaint().apply {
                        color = TH.toArgb()
                        textSize = 13f
                        isAntiAlias = true
                        isFakeBoldText = true
                        textAlign = NativePaint.Align.CENTER
                    }
                    drawContext.canvas.nativeCanvas.drawText(label, labelX, chartT + 14f, paint)
                    lastKillzoneLabelRight = x2
                }
            }
        }

        // ======== زون‌ها: OB/FVG/BRK پشت کندل‌ها ========
        for (z in report.overlay.zones) {
            if (z.kind == "KZ") continue
            if (z.kind !in listOf("OB", "FVG", "iFVG", "BRK")) continue
            val zoneStart = z.index
            val zoneEnd = if (z.endIdx >= zoneStart) z.endIdx else totalCandles - 1
            if (zoneEnd < startIdx || zoneStart >= totalCandles) continue
            val visibleZoneStart = max(zoneStart, startIdx)
            val visibleZoneEnd = min(zoneEnd, totalCandles - 1)
            val rawY1 = priceY(z.top)
            val rawY2 = priceY(z.bottom)
            if (max(rawY1, rawY2) < chartT || min(rawY1, rawY2) > chartB) continue
            val top = min(rawY1, rawY2).coerceIn(chartT, chartB)
            val bottom = max(rawY1, rawY2).coerceIn(chartT, chartB)
            val xstart = (idxX(visibleZoneStart) - cw / 2f).coerceIn(chartL, chartR)
            val xend = (idxX(visibleZoneEnd) + cw / 2f).coerceIn(chartL, chartR)
            val color = when(z.kind) {
                "OB" -> if(z.side=="bullish") BullOB else BearOB
                "FVG" -> FvgC
                "iFVG" -> iFvgC
                "BRK" -> BrkC
                else -> Color.Transparent
            }
            if (color == Color.Transparent || xend <= xstart) continue
            val zoneH = (bottom - top).coerceAtLeast(2f)
            val fillAlpha = when (z.kind) {
                "OB" -> 0.20f
                "FVG", "iFVG" -> 0.11f
                "BRK" -> 0.055f
                else -> 0.1f
            }
            val borderAlpha = when (z.kind) {
                "OB" -> 0.88f
                "FVG", "iFVG" -> 0.62f
                "BRK" -> 0.42f
                else -> 0.6f
            }
            drawRect(
                color=color.copy(alpha=fillAlpha),
                topLeft=Offset(xstart, top),
                size=Size(xend-xstart, zoneH)
            )
            drawRect(
                color=color.copy(alpha=borderAlpha),
                topLeft=Offset(xstart, top),
                size=Size(xend-xstart, zoneH),
                style=Stroke(
                    width=if (z.kind == "OB") 1.1f else 0.8f,
                    pathEffect=if (z.kind == "BRK") {
                        PathEffect.dashPathEffect(floatArrayOf(6f, 4f))
                    } else null
                )
            )
            // عنوان درون زون (مثل TV: Bearish Order Block داخل مستطیل نارنجی)
            val label = when(z.kind) {
                "OB" -> if(z.side=="bullish") "Bullish Order Block" else "Bearish Order Block"
                "BRK" -> "Breaker Block"
                "FVG" -> if (z.inverse) "iFVG" else "FVG"
                else -> z.kind
            }
            if (zoneH >= 11f && xend - xstart >= 64f) {
                val zoneLabelPaint = NativePaint().apply {
                    this.color = color.toArgb()
                    textSize = 12f
                    isAntiAlias = true
                    isFakeBoldText = true
                }
                val textX = xstart + 5f
                val textY = top + zoneH / 2f + 4f
                val textRect = Rect()
                zoneLabelPaint.getTextBounds(label, 0, label.length, textRect)
                val maxTextWidth = xend - textX - 3f
                if (textRect.width() <= maxTextWidth) {
                    drawRect(
                        color = ChartBg.copy(alpha = 0.72f),
                        topLeft = Offset(textX - 2f, textY + textRect.top - 2f),
                        size = Size(textRect.width() + 4f, textRect.height() + 4f)
                    )
                    drawContext.canvas.nativeCanvas.drawText(label, textX, textY, zoneLabelPaint)
                }
            }
        }

        // ======== Volume pane (hidden when Forex provider has no volume) ========
        if (hasVolume) {
            val maxVol = maxVisibleVolume.coerceAtLeast(1f)
            visible.forEachIndexed { idx, candle ->
                val x = idxX(idx + startIdx)
                val color = if (candle.c >= candle.o) VolUp else VolDn
                val volumeHeight = ((abs(candle.v) / maxVol) * (volB - volT - 2f))
                    .coerceAtLeast(1f)
                drawRect(
                    color,
                    topLeft = Offset(x - bw / 2f, volB - volumeHeight),
                    size = Size(bw, volumeHeight)
                )
            }
            drawLine(ChartGrid, Offset(chartL, volB), Offset(chartR, volB), strokeWidth = 0.6f)
        }

        // ======== کندل‌ها ========
        visible.forEachIndexed { idx, c ->
            val x = idxX(idx+startIdx)
            val up = c.c >= c.o
            val col = if (up) UpC else DnC
            val yH=priceY(c.h); val yL=priceY(c.l); val yO=priceY(c.o); val yC=priceY(c.c)
            drawLine(col, Offset(x,yH), Offset(x,yL), strokeWidth=1f)
            val top=kotlin.math.min(yO,yC); val hgt=kotlin.math.abs(yC-yO).coerceAtLeast(1.2f)
            drawRect(col, topLeft=Offset(x-bw/2, top), size=Size(bw, hgt))
        }

        // ======== VWAP ========
        if (report.vwap > 0f) {
            val y = priceY(report.vwap)
            if (y >= chartT && y <= chartB) {
                drawLine(VwapC.copy(alpha=0.7f), Offset(chartL, y), Offset(chartR, y), strokeWidth=1.1f,
                    pathEffect = PathEffect.dashPathEffect(floatArrayOf(5f,3f)))
                val vp = NativePaint().apply { color=VwapC.toArgb(); textSize=14f; isAntiAlias=true }
                drawContext.canvas.nativeCanvas.drawText("VWAP", chartL+4f, y-4f, vp)
            }
        }

        // ======== Only the latest EQH/EQL reference levels ========
        var lastArrowRight = false
        val plottedLiquidityY = mutableListOf<Float>()
        val simpleLiquidity = report.inducements
            .filter { it.kind in listOf("buyside_liq", "sellside_liq", "eqh", "eql") }
            .takeLast(4)
        for (lab in simpleLiquidity.asReversed()) {
            val col = when (lab.kind) {
                "buyside_liq", "eqh" -> DnC
                "sellside_liq", "eql" -> UpC
                else -> TL
            }
            val y = priceY(lab.price)
            if (y < chartT || y > chartB) continue
            if (plottedLiquidityY.any { abs(it - y) < 12f }) continue
            plottedLiquidityY += y
            val lineStartX = if (
                lab.kind.contains("liq") && lab.index in startIdx until totalCandles
            ) idxX(lab.index) else chartL
            drawLine(col.copy(alpha=0.48f), Offset(lineStartX, y), Offset(chartR, y), strokeWidth=0.8f,
                pathEffect=PathEffect.dashPathEffect(floatArrayOf(4f,3f)))
            val lbl = when(lab.kind) {
                "eqh" -> "EQH →"
                "eql" -> "EQL →"
                "buyside_liq" -> "BSL ▲"
                "sellside_liq" -> "SSL ▼"
                "recent_high_liq" -> "H →"
                "recent_low_liq" -> "L →"
                else -> ""
            }
            if (lbl.isNotEmpty()) {
                val lp = NativePaint().apply { color = col.toArgb(); textSize = 11f; isAntiAlias = true; isFakeBoldText = true }
                val ax = if (lab.kind.contains("liq")) {
                    chartR - 42f
                } else if (lastArrowRight) {
                    chartR - 42f
                } else {
                    chartL + 4f
                }
                drawContext.canvas.nativeCanvas.drawText(lbl, ax, y-4f, lp)
                if (!lab.kind.contains("liq")) lastArrowRight = !lastArrowRight
            }
        }

        // ======== BOS/CHoCH — فلش‌دار روی کندل، خط کوتاه به لیبل (مثل TV) ========
        for (ev in report.events.takeLast(4)) {
            if (ev.index < startIdx || ev.index >= totalCandles) continue
            val col = if (ev.dir == "bullish") UpC else DnC
            val y = priceY(ev.price)
            if (y < chartT || y > chartB) continue
            val idx = ev.index
            val x = idxX(idx)
            val isBull = ev.dir == "bullish"
            // خط افقی کوتاه
            val lineEndX = min(x + 48f, chartR - 48f)
            drawLine(col.copy(alpha=0.65f), Offset(x, y), Offset(lineEndX, y), strokeWidth=1.2f)
            // دایره کوچک روی کندل
            drawCircle(col, radius=3.5f, center=Offset(x, y))
            // لیبل جهت‌دار
            val lp = NativePaint().apply { color=col.toArgb(); textSize=11f; isAntiAlias=true; isFakeBoldText=true }
            val arr = if (isBull) "▲ ${ev.kind}" else "▼ ${ev.kind}"
            drawContext.canvas.nativeCanvas.drawText(arr, lineEndX+4f, y-4f, lp)
        }

        // ======== IDM نقاط زرد (Inducement) ========
        for (lab in report.inducements.takeLast(3)) {
            if (!lab.kind.contains("liq")) continue
            if (lab.index < startIdx || lab.index >= totalCandles) continue
            val idx = lab.index
            val x = idxX(idx); val y = priceY(lab.price)
            if (y < chartT || y > chartB) continue
            drawCircle(IdmColor, radius=3.5f, center=Offset(x, y))
            val lp = NativePaint().apply { color=IdmColor.toArgb(); textSize=12f; isAntiAlias=true; isFakeBoldText=true }
            drawContext.canvas.nativeCanvas.drawText("IDM", x+6f, y-5f, lp)
        }

        // ======== خطوط طرح معامله (فقط ستاپ معتبر) ========
        val actionable = report.grade !in listOf("F","D","-") &&
                report.direction in listOf("long","short") && report.omegaCompliant
        if (actionable) {
            for (pl in report.planLines.filter { it.kind in listOf("entry", "sl", "tp1") }) {
                val y = priceY(pl.price)
                if (y < chartT-2f || y > chartB+2f) continue
                val (c, label) = when(pl.kind) {
                    "entry" -> Gold to "Entry"
                    "sl"    -> DnC to "Safe SL"
                    "tp1"   -> UpC to "TP1"
                    "tp2"   -> UpC to "TP2"
                    "tp3"   -> UpC.copy(alpha=0.6f) to "TP3"
                    else    -> continue
                }
                val sw = if (pl.kind=="entry" || pl.kind=="sl") 1.5f else 1.0f
                drawLine(c, Offset(chartL, y), Offset(chartR, y), strokeWidth=sw,
                    pathEffect=if (pl.kind=="entry") null else PathEffect.dashPathEffect(floatArrayOf(6f,4f)))
                // لیبل به شکل باکس تیره در محور راست (Safe Stop-Loss TV-style)
                val lp = NativePaint().apply { color=android.graphics.Color.WHITE; textSize=13f; isAntiAlias=true; isFakeBoldText=true }
                val br = Rect(); lp.getTextBounds(label,0,label.length,br)
                val pad=5f
                val bx = chartR+2f
                val by = y - br.height()/2f - pad
                val bgC = NativePaint().apply { color=c.toArgb() }
                drawContext.canvas.nativeCanvas.drawRect(bx, by, bx + br.width()+pad*2, by + br.height()+pad*2, bgC)
                drawContext.canvas.nativeCanvas.drawText(label, bx+pad, y+br.height()/2f-1f, lp)
            }
        }

        // ======== قیمت لحظه‌ای (last price tag) مثل TV: برچسب روی محور راست ========
        val yPrice = priceY(report.price).coerceIn(chartT, chartB)
        val lastCol = if (candles.lastOrNull()?.let { it.c >= it.o } == true) UpC else DnC
        drawLine(lastCol.copy(alpha=0.9f), Offset(chartL, yPrice), Offset(chartR, yPrice), strokeWidth=1.2f,
            pathEffect=PathEffect.dashPathEffect(floatArrayOf(3f,3f)))
        drawCircle(lastCol, radius=3.5f, center=Offset(chartR-2f, yPrice))
        val plbl = df.format(report.price)
        val pp = NativePaint().apply { color=android.graphics.Color.WHITE; textSize=13f; isAntiAlias=true; isFakeBoldText=true }
        val pr = Rect(); pp.getTextBounds(plbl,0,plbl.length,pr)
        val ppad=4f
        val pbx = chartR+2f
        val pby = yPrice - pr.height()/2f - ppad
        val pbg = NativePaint().apply { color=lastCol.toArgb() }
        drawContext.canvas.nativeCanvas.drawRect(pbx, pby, pbx + pr.width()+ppad*2, pby + pr.height()+ppad*2, pbg)
        drawContext.canvas.nativeCanvas.drawText(plbl, pbx+ppad, yPrice+pr.height()/2f-2f, pp)

        // نام اندیکاتور/برچسب در گوشه چپ پایین چارت
        if (hasVolume) {
            val volumeLabelPaint = NativePaint().apply { color=TL.toArgb(); textSize=11f; isAntiAlias=true }
            drawContext.canvas.nativeCanvas.drawText("Volume", 6f, volT+12f, volumeLabelPaint)
        }
    }
}

// ======================== ابزارهای کوچک ========================
@Composable private fun Label(t: String) = Text(t, color=TL, fontSize=10.sp, fontWeight=FontWeight.SemiBold)
@Composable
private fun ChipRow(options: List<String>, selected: String, onPick:(String)->Unit) {
    val listState = rememberLazyListState()
    LaunchedEffect(selected, options) {
        val index = options.indexOf(selected)
        if (index >= 0) listState.animateScrollToItem(index)
    }
    CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Ltr) {
        LazyRow(
            state = listState,
            horizontalArrangement = Arrangement.spacedBy(6.dp),
            contentPadding = PaddingValues(horizontal = 2.dp)
        ) {
            items(options) { option ->
                val selectedOption = option == selected
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = if (selectedOption) Gold else Surf,
                    modifier = Modifier.clickable { onPick(option) }
                ) {
                    Text(
                        text = option,
                        color = if (selectedOption) Color.Black else TH,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp)
                    )
                }
            }
        }
    }
}
@Composable private fun Section(t:String, c:Color) = Text(t, color=c, fontSize=13.sp, fontWeight=FontWeight.Black, modifier=Modifier.padding(top=4.dp))
@Composable
private fun RowScope.Lvl(label:String, v:Float?, c:Color) {
    Card(colors=CardDefaults.cardColors(containerColor=BgDark), shape=RoundedCornerShape(10.dp), modifier=Modifier.weight(1f)) {
        Column(Modifier.padding(9.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Text(label, color=TL, fontSize=11.sp)
            Spacer(Modifier.height(4.dp))
            Text(if(v!=null && v>0f) fmt(v) else "-", color=c, fontSize=14.sp, fontWeight=FontWeight.Black)
        }
    }
}
@Composable
private fun Zc(z:SmcZone, tag:String, c:Color, name:String="") {
    Card(colors=CardDefaults.cardColors(containerColor=Surf2), shape=RoundedCornerShape(10.dp)) {
        Column(Modifier.fillMaxWidth().padding(12.dp)) {
            Row(horizontalArrangement=Arrangement.SpaceBetween, modifier=Modifier.fillMaxWidth()) {
                Text(if(name.isNotBlank()) "$tag · $name" else "$tag · ${z.side.ifBlank{z.kind}}",
                    color=c, fontSize=12.sp, fontWeight=FontWeight.Black)
                Text("idx ${z.index}", color=TL, fontSize=10.sp)
            }
            Spacer(Modifier.height(6.dp))
            Row(horizontalArrangement=Arrangement.spacedBy(14.dp)) {
                Text("بالا: ${fmt(z.top)}", color=UpC, fontSize=12.sp)
                Text("پایین: ${fmt(z.bottom)}", color=DnC, fontSize=12.sp)
                if (z.quality>0) Text("★".repeat(z.quality.coerceAtMost(5)), color=Gold, fontSize=12.sp)
            }
        }
    }
}
@Composable
private fun KzRow(kz:SmcZone) {
    val c = when {
        kz.name.contains("لندن") && kz.name.contains("نیویورک") -> Gold
        kz.name.contains("نیویورک") -> DnC
        kz.name.contains("لندن") -> LiqC
        else -> GoldDim
    }
    Card(colors=CardDefaults.cardColors(containerColor=Surf2), shape=RoundedCornerShape(10.dp)) {
        Row(Modifier.fillMaxWidth().padding(12.dp), horizontalArrangement=Arrangement.SpaceBetween, verticalAlignment=Alignment.CenterVertically) {
            Text("◼ ${kz.name}", color=c, fontSize=12.sp, fontWeight=FontWeight.Black)
            Text("کندل ${kz.startIdx}–${kz.endIdx}", color=TL, fontSize=11.sp)
        }
    }
}
@Composable
private fun LiqRow(kind:String, price:Float) {
    val label = when {
        kind=="buyside_liq" -> "BSL ▲ (Buy-side liquidity)"
        kind=="sellside_liq" -> "SSL ▼ (Sell-side liquidity)"
        kind=="eqh" -> "EQH — سقف‌های برابر"
        kind=="eql" -> "EQL — کف‌های برابر"
        else -> kind.replace("_"," ")
    }
    val col = when {
        kind.contains("sell")||kind=="eqh"||kind.contains("high") -> DnC
        kind.contains("buy")||kind=="eql"||kind.contains("low") -> UpC
        else -> LiqC
    }
    Card(colors=CardDefaults.cardColors(containerColor=Surf2), shape=RoundedCornerShape(10.dp)) {
        Row(Modifier.fillMaxWidth().padding(12.dp), horizontalArrangement=Arrangement.SpaceBetween) {
            Text(label, color=col, fontSize=12.sp, fontWeight=FontWeight.Bold)
            Text(fmt(price), color=TH, fontSize=12.sp, fontWeight=FontWeight.SemiBold)
        }
    }
}
@Composable
private fun EventRow(kind:String, dir:String, price:Float) {
    val col = if (dir=="bullish") UpC else DnC
    val label = when(kind) { "BOS"->"BOS — شکست ساختار"; "CHoCH"->"CHoCH — تغییر ساختار"; else->kind }
    Card(colors=CardDefaults.cardColors(containerColor=Surf2), shape=RoundedCornerShape(10.dp)) {
        Row(Modifier.fillMaxWidth().padding(12.dp), horizontalArrangement=Arrangement.SpaceBetween) {
            Text("$label · ${dir.uppercase()}", color=col, fontSize=12.sp, fontWeight=FontWeight.Bold)
            Text(fmt(price), color=TH, fontSize=12.sp, fontWeight=FontWeight.SemiBold)
        }
    }
}
@Composable private fun LegendDot(c:Color, text:String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(8.dp).clip(CircleShape).background(c))
        Spacer(Modifier.width(4.dp))
        Text(text, color=TL, fontSize=9.sp, fontWeight=FontWeight.SemiBold)
    }
}
@Composable
private fun ChipS(t:String, c:Color) {
    Surface(color=c.copy(alpha=0.18f), shape=RoundedCornerShape(999.dp)) {
        Text(t, color=c, fontSize=10.sp, fontWeight=FontWeight.Black,
            modifier=Modifier.padding(horizontal=9.dp, vertical=4.dp))
    }
}
private fun safeChartMessage(message: String): String {
    val value = message.trim()
    if (value.isBlank()) return "-"
    val unsafe = listOf("apikey=", "api_key=", "token=", "https://", "http://")
        .any { value.contains(it, ignoreCase = true) }
    return if (unsafe) {
        "داده بازار موقتاً در دسترس نیست؛ چند لحظه دیگر دوباره تلاش کنید."
    } else value
}

internal fun fmt(v:Float): String {
    if (v<=0f) return "-"
    return when {
        v>1000 -> "%.2f".format(v)
        v>100  -> "%.3f".format(v)
        else -> "%.4f".format(v)
    }
}

@Composable
fun AiSignalBoard(signals: List<com.arena.smartmoney.data.model.SmcSignal>, loading: Boolean, onRefresh: ()->Unit) {
    Card(colors = CardDefaults.cardColors(containerColor = Color(0xFF161C25)), shape = RoundedCornerShape(14.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, Gold.copy(alpha=0.35f))) {
        Column(Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.AutoAwesome, "ai", tint = Gold)
                Spacer(Modifier.width(8.dp))
                Text("Apex AI Pro SMC — اسکن زنده", color = Gold, fontWeight = FontWeight.Black, fontSize = 14.sp)
                Spacer(Modifier.weight(1f))
                androidx.compose.material3.IconButton(onClick = onRefresh) {
                    Icon(Icons.Default.Refresh, "refresh", tint = Gold)
                }
            }
            if (loading) {
                Text("در حال اسکن بازار...", color = TL, fontSize = 12.sp)
            } else if (signals.isEmpty()) {
                Text("ستاپ با کانفلونس بالا پیدا نشد.", color = TL, fontSize = 12.sp)
            } else {
                Text("${signals.size} سیگنال فعال", color = TH, fontSize = 12.sp)
                Spacer(Modifier.height(6.dp))
                signals.take(5).forEach { s ->
                    val col = if (s.direction == "long") UpC else if (s.direction == "short") DnC else GoldDim
                    val side = if (s.direction == "long") "خرید" else if (s.direction == "short") "فروش" else "انتظار"
                    Surface(shape = RoundedCornerShape(10.dp), color = col.copy(alpha = 0.08f),
                        modifier = Modifier.fillMaxWidth().padding(vertical = 3.dp)) {
                        Row(Modifier.padding(10.dp), verticalAlignment = Alignment.CenterVertically) {
                            Column(Modifier.weight(1f)) {
                                Text("${s.symbol} · ${s.timeframe}", color = TH, fontSize = 13.sp, fontWeight = FontWeight.Black)
                                Text(s.note, color = TL, fontSize = 11.sp, maxLines = 1)
                            }
                            Column(horizontalAlignment = Alignment.End) {
                                Surface(shape = RoundedCornerShape(6.dp), color = col.copy(alpha=0.2f)) {
                                    Text("  $side  ", color = col, fontSize = 10.sp, fontWeight = FontWeight.Black)
                                }
                                Spacer(Modifier.height(3.dp))
                                Text("${s.grade} · conf ${s.confluence} · %${s.probability} · RR 1:" + "%.1f".format(s.rr), color = col, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }
            }
        }
    }
}
