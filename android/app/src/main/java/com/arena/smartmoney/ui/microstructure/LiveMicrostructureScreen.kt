package com.arena.smartmoney.ui.microstructure

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.view
import com.arena.smartmoney.data.model.MicroStructureInfo
import com.arena.smartmoney.data.model.SmcReport
import com.arena.smartmoney.data.repository.TradingRepository
import com.arena.smartmoney.ui.theme.CardBg
import com.arena.smartmoney.ui.theme.CyanAccent
import com.arena.smartmoney.ui.theme.DarkBg
import com.arena.smartmoney.ui.theme.SoftText
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

private val WATCHLIST_20 = listOf(
    "BTCUSDT" to "crypto", "ETHUSDT" to "crypto", "SOLUSDT" to "crypto", "XRPUSDT" to "crypto",
    "BNBUSDT" to "crypto", "AVAXUSDT" to "crypto", "DOGEUSDT" to "crypto", "XAUUSD" to "",
    "XAGUSD" to "", "EURUSD" to "", "GBPUSD" to "", "USDJPY" to "",
    "GBPJPY" to "", "AUDUSD" to "", "NZDUSD" to "", "USDCAD" to "",
    "USDCHF" to "", "USOIL" to "", "US100" to "", "US30" to ""
)

data class LiveMicroUiState(
    val selected: String = "BTCUSDT",
    val market: String = "crypto",
    val loading: Boolean = false,
    val report: SmcReport? = null,
    val error: String? = null,
    val lastUpdate: String = "",
    val autoRefresh: Boolean = true
)

class LiveMicroViewModel(
    private val repo: TradingRepository = TradingRepository()
) : ViewModel() {
    private val _state = MutableStateFlow(LiveMicroUiState())
    val state: StateFlow<LiveMicroUiState> = _state

    init { refresh() }

    fun select(symbol: String, market: String) {
        _state.value = _state.value.copy(selected = symbol, market = market)
        refresh()
    }

    fun toggleAuto() {
        _state.value = _state.value.copy(autoRefresh = !_state.value.autoRefresh)
    }

    fun refresh() {
        val s = _state.value.selected
        val m = _state.value.market
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            try {
                val r = repo.getSmcAnalysis(symbol = s, market = m, interval = "15min")
                _state.value = _state.value.copy(
                    loading = false,
                    report = r,
                    lastUpdate = java.time.LocalTime.now().withNano(0).toString() + " UTC",
                    error = null
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(loading = false, error = e.message ?: "خطا در دریافت")
            }
        }
    }
}

