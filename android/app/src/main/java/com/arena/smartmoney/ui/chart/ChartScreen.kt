@file:OptIn(ExperimentalMaterial3Api::class)
package com.arena.smartmoney.ui.chart

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
import android.graphics.Paint as NativePaint
import android.graphics.Color as NativeColor
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.arena.smartmoney.data.model.SmcCandle
import com.arena.smartmoney.data.model.SmcReport
import com.arena.smartmoney.data.model.SmcZone
import com.arena.smartmoney.data.repository.TradingRepository
import kotlinx.coroutines.launch
import java.text.DecimalFormat
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

// ===== Luxe dark + gold palette =====
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
private val KzAsia   = Color(0x2660A5FA)
private val KzLon    = Color(0x2BD4AF37)
private val KzNy     = Color(0x33EF4444)

private val SYMBOLS = listOf("XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSDT", "ETHUSDT", "XAUUSD+", "US30", "NAS100")
private val TIMEFRAMES = listOf("1min", "5min", "15min", "30min", "1h", "4h", "1d")
private val MARKETS = listOf("forex", "crypto")

@Composable
fun ChartScreen(onBack: (() -> Unit)? = null) {
    val repo = remember { TradingRepository() }
    val scope = rememberCoroutineScope()
    var r by remember { mutableStateOf(SmcReport()) }
    var loading by remember { mutableStateOf(true) }
    var sym by remember { mutableStateOf("XAUUSD") }
    var mkt by remember { mutableStateOf("forex") }
    var tf  by remember { mutableStateOf("15min") }
    var scale by remember { mutableFloatStateOf(1f) }

    fun load() {
        scope.launch {
            loading = true
            try { r = repo.getSmcAnalysis(sym, mkt, tf, 220) }
            finally { loading = false }
        }
    }
    LaunchedEffect(sym, mkt, tf) { load() }

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
            // ===== Selectors =====
            item {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Label("نماد / Symbol")
                    ChipRow(SYMBOLS, sym) { sym = it; if (it.contains("BTC") || it.contains("ETH")) mkt = "crypto" else mkt = "forex" }
                    Label("بازار")
                    ChipRow(MARKETS, mkt) { mkt = it }
                    Label("تایم‌فریم")
                    ChipRow(TIMEFRAMES, tf) { tf = it; scale = 1f }
                }
            }
            // ===== Header Card =====
            item {
                Card(colors = CardDefaults.cardColors(containerColor = Surf), shape = RoundedCornerShape(16.dp)) {
                    Column(modifier = Modifier.padding(14.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween,
                            modifier = Modifier.fillMaxWidth()) {
                            Column {
                                Text(r.symbol.ifBlank { sym }, color = TH, fontSize = 24.sp, fontWeight = FontWeight.Black)
                                Text("${r.timeframe.ifBlank { tf }}  •  ${mkt.uppercase()}", color = TL, fontSize = 11.sp)
                            }
                            Column(horizontalAlignment = Alignment.End) {
                                val p = r.price
                                Text(if (p > 0f) fmt(p) else "-", color = Gold, fontSize = 22.sp, fontWeight = FontWeight.Black)
                                val bc = when (r.bias) { "bullish" -> UpC; "bearish" -> DnC; else -> GoldDim }
                                val bl = when (r.bias) { "bullish" -> "BULLISH صعودی"; "bearish" -> "BEARISH نزولی"; else -> "NEUTRAL خنثی" }
                                Surface(shape = RoundedCornerShape(6.dp), color = bc.copy(alpha = 0.15f)) {
                                    Text("  $bl  ", color = bc, fontSize = 10.sp, fontWeight = FontWeight.Black)
                                }
                            }
                        }
                        Spacer(Modifier.height(10.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            ChipS("conf ${r.confluence}/4", if (r.confluence >= 3) Gold else GoldDim)
                            ChipS("${r.candlesCount}c", TL)
                            ChipS(r.status.ifBlank { "-" }, TL)
                            val pr = r.orderflow.pressure
                            ChipS(when (pr) { "buy" -> "OF: BUY"; "sell" -> "OF: SELL"; else -> "OF: NEU" },
                                when (pr) { "buy" -> UpC; "sell" -> DnC; else -> TL })
                        }
                        Spacer(Modifier.height(8.dp))
                        Text(if (loading) "در حال بارگذاری..." else r.note.ifBlank { "-" }, color = TH, fontSize = 12.sp, lineHeight = 18.sp)
                        if (r.sessions.isNotEmpty()) {
                            Spacer(Modifier.height(6.dp))
                            Text("سشن فعال: " + r.sessions.joinToString(" / "), color = GoldDim, fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
                        }
                    }
                }
            }

            // ===== Candlestick chart =====
            item {
                Card(colors = CardDefaults.cardColors(containerColor = Surf), shape = RoundedCornerShape(16.dp)) {
                    Column(modifier = Modifier.padding(10.dp)) {
                        Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                            Text("نمودار SMC", color = Gold, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                            Text("(با زوم دو انگشت)", color = TL, fontSize = 9.sp)
                        }
                        Spacer(Modifier.height(8.dp))
                        if (r.candles.isNotEmpty()) {
                            SmcCanvas(modifier = Modifier.fillMaxWidth().height(260.dp), report = r, scale = scale, onScale = { scale = (scale * it).coerceIn(0.5f, 4f) })
                        } else {
                            Box(Modifier.fillMaxWidth().height(260.dp), contentAlignment = Alignment.Center) {
                                Text("داده کافی برای رسم نمودار نیست", color = TL, fontSize = 12.sp)
                            }
                        }
                        // Legend
                        Spacer(Modifier.height(6.dp))
                        LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            item { LegendDot(UpC,  "BUY OB") }
                            item { LegendDot(DnC,  "SELL OB") }
                            item { LegendDot(FvgC, "FVG") }
                            item { LegendDot(iFvgC,"iFVG") }
                            item { LegendDot(BrkC, "Breaker") }
                            item { LegendDot(LiqC, "Liquidity") }
                            item { LegendDot(KzLon,"KZ London") }
                            item { LegendDot(KzNy, "KZ NY") }
                        }
                    }
                }
            }

            // ===== AI Narrative =====
            item {
                Card(colors = CardDefaults.cardColors(containerColor = GoldSoft), shape = RoundedCornerShape(16.dp),
                    border = androidx.compose.foundation.BorderStroke(1.dp, GoldDim.copy(alpha = 0.3f))) {
                    Column(modifier = Modifier.padding(14.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.AutoAwesome, "ai", tint = Gold)
                            Spacer(Modifier.width(8.dp))
                            Text("تحلیل هوشمند Apex AI", color = Gold, fontWeight = FontWeight.Black, fontSize = 14.sp)
                            Spacer(Modifier.weight(1f))
                            val sideC = when (r.direction) { "long" -> UpC; "short" -> DnC; else -> GoldDim }
                            Surface(shape = RoundedCornerShape(6.dp), color = sideC.copy(alpha = 0.18f)) {
                                Text("  ${r.ai.side}  ", color = sideC, fontSize = 10.sp, fontWeight = FontWeight.Black)
                            }
                        }
                        Spacer(Modifier.height(8.dp))
                        Text(if (loading) "در حال تحلیل..." else r.ai.summary.ifBlank { r.note },
                            color = TH, fontSize = 12.sp, lineHeight = 20.sp)
                        Spacer(Modifier.height(6.dp))
                        Text(if (loading) "" else "◀ ${r.ai.recommendation}", color = Gold, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                    }
                }
            }

            // ===== Trade Levels =====
            item {
                Card(colors = CardDefaults.cardColors(containerColor = Surf2), shape = RoundedCornerShape(16.dp)) {
                    Column(modifier = Modifier.padding(14.dp)) {
                        Text("سطوح ورود / حد ضرر / هدف", color = Gold, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                        Spacer(Modifier.height(10.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Lvl("Entry", r.levels.entry, Gold)
                            Lvl("SL",    r.levels.sl,    DnC)
                            Lvl("TP",    r.levels.tp,    UpC)
                        }
                    }
                }
            }

            // ===== Kill Zones =====
            if (r.killzones.isNotEmpty()) item { Section("سشن‌ها و کیل‌زون‌ها", Gold) }
            if (r.killzones.isNotEmpty()) items(r.killzones.take(4)) { kz ->
                Zc(kz, "KZ", when {
                    kz.name.contains("نیویورک") || kz.name.contains("لندن+") -> KzNy
                    kz.name.contains("لندن") -> Gold
                    else -> LiqC
                }, name = kz.name)
            }

            // ===== Buy/Sell side liquidity =====
            val liqSweeps = r.inducements.filter { it.kind.contains("liq") || it.kind.startsWith("eq") || it.kind.contains("recent") }
            if (liqSweeps.isNotEmpty()) item { Section("بای‌ساید / سل‌ساید لیکوئیدیتی", LiqC) }
            if (liqSweeps.isNotEmpty()) items(liqSweeps.take(10)) { lbl ->
                LiqRow(lbl.kind, lbl.price)
            }

            // ===== Order Blocks =====
            if (r.orderBlocks.isNotEmpty()) item { Section("اوردر بلاک‌ها (Order Blocks)", Gold) }
            if (r.orderBlocks.isNotEmpty()) items(r.orderBlocks.take(6)) { Zc(it, "OB", if (it.kind == "bullish" || it.side == "bullish") UpC else DnC) }

            // ===== FVGs / iFVGs =====
            if (r.fvg.isNotEmpty()) item { Section("نواحی عدم تعادل (FVG / iFVG)", FvgC) }
            if (r.fvg.isNotEmpty()) items(r.fvg.take(8)) { g ->
                Zc(g, if (g.inverse) "iFVG" else "FVG", if (g.inverse) iFvgC else FvgC)
            }

            // ===== Breakers =====
            if (r.breakers.isNotEmpty()) item { Section("بریکر بلاک‌ها (Breaker Blocks)", BrkC) }
            if (r.breakers.isNotEmpty()) items(r.breakers.take(5)) { Zc(it, "BRK", BrkC) }

            // ===== BOS/CHoCH events =====
            if (r.events.isNotEmpty()) item { Section("وقایع ساختاری BOS / CHoCH", Gold) }
            if (r.events.isNotEmpty()) items(r.events.takeLast(8)) { ev ->
                EventRow(ev.kind, ev.dir, ev.price)
            }

            item { Spacer(Modifier.height(40.dp)) }
            item {
                Text("Created by Amin Omidi", color = GoldDim, fontSize = 11.sp,
                    modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Center)
                Spacer(Modifier.height(18.dp))
            }
        }
    }
}

