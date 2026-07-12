@file:OptIn(ExperimentalMaterial3Api::class)
package com.arena.smartmoney.ui.chart

import android.graphics.Paint as NativePaint
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.arena.smartmoney.data.model.SmcCandle
import com.arena.smartmoney.data.model.SmcReport
import com.arena.smartmoney.data.model.SmcZone
import com.arena.smartmoney.data.repository.TradingRepository
import kotlinx.coroutines.launch

// ===== رنگ‌های لوکس تیره + طلایی =====
private val BgDark   = Color(0xFF070A11)
private val Surf     = Color(0xFF101621)
private val Surf2    = Color(0xFF171F2D)
private val GridLn   = Color(0xFF1C2638)
private val Gold     = Color(0xFFD4AF37)
private val GoldDim  = Color(0xFF8C7630)
private val GoldSoft = Color(0xFF2E2714)
private val TH       = Color(0xFFF5F0DC)
private val TL       = Color(0xFF9099A8)
private val UpC      = Color(0xFF22C55E)
private val DnC      = Color(0xFFEF4444)
private val FvgC     = Color(0xFFB388FF)
private val iFvgC    = Color(0xFF7C4DFF)
private val BrkC     = Color(0xFFFF9F43)
private val LiqC     = Color(0xFF54A0FF)
private val KzAsia   = Color(0x2960A5FA)
private val KzLon    = Color(0x2BD4AF37)
private val KzNy     = Color(0x36EF4444)
private val KzOver   = Color(0x44D4AF37)
private val EqColor  = Color(0xFF94A3B8)

private val SYMBOLS = listOf("XAUUSD","EURUSD","GBPUSD","USDJPY","AUDUSD","BTCUSDT","ETHUSDT","SOLUSDT","US30","NAS100")
private val TIMEFRAMES = listOf("1m","5m","15m","30m","1h","4h","1d")

