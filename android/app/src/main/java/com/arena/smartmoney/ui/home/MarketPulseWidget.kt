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
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.arena.smartmoney.data.repository.TradingRepository
import com.arena.smartmoney.ui.theme.BlueAccent
import com.arena.smartmoney.ui.theme.CardBg
import com.arena.smartmoney.ui.theme.CyanAccent
import com.arena.smartmoney.ui.theme.DangerRed
import com.arena.smartmoney.ui.theme.SoftText
import com.arena.smartmoney.ui.theme.SuccessGreen
import com.arena.smartmoney.util.AlertPrefs
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class PulseItem(
    val symbol: String,
    val tier: String,
    val probability: Int,
    val side: String,
    val price: Float,
)

data class PulseUiState(
    val loading: Boolean = false,
    val items: List<PulseItem> = emptyList(),
    val scanned: Int = 0,
    val lastScan: String = "",
    val lastScanMillis: Long = 0L,
    val error: String? = null
)

class MarketPulseViewModel(
    private val repository: TradingRepository = TradingRepository()
) : ViewModel() {
    private val _uiState = MutableStateFlow(PulseUiState())
    val uiState: StateFlow<PulseUiState> = _uiState
    private val watchlist = AlertPrefs.watchlist

    init { scan() }

    fun scan() {
        if (_uiState.value.loading) return
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, error = null)
            val list = mutableListOf<PulseItem>()
            var scanned = 0
            var firstError: String? = null
            try {
                val results = coroutineScope {
                    watchlist.map { (symbol, market, interval) ->
                        async {
                            try { symbol to repository.getSmcAnalysis(symbol, market, interval) }
                            catch (e: Exception) { symbol to null }
                        }
                    }.map { it.await() }
                }
                for ((symbol, report) in results) {
                    scanned++
                    if (report == null) {
                        if (firstError == null) firstError = "برخی نمادها پاسخ ندادند"
                        // still add as gray unknown
                        list.add(PulseItem(symbol, "UNKNOWN", 0, "flat", 0f))
                        continue
                    }
                    val tier = report.displayTier.ifEmpty { "NONE" }
                    list.add(PulseItem(symbol, tier, report.estimatedWinProbability, report.direction, report.price))
                }
            } catch (e: Exception) {
                firstError = e.message
            }
            // sort: ACTIONABLE first, then HIGH, then PROB70, then WATCH, then NONE/UNKNOWN last, then by prob desc
            val order = mapOf("ACTIONABLE" to 0, "HIGH_CONFIDENCE_WATCH" to 1, "PROB_WATCH_70" to 2, "WATCH" to 3, "NONE" to 4, "UNKNOWN" to 5)
            list.sortWith(compareBy({ order[it.tier] ?: 9 }, { -it.probability }))
            _uiState.value = PulseUiState(
                loading = false,
                items = list,
                scanned = scanned,
                lastScan = java.time.ZonedDateTime.now(java.time.ZoneOffset.UTC).format(java.time.format.DateTimeFormatter.ofPattern("HH:mm")),
                lastScanMillis = System.currentTimeMillis(),
                error = firstError
            )
        }
    }
}