// ========== Candlestick Canvas with SMC overlay ==========
@Composable
private fun SmcCanvas(modifier: Modifier = Modifier, report: SmcReport, scale: Float, onScale: (Float) -> Unit) {
    var sizePx by remember { mutableIntStateOf(0) }
    Canvas(modifier = modifier
        .background(BgDark, RoundedCornerShape(10.dp))
        .pointerInput(Unit) { detectTransformGestures { _, _, zoom, _ -> onScale(zoom) } }
    ) {
        val w = size.width; val h = size.height
        sizePx = w.toInt()
        val candles = report.candles
        if (candles.isEmpty()) return@Canvas
        // visible window
        val totalCandles = candles.size
        val visibleCount = (totalCandles / scale).toInt().coerceIn(20, totalCandles)
        val startIdx = (totalCandles - visibleCount).coerceAtLeast(0)
        val visible = candles.subList(startIdx, totalCandles)
        val hi = visible.maxOf { it.h } * 1.0015f
        val lo = visible.minOf { it.l } * 0.9985f
        val range = (hi - lo).takeIf { it > 0f } ?: 1f
        val chartTop = 18f; val chartBot = h - 18f
        val chartH = chartBot - chartTop
        val cw = w / visible.size.toFloat()
        val bw = (cw * 0.7f).coerceAtLeast(1.5f)

        // Grid lines
        for (i in 0..4) {
            val y = chartTop + chartH * i / 4f
            drawLine(GridLn, Offset(0f, y), Offset(w, y), strokeWidth = 0.6f)
        }
        // Price labels right axis
        val df = DecimalFormat("0.00")
        for (i in 0..4) {
            val y = chartTop + chartH * i / 4f
            val p = hi - (hi - lo) * i / 4f
            drawContext.canvas.nativeCanvas.drawText(df.format(p), w - 58f, y + 4f,
                NativePaint().apply { color = TL.toArgb(); textSize = 22f; isAntiAlias = true })
        }

        fun priceY(p: Float) = chartTop + (hi - p) / range * chartH
        fun idxX(i: Int) = (i - startIdx) * cw + cw / 2f

        // Draw killzones first (background shaders)
        for (kz in report.killzones) {
            val s = kz.startIdx.coerceAtLeast(startIdx); val e = kz.endIdx.coerceAtMost(totalCandles - 1)
            if (e < startIdx || s > totalCandles - 1) continue
            val x1 = idxX(s) - cw/2; val x2 = idxX(e) + cw/2
            val color = when {
                kz.name.contains("نیویورک") || kz.name.contains("لندن+") -> KzNy
                kz.name.contains("لندن") -> KzLon
                else -> KzAsia
            }
            drawRect(color, topLeft = Offset(x1, chartTop), size = Size(x2 - x1, chartH))
        }

        // Draw zones (OB / FVG / BRK)
        for (z in report.orderBlocks + report.fvg + report.breakers + report.killzones) {
            val i = z.index
            if (i < startIdx || i >= totalCandles) continue
            val x = idxX(i) - cw
            val color = when (z.kind) {
                "OB"  -> if (z.side == "bullish") UpC else DnC
                "FVG" -> if (z.inverse) iFvgC else FvgC
                "BRK" -> BrkC
                else  -> Color.Transparent
            }
            if (color == Color.Transparent) continue
            val top = priceY(z.top); val bot = priceY(z.bottom)
            drawRect(color = color.copy(alpha = 0.18f), topLeft = Offset(x, top), size = Size(cw*3f, bot - top))
            drawRect(color = color.copy(alpha = 0.6f), topLeft = Offset(x, top), size = Size(cw*3f, bot - top), style = Stroke(1.2f))
        }

        // Candles
        visible.forEachIndexed { idx, c ->
            val x = idxX(idx + startIdx)
            val up = c.c >= c.o
            val col = if (up) UpC else DnC
            val yH = priceY(c.h); val yL = priceY(c.l)
            val yO = priceY(c.o); val yC = priceY(c.c)
            drawLine(col, Offset(x, yH), Offset(x, yL), strokeWidth = 1f)
            val top = min(yO, yC); val hgt = abs(yC - yO).coerceAtLeast(1.2f)
            drawRect(col, topLeft = Offset(x - bw/2, top), size = Size(bw, hgt))
        }

        // Liquidity / BOS/CHoCH lines & labels
        for (lab in report.inducements) {
            val col = if (lab.kind.contains("buyside")) UpC else if (lab.kind.contains("sellside")) DnC else LiqC
            val y = priceY(lab.price)
            if (y < chartTop - 5f || y > chartBot + 5f) continue
            drawLine(col.copy(alpha = 0.75f), Offset(0f, y), Offset(w, y), strokeWidth = 0.9f, pathEffect = PathEffect.dashPathEffect(floatArrayOf(6f,4f)))
        }
        for (ev in report.events) {
            val col = if (ev.dir == "bullish") UpC else DnC
            val y = priceY(ev.price)
            if (y < chartTop - 5f || y > chartBot + 5f) continue
            drawLine(col.copy(alpha = 0.9f), Offset(0f, y), Offset(w, y), strokeWidth = 1.2f)
            drawCircle(col, radius = 4f, center = Offset(idxX(ev.index.coerceIn(startIdx, totalCandles-1)), y))
        }
        // Order flow highlight — vertical bar at last candle if strong pressure
        val of = report.orderflow
        if (of.pressure != "neutral") {
            val col = if (of.pressure == "buy") UpC else DnC
            drawRect(col.copy(alpha = 0.08f), topLeft = Offset(w - 40f, chartTop), size = Size(40f, chartH))
        }
        // Current price line
        val yPrice = priceY(report.price)
        drawLine(Gold, Offset(0f, yPrice), Offset(w - 60f, yPrice), strokeWidth = 1f, pathEffect = PathEffect.dashPathEffect(floatArrayOf(4f,3f)))
    }
}

