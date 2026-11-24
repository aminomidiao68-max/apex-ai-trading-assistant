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
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.arena.smartmoney.data.repository.TradingRepository
import com.arena.smartmoney.ui.theme.BlueAccent
import com.arena.smartmoney.ui.theme.CardBg
import com.arena.smartmoney.ui.theme.CyanAccent
import com.arena.smartmoney.ui.theme.DangerRed
import com.arena.smartmoney.ui.theme.DarkBg
import com.arena.smartmoney.ui.theme.SoftText
import com.arena.smartmoney.ui.theme.SuccessGreen
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class ProbableItem(
    val symbol: String,
    val side: String,
    val grade: String,
    val tier: String,
    val probability: Int,
    val rr: Float,
    val price: Float,
)

data class ProbableUiState(
    val loading: Boolean = false,
    val items: List<ProbableItem> = emptyList(),
    val scanned: Int = 0,
    val lastScan: String = "",
    val error: String? = null,
)

class ProbableSetupsViewModel(
    private val repository: TradingRepository = TradingRepository(),
) : ViewModel() {

    private val _uiState = MutableStateFlow(ProbableUiState())
    val uiState: StateFlow<ProbableUiState> = _uiState

    private val watchlist = listOf(
        Triple("BTCUSDT", "crypto", "1h"),
        Triple("ETHUSDT", "crypto", "1h"),
        Triple("SOLUSDT", "crypto", "1h"),
        Triple("XAUUSD", "", "1h"),
        Triple("EURUSD", "", "1h"),
        Triple("GBPUSD", "", "1h"),
    )

    init {
        scan()
    }

    fun scan() {
        if (_uiState.value.loading) return
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, error = null)
            val found = mutableListOf<ProbableItem>()
            var scanned = 0
            var firstError: String? = null
            try {
                val results = coroutineScope {
                    watchlist.map { (symbol, market, interval) ->
                        async {
                            try {
                                symbol to repository.getSmcAnalysis(
                                    symbol = symbol,
                                    market = market,
                                    interval = interval,
                                )
                            } catch (e: Exception) {
                                symbol to null
                            }
                        }
                    }.map { it.await() }
                }
                for ((symbol, report) in results) {
                    scanned++
                    if (report == null) {
                        if (firstError == null) firstError = "برخی نمادها پاسخ ندادند (سرور یا شبکه)"
                        continue
                    }
                    val tier = report.displayTier
                    if (tier.isNotEmpty() && tier != "NONE" && report.estimatedWinProbability >= 70) {
                        found.add(
                            ProbableItem(
                                symbol = symbol,
                                side = report.direction,
                                grade = report.grade,
                                tier = tier,
                                probability = report.estimatedWinProbability,
                                rr = report.rr,
                                price = report.price,
                            ),
                        )
                    }
                }
            } catch (e: Exception) {
                firstError = e.message ?: "خطای ناشناخته"
            }
            val order = mapOf("ACTIONABLE" to 0, "HIGH_CONFIDENCE_WATCH" to 1, "PROB_WATCH_70" to 2)
            found.sortWith(
                compareBy({ order[it.tier] ?: 9 }, { -it.probability }),
            )
            _uiState.value = ProbableUiState(
                loading = false,
                items = found,
                scanned = scanned,
                lastScan = java.time.ZonedDateTime.now(java.time.ZoneOffset.UTC)
                    .format(java.time.format.DateTimeFormatter.ofPattern("HH:mm:ss")),
                error = firstError,
            )
        }
    }
}