@Composable
fun MarketPulseWidget(
    viewModel: MarketPulseViewModel = viewModel(),
    onOpenProbable: () -> Unit = {}
) {
    val state by viewModel.uiState.collectAsState()
    var autoRefresh by remember { mutableStateOf(true) }
    LaunchedEffect(autoRefresh) {
        while (autoRefresh) {
            kotlinx.coroutines.delay(90_000)
            if (!viewModel.uiState.value.loading) viewModel.scan()
        }
    }
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(CardBg, RoundedCornerShape(18.dp))
            .border(1.dp, Color(0xFF2A4A6B), RoundedCornerShape(18.dp))
            .padding(14.dp)
    ) {
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Column(modifier = Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    val ageSec = if (state.lastScanMillis > 0) ((System.currentTimeMillis() - state.lastScanMillis) / 1000).toInt() else 999
                    val dotColor = when { ageSec < 120 -> SuccessGreen; ageSec < 300 -> Color(0xFFFFC857); else -> DangerRed }
                    Box(modifier = Modifier.width(8.dp).height(8.dp).background(dotColor, RoundedCornerShape(4.dp)))
                    Spacer(Modifier.width(6.dp))
                    Text("🗺 پالس بازار — ۲۰ نماد", color = Color.White, fontSize = 13.5.sp, fontWeight = FontWeight.Bold)
                }
                Text("خودکار ۹۰ثانیه ${if (autoRefresh) "فعال" else "متوقف"} • ${state.lastScan.ifEmpty { "—" }} UTC • ${state.scanned} نماد", color = SoftText.copy(alpha = 0.55f), fontSize = 10.sp, lineHeight = 13.sp)
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(if (autoRefresh) "⏸" else "▶", color = if (autoRefresh) SoftText else CyanAccent, fontSize = 14.sp, modifier = Modifier.clickable { autoRefresh = !autoRefresh }.padding(6.dp))
                Text(if (state.loading) "…" else "↻", color = CyanAccent, fontSize = 18.sp, modifier = Modifier.clickable(enabled = !state.loading) { viewModel.scan() }.padding(6.dp))
            }
        }
        Spacer(Modifier.height(10.dp))
        if (state.loading && state.items.isEmpty()) {
            Box(modifier = Modifier.fillMaxWidth().height(80.dp), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = CyanAccent, strokeWidth = 2.dp, modifier = Modifier.width(22.dp).height(22.dp))
            }
        } else if (state.items.isNotEmpty()) {
            // 4 columns × 5 rows = 20
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                for (row in state.items.chunked(4)) {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        for (item in row) {
                            PulseTile(item, modifier = Modifier.weight(1f), onClick = onOpenProbable)
                        }
                        // fill remainder if last row <4 (should not happen with 20)
                        repeat(4 - row.size) { Spacer(Modifier.weight(1f)) }
                    }
                }
            }
            Spacer(Modifier.height(8.dp))
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("${state.scanned} نماد • ${state.lastScan} UTC", color = SoftText.copy(alpha = 0.45f), fontSize = 10.sp)
                Text("ضربه برای جزئیات →", color = CyanAccent.copy(alpha = 0.7f), fontSize = 10.sp, modifier = Modifier.clickable(onClick = onOpenProbable))
            }
            // legend
            Spacer(Modifier.height(6.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                LegendDot(SuccessGreen, "اکشن")
                LegendDot(CyanAccent, "≥۸۰٪")
                LegendDot(BlueAccent, "≥۷۰٪")
                LegendDot(Color(0xFFFFC857), "WATCH")
                LegendDot(Color(0xFF3A4A5E), "فعلاً هیچ")
            }
        }
        if (state.error != null && state.items.isEmpty()) {
            Spacer(Modifier.height(6.dp))
            Text(state.error ?: "", color = DangerRed, fontSize = 11.sp)
        }
    }
}

@Composable
private fun PulseTile(item: PulseItem, modifier: Modifier, onClick: () -> Unit) {
    val bg: Color
    val border: Color
    val probColor: Color
    val tierFa: String
    when (item.tier) {
        "ACTIONABLE" -> { bg = SuccessGreen.copy(alpha = 0.18f); border = SuccessGreen.copy(alpha = 0.55f); probColor = SuccessGreen; tierFa = "اکشن" }
        "HIGH_CONFIDENCE_WATCH" -> { bg = CyanAccent.copy(alpha = 0.16f); border = CyanAccent.copy(alpha = 0.5f); probColor = CyanAccent; tierFa = "۸۰٪" }
        "PROB_WATCH_70" -> { bg = BlueAccent.copy(alpha = 0.16f); border = BlueAccent.copy(alpha = 0.45f); probColor = BlueAccent; tierFa = "۷۰٪" }
        "WATCH" -> { bg = Color(0xFFFFC857).copy(alpha = 0.14f); border = Color(0xFFFFC857).copy(alpha = 0.45f); probColor = Color(0xFFFFC857); tierFa = "WATCH" }
        else -> { bg = Color(0xFF1A2535); border = Color.White.copy(alpha = 0.08f); probColor = SoftText.copy(alpha = 0.5f); tierFa = "—" }
    }
    val sideArrow = when (item.side) {
        "long" -> "▲"
        "short" -> "▼"
        else -> "•"
    }
    val sideColor = when (item.side) {
        "long" -> SuccessGreen
        "short" -> DangerRed
        else -> SoftText.copy(alpha = 0.4f)
    }
    Column(
        modifier = modifier
            .background(bg, RoundedCornerShape(10.dp))
            .border(1.dp, border, RoundedCornerShape(10.dp))
            .clickable(onClick = onClick)
            .padding(horizontal = 6.dp, vertical = 7.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(item.symbol, color = Color.White, fontSize = 10.5.sp, fontWeight = FontWeight.Bold, maxLines = 1, textAlign = TextAlign.Center)
        Spacer(Modifier.height(3.dp))
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.Center) {
            Text(sideArrow, color = sideColor, fontSize = 9.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.width(3.dp))
            Text(if (item.probability > 0) "${item.probability}٪" else tierFa, color = probColor, fontSize = 11.sp, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun LegendDot(color: Color, label: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(modifier = Modifier.width(8.dp).height(8.dp).background(color, RoundedCornerShape(4.dp)))
        Spacer(Modifier.width(4.dp))
        Text(label, color = SoftText.copy(alpha = 0.6f), fontSize = 9.sp)
    }
}