@Composable
fun ChartScreen(onBack: (() -> Unit)? = null) {
    val repo = remember { TradingRepository() }
    val scope = rememberCoroutineScope()
    var r by remember { mutableStateOf(SmcReport()) }
    var loading by remember { mutableStateOf(true) }
    var sym by remember { mutableStateOf("XAUUSD") }
    var mkt by remember { mutableStateOf("") }  // auto
    var tf  by remember { mutableStateOf("15m") }
    var scale by remember { mutableStateOf(1f) }

    fun load() {
        scope.launch {
            loading = true
            try { r = repo.getSmcAnalysis(sym, mkt, tf, 220) }
            finally { loading = false }
        }
    }
    LaunchedEffect(sym, tf) { load() }

    Scaffold(
        containerColor = BgDark,
        topBar = {
            TopAppBar(
                title = { Text("تحلیل هوشمند SMC", color = Gold, fontWeight = FontWeight.Black, fontSize = 19.sp) },
                navigationIcon = { if (onBack != null) IconButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, "back", tint = Gold) } },
                actions = { IconButton(onClick = { load() }) { Icon(Icons.Default.Refresh, "refresh", tint = Gold) } },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = BgDark)
            )
        }
    ) { pad ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(pad).padding(horizontal = 12.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            item {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Label("نماد")
                    ChipRow(SYMBOLS, sym) { sym = it; mkt = "" }
                    Label("تایم‌فریم")
                    ChipRow(TIMEFRAMES, tf) { tf = it; scale = 1f }
                }
            }
            item { HeaderCard(r, sym, mkt, tf, loading) }
            item {
                Card(colors = CardDefaults.cardColors(containerColor = Surf), shape = RoundedCornerShape(16.dp)) {
                    Column(modifier = Modifier.padding(10.dp)) {
                        Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                            Text("نمودار SMC", color = Gold, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                            Text("(با زوم دو انگشت)", color = TL, fontSize = 9.sp)
                        }
                        Spacer(Modifier.height(8.dp))
                        if (r.candles.isNotEmpty()) {
                            SmcCanvas(
                                modifier = Modifier.fillMaxWidth().height(280.dp),
                                report = r, scale = scale,
                                onScale = { scale = (scale * it).coerceIn(0.5f, 4f) }
                            )
                        } else {
                            Box(Modifier.fillMaxWidth().height(280.dp), contentAlignment = Alignment.Center) {
                                Text("داده کافی برای رسم نمودار نیست", color = TL, fontSize = 12.sp)
                            }
                        }
                        Spacer(Modifier.height(6.dp))
                        LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            item { LegendDot(UpC,  "Buy OB") }
                            item { LegendDot(DnC,  "Sell OB") }
                            item { LegendDot(FvgC, "FVG") }
                            item { LegendDot(iFvgC,"iFVG") }
                            item { LegendDot(BrkC, "Brk") }
                            item { LegendDot(LiqC, "Liq") }
                            item { LegendDot(KzLon,"KZ لندن") }
                            item { LegendDot(KzNy, "KZ نیویورک") }
                        }
                    }
                }
            }
            item { AiCard(r, loading) }
            item { LevelsCard(r) }
            if (r.watching.isNotEmpty()) item { WatchingCard(r) }
            if (r.killzones.isNotEmpty()) item { Section("سشن‌ها و کیل‌زون‌ها", Gold) }
            if (r.killzones.isNotEmpty()) items(r.killzones.take(4)) { kz ->
                KzRow(kz)
            }
            val liqSweeps = r.inducements.filter { it.kind.contains("liq") || it.kind.startsWith("eq") || it.kind.contains("recent") }
            if (liqSweeps.isNotEmpty()) item { Section("بای‌ساید / سل‌ساید لیکوئیدیتی", LiqC) }
            if (liqSweeps.isNotEmpty()) items(liqSweeps.take(6)) { LiqRow(it.kind, it.price) }
            if (r.orderBlocks.isNotEmpty()) item { Section("اوردر بلاک‌ها", Gold) }
            if (r.orderBlocks.isNotEmpty()) items(r.orderBlocks.take(5)) { Zc(it, "OB", if (it.kind == "bullish" || it.side == "bullish") UpC else DnC) }
            if (r.fvg.isNotEmpty()) item { Section("نواحی عدم تعادل FVG / iFVG", FvgC) }
            if (r.fvg.isNotEmpty()) items(r.fvg.take(6)) { g -> Zc(g, if (g.inverse) "iFVG" else "FVG", if (g.inverse) iFvgC else FvgC) }
            if (r.breakers.isNotEmpty()) item { Section("بریکر بلاک‌ها", BrkC) }
            if (r.breakers.isNotEmpty()) items(r.breakers.take(4)) { Zc(it, "BRK", BrkC) }
            if (r.events.isNotEmpty()) item { Section("وقایع ساختاری BOS / CHoCH", Gold) }
            if (r.events.isNotEmpty()) items(r.events.takeLast(6)) { ev -> EventRow(ev.kind, ev.dir, ev.price) }
            item { Spacer(Modifier.height(40.dp)) }
            item { Text("Created by Amin Omidi", color = GoldDim, fontSize = 11.sp,
                modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Center)
                Spacer(Modifier.height(18.dp)) }
        }
    }
}