@Composable
fun ProbableSetupsScreen(
    viewModel: ProbableSetupsViewModel = androidx.lifecycle.viewmodel.compose.viewModel(),
) {
    val state by viewModel.uiState.collectAsState()
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkBg),
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(PaddingValues(start = 16.dp, top = 14.dp, end = 16.dp, bottom = 24.dp)),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text("🎖 ستاپ‌های محتمل", color = SoftText, fontSize = 20.sp, fontWeight = FontWeight.Bold)
                Text(
                    if (state.loading) "در حال اسکن…" else "↻ اسکن دوباره",
                    color = CyanAccent,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier
                        .clickable(enabled = !state.loading) { viewModel.scan() }
                        .padding(PaddingValues(all = 6.dp)),
                )
            }
            Spacer(Modifier.height(8.dp))
            Text(
                "لایهٔ تماشا — مجوز ورود نیست. احتمال برد، تخمین غیرکالیبرهٔ مدل است، نه وعده. " +
                    "فقط ردیف ACTIONABLE تمام ۲۷ گیت سخت‌گیرانه را پاس کرده است.",
                color = SoftText.copy(alpha = 0.75f),
                fontSize = 12.sp,
                lineHeight = 19.sp,
            )
            Spacer(Modifier.height(12.dp))
            if (state.loading && state.items.isEmpty()) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(120.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    CircularProgressIndicator(color = CyanAccent)
                }
            } else if (state.items.isEmpty()) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(CardBg, RoundedCornerShape(16.dp))
                        .border(1.dp, Color.White.copy(alpha = 0.06f), RoundedCornerShape(16.dp))
                        .padding(PaddingValues(all = 18.dp)),
                ) {
                    Text(
                        "فعلاً هیچ ستاپی با احتمال برد تخمینی ≥۷۰٪ دیده نشد.\n" +
                            "این طبیعی است: کیفیت مهم است، نه تعداد — بعضی روزها چند ستاپ، بعضی هفته‌ها هیچ.",
                        color = SoftText.copy(alpha = 0.85f),
                        fontSize = 13.sp,
                        lineHeight = 21.sp,
                    )
                }
            } else {
                for (item in state.items) {
                    ProbableCard(item)
                    Spacer(Modifier.height(10.dp))
                }
            }
            if (state.error != null) {
                Spacer(Modifier.height(6.dp))
                Text(state.error ?: "", color = DangerRed, fontSize = 12.sp)
            }
            if (state.scanned > 0) {
                Spacer(Modifier.height(6.dp))
                Text(
                    "${state.scanned} نماد اسکن شد • آخرین اسکن ${state.lastScan} UTC",
                    color = SoftText.copy(alpha = 0.5f),
                    fontSize = 11.sp,
                )
            }
        }
    }
}

@Composable
private fun ProbableCard(item: ProbableItem) {
    val tierColor = when (item.tier) {
        "ACTIONABLE" -> SuccessGreen
        "HIGH_CONFIDENCE_WATCH" -> CyanAccent
        else -> BlueAccent
    }
    val tierFa = when (item.tier) {
        "ACTIONABLE" -> "اکشن — همهٔ گیت‌ها پاس"
        "HIGH_CONFIDENCE_WATCH" -> "تماشای اطمینان بالا (≥۸۰٪)"
        else -> "ستاپ محتمل (≥۷۰٪)"
    }
    val sideFa = if (item.side == "long") "خرید (LONG)" else "فروش (SHORT)"
    val sideColor = if (item.side == "long") SuccessGreen else DangerRed
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(CardBg, RoundedCornerShape(16.dp))
            .border(1.dp, tierColor.copy(alpha = 0.45f), RoundedCornerShape(16.dp))
            .padding(PaddingValues(all = 14.dp)),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(item.symbol, color = SoftText, fontSize = 16.sp, fontWeight = FontWeight.Bold)
            Box(
                modifier = Modifier
                    .background(tierColor.copy(alpha = 0.16f), RoundedCornerShape(10.dp))
                    .border(1.dp, tierColor.copy(alpha = 0.5f), RoundedCornerShape(10.dp))
                    .padding(PaddingValues(start = 10.dp, top = 4.dp, end = 10.dp, bottom = 4.dp)),
            ) {
                Text(tierFa, color = tierColor, fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
            }
        }
        Spacer(Modifier.height(10.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("احتمال برد تخمینی", color = SoftText.copy(alpha = 0.7f), fontSize = 12.sp)
            Spacer(Modifier.width(8.dp))
            Text(
                "${item.probability}٪",
                color = tierColor,
                fontSize = 20.sp,
                fontWeight = FontWeight.ExtraBold,
            )
            Spacer(Modifier.width(14.dp))
            Text(sideFa, color = sideColor, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
        }
        Spacer(Modifier.height(6.dp))
        Text(
            "گرید ${item.grade} • RR ${"%.1f".format(item.rr)} • قیمت ${"%.2f".format(item.price)}",
            color = SoftText.copy(alpha = 0.6f),
            fontSize = 12.sp,
        )
    }
}