@Composable
fun LiveMicrostructureScreen() {
    val vm: LiveMicroViewModel = androidx.lifecycle.viewmodel.compose.viewModel()
    val ui by vm.state.collectAsState()
    var tick by remember { mutableStateOf(0) }
    LaunchedEffect(ui.autoRefresh) {
        while (true) {
            delay(if (ui.autoRefresh) 5000 else 10000)
            if (ui.autoRefresh) vm.refresh()
            tick++
        }
    }
    Column(
        Modifier
            .fillMaxSize()
            .background(DarkBg)
            .verticalScroll(rememberScrollState())
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        // Header
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.weight(1f)) {
                Text("🧱 L2 / VP / Footprint زنده", color = Color.White, fontSize = 16.sp, fontWeight = FontWeight.Bold)
                Text("OrderFlow واقعی 400 لول + VP 20 + Footprint 6×12 از OKX", color = SoftText, fontSize = 11.sp)
            }
            Box(
                Modifier
                    .clip(RoundedCornerShape(8.dp))
                    .background(if (ui.autoRefresh) CyanAccent else Color(0xFF334155))
                    .clickable { vm.toggleAuto() }
                    .padding(horizontal = 10.dp, vertical = 6.dp)
            ) {
                Text(if (ui.autoRefresh) "⏸ توقف" else "▶ زنده 5ث", color = if (ui.autoRefresh) Color.Black else Color.White, fontSize = 11.sp, fontWeight = FontWeight.Bold)
            }
        }
        Text("آخرین: ${ui.lastUpdate} • ${ui.selected} • ${if (ui.loading) "در حال بارگذاری..." else "آماده"}", color = SoftText.copy(alpha = 0.7f), fontSize = 10.sp)

        // Symbol chips
        LazyRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            items(WATCHLIST_20) { (sym, mk) ->
                val sel = ui.selected == sym
                Box(
                    Modifier
                        .clip(RoundedCornerShape(12.dp))
                        .background(if (sel) CyanAccent else CardBg)
                        .border(1.dp, if (sel) CyanAccent else Color(0xFF22364F), RoundedCornerShape(12.dp))
                        .clickable { vm.select(sym, mk) }
                        .padding(horizontal = 10.dp, vertical = 6.dp)
                ) {
                    Text(sym, color = if (sel) Color.Black else Color.White, fontSize = 11.sp, fontWeight = if (sel) FontWeight.Bold else FontWeight.Normal)
                }
            }
        }

        if (ui.loading && ui.report == null) {
            Box(Modifier.fillMaxWidth().padding(30.dp), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = CyanAccent)
            }
        }

        ui.error?.let {
            Box(Modifier.fillMaxWidth().background(Color(0xFF7F1D1D).copy(alpha = 0.3f), RoundedCornerShape(12.dp)).padding(12.dp)) {
                Text(it, color = Color(0xFFFCA5A5), fontSize = 11.sp)
            }
        }

        ui.report?.let { r ->
            val micro = r.decision.orderflow.micro
            val of = r.decision.orderflow
            val isReal = micro?.isReal == true || of.isReal
            // Badge
            Row(
                Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(10.dp))
                    .background(if (isReal) Color(0xFF065F46).copy(alpha = 0.5f) else Color(0xFF7C2D12).copy(alpha = 0.5f))
                    .border(1.dp, if (isReal) Color(0xFF10B981) else Color(0xFFF59E0B), RoundedCornerShape(10.dp))
                    .padding(10.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(if (isReal) "✅ REAL" else "⚠️ PROXY", color = if (isReal) Color(0xFF6EE7B7) else Color(0xFFFCD34D), fontSize = 11.sp, fontWeight = FontWeight.Bold)
                Spacer(Modifier.width(8.dp))
                Text(micro?.source ?: of.source, color = Color.White, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                Spacer(Modifier.weight(1f))
                Text("conf ${(micro?.confidence ?: of.confidence)} • ${micro?.windowTrades ?: "-"} trades", color = SoftText, fontSize = 10.sp)
            }
            if (!isReal) {
                Text("فارکس / طلا proxy است — L2 واقعی متمرکز ندارد. برای کریپتو REAL است.", color = Color(0xFFFCD34D), fontSize = 10.sp, modifier = Modifier.background(Color(0xFF78350F).copy(alpha = 0.3f), RoundedCornerShape(8.dp)).padding(8.dp))
            }

            // L2 Card
            L2Card(micro)

            // VP Card
            VPCard(micro)

            // Footprint Card
            FootprintCard(micro)

            // OrderFlow delta
            OrderFlowCard(of, micro)
        }

        Spacer(Modifier.height(20.dp))
        Text("منبع: OKX public — 400 لول + 2600 ترید — هر 5ث زنده (WebSocket <1ث در alpha84) — فقط یک صرافی، نه کل بازار", color = SoftText.copy(alpha = 0.5f), fontSize = 9.sp)
    }
}

@Composable
private fun L2Card(micro: MicroStructureInfo?) {
    val l2 = micro?.l2
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(CardBg)
            .border(1.dp, Color(0xFF22364F), RoundedCornerShape(14.dp))
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Text("🧱 Level-2 Depth 400", color = CyanAccent, fontSize = 13.sp, fontWeight = FontWeight.Bold)
        if (l2 == null) {
            Text("داده L2 در دسترس نیست (proxy)", color = SoftText, fontSize = 11.sp)
            return
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Info("mid", l2.mid?.toString() ?: "-")
            Info("spread", (l2.spreadBps?.let { "${"%.1f".format(it)}bp" } ?: "-"))
            Info("imb 25", l2.imbalanceTop25?.let { "${"%.2f".format(it)}" } ?: "-")
        }
        l2.bidWall?.let { w ->
            Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(8.dp)).background(Color(0xFF065F46).copy(alpha = 0.3f)).padding(8.dp), verticalAlignment = Alignment.CenterVertically) {
                Text("🟢 BID WALL", color = Color(0xFF6EE7B7), fontSize = 11.sp, fontWeight = FontWeight.Bold)
                Spacer(Modifier.weight(1f))
                Text("${w.price} • notional ${w.notional?.let { "%.0f".format(it) } ?: "-"} • ×${w.xMedian ?: "-"}", color = Color.White, fontSize = 11.sp)
            }
        }
        l2.askWall?.let { w ->
            Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(8.dp)).background(Color(0xFF7F1D1D).copy(alpha = 0.3f)).padding(8.dp), verticalAlignment = Alignment.CenterVertically) {
                Text("🔴 ASK WALL", color = Color(0xFFFCA5A5), fontSize = 11.sp, fontWeight = FontWeight.Bold)
                Spacer(Modifier.weight(1f))
                Text("${w.price} • notional ${w.notional?.let { "%.0f".format(it) } ?: "-"} • ×${w.xMedian ?: "-"}", color = Color.White, fontSize = 11.sp)
            }
        }
        // Depth bars for top25 imbalance visual
        val imb = l2.imbalanceTop25 ?: 0f
        Column(Modifier.fillMaxWidth()) {
            Text("عدم توازن 25 سطح: ${"%.2f".format(imb)}", color = SoftText, fontSize = 10.sp)
            Row(Modifier.fillMaxWidth().height(10.dp).clip(RoundedCornerShape(6.dp)).background(Color(0xFF1F2937))) {
                val bidPct = ((imb + 1f) / 2f).coerceIn(0f, 1f)
                Box(Modifier.fillMaxHeight().weight(bidPct).background(Color(0xFF10B981)))
                Box(Modifier.fillMaxHeight().weight(1f - bidPct).background(Color(0xFFEF4444)))
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("BID", color = Color(0xFF6EE7B7), fontSize = 9.sp)
                Text("ASK", color = Color(0xFFFCA5A5), fontSize = 9.sp)
            }
        }
    }
}

