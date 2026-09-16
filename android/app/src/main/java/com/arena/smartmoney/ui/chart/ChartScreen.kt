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
import androidx.compose.material.icons.filled.Notifications
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.arena.smartmoney.data.model.ProximityAlertDto
import com.arena.smartmoney.data.model.SmcCandle
import com.arena.smartmoney.data.model.SmcIct
import com.arena.smartmoney.data.model.SmcReport
import com.arena.smartmoney.data.model.SmcSignal
import com.arena.smartmoney.data.model.SmtInfoDto
import com.arena.smartmoney.data.model.StrategiesV2Dto
import com.arena.smartmoney.data.model.ClassicLevelsDto
import com.arena.smartmoney.data.model.IndicatorsV2SummaryDto
import com.arena.smartmoney.data.model.SmcZone
import com.arena.smartmoney.data.network.MarketWebSocketClient
import com.arena.smartmoney.data.preferences.AppPreferencesManager
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
private val DonchC   = Color(0xFFFFB74D)   // v3.13: Donchian 20 — نارنجی
private val KeltC    = Color(0xFFB39DDB)   // v3.13: Keltner 2.5ATR — بنفش
private val BandC    = Color(0xFF4DD0E1)   // v3.13: VWAP ±2σ — فیروزه‌ای
private val PivotC   = Color(0xFF90A4AE)   // v3.13: Pivot/R1/S1 — خاکستری‌آبی
private val VolUp    = Color(0x6626A69A)
private val VolDn    = Color(0x66EF5350)

private val CompareBlue = Color(0xFF42A5F5)
private val CompareViolet = Color(0xFFCE93D8)
private val COMPARE_COLORS = listOf(CompareBlue, CompareViolet)

private val SYMBOLS = listOf("XAUUSD","EURUSD","GBPUSD","USDJPY","AUDUSD","BTCUSDT","ETHUSDT","SOLUSDT","US30","NAS100")
private val TIMEFRAMES = listOf("1m","5m","15m","30m","1h","4h","1d")