// ========== هدر ==========
@Composable
private fun HeaderCard(r: SmcReport, sym: String, mkt: String, tf: String, loading: Boolean) {
    Card(colors = CardDefaults.cardColors(containerColor = Surf), shape = RoundedCornerShape(16.dp)) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                Column {
                    Text(r.symbol.ifBlank { sym }, color = TH, fontSize = 24.sp, fontWeight = FontWeight.Black)
                    val tflbl = r.timeframe.ifBlank { tf }
                    val mklbl = r.market.ifBlank { if (mkt.isBlank()) "auto" else mkt }.uppercase()
                    Text("$tflbl  •  $mklbl", color = TL, fontSize = 11.sp)
                    r.htf.bias?.let { hb ->
                        r.htf.timeframe?.let { htf ->
                            val hc = when(hb){"bullish"->UpC;"bearish"->DnC;else->GoldDim}
                            Spacer(Modifier.height(4.dp))
                            Surface(shape=RoundedCornerShape(6.dp), color=hc.copy(alpha=0.15f)){
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
                    Surface(shape = RoundedCornerShape(6.dp), color = bc.copy(alpha = 0.15f)) {
                        Text("  $bl  ", color = bc, fontSize = 10.sp, fontWeight = FontWeight.Black)
                    }
                }
            }
            Spacer(Modifier.height(10.dp))
            // First row: key metrics (grade/conf/prob/RR/TS)
            LazyRow(horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                item {
                    val gradeC = when(r.grade) {
                        "A+","A" -> Gold; "B" -> UpC; "C" -> GoldDim; "D" -> BrkC; else -> TL
                    }
                    ChipS("درجه ${r.grade}", gradeC)
                }
                item { ChipS("conf ${r.confluence}", when { r.confluence>=70->Gold; r.confluence>=40->GoldDim; else->TL }) }
                item { ChipS(if(r.probability>0) "%${r.probability}" else "احتمال -", when { r.probability>=75->UpC; r.probability>=55->GoldDim; else->TL }) }
                item { ChipS(if (r.rr > 0f) "RR 1:%.1f".format(r.rr) else "RR -", if(r.rr>=2f) UpC else TL) }
                item { ChipS("TS ${r.trendStrength}", when{r.trendStrength>=60->UpC;r.trendStrength<30->DnC;else->TL}) }
                item { ChipS("${r.candlesCount}c", TL) }
            }
            Spacer(Modifier.height(4.dp))
            // Second row: OF/session/news
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
                item { ChipS(when(r.premiumZone){"premium"->"پرمیوم";"discount"->"دیسکانت";else->"تعادل"}, GoldDim) }
                if (r.newsBlocked) item { ChipS("⚠️خبر", DnC) }
                if (r.mtfAligned) item { ChipS("MTF✓", UpC) }
                item { ChipS(r.status.ifBlank { "-" }, TL) }
            }
            if (r.setupType != "-" && r.setupType.isNotBlank()) {
                Spacer(Modifier.height(6.dp))
                Surface(shape=RoundedCornerShape(8.dp), color=Gold.copy(alpha=0.18f)) {
                    Text("  ستاپ: ${r.setupType}  ", color=Gold, fontSize=11.sp, fontWeight=FontWeight.Black)
                }
            }
            Spacer(Modifier.height(8.dp))
            Text(if (loading) "در حال بارگذاری..." else r.note.ifBlank { "-" }, color = TH, fontSize = 12.sp, lineHeight = 18.sp)
            if (r.sessionActive != "-") {
                Spacer(Modifier.height(6.dp))
                Text("سشن فعال: ${r.sessionActive}  •  VWAP ${fmt(r.vwap)}", color = GoldDim, fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
            } else {
                Spacer(Modifier.height(6.dp))
                Text("VWAP: ${fmt(r.vwap)}", color = TL, fontSize = 11.sp)
            }
        }
    }
}