@Composable
private fun VPCard(micro: MicroStructureInfo?) {
    val vp = micro?.vp
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(CardBg)
            .border(1.dp, Color(0xFF22364F), RoundedCornerShape(14.dp))
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Text("📊 Volume Profile 20 bins (واقعی)", color = CyanAccent, fontSize = 13.sp, fontWeight = FontWeight.Bold)
        if (vp == null) {
            Text("VP در دسترس نیست", color = SoftText, fontSize = 11.sp)
            return
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Info("POC", vp.poc?.toString() ?: "-")
            Info("VAH", vp.vah?.toString() ?: "-")
            Info("VAL", vp.valueLow?.toString() ?: "-")
        }
        // HVN / LVN
        if (vp.hvn.isNotEmpty()) {
            Text("HVN: ${vp.hvn.take(3).joinToString(", ")}", color = Color(0xFFFCD34D), fontSize = 10.sp)
        }
        if (vp.lvn.isNotEmpty()) {
            Text("LVN: ${vp.lvn.take(3).joinToString(", ")}", color = SoftText, fontSize = 10.sp)
        }
        // Histogram (use POC/VAH/VAL as proxy bars — real bins not exposed in micro compact, show levels)
        Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(8.dp)).background(Color(0xFF0F172A)).padding(8.dp)) {
            val levels = listOfNotNull(vp.valueLow, vp.poc, vp.vah).sorted()
            if (levels.size >= 2) {
                levels.forEach { lvl ->
                    val isPoc = lvl == vp.poc
                    Row(Modifier.fillMaxWidth().padding(vertical = 3.dp), verticalAlignment = Alignment.CenterVertically) {
                        Text("${"%.2f".format(lvl)}", color = if (isPoc) Color(0xFFFCD34D) else SoftText, fontSize = 10.sp, modifier = Modifier.width(80.dp))
                        Box(
                            Modifier
                                .height(8.dp)
                                .weight(if (isPoc) 1f else 0.6f)
                                .clip(RoundedCornerShape(4.dp))
                                .background(if (isPoc) Color(0xFFF59E0B) else if (lvl == vp.vah || lvl == vp.valueLow) Color(0xFF3B82F6) else Color(0xFF475569))
                        )
                        if (isPoc) Text(" POC", color = Color(0xFFFCD34D), fontSize = 9.sp, fontWeight = FontWeight.Bold)
                    }
                }
            } else {
                Text("bins: ${vp.poc} • شکل پروفایل از 20 bins واقعی", color = SoftText, fontSize = 10.sp)
            }
        }
        Text("برای هیستوگرام کامل 20 میله‌ای، API orderflow.volume_profile.bins را می‌خوانیم (در alpha84 کامل می‌شود)", color = SoftText.copy(alpha = 0.6f), fontSize = 9.sp)
    }
}