@Composable
fun ChartScreen(
    onBack: (() -> Unit)? = null,
    initialSymbol: String = "",
    initialMarket: String = "",
    initialTimeframe: String = "",
) {
    val repo = remember { TradingRepository() }
    val scope = rememberCoroutineScope()
    val context = LocalContext.current
    val prefs = remember { AppPreferencesManager(context) }
    var r by remember { mutableStateOf(SmcReport()) }
    var loading by remember { mutableStateOf(true) }
    var sym by remember { mutableStateOf(initialSymbol.ifBlank { prefs.getChartSymbol() }) }
    var mkt by remember { mutableStateOf(initialMarket.ifBlank { prefs.getChartMarket() }) }
    var tf by remember { mutableStateOf(initialTimeframe.ifBlank { prefs.getChartTimeframe() }) }
    var scale by remember { mutableStateOf(defaultChartScale(tf)) }
    var signals by remember { mutableStateOf<List<SmcSignal>>(emptyList()) }
    var scanLoading by remember { mutableStateOf(false) }
    var refreshNonce by remember { mutableIntStateOf(0) }
    var compareSyms by remember { mutableStateOf(prefs.getChartCompareSymbols().filter { it != sym }) }
    var compareSeries by remember { mutableStateOf<List<CompareSeries>>(emptyList()) }
    var alerts by remember { mutableStateOf<List<ProximityAlertDto>>(emptyList()) }
    var alertsOpen by remember { mutableStateOf(false) }
    var alertsEnabled by remember { mutableStateOf(prefs.isProximityAlertsEnabled()) }
    var showClassic by remember { mutableStateOf(prefs.isClassicLevelsEnabled()) }
    val wsClient = remember { MarketWebSocketClient() }
    val screenListState = rememberLazyListState()

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
        screenListState.scrollToItem(0)
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

    // v3.11: persist the user's chart settings (symbol / timeframe / compare / alerts)
    LaunchedEffect(sym, mkt, tf, compareSyms, alertsEnabled, showClassic) {
        prefs.setChartSymbol(sym)
        prefs.setChartMarket(mkt)
        prefs.setChartTimeframe(tf)
        prefs.setChartCompareSymbols(compareSyms)
        prefs.setProximityAlertsEnabled(alertsEnabled)
        prefs.setClassicLevelsEnabled(showClassic)
    }

    // v3.11: fetch compare-symbol candles (up to 2) for the overlay
    LaunchedEffect(compareSyms, tf) {
        if (compareSyms.isEmpty()) {
            compareSeries = emptyList()
            return@LaunchedEffect
        }
        val out = mutableListOf<CompareSeries>()
        compareSyms.forEach { compareSymbol ->
            runCatching { repo.getCandles(compareSymbol, marketOf(compareSymbol), tf, 260) }
                .onSuccess { resp ->
                    val closes = resp.items.map { it.close.toFloat() }.filter { it > 0f }
                    if (closes.size >= 2) out.add(CompareSeries(compareSymbol, closes))
                }
        }
        compareSeries = out
    }

    // v3.11: seed proximity alerts once per symbol/timeframe (REST snapshot)
    LaunchedEffect(sym, tf) {
        alerts = emptyList()
        runCatching { repo.getProximityAlerts(sym, marketOf(sym), tf) }
            .onSuccess { resp -> alerts = resp.alerts }
    }

    // v3.11: live proximity alerts over the market WebSocket
    DisposableEffect(sym, mkt, tf, alertsEnabled) {
        if (alertsEnabled) {
            wsClient.connect(
                symbol = sym,
                market = mkt.ifBlank { marketOf(sym) },
                timeframe = tf,
                alertsEnabled = true,
                onStatus = { },
                onSnapshot = { },
                onAlert = { fresh -> alerts = (fresh + alerts).take(30) }
            )
        } else {
            wsClient.disconnect()
        }
        onDispose { wsClient.disconnect() }
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
            state = screenListState,
            modifier = Modifier.fillMaxSize().padding(pad).padding(horizontal = 10.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            item {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Label("نماد")
                    ChipRow(SYMBOLS, sym) { picked -> sym = picked; mkt = ""; compareSyms = compareSyms.filter { it != picked } }
                    Label("تایم‌فریم")
                    ChipRow(TIMEFRAMES, tf) { tf = it; scale = defaultChartScale(it) }
                    Label("مقایسه هم‌زمان (حداکثر ۲ نماد)")
                    CompareChipRow(SYMBOLS.filter { it != sym }, compareSyms) { picked ->
                        compareSyms = if (compareSyms.contains(picked)) {
                            compareSyms - picked
                        } else if (compareSyms.size >= 2) {
                            compareSyms
                        } else {
                            compareSyms + picked
                        }
                    }
                }
            }
            item { HeaderCard(r, sym, mkt, tf, loading) }
            item {
                AlertCard(
                    alerts = alerts,
                    enabled = alertsEnabled,
                    expanded = alertsOpen,
                    onToggleEnabled = { alertsEnabled = !alertsEnabled },
                    onToggleOpen = { alertsOpen = !alertsOpen }
                )
            }
            val smtInfo = r.smt
            if (smtInfo != null && smtInfo.available) {
                item { SmtCard(smtInfo) }
            }
            // === v3.12: پک استراتژی‌های کلاسیک + پک اندیکاتور پیشرفته + ICT Pro ===
            val strat2 = r.strategiesV2
            if (strat2 != null && strat2.available && (strat2.active.isNotEmpty() || strat2.forming.isNotEmpty())) {
                item { StrategyPackCard(strat2) }
            }
            val ind2 = r.indicatorsV2?.summary
            if (ind2 != null && ind2.available) {
                item { IndicatorPackCard(ind2) }
            }
            val ictPro = r.ict
            if (ictPro != null && (ictPro.marketStructure != null || (ictPro.ote?.available == true) || ictPro.killzone != null)) {
                item { IctProCard(ictPro) }
            }
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
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Text(
                                    if (showClassic) "سطوح کلاسیک ✓" else "سطوح کلاسیک",
                                    color = if (showClassic) BandC else TL.copy(alpha = 0.45f),
                                    fontSize = 9.sp,
                                    fontWeight = FontWeight.SemiBold,
                                    modifier = Modifier
                                        .clickable { showClassic = !showClassic }
                                        .padding(horizontal = 6.dp, vertical = 3.dp)
                                )
                                Text("(با دو انگشت زوم کنید)", color = TL.copy(alpha = 0.6f), fontSize = 9.sp)
                            }
                        }
                        if (r.candles.isNotEmpty()) {
                            SmcCanvas(
                                modifier = Modifier.fillMaxWidth().height(390.dp),
                                report = r, scale = scale,
                                onScale = { scale = (scale * it).coerceIn(0.6f, 4f) },
                                compare = compareSeries.mapIndexed { idx, cs ->
                                    CompareOverlay(cs.symbol, cs.closes, COMPARE_COLORS[idx % COMPARE_COLORS.size])
                                },
                                classicLevels = r.indicatorsV2?.summary?.levels,
                                showClassic = showClassic
                            )
                        } else {
                            Box(Modifier.fillMaxWidth().height(390.dp), contentAlignment = Alignment.Center) {
                                Text(if (loading) "در حال بارگذاری..." else "داده کافی نیست", color = TL, fontSize = 12.sp)
                            }
                        }
                        // پایین چارت
                        CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Ltr) {
                            LazyRow(
                                modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp),
                                contentPadding = PaddingValues(horizontal = 10.dp),
                                horizontalArrangement = Arrangement.spacedBy(12.dp)
                            ) {
                                item { LegendDot(BullOB, "Bull OB") }
                                item { LegendDot(BearOB, "Bear OB") }
                                item { LegendDot(FvgC, "FVG") }
                                item { LegendDot(BrkC.copy(alpha = 0.55f), "Breaker") }
                                item { LegendDot(Color(0xFF10B981), "RTM S/D") }
                                item { LegendDot(Color(0xFFF59E0B), "QML/MPL") }
                                item { LegendDot(LiqC, "BSL / SSL") }
                                item { LegendDot(UpC, "BOS / CHoCH") }
                                item { LegendDot(KzLon.copy(alpha=0.7f), "Sessions") }
                                items(compareSeries) { cs ->
                                    val idx = compareSeries.indexOf(cs)
                                    val pct = if (cs.closes.first() > 0f)
                                        (cs.closes.last() / cs.closes.first() - 1f) * 100f else 0f
                                    val pctTxt = (if (pct >= 0f) "+" else "") + (Math.round(pct * 10.0) / 10.0) + "%"
                                    LegendDot(COMPARE_COLORS[idx % COMPARE_COLORS.size], cs.symbol + " " + pctTxt)
                                }
                            }
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
                r.ict?.let { ict ->
                    ict.events.take(2).forEach { ev ->
                        item {
                            val isBull = ev.dir == "bullish"
                            val lbl = when (ev.kind) {
                                "sweep_high" -> "SWEEP▼"
                                "sweep_low" -> "SWEEP▲"
                                "displacement" -> if (isBull) "DISP▲" else "DISP▼"
                                else -> ev.kind
                            }
                            ChipS(lbl, if (isBull) UpC else DnC)
                        }
                    }
                    if (ict.silverBullet.active) item { ChipS("SB⚡", Gold) }
                    if (ict.pointsBull > 0 || ict.pointsBear > 0) {
                        item {
                            ChipS("ICT ▲${ict.pointsBull}/▼${ict.pointsBear}", if (ict.pointsBull >= ict.pointsBear) UpC else DnC)
                        }
                    }
                }
                r.force?.let { f ->
                    item {
                        val col = if (f.buyersPct >= 58f) UpC else if (f.buyersPct <= 42f) DnC else TL
                        ChipS("🐂${"%.0f".format(f.buyersPct)} 🐻${"%.0f".format(f.sellersPct)}", col)
                    }
                }
                item { ChipS(if(r.probability>0) "%${r.probability}" else "احتمال -", when { r.probability>=75->UpC; r.probability>=55->GoldDim; else->TL }) }
                item { ChipS(if (r.rr > 0f) "RR 1:%.1f".format(r.rr) else "RR -", if(r.rr>=2f) UpC else TL) }
                item { ChipS("TS ${r.trendStrength}", when{r.trendStrength>=60->UpC;r.trendStrength<30->DnC;else->TL}) }
            }
            Spacer(Modifier.height(4.dp))
            LazyRow(horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                item {
                    ChipS(
                        if (r.orderflow.isReal) "REAL OF" else "PROXY OF",
                        if (r.orderflow.isReal) UpC else GoldDim,
                    )
                }
                item {
                    val pr = r.orderflow.pressure
                    ChipS(when(pr){"buy"->"OF+";"sell"->"OF−";else->"OF"}, when(pr){"buy"->UpC;"sell"->DnC;else->TL})
                }
                r.orderflow.depthImbalance?.let { depth ->
                    item {
                        ChipS(
                            "DEPTH ${if (depth >= 0) "+" else ""}${"%.2f".format(depth)}",
                            if (depth >= 0.12f) UpC else if (depth <= -0.12f) DnC else TL,
                        )
                    }
                }
                r.orderflow.spreadBps?.let { spread ->
                    item { ChipS("SPR ${"%.1f".format(spread)}bp", if (spread <= 5f) UpC else DnC) }
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
                r.orderflow.openInterestChangePct?.let { change ->
                    item {
                        ChipS(
                            "OI ${if (change >= 0) "+" else ""}${"%.2f".format(change)}%",
                            if (change >= 0) UpC else DnC,
                        )
                    }
                }
                r.orderflow.fundingRate?.let { funding ->
                    item {
                        ChipS(
                            "FUND ${"%.4f".format(funding * 100)}%",
                            if (kotlin.math.abs(funding) < 0.001f) TL else Gold,
                        )
                    }
                }
                r.orderflow.micro?.let { micro ->
                    if (micro.isReal) {
                        micro.filters?.let { f ->
                            item {
                                val biasArrow = when (f.netBias) { "bullish" -> "▲"; "bearish" -> "▼"; else -> "•" }
                                val biasColor = when (f.netBias) { "bullish" -> UpC; "bearish" -> DnC; else -> TL }
                                ChipS("NET$biasArrow ${"%.2f".format(f.score)}", biasColor)
                            }
                        }
                        micro.vp?.poc?.let { poc ->
                            item { ChipS("POC ${"%.2f".format(poc)}", GoldDim) }
                        }
                        micro.l2?.imbalanceTop25?.let { imb ->
                            item {
                                ChipS(
                                    "L2 ${if (imb >= 0) "+" else ""}${"%.2f".format(imb)}",
                                    if (imb >= 0.15f) UpC else if (imb <= -0.15f) DnC else TL,
                                )
                            }
                        }
                        micro.footprint?.lastDelta?.let { delta ->
                            item {
                                ChipS(
                                    "FPΔ ${if (delta >= 0) "+" else ""}${"%.2f".format(delta)}",
                                    if (delta >= 0) UpC else DnC,
                                )
                            }
                        }
                        micro.footprint?.stackedBuy?.takeIf { it >= 3 }?.let { stk ->
                            item { ChipS("STK▲$stk", UpC) }
                        }
                        micro.footprint?.stackedSell?.takeIf { it >= 3 }?.let { stk ->
                            item { ChipS("STK▼$stk", DnC) }
                        }
                        micro.footprint?.summary?.takeIf { it.available }?.let { fps ->
                            fps.pocMigration?.let { m ->
                                item {
                                    ChipS(
                                        when (m) { "rising" -> "POC↑"; "falling" -> "POC↓"; else -> "POC→" },
                                        when (m) { "rising" -> UpC; "falling" -> DnC; else -> TL }
                                    )
                                }
                            }
                            fps.deltaPriceDivergence?.let { dv ->
                                item {
                                    ChipS(
                                        if (dv == "bullish") "ΔDIV▲" else "ΔDIV▼",
                                        if (dv == "bullish") UpC else DnC
                                    )
                                }
                            }
                            fps.deltaTrend?.takeIf { it.startsWith("accelerating") }?.let { dt ->
                                item {
                                    ChipS(
                                        if (dt == "accelerating_buy") "Δ++" else "Δ--",
                                        if (dt == "accelerating_buy") UpC else DnC
                                    )
                                }
                            }
                            fps.unfinishedBias?.let { ub ->
                                item { ChipS(if (ub == "up") "UNF▲" else "UNF▼", GoldDim) }
                            }
                        }
                        micro.l2?.bidWall?.price?.let { wallPrice ->
                            item { ChipS("BW ${"%.2f".format(wallPrice)}", GoldDim) }
                        }
                        micro.l2?.askWall?.price?.let { wallPrice ->
                            item { ChipS("SW ${"%.2f".format(wallPrice)}", GoldDim) }
                        }
                    } else {
                        item { ChipS("µ-PROXY", TL) }
                    }
                }
                item { ChipS(when(r.premiumZone){"premium"->"پرِمیوم";"discount"->"دیسکانت";else->"تعادل"}, GoldDim) }
                if (r.newsBlocked) item { ChipS("⚠️اخبار", DnC) }
                if (r.mtfAligned) item { ChipS("MTF✓", UpC) }
                val actLbl = when(r.actionLabel) {
                    "STRONG_LONG" -> "STRONG LONG"
                    "LONG" -> "LONG"
                    "STRONG_SHORT" -> "STRONG SHORT"
                    "SHORT" -> "SHORT"
                    "NO_TRADE" -> "NO TRADE"
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
                    "STRONG_LONG", "LONG", "STRONG_BUY/SELL", "BUY/SELL" -> UpC
                    "STRONG_SHORT", "SHORT", "NO_TRADE", "AVOID" -> DnC
                    "CONSIDER" -> Gold
                    "WATCH", "CAUTION" -> GoldDim
                    "HALF_SIZE" -> BrkC
                    else -> TL
                }
                item { ChipS(actLbl, actCol) }
            }
            if (r.dataQuality.score > 0f) {
                Spacer(Modifier.height(4.dp))
                LazyRow(horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                    item {
                        ChipS(
                            "DATA Q ${"%.0f".format(r.dataQuality.score)}",
                            if (r.dataQuality.tradable) UpC else DnC,
                        )
                    }
                    item { ChipS(r.marketRegime.name.uppercase(), GoldDim) }
                    item {
                        ChipS(
                            "GATES ${r.decision.hardGatesPassed}/${r.decision.hardGatesTotal}",
                            if (r.decision.strictOmegaCompliant) UpC else DnC,
                        )
                    }
                    item { ChipS(r.decision.riskTier.uppercase(), TL) }
                }
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
    val verificationColor = if (r.ai.verified && r.ai.grounded) UpC else DnC
    Card(colors = CardDefaults.cardColors(containerColor = GoldSoft), shape = RoundedCornerShape(14.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, GoldDim.copy(alpha = 0.3f))) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.AutoAwesome, "ai", tint = Gold)
                Spacer(Modifier.width(8.dp))
                Text("Apex AI Explainability", color = Gold, fontWeight = FontWeight.Black, fontSize = 14.sp)
                Spacer(Modifier.weight(1f))
                Surface(shape = RoundedCornerShape(5.dp), color = sideC.copy(alpha = 0.20f)) {
                    Text("  ${r.ai.deterministicActionLabel}  ", color = sideC, fontSize = 9.sp, fontWeight = FontWeight.Black)
                }
            }
            Spacer(Modifier.height(7.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                ChipS(r.ai.provider.uppercase(), Gold)
                ChipS(r.ai.mode.uppercase(), TL)
                ChipS(if (r.ai.verified && r.ai.grounded) "VERIFIED" else "REFUSED", verificationColor)
            }
            Spacer(Modifier.height(7.dp))
            Text(
                if (loading) "در حال تحلیل..." else safeChartMessage(r.ai.summary.ifBlank { r.note }),
                color = TH,
                fontSize = 12.sp,
                lineHeight = 20.sp
            )
            if (!loading) {
                Spacer(Modifier.height(6.dp))
                Text(
                    if (r.ai.probabilityIsCalibrated) "Probability: calibrated • ${r.ai.probabilityLabel}"
                    else "Probability: model estimate • NOT CALIBRATED",
                    color = GoldDim,
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Bold
                )
                r.ai.refusalReason?.takeIf { it.isNotBlank() }?.let {
                    Spacer(Modifier.height(6.dp))
                    Text("Refusal: $it", color = DnC, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                }
                if (r.ai.evidenceItems.isNotEmpty()) {
                    Spacer(Modifier.height(8.dp))
                    Text("شواهد مثبت", color = UpC, fontSize = 11.sp, fontWeight = FontWeight.Black)
                    r.ai.evidenceItems.take(3).forEach { evidence ->
                        Text("• [${evidence.evidenceId}] ${safeChartMessage(evidence.statement)}", color = TH, fontSize = 10.sp, lineHeight = 15.sp)
                    }
                }
                if (r.ai.negativeEvidence.isNotEmpty()) {
                    Spacer(Modifier.height(7.dp))
                    Text("شواهد منفی / ریسک", color = DnC, fontSize = 11.sp, fontWeight = FontWeight.Black)
                    r.ai.negativeEvidence.take(3).forEach { evidence ->
                        Text("• [${evidence.evidenceId}] ${safeChartMessage(evidence.statement)}", color = TH, fontSize = 10.sp, lineHeight = 15.sp)
                    }
                }
                if (r.ai.whatWouldConfirm.isNotEmpty()) {
                    Spacer(Modifier.height(7.dp))
                    Text("چه چیزی تأیید می‌کند؟", color = Gold, fontSize = 11.sp, fontWeight = FontWeight.Black)
                    r.ai.whatWouldConfirm.take(3).forEach { item ->
                        Text("• ${safeChartMessage(item)}", color = TH, fontSize = 10.sp, lineHeight = 15.sp)
                    }
                }
                r.ai.invalidation?.takeIf { it.isNotBlank() }?.let {
                    Spacer(Modifier.height(7.dp))
                    Text("Invalidation: ${safeChartMessage(it)}", color = DnC, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                }
                Spacer(Modifier.height(7.dp))
                Text(
                    if (r.ai.deterministicCorePreserved) "🔒 Deterministic core preserved • AI cannot authorize execution"
                    else "⚠ Explainability contract unavailable",
                    color = TL,
                    fontSize = 9.sp
                )
            }
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
private fun SmcCanvas(modifier: Modifier = Modifier, report: SmcReport, scale: Float, onScale: (Float)->Unit, compare: List<CompareOverlay> = emptyList(), classicLevels: ClassicLevelsDto? = null, showClassic: Boolean = false) {
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
            if (z.kind !in listOf("OB", "FVG", "iFVG", "BRK", "SD")) continue
            if (!ChartRenderPolicy.isZoneLifecycleValid(z, totalCandles)) continue
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
                "SD" -> if (z.side == "bullish") Color(0xFF10B981) else Color(0xFFEF4444)
                else -> Color.Transparent
            }
            if (color == Color.Transparent || xend <= xstart) continue
            val zoneH = (bottom - top).coerceAtLeast(2f)
            val fillAlpha = when (z.kind) {
                "OB" -> 0.20f
                "FVG", "iFVG" -> 0.11f
                "BRK" -> 0.055f
                "SD" -> 0.14f
                else -> 0.1f
            }
            val borderAlpha = when (z.kind) {
                "OB" -> 0.88f
                "FVG", "iFVG" -> 0.62f
                "BRK" -> 0.42f
                "SD" -> 0.7f
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
            val label = ChartRenderPolicy.compactZoneLabel(z)
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

        // ======== v3.13: Classic levels (Donchian / Keltner / VWAP±2σ / Pivots) ========
        if (showClassic && classicLevels != null) {
            fun classicLine(price: Double?, col: Color, label: String, dash: FloatArray?) {
                if (price == null || price <= 0.0) return
                val y = priceY(price.toFloat())
                if (y < chartT || y > chartB) return
                drawLine(
                    col.copy(alpha = 0.8f), Offset(chartL, y), Offset(chartR, y),
                    strokeWidth = 1f,
                    pathEffect = dash?.let { PathEffect.dashPathEffect(it) }
                )
                val lp = NativePaint().apply { color = col.toArgb(); textSize = 13f; isAntiAlias = true }
                drawContext.canvas.nativeCanvas.drawText(
                    "$label  ${df.format(price.toFloat())}", chartL + 4f, y - 3f, lp
                )
            }
            classicLine(classicLevels.donchianUpper, DonchC, "DON 20 ↑", null)
            classicLine(classicLevels.donchianLower, DonchC, "DON 20 ↓", null)
            classicLine(classicLevels.keltnerUpper, KeltC, "KELT ↑", floatArrayOf(7f, 4f))
            classicLine(classicLevels.keltnerLower, KeltC, "KELT ↓", floatArrayOf(7f, 4f))
            classicLine(classicLevels.vwapUp2, BandC, "VWAP +2σ", floatArrayOf(2f, 4f))
            classicLine(classicLevels.vwapDn2, BandC, "VWAP -2σ", floatArrayOf(2f, 4f))
            classicLine(classicLevels.pivot, PivotC, "PIVOT", floatArrayOf(10f, 3f, 2f, 3f))
            classicLine(classicLevels.pivotR1, PivotC, "R1", floatArrayOf(10f, 3f, 2f, 3f))
            classicLine(classicLevels.pivotS1, PivotC, "S1", floatArrayOf(10f, 3f, 2f, 3f))
        }

        // ======== Only the latest EQH/EQL reference levels ========
        var lastArrowRight = false
        val plottedLiquidityY = mutableListOf<Float>()
        val simpleLiquidity = ChartRenderPolicy.latestLiquidityLevels(report.inducements)
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

        // ======== BOS/CHoCH — latest non-overlapping structure events ========
        val eventAnchors = mutableListOf<Offset>()
        for (ev in report.events.takeLast(6).asReversed()) {
            if (ev.index < startIdx || ev.index >= totalCandles) continue
            val col = if (ev.dir == "bullish") UpC else DnC
            val y = priceY(ev.price)
            if (y < chartT || y > chartB) continue
            val x = idxX(ev.index)
            if (eventAnchors.any { abs(it.x - x) < 48f && abs(it.y - y) < 16f }) continue
            eventAnchors += Offset(x, y)
            if (eventAnchors.size > 4) break

            val isBull = ev.dir == "bullish"
            val placeRight = x < chartR - 88f
            val lineEndX = if (placeRight) x + 40f else x - 40f
            drawLine(col.copy(alpha=0.65f), Offset(x, y), Offset(lineEndX, y), strokeWidth=1.0f)
            drawCircle(col, radius=3.2f, center=Offset(x, y))
            val paint = NativePaint().apply {
                color=col.toArgb(); textSize=10f; isAntiAlias=true; isFakeBoldText=true
            }
            val label = if (isBull) "▲ ${ev.kind}" else "▼ ${ev.kind}"
            val textX = if (placeRight) lineEndX + 3f else lineEndX - 34f
            drawContext.canvas.nativeCanvas.drawText(label, textX, y-4f, paint)
        }

        // ======== IDM نقاط زرد (Inducement) ========
        val idmAnchors = mutableListOf<Offset>()
        for (lab in report.inducements.asReversed()) {
            if (!lab.kind.contains("liq")) continue
            if (lab.index < startIdx || lab.index >= totalCandles) continue
            val x = idxX(lab.index)
            val y = priceY(lab.price)
            if (y < chartT || y > chartB) continue
            if (idmAnchors.any { abs(it.x - x) < 30f && abs(it.y - y) < 13f }) continue
            idmAnchors += Offset(x, y)
            if (idmAnchors.size > 3) break
            drawCircle(IdmColor, radius=3.2f, center=Offset(x, y))
            val paint = NativePaint().apply {
                color=IdmColor.toArgb(); textSize=10f; isAntiAlias=true; isFakeBoldText=true
            }
            drawContext.canvas.nativeCanvas.drawText("IDM", x+5f, y-4f, paint)
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

        // ======== سطوح واقعی خردساختار (POC/VAH/VAL/دیوارهای خرید و فروش) ========
        for (ml in report.microLevels) {
            val y = priceY(ml.price)
            if (y < chartT - 2f || y > chartB + 2f) continue
            val (c, label, dashed) = when (ml.kind) {
                "POC" -> Triple(Gold, "POC", false)
                "VAH" -> Triple(GoldDim, "VAH", true)
                "VAL" -> Triple(GoldDim, "VAL", true)
                "BIDWALL" -> Triple(UpC, "Bid Wall", true)
                "ASKWALL" -> Triple(DnC, "Ask Wall", true)
                else -> continue
            }
            drawLine(
                c.copy(alpha = 0.7f), Offset(chartL, y), Offset(chartR, y), strokeWidth = 0.9f,
                pathEffect = if (dashed) PathEffect.dashPathEffect(floatArrayOf(4f, 5f)) else null
            )
            val lp = NativePaint().apply { color = c.toArgb(); textSize = 10f; isAntiAlias = true; isFakeBoldText = true }
            val br = Rect(); lp.getTextBounds(label, 0, label.length, br)
            val pad = 3f
            val bx = chartR + 2f
            val by = y - br.height() / 2f - pad
            val bg = NativePaint().apply { color = android.graphics.Color.argb(200, 10, 12, 18) }
            drawContext.canvas.nativeCanvas.drawRect(bx, by, bx + br.width() + pad * 2, by + br.height() + pad * 2, bg)
            drawContext.canvas.nativeCanvas.drawText(label, bx + pad, y + br.height() / 2f - 1f, lp)
        }

        // ======== v3.19: خطوط RTM (QML / MPL / هدف نقدینگی DOL) ========
        for (ln in report.overlay.lines) {
            if (ln.price <= 0f) continue
            val (c, label, dash) = when (ln.kind) {
                "QML" -> Triple(Color(0xFFF59E0B), ln.label.ifEmpty { "QML" }, floatArrayOf(6f, 4f))
                "MPL" -> Triple(Color(0xFF8B5CF6), ln.label.ifEmpty { "MPL" }, floatArrayOf(2f, 4f))
                "DOL" -> Triple(Color(0xFF38BDF8), ln.label.ifEmpty { "DOL" }, floatArrayOf(8f, 4f))
                else -> continue
            }
            val y = priceY(ln.price)
            if (y < chartT - 2f || y > chartB + 2f) continue
            drawLine(
                c.copy(alpha = 0.85f), Offset(chartL, y), Offset(chartR, y), strokeWidth = 1.4f,
                pathEffect = PathEffect.dashPathEffect(dash)
            )
            val lp = NativePaint().apply { color = c.toArgb(); textSize = 11f; isAntiAlias = true; isFakeBoldText = true }
            drawContext.canvas.nativeCanvas.drawText(label, chartL + 6f, y - 5f, lp)
        }

        // ======== v3.11: خطوط مقایسه هم‌زمان (نرمال‌شده به محور قیمت نماد اصلی) ========
        if (compare.isNotEmpty() && visible.isNotEmpty()) {
            val anchor = visible.first().c
            compare.forEach { ov ->
                if (ov.closes.size < 2 || anchor <= 0f) return@forEach
                val offset = totalCandles - ov.closes.size
                val baseIdx = (startIdx - offset).coerceIn(0, ov.closes.size - 1)
                val base = ov.closes[baseIdx]
                if (base <= 0f) return@forEach
                var prevX = 0f
                var prevY = 0f
                var started = false
                for (ci in ov.closes.indices) {
                    val absIdx = offset + ci
                    if (absIdx < startIdx || absIdx >= totalCandles) continue
                    val scaled = anchor * (ov.closes[ci] / base)
                    val x = idxX(absIdx)
                    val y = priceY(scaled).coerceIn(chartT, chartB)
                    if (started) drawLine(ov.color.copy(alpha = 0.9f), Offset(prevX, prevY), Offset(x, y), strokeWidth = 1.6f)
                    prevX = x
                    prevY = y
                    started = true
                }
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
    val unsafe = listOf(
        "apikey=", "api_key=", "token=", "https://", "http://",
        "failed to connect", "connect to", "timeout", "onrender.com", ":443",
    ).any { value.contains(it, ignoreCase = true) }
    return if (unsafe) {
        "اتصال موقتاً برقرار نشد؛ دکمه بروزرسانی را بزنید."
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

// ============================ v3.11: مقایسه / SMT / هشدارها ============================
data class CompareSeries(val symbol: String, val closes: List<Float>)
data class CompareOverlay(val symbol: String, val closes: List<Float>, val color: Color)

private fun marketOf(symbol: String): String = when (symbol.uppercase()) {
    "BTCUSDT", "ETHUSDT", "SOLUSDT" -> "crypto"
    else -> "forex"
}

@Composable
private fun CompareChipRow(options: List<String>, selected: List<String>, onToggle: (String) -> Unit) {
    CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Ltr) {
        LazyRow(
            horizontalArrangement = Arrangement.spacedBy(6.dp),
            contentPadding = PaddingValues(horizontal = 2.dp)
        ) {
            items(options) { option ->
                val idx = selected.indexOf(option)
                val isOn = idx >= 0
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = if (isOn) COMPARE_COLORS[idx % COMPARE_COLORS.size].copy(alpha = 0.25f) else Surf,
                    border = if (isOn) androidx.compose.foundation.BorderStroke(
                        1.dp, COMPARE_COLORS[idx % COMPARE_COLORS.size]
                    ) else null,
                    modifier = Modifier.clickable { onToggle(option) }
                ) {
                    Text(
                        text = option,
                        color = if (isOn) TH else TL,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 7.dp)
                    )
                }
            }
        }
    }
}

@Composable
private fun SmtCard(smt: SmtInfoDto) {
    val scoreColor = if (smt.score > 0) UpC else if (smt.score < 0) DnC else TL
    Card(
        colors = CardDefaults.cardColors(containerColor = Surf),
        shape = RoundedCornerShape(14.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, Gold.copy(alpha = 0.25f))
    ) {
        Column(Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("🔗 واگرایی SMT (هوش پول هوشمند)", color = Gold, fontWeight = FontWeight.Black, fontSize = 13.sp)
                Spacer(Modifier.weight(1f))
                Text("امتیاز ${smt.score}", color = scoreColor, fontWeight = FontWeight.Black, fontSize = 13.sp)
            }
            Spacer(Modifier.height(6.dp))
            Text(smt.summaryFa, color = TH, fontSize = 12.sp, lineHeight = 20.sp)
            Spacer(Modifier.height(6.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                val corrTxt = smt.correlation?.let { String.format(java.util.Locale.US, "%.2f", it) } ?: "—"
                ChipS("همبستگی $corrTxt", if (smt.correlationReliable) UpC else DnC)
                Spacer(Modifier.width(6.dp))
                ChipS("${smt.primary} ↔ ${smt.correlated}", Gold)
            }
        }
    }
}

@Composable
private fun StrategyPackCard(s: StrategiesV2Dto) {
    val netColor = when (s.netDirection) { "long" -> UpC; "short" -> DnC; "conflict" -> BearOB; else -> TL }
    val netLabel = when (s.netDirection) {
        "long" -> "خالص: صعودی"; "short" -> "خالص: نزولی"
        "conflict" -> "تضاد سیگنال‌ها"; else -> "بدون جهت خالص"
    }
    Card(
        colors = CardDefaults.cardColors(containerColor = Surf),
        shape = RoundedCornerShape(14.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, netColor.copy(alpha = 0.45f))
    ) {
        Column(Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("🧰 استراتژی‌های کلاسیک (اسکن لایو)", color = Gold, fontWeight = FontWeight.Black, fontSize = 13.sp)
                Spacer(Modifier.weight(1f))
                ChipS(netLabel, netColor)
            }
            Spacer(Modifier.height(4.dp))
            val activeN = s.counts["active"] ?: s.active.size
            val formN = s.counts["forming"] ?: s.forming.size
            Text(
                "$activeN سیگنال فعال • $formN در حال شکل‌گیری • توافق ${s.agreementPct}٪",
                color = TL, fontSize = 11.sp
            )
            val gi = s.gates
            if (gi != null && gi.counts.tagged > 0) {
                Text(
                    "🛡️ گیت هم‌جهتی (EMA${gi.emaSpan}+رأی ±${gi.voteThreshold}): " +
                        "${gi.counts.gateOk} از ${gi.counts.tagged} هم‌جهت • خالص رأی ${gi.netVotes ?: "—"}",
                    color = if (gi.counts.gateOk * 2 >= gi.counts.tagged) Color(0xFF9BFFC8) else BearOB,
                    fontSize = 10.sp
                )
            }
            if (s.active.isNotEmpty()) {
                Spacer(Modifier.height(8.dp))
                s.active.take(6).forEach { st ->
                    val col = if (st.direction == "long") UpC else if (st.direction == "short") DnC else TL
                    Surface(
                        shape = RoundedCornerShape(10.dp), color = col.copy(alpha = 0.07f),
                        modifier = Modifier.fillMaxWidth().padding(vertical = 3.dp)
                    ) {
                        Row(Modifier.padding(10.dp), verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                Modifier.width(3.dp).height(34.dp).clip(RoundedCornerShape(2.dp)).background(col)
                            )
                            Spacer(Modifier.width(9.dp))
                            Column(Modifier.weight(1f)) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Text(
                                        st.nameFa, color = TH, fontSize = 12.sp,
                                        fontWeight = FontWeight.Black, modifier = Modifier.weight(1f, fill = false)
                                    )
                                    Spacer(Modifier.width(6.dp))
                                    Text(
                                        if (st.direction == "long") "LONG" else if (st.direction == "short") "SHORT" else "-",
                                        color = col, fontSize = 10.sp, fontWeight = FontWeight.Black
                                    )
                                }
                                Text(st.reasonFa, color = TL, fontSize = 10.sp, lineHeight = 15.sp, maxLines = 2)
                            }
                            Spacer(Modifier.width(8.dp))
                            Column(horizontalAlignment = Alignment.End) {
                                Surface(shape = RoundedCornerShape(6.dp), color = col.copy(alpha = 0.2f)) {
                                    Text(
                                        " ${st.quality}٪ ", color = col,
                                        fontSize = 11.sp, fontWeight = FontWeight.Black
                                    )
                                }
                                if (st.gateOk != null) {
                                    Spacer(Modifier.height(3.dp))
                                    Text(
                                        if (st.gateOk == true) "🛡️ هم‌جهت" else "⚠ ناهم‌جهت",
                                        color = if (st.gateOk == true) Color(0xFF9BFFC8) else BearOB,
                                        fontSize = 8.sp, fontWeight = FontWeight.Black
                                    )
                                }
                                if (st.perfOk != null) {
                                    Spacer(Modifier.height(3.dp))
                                    Text(
                                        if (st.perfOk == true) "📈 edge واقعی +" else "📉 edge واقعی −",
                                        color = if (st.perfOk == true) Color(0xFF9BFFC8) else BearOB,
                                        fontSize = 8.sp, fontWeight = FontWeight.Black
                                    )
                                }
                                if (st.entry != null && st.stop != null && st.target != null) {
                                    Spacer(Modifier.height(3.dp))
                                    Text(
                                        "E ${fmt(st.entry.toFloat())}",
                                        color = TL, fontSize = 8.sp
                                    )
                                }
                            }
                        }
                    }
                }
            }
            if (s.forming.isNotEmpty()) {
                Spacer(Modifier.height(6.dp))
                s.forming.take(3).forEach { st ->
                    Text("◌ ${st.nameFa} — ${st.reasonFa}", color = TL.copy(alpha = 0.8f), fontSize = 10.sp,
                        maxLines = 1, modifier = Modifier.padding(vertical = 1.dp))
                }
            }
        }
    }
}

@Composable
private fun IndicatorPackCard(s: IndicatorsV2SummaryDto) {
    val verdictColor = when (s.verdict) { "bullish" -> UpC; "bearish" -> DnC; "range" -> BearOB; else -> TL }
    val verdictLabel = when (s.verdict) {
        "bullish" -> "صعودی"; "bearish" -> "نزولی"; "range" -> "رنج"; "mixed" -> "ترکیبی"; else -> "-"
    }
    Card(
        colors = CardDefaults.cardColors(containerColor = Surf),
        shape = RoundedCornerShape(14.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, Gold.copy(alpha = 0.25f))
    ) {
        Column(Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("🔬 رأی اندیکاتورهای پیشرفته", color = Gold, fontWeight = FontWeight.Black, fontSize = 13.sp)
                Spacer(Modifier.weight(1f))
                ChipS("$verdictLabel • خالص ${s.net}٪", verdictColor)
            }
            Spacer(Modifier.height(8.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("▲ ${s.votes["bullish"] ?: 0}", color = UpC, fontWeight = FontWeight.Black, fontSize = 14.sp)
                Spacer(Modifier.width(14.dp))
                Text("▼ ${s.votes["bearish"] ?: 0}", color = DnC, fontWeight = FontWeight.Black, fontSize = 14.sp)
                Spacer(Modifier.width(14.dp))
                Text("• ${s.votes["neutral"] ?: 0}", color = TL, fontWeight = FontWeight.Black, fontSize = 14.sp)
                Spacer(Modifier.weight(1f))
                Text("از ${s.votes["total"] ?: 16} اندیکاتور", color = TL, fontSize = 10.sp)
            }
            Spacer(Modifier.height(8.dp))
            LazyRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                if (s.squeezeOn == true) item { ChipS("🗜️ SQUEEZE فعال", BearOB) }
                if (s.squeezeFired == true) item { ChipS("💥 Squeeze آزاد شد", Gold) }
                s.regimeChoppiness?.let { reg ->
                    item {
                        val chopVal = s.choppinessValue?.let { String.format(java.util.Locale.US, "%.0f", it) } ?: ""
                        ChipS(
                            when (reg) { "trend" -> "رونددار $chopVal"; "range" -> "رنج $chopVal"; else -> "گذار $chopVal" },
                            when (reg) { "trend" -> UpC; "range" -> BearOB; else -> TL }
                        )
                    }
                }
                s.vwapZ?.let { z ->
                    item {
                        ChipS(
                            "VWAP z=${String.format(java.util.Locale.US, "%.1f", z)}",
                            if (z > 2) DnC else if (z < -2) UpC else TL
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun IctProCard(ict: SmcIct) {
    val ms = ict.marketStructure
    val ote = ict.ote
    val kz = ict.killzone
    val stateColor = when (ms?.state) { "bullish" -> UpC; "bearish" -> DnC; "ranging" -> BearOB; else -> TL }
    Card(
        colors = CardDefaults.cardColors(containerColor = Surf),
        shape = RoundedCornerShape(14.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, FvgC.copy(alpha = 0.3f))
    ) {
        Column(Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("🏛️ ICT Pro — ساختار و زمان‌بندی", color = Gold, fontWeight = FontWeight.Black, fontSize = 13.sp)
                Spacer(Modifier.weight(1f))
                if (ms != null) {
                    ChipS("${ms.pattern} • ${ms.state}", stateColor)
                }
            }
            Spacer(Modifier.height(8.dp))
            if (ote != null && ote.available) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        "OTE (${if (ote.direction == "long") "صعودی" else "نزولی"}): " +
                            "${ote.oteBottom?.let { fmt(it.toFloat()) } ?: "—"} – ${ote.oteTop?.let { fmt(it.toFloat()) } ?: "—"}",
                        color = TH, fontSize = 11.sp
                    )
                    Spacer(Modifier.width(6.dp))
                    if (ote.priceInZone) ChipS("قیمت داخل OTE ⭐", Gold)
                }
                Spacer(Modifier.height(4.dp))
            }
            if (kz != null) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    val kzAct = kz.active
                    Text(
                        if (kzAct != null)
                            "⏰ کیلزون ${kzAct.name} — ${kzAct.minutesLeft} دقیقه مانده"
                        else "⏰ خارج از کیلزون",
                        color = if (kzAct != null) TH else TL, fontSize = 11.sp
                    )
                    Spacer(Modifier.width(6.dp))
                    ChipS(
                        when (kz.quality) { "high" -> "کیفیت بالا"; "medium" -> "کیفیت متوسط"; else -> "کیفیت پایین" },
                        when (kz.quality) { "high" -> UpC; "medium" -> BearOB; else -> DnC }
                    )
                }
                kz.active?.noteFa?.takeIf { it.isNotBlank() }?.let { note ->
                    Spacer(Modifier.height(3.dp))
                    Text(note, color = TL, fontSize = 10.sp)
                }
            }
            if (ms != null && ms.events.isNotEmpty()) {
                Spacer(Modifier.height(6.dp))
                ms.events.takeLast(3).forEach { ev ->
                    val col = if (ev.dir == "bullish") UpC else DnC
                    Text(
                        "${ev.kind} ${if (ev.dir == "bullish") "▲" else "▼"} @ ${ev.price?.let { fmt(it.toFloat()) } ?: "-"}",
                        color = col, fontSize = 10.sp, fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(vertical = 1.dp)
                    )
                }
            }
        }
    }
}

@Composable
private fun AlertCard(
    alerts: List<ProximityAlertDto>,
    enabled: Boolean,
    expanded: Boolean,
    onToggleEnabled: () -> Unit,
    onToggleOpen: () -> Unit
) {
    val latest = alerts.firstOrNull()
    Card(
        colors = CardDefaults.cardColors(containerColor = Surf),
        shape = RoundedCornerShape(14.dp),
        border = androidx.compose.foundation.BorderStroke(
            1.dp,
            when {
                latest == null -> Gold.copy(alpha = 0.18f)
                latest.severity == "critical" -> DnC.copy(alpha = 0.55f)
                else -> Gold.copy(alpha = 0.4f)
            }
        )
    ) {
        Column(Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.Notifications, "alerts", tint = Gold, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(8.dp))
                Text("هشدار مجاورت سطوح", color = Gold, fontWeight = FontWeight.Black, fontSize = 13.sp)
                Spacer(Modifier.weight(1f))
                Text(if (enabled) "زنده" else "خاموش", color = if (enabled) UpC else TL, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                Switch(checked = enabled, onCheckedChange = { onToggleEnabled() }, modifier = Modifier.height(24.dp))
            }
            if (latest != null) {
                Spacer(Modifier.height(8.dp))
                Text(
                    latest.messageFa,
                    color = if (latest.severity == "critical") DnC else TH,
                    fontSize = 12.sp,
                    lineHeight = 20.sp,
                    modifier = Modifier.clickable { onToggleOpen() }
                )
                if (alerts.size > 1) {
                    Spacer(Modifier.height(4.dp))
                    Text(
                        if (expanded) "بستن فهرست ▲" else "${alerts.size - 1} هشدار دیگر — نمایش ▼",
                        color = TL,
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.clickable { onToggleOpen() }
                    )
                    if (expanded) {
                        Spacer(Modifier.height(6.dp))
                        alerts.drop(1).take(8).forEach { row ->
                            Text(
                                row.messageFa,
                                color = if (row.severity == "critical") DnC.copy(alpha = 0.85f) else TL,
                                fontSize = 11.sp,
                                lineHeight = 18.sp,
                                modifier = Modifier.padding(vertical = 2.dp)
                            )
                        }
                    }
                }
            } else {
                Spacer(Modifier.height(6.dp))
                Text(
                    if (enabled) "در حال پایش فاصله قیمت تا نقدینگی‌ها، دیوارهای L2، POC/VAH/VAL و گپ‌ها..."
                    else "هشدارها خاموش است؛ برای پایش زنده روشن کنید.",
                    color = TL, fontSize = 11.sp
                )
            }
        }
    }
}