// ========== کارت هوش مصنوعی ==========
@Composable
private fun AiCard(r: SmcReport, loading: Boolean) {
    val sideC = when (r.direction) { "long" -> UpC; "short" -> DnC; else -> GoldDim }
    Card(colors = CardDefaults.cardColors(containerColor = GoldSoft), shape = RoundedCornerShape(16.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, GoldDim.copy(alpha = 0.3f))) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.AutoAwesome, "ai", tint = Gold)
                Spacer(Modifier.width(8.dp))
                Text("تحلیل هوشمند Apex AI", color = Gold, fontWeight = FontWeight.Black, fontSize = 14.sp)
                Spacer(Modifier.weight(1f))
                Surface(shape = RoundedCornerShape(6.dp), color = sideC.copy(alpha = 0.18f)) {
                    Text("  ${r.ai.side}  ", color = sideC, fontSize = 10.sp, fontWeight = FontWeight.Black)
                }
            }
            Spacer(Modifier.height(8.dp))
            Text(if (loading) "در حال تحلیل..." else r.ai.summary.ifBlank { r.note },
                color = TH, fontSize = 12.sp, lineHeight = 22.sp)
            Spacer(Modifier.height(6.dp))
            Text(if (loading) "" else r.ai.recommendation, color = Gold, fontSize = 12.sp, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun WatchingCard(r: SmcReport) {
    Card(colors = CardDefaults.cardColors(containerColor = Surf2), shape = RoundedCornerShape(16.dp)) {
        Column(Modifier.padding(14.dp)) {
            Text("👀 ستاپ‌های زیر نظر (Watching)", color = Gold, fontSize = 13.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(8.dp))
            r.watching.take(3).forEach { w ->
                val col = if (w.direction == "long") UpC else if (w.direction == "short") DnC else TL
                val lbl = if (w.direction == "long") "خرید (LONG)" else if (w.direction == "short") "فروش (SHORT)" else "خنثی"
                val distPct = if (w.atr > 0f) (w.distance/w.atr) else 0f
                val statusLbl = when(w.status) {
                    "in_zone" -> "✅ داخل ناحیه"
                    "approaching" -> "🟡 نزدیک"
                    else -> "🔴 دور"
                }
                Surface(shape = RoundedCornerShape(10.dp), color = col.copy(alpha=0.08f),
                    modifier = Modifier.fillMaxWidth().padding(vertical=3.dp)) {
                    Column(Modifier.padding(10.dp)) {
                        Row(horizontalArrangement=Arrangement.SpaceBetween, modifier=Modifier.fillMaxWidth()) {
                            Text(lbl, color=col, fontSize=12.sp, fontWeight=FontWeight.Black)
                            Text(statusLbl, color=col, fontSize=11.sp, fontWeight=FontWeight.Bold)
                        }
                        Spacer(Modifier.height(4.dp))
                        Text("فاصله: %.2f ATR • ورود: %s • SL: %s • TP: %s".format(
                            distPct, fmt(w.entry), fmt(w.sl), fmt(w.tp)),
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
    Card(colors = CardDefaults.cardColors(containerColor = Surf2), shape = RoundedCornerShape(16.dp)) {
        Column(modifier = Modifier.padding(14.dp)) {
            Text("طرح معامله (Entry / SL / TP1 / TP2 / TP3)", color = Gold, fontSize = 13.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(10.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                Lvl("Inval", r.invalidation, GoldDim)
                Lvl("SL",    r.levels.sl,    DnC)
                Lvl("Entry", r.levels.entry, Gold)
                Lvl("TP1",   r.tp1,          UpC.copy(alpha=0.8f))
                Lvl("TP2",   r.levels.tp,    UpC)
                Lvl("TP3",   r.tp3,          UpC.copy(alpha=0.6f))
            }
            if (r.entryZone != null) {
                Spacer(Modifier.height(6.dp))
                Text("محدوده ورود: ${fmt(r.entryZone.low)} — ${fmt(r.entryZone.high)}", color = TL, fontSize = 11.sp)
            }
        }
    }
}

// ========== بوم نمودار ==========
@Composable
private fun SmcCanvas(modifier: Modifier = Modifier, report: SmcReport, scale: Float, onScale: (Float)->Unit) {
    Canvas(modifier = modifier
        .background(BgDark, RoundedCornerShape(10.dp))
        .pointerInput(Unit) { detectTransformGestures { _, _, zoom, _ -> onScale(zoom) } }
    ) {
        val w = size.width; val h = size.height
        val candles = report.candles
        if (candles.isEmpty()) return@Canvas

        val totalCandles = candles.size
        val visibleCount = (totalCandles / scale).toInt().coerceIn(20, totalCandles)
        val startIdx = (totalCandles - visibleCount).coerceAtLeast(0)
        val visible = if (startIdx == 0) candles else candles.subList(startIdx, totalCandles)

        // Use visible_range if available (outlier-trimmed)
        var hi = report.visibleRange.high; var lo = report.visibleRange.low
        if (hi <= lo) { hi = visible.maxOf { it.h }; lo = visible.minOf { it.l } }
        val range = (hi - lo).takeIf { it > 0f } ?: 1f
        val pricePad = range * 0.05f
        hi += pricePad; lo -= pricePad; val nr = hi-lo

        val chartL = 4f; val chartR = w - 62f; val chartT = 28f; val chartB = h - 4f
        val chartW = chartR - chartL; val chartH = chartB - chartT
        val cw = chartW / visible.size.toFloat()
        val bw = (cw * 0.65f).coerceAtLeast(1.5f)

        fun priceY(p: Float) = chartT + (hi - p)/nr * chartH
        fun idxX(i: Int) = chartL + (i - startIdx)*cw + cw/2

        // Grid
        for (i in 0..5) {
            val y = chartT + chartH*i/5f
            drawLine(GridLn, Offset(chartL, y), Offset(chartR, y), strokeWidth=0.6f)
        }
        val df = java.text.DecimalFormat(if (hi > 1000) "0.00" else "0.0000")
        val axisPaint = NativePaint().apply { color = TL.toArgb(); textSize=22f; isAntiAlias=true }
        for (i in 0..5) {
            val y = chartT + chartH*i/5f
            val p = hi - nr*i/5f
            drawContext.canvas.nativeCanvas.drawText(df.format(p), w-58f, y+8f, axisPaint)
        }
        // zero baseline not needed

        // Killzones (full-height)
        for (kz in report.killzones) {
            val s = kz.startIdx.coerceAtLeast(startIdx); val e = kz.endIdx.coerceAtMost(totalCandles-1)
            if (e < startIdx || s > totalCandles-1) continue
            val x1 = idxX(s) - cw/2; val x2 = idxX(e) + cw/2
            val kzCol = when {
                kz.name.contains("نیویورک") && kz.name.contains("لندن") -> KzOver
                kz.name.contains("نیویورک") -> KzNy
                kz.name.contains("لندن") -> KzLon
                else -> KzAsia
            }
            drawRect(kzCol, topLeft = Offset(x1, chartT), size = Size(x2-x1, chartH))
            val kzPaint = NativePaint().apply {
                color = kzCol.copy(alpha = 0.95f).toArgb(); textSize = 18f; isAntiAlias = true
                isFakeBoldText = true
            }
            drawContext.canvas.nativeCanvas.drawText(kz.name, x1+6f, chartT-4f, kzPaint)
        }

        // Zones (OB/FVG/BRK) - draw slightly wider than 1 candle
        for (z in report.overlay.zones) {
            if (z.kind == "KZ") continue
            val i = z.index; if (i<startIdx || i>=totalCandles) continue
            val top = priceY(z.top); val bot = priceY(z.bottom)
            val xstart = idxX(i) - cw
            // Extend OB/BRK zones forward to current price
            val extend = (z.kind == "OB" || z.kind == "BRK")
            val xend = if (extend) chartR else idxX(i) + cw*2
            val color = when(z.kind) {
                "OB" -> if(z.side=="bullish") UpC else DnC
                "FVG" -> if(z.inverse) iFvgC else FvgC
                "BRK" -> BrkC
                else -> Color.Transparent
            }
            if (color == Color.Transparent) continue
            drawRect(color=color.copy(alpha=0.20f), topLeft=Offset(xstart, top), size=Size(xend-xstart, (bot-top).coerceAtLeast(2f)))
            drawRect(color=color.copy(alpha=0.7f), topLeft=Offset(xstart, top), size=Size(xend-xstart, (bot-top).coerceAtLeast(2f)), style=Stroke(1.2f))
            // Tag with quality stars
            val stars = if (z.quality >= 1) "★".repeat(z.quality.coerceAtMost(5)) else ""
            val fresh_dot = if (z.fresh) "●" else "○"
            val tag = "${z.kind} $fresh_dot$stars"
            val tp = NativePaint().apply { this.color = color.toArgb(); textSize = 18f; isAntiAlias = true }
            drawContext.canvas.nativeCanvas.drawText(tag, xstart+4f, top-4f, tp)
        }

        // Candles
        visible.forEachIndexed { idx, c ->
            val x = idxX(idx+startIdx)
            val up = c.c >= c.o
            val col = if (up) UpC else DnC
            val yH=priceY(c.h); val yL=priceY(c.l); val yO=priceY(c.o); val yC=priceY(c.c)
            drawLine(col, Offset(x,yH), Offset(x,yL), strokeWidth=1f)
            val top=kotlin.math.min(yO,yC); val hgt=kotlin.math.abs(yC-yO).coerceAtLeast(1.2f)
            drawRect(col, topLeft=Offset(x-bw/2, top), size=Size(bw, hgt))
        }

        // VWAP line
        if (report.vwap > 0f) {
            val y = priceY(report.vwap)
            if (y >= chartT-5f && y <= chartB+5f) {
                drawLine(Color.Cyan.copy(alpha=0.55f), Offset(chartL, y), Offset(chartR, y), strokeWidth=1f,
                    pathEffect = PathEffect.dashPathEffect(floatArrayOf(3f,3f)))
                val vp = NativePaint().apply { color=android.graphics.Color.CYAN; textSize=17f; isAntiAlias=true }
                drawContext.canvas.nativeCanvas.drawText("VWAP", 6f, y-4f, vp)
            }
        }
        // Fib lines from overlay (fib50/fib62/fib79)
        for (fl in report.overlay.lines) {
            if (fl.kind == "vwap" || fl.kind.startsWith("fib")) {
                val col = when(fl.kind) {
                    "fib50" -> Color.Magenta.copy(alpha=0.45f)
                    "fib62" -> Color(0xFFfbbf24).copy(alpha=0.55f)
                    "fib79" -> Color(0xFFef4444).copy(alpha=0.55f)
                    else -> Color.Transparent
                }
                if (col == Color.Transparent) continue
                val y = priceY(fl.price)
                if (y < chartT-5f || y > chartB+5f) continue
                drawLine(col, Offset(chartL, y), Offset(chartR, y), strokeWidth=0.8f,
                    pathEffect = PathEffect.dashPathEffect(floatArrayOf(2f,4f)))
                val fp = NativePaint().apply { this.color = col.toArgb(); textSize = 16f; isAntiAlias = true }
                drawContext.canvas.nativeCanvas.drawText(fl.kind.uppercase(), 6f, y-4f, fp)
            }
        }
        // Liquidity / EQ lines + labels (alternate label sides to avoid overlap)
        var liLabelRight = false
        for (lab in report.inducements) {
            val col = when {
                lab.kind.contains("buyside") -> UpC
                lab.kind.contains("sellside") -> DnC
                lab.kind.startsWith("eq") -> EqColor
                lab.kind.contains("recent_high") -> DnC.copy(alpha=0.6f)
                lab.kind.contains("recent_low") -> UpC.copy(alpha=0.6f)
                else -> LiqC
            }
            val y = priceY(lab.price)
            if (y < chartT-5f || y > chartB+5f) continue
            drawLine(col.copy(alpha=0.75f), Offset(chartL, y), Offset(chartR, y), strokeWidth=0.9f,
                pathEffect = PathEffect.dashPathEffect(floatArrayOf(6f,4f)))
            val lbl = when(lab.kind) {
                "buyside_liq" -> "BUY LIQ ▲"
                "sellside_liq" -> "SELL LIQ ▼"
                "eqh" -> "EQH"
                "eql" -> "EQL"
                "recent_high_liq" -> "H"
                "recent_low_liq" -> "L"
                else -> lab.kind
            }
            val lp = NativePaint().apply { color = col.toArgb(); textSize = 16f; isAntiAlias = true }
            if (liLabelRight) {
                drawContext.canvas.nativeCanvas.drawText(lbl, chartR+4f, y-3f, lp)
            } else {
                drawContext.canvas.nativeCanvas.drawText(lbl, 6f, y-4f, lp)
            }
            liLabelRight = !liLabelRight
        }
        // BOS / CHoCH (label at event location, not stacked on left)
        for (ev in report.events.takeLast(8)) {
            val col = if (ev.dir == "bullish") UpC else DnC
            val y = priceY(ev.price)
            if (y < chartT-5f || y > chartB+5f) continue
            drawLine(col.copy(alpha=0.5f), Offset(chartL, y), Offset(chartR, y), strokeWidth=0.9f,
                pathEffect=PathEffect.dashPathEffect(floatArrayOf(3f,5f)))
            val idx = ev.index.coerceIn(startIdx, totalCandles-1)
            drawCircle(col, radius=5f, center=Offset(idxX(idx), y))
            val lp = NativePaint().apply { color = col.toArgb(); textSize = 15f; isAntiAlias = true; isFakeBoldText=true }
            drawContext.canvas.nativeCanvas.drawText(ev.kind, idxX(idx)+8f, y-5f, lp)
        }
        // Trade plan lines (entry/sl/tp) — only if actionable (grade not F)
        if (report.grade != "F" && report.direction != "neutral" && report.direction != "watching") {
            for (pl in report.planLines) {
                val y = priceY(pl.price)
                if (y < chartT-5f || y > chartB+5f) continue
                val (c, label) = when(pl.kind) {
                    "entry" -> Gold to "ENTRY"
                    "sl"    -> DnC to "SL"
                    "tp1"   -> UpC.copy(alpha=0.7f) to "TP1"
                    "tp2"   -> UpC to "TP2"
                    "tp3"   -> UpC.copy(alpha=0.5f) to "TP3"
                    else    -> continue to ""
                }
                drawLine(c, Offset(chartL, y), Offset(chartR, y), strokeWidth=1.6f,
                    pathEffect=if (pl.kind=="entry") null else PathEffect.dashPathEffect(floatArrayOf(5f,3f)))
                val lp = NativePaint().apply { color=c.toArgb(); textSize=16f; isAntiAlias=true; isFakeBoldText=true }
                // Draw label on RIGHT side (axis side) to avoid overlap with left labels
                drawContext.canvas.nativeCanvas.drawText(label, chartR+4f, y-3f, lp)
            }
        }
        // Current price
        val yPrice = priceY(report.price)
        drawLine(Gold, Offset(chartL, yPrice), Offset(chartR, yPrice), strokeWidth=1.4f,
            pathEffect=PathEffect.dashPathEffect(floatArrayOf(4f,3f)))
        drawCircle(Gold, radius=5f, center=Offset(chartR-2f, yPrice))
        val cp = NativePaint().apply { color=Gold.toArgb(); textSize=22f; isAntiAlias=true; isFakeBoldText=true }
        drawContext.canvas.nativeCanvas.drawText(df.format(report.price), 6f, yPrice+8f, cp)
    }
}

// ========== ابزارهای کوچک ==========
@Composable private fun Label(t: String) = Text(t, color=TL, fontSize=10.sp, fontWeight=FontWeight.SemiBold)
@Composable
private fun ChipRow(options: List<String>, selected: String, onPick:(String)->Unit) {
    LazyRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        items(options) { o ->
            val sel = o==selected
            Surface(shape=RoundedCornerShape(10.dp), color=if(sel)Gold else Surf, modifier=Modifier.clickable{onPick(o)}) {
                Text("  $o  ", color=if(sel)Color.Black else TH, fontSize=11.sp, fontWeight=FontWeight.Bold,
                    modifier=Modifier.padding(vertical=8.dp))
            }
        }
    }
}
@Composable private fun Section(t:String, c:Color) = Text(t, color=c, fontSize=13.sp, fontWeight=FontWeight.Black, modifier=Modifier.padding(top=4.dp))
@Composable
private fun RowScope.Lvl(label:String, v:Float?, c:Color) {
    Card(colors=CardDefaults.cardColors(containerColor=BgDark), shape=RoundedCornerShape(12.dp), modifier=Modifier.weight(1f)) {
        Column(Modifier.padding(10.dp), horizontalAlignment=Alignment.CenterHorizontally) {
            Text(label, color=TL, fontSize=11.sp)
            Spacer(Modifier.height(4.dp))
            Text(if(v!=null && v>0f) fmt(v) else "-", color=c, fontSize=14.sp, fontWeight=FontWeight.Black)
        }
    }
}
@Composable
private fun Zc(z:SmcZone, tag:String, c:Color, name:String="") {
    Card(colors=CardDefaults.cardColors(containerColor=Surf2), shape=RoundedCornerShape(12.dp)) {
        Column(Modifier.fillMaxWidth().padding(12.dp)) {
            Row(horizontalArrangement=Arrangement.SpaceBetween, modifier=Modifier.fillMaxWidth()) {
                Text(if(name.isNotBlank()) "$tag · $name" else "$tag · ${z.side.ifBlank{z.kind}}",
                    color=c, fontSize=12.sp, fontWeight=FontWeight.Black)
                Text("idx ${if(z.endIdx>=0) "${z.startIdx}-${z.endIdx}" else z.index}", color=TL, fontSize=10.sp)
            }
            Spacer(Modifier.height(6.dp))
            Row(horizontalArrangement=Arrangement.spacedBy(14.dp)) {
                Text("بالا: ${fmt(z.top)}", color=UpC, fontSize=12.sp)
                Text("پایین: ${fmt(z.bottom)}", color=DnC, fontSize=12.sp)
                if (z.sizePct>0f) Text("%.2f%%".format(z.sizePct), color=TL, fontSize=11.sp)
            }
        }
    }
}
@Composable
private fun KzRow(kz:SmcZone) {
    val c = when {
        kz.name.contains("نیویورک") && kz.name.contains("لندن") -> Gold
        kz.name.contains("نیویورک") -> DnC
        kz.name.contains("لندن") -> Gold
        else -> LiqC
    }
    Card(colors=CardDefaults.cardColors(containerColor=Surf2), shape=RoundedCornerShape(12.dp)) {
        Row(Modifier.fillMaxWidth().padding(12.dp), horizontalArrangement=Arrangement.SpaceBetween, verticalAlignment=Alignment.CenterVertically) {
            Text("◼ ${kz.name}", color=c, fontSize=12.sp, fontWeight=FontWeight.Black)
            Text("کندل ${kz.startIdx}–${kz.endIdx}", color=TL, fontSize=11.sp)
        }
    }
}
@Composable
private fun LiqRow(kind:String, price:Float) {
    val label = when {
        kind=="buyside_liq" -> "نقدینگی بای‌ساید ▲ (خرید)"
        kind=="sellside_liq" -> "نقدینگی سل‌ساید ▼ (فروش)"
        kind=="eqh" -> "سقف‌های برابر (EQH)"
        kind=="eql" -> "کف‌های برابر (EQL)"
        kind=="recent_high_liq" -> "سقف ۲۰ کندل اخیر"
        kind=="recent_low_liq"  -> "کف ۲۰ کندل اخیر"
        else -> kind.replace("_"," ")
    }
    val col = when {
        kind.contains("sell") || kind=="eqh" || kind.contains("high") -> DnC
        kind.contains("buy") || kind=="eql" || kind.contains("low") -> UpC
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
    val label = when(kind) {
        "BOS" -> "BOS — شکست ساختاری در جهت روند"
        "CHoCH" -> "CHoCH — تغییر ساختار بازار"
        else -> kind
    }
    Card(colors=CardDefaults.cardColors(containerColor=Surf2), shape=RoundedCornerShape(10.dp)) {
        Row(Modifier.fillMaxWidth().padding(12.dp), horizontalArrangement=Arrangement.SpaceBetween) {
            Text("$label · ${dir.uppercase()}", color=col, fontSize=12.sp, fontWeight=FontWeight.Bold)
            Text(fmt(price), color=TH, fontSize=12.sp, fontWeight=FontWeight.SemiBold)
        }
    }
}
@Composable private fun LegendDot(c:Color, text:String) {
    Row(verticalAlignment=Alignment.CenterVertically) {
        Box(Modifier.size(8.dp).clip(CircleShape).background(c))
        Spacer(Modifier.width(4.dp))
        Text(text, color=TL, fontSize=9.sp, fontWeight=FontWeight.SemiBold)
    }
}
@Composable
private fun ChipS(t:String, c:Color) {
    Surface(color=c.copy(alpha=0.18f), shape=RoundedCornerShape(999.dp)) {
        Text(t, color=c, fontSize=10.sp, fontWeight=FontWeight.Black,
            modifier=Modifier.padding(horizontal=10.dp, vertical=4.dp))
    }
}
internal fun fmt(v:Float): String {
    if (v<=0f) return "-"
    return when {
        v>1000 -> "%.2f".format(v)
        v>100  -> "%.3f".format(v)
        else -> "%.4f".format(v)
    }
}

// ======== AI Signal Board (used by Signals screen) ========
@Composable
fun AiSignalBoard(signals: List<com.arena.smartmoney.data.model.SmcSignal>, loading: Boolean, onRefresh: ()->Unit) {
    Card(colors = CardDefaults.cardColors(containerColor = Color(0xFF161C25)), shape = RoundedCornerShape(18.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, Gold.copy(alpha=0.35f))) {
        Column(Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.AutoAwesome, "ai", tint = Gold)
                Spacer(Modifier.width(8.dp))
                Text("Apex AI Pro SMC — اسکن زنده چند نماد", color = Gold, fontWeight = FontWeight.Black, fontSize = 14.sp)
                Spacer(Modifier.weight(1f))
                androidx.compose.material3.IconButton(onClick = onRefresh) {
                    Icon(Icons.Default.Refresh, "refresh", tint = Gold)
                }
            }
            if (loading) {
                Text("در حال اسکن بازار...", color = TL, fontSize = 12.sp)
            } else if (signals.isEmpty()) {
                Text("ستاپ با کانفلونس بالا در این لحظه پیدا نشد.", color = TL, fontSize = 12.sp)
            } else {
                Text("${signals.size} ستاپ فعال پیدا شد", color = TH, fontSize = 12.sp)
                Spacer(Modifier.height(8.dp))
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