@Composable
private fun FootprintCard(micro: MicroStructureInfo?) {
    val fp = micro?.footprint
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(CardBg)
            .border(1.dp, Color(0xFF22364F), RoundedCornerShape(14.dp))
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Text("👣 Footprint 6×12 (واقعی)", color = CyanAccent, fontSize = 13.sp, fontWeight = FontWeight.Bold)
        if (fp == null) {
            Text("Footprint در دسترس نیست", color = SoftText, fontSize = 11.sp)
            return
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Info("candles", "${fp.candlesCovered ?: "-"}")
            Info("last Δ", fp.lastDelta?.let { "${"%.2f".format(it)}" } ?: "-")
            Info("POC", fp.lastPoc?.toString() ?: "-")
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Box(Modifier.clip(RoundedCornerShape(6.dp)).background(if ((fp.stackedBuy ?: 0) >= 3) Color(0xFF065F46) else Color(0xFF1F2937)).padding(horizontal = 8.dp, vertical = 4.dp)) {
                Text("stacked BUY ${fp.stackedBuy ?: 0}", color = Color(0xFF6EE7B7), fontSize = 10.sp)
            }
            Box(Modifier.clip(RoundedCornerShape(6.dp)).background(if ((fp.stackedSell ?: 0) >= 3) Color(0xFF7F1D1D) else Color(0xFF1F2937)).padding(horizontal = 8.dp, vertical = 4.dp)) {
                Text("stacked SELL ${fp.stackedSell ?: 0}", color = Color(0xFFFCA5A5), fontSize = 10.sp)
            }
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text("unfinished high: ${if (fp.unfinishedHigh == true) "✅" else "—"}", color = SoftText, fontSize = 10.sp)
            Text("low: ${if (fp.unfinishedLow == true) "✅" else "—"}", color = SoftText, fontSize = 10.sp)
        }
        fp.summary?.let { s ->
            Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(8.dp)).background(Color(0xFF0F172A)).padding(8.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("جمع‌بندی:", color = CyanAccent, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                Text("POC migration: ${s.pocMigration ?: "-"} • divergence: ${s.deltaPriceDivergence ?: "-"}", color = Color.White, fontSize = 10.sp)
                Text("stacked bias: ${s.stackedBias ?: "-"} • delta trend: ${s.deltaTrend ?: "-"} • unfinished: ${s.unfinishedBias ?: "-"}", color = SoftText, fontSize = 10.sp)
            }
        }
    }
}

@Composable
private fun OrderFlowCard(of: com.arena.smartmoney.data.model.SmcDecisionOrderFlow, micro: MicroStructureInfo?) {
    val flow = micro?.flow
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(CardBg)
            .border(1.dp, Color(0xFF22364F), RoundedCornerShape(14.dp))
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Text("⚡ OrderFlow Delta / CVD", color = CyanAccent, fontSize = 13.sp, fontWeight = FontWeight.Bold)
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Info("pressure", flow?.pressure ?: of.pressure)
            Info("delta", flow?.delta?.let { "${"%.3f".format(it)}" } ?: "-")
            Info("CVD", flow?.cvd?.let { "${"%.1f".format(it)}" } ?: "-")
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Box(Modifier.weight(1f).clip(RoundedCornerShape(8.dp)).background(if (flow?.absorption == true) Color(0xFFF59E0B).copy(alpha = 0.2f) else Color(0xFF1F2937)).padding(8.dp), contentAlignment = Alignment.Center) {
                Text(if (flow?.absorption == true) "⚠️ Absorption" else "— absorption", color = if (flow?.absorption == true) Color(0xFFFCD34D) else SoftText, fontSize = 10.sp)
            }
            Box(Modifier.weight(1f).clip(RoundedCornerShape(8.dp)).background(if (flow?.climax == true) Color(0xFFEF4444).copy(alpha = 0.2f) else Color(0xFF1F2937)).padding(8.dp), contentAlignment = Alignment.Center) {
                Text(if (flow?.climax == true) "🔥 Climax" else "— climax", color = if (flow?.climax == true) Color(0xFFFCA5A5) else SoftText, fontSize = 10.sp)
            }
        }
        flow?.cvdDivergence?.let {
            Text("واگرایی CVD: $it", color = if (it == "bullish") Color(0xFF6EE7B7) else Color(0xFFFCA5A5), fontSize = 11.sp, fontWeight = FontWeight.Bold, modifier = Modifier.background(Color(0xFF1F2937), RoundedCornerShape(6.dp)).padding(6.dp))
        }
        micro?.filters?.let { f ->
            Text("فیلترها: ${f.netBias} (score ${"%.2f".format(f.score)}) • ${f.signals.take(3).joinToString(", ")}", color = SoftText, fontSize = 10.sp)
        }
    }
}

@Composable
private fun Info(label: String, value: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(label, color = SoftText, fontSize = 9.sp)
        Text(value, color = Color.White, fontSize = 11.sp, fontWeight = FontWeight.Bold)
    }
}