// ========== Small UI pieces ==========
@Composable private fun Label(t: String) = Text(t, color = TL, fontSize = 10.sp, fontWeight = FontWeight.SemiBold)

@Composable
private fun ChipRow(options: List<String>, selected: String, onPick: (String) -> Unit) {
    LazyRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        items(options) { o ->
            val sel = o == selected
            Surface(
                shape = RoundedCornerShape(10.dp),
                color = if (sel) Gold else Surf,
                modifier = Modifier.clickable { onPick(o) }
            ) {
                Text("  $o  ", color = if (sel) Color.Black else TH,
                    fontSize = 11.sp, fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(vertical = 8.dp))
            }
        }
    }
}

@Composable private fun Section(t: String, c: Color) {
    Text(t, color = c, fontSize = 13.sp, fontWeight = FontWeight.Black, modifier = Modifier.padding(top = 4.dp))
}

@Composable
private fun RowScope.Lvl(label: String, v: Float?, c: Color) {
    Card(colors = CardDefaults.cardColors(containerColor = BgDark), shape = RoundedCornerShape(12.dp), modifier = Modifier.weight(1f)) {
        Column(Modifier.padding(10.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Text(label, color = TL, fontSize = 11.sp)
            Spacer(Modifier.height(4.dp))
            Text(if (v != null && v > 0f) fmt(v) else "-", color = c, fontSize = 14.sp, fontWeight = FontWeight.Black)
        }
    }
}

@Composable
private fun Zc(z: SmcZone, tag: String, c: Color, name: String = "") {
    Card(colors = CardDefaults.cardColors(containerColor = Surf2), shape = RoundedCornerShape(12.dp)) {
        Column(Modifier.fillMaxWidth().padding(12.dp)) {
            Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                Text(if (name.isNotBlank()) "$tag · $name" else "$tag · ${z.side.ifBlank { z.kind }}",
                    color = c, fontSize = 12.sp, fontWeight = FontWeight.Black)
                Text("idx ${if (z.endIdx >= 0) "${z.startIdx}-${z.endIdx}" else z.index}",
                    color = TL, fontSize = 10.sp)
            }
            Spacer(Modifier.height(6.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                Text("top: ${fmt(z.top)}", color = UpC, fontSize = 12.sp)
                Text("bot: ${fmt(z.bottom)}", color = DnC, fontSize = 12.sp)
                if (z.sizePct > 0f) Text("%.2f%%".format(z.sizePct), color = TL, fontSize = 11.sp)
            }
        }
    }
}

@Composable
private fun LiqRow(kind: String, price: Float) {
    val label = when {
        kind == "buyside_liq" -> "Buyside Liq ▲ (نقدینگی خرید)"
        kind == "sellside_liq" -> "Sellside Liq ▼ (نقدینگی فروش)"
        kind == "eqh" -> "Equal Highs (سقف‌های برابر)"
        kind == "eql" -> "Equal Lows (کف‌های برابر)"
        kind == "recent_high_liq" -> "سقف اخیر"
        kind == "recent_low_liq"  -> "کف اخیر"
        else -> kind.replace("_", " ")
    }
    val col = when {
        kind.contains("sell") || kind == "eqh" || kind.contains("high") -> DnC
        kind.contains("buy") || kind == "eql" || kind.contains("low") -> UpC
        else -> LiqC
    }
    Card(colors = CardDefaults.cardColors(containerColor = Surf2), shape = RoundedCornerShape(10.dp)) {
        Row(Modifier.fillMaxWidth().padding(12.dp), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(label, color = col, fontSize = 12.sp, fontWeight = FontWeight.Bold)
            Text(fmt(price), color = TH, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
        }
    }
}

@Composable
private fun EventRow(kind: String, dir: String, price: Float) {
    val col = if (dir == "bullish") UpC else DnC
    val label = when (kind) {
        "BOS" -> "BOS — شکست ساختاری"
        "CHoCH" -> "CHoCH — تغییر ساختار"
        else -> kind
    }
    Card(colors = CardDefaults.cardColors(containerColor = Surf2), shape = RoundedCornerShape(10.dp)) {
        Row(Modifier.fillMaxWidth().padding(12.dp), horizontalArrangement = Arrangement.SpaceBetween) {
            Text("$label · $dir", color = col, fontSize = 12.sp, fontWeight = FontWeight.Bold)
            Text(fmt(price), color = TH, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
        }
    }
}

@Composable
private fun LegendDot(c: Color, text: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(8.dp).clip(CircleShape).background(c))
        Spacer(Modifier.width(4.dp))
        Text(text, color = TL, fontSize = 9.sp, fontWeight = FontWeight.SemiBold)
    }
}

@Composable
private fun ChipS(t: String, c: Color) {
    Surface(color = c.copy(alpha = 0.18f), shape = RoundedCornerShape(999.dp)) {
        Text(t, color = c, fontSize = 10.sp, fontWeight = FontWeight.Black, modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp))
    }
}

private fun fmt(v: Float): String {
    if (v <= 0f) return "-"
    return when {
        v > 1000 -> "%.2f".format(v)
        v > 100  -> "%.3f".format(v)
        else -> "%.4f".format(v)
    }
}
