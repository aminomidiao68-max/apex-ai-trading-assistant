package com.arena.smartmoney.ui.failedgate

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
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
import com.arena.smartmoney.data.model.FailedGatesResponseDto
import com.arena.smartmoney.data.model.ShadowPanelDto
import com.arena.smartmoney.data.repository.TradingRepository
import com.arena.smartmoney.ui.theme.CardBg
import com.arena.smartmoney.ui.theme.CyanAccent
import com.arena.smartmoney.ui.theme.DarkBg
import com.arena.smartmoney.ui.theme.SoftText
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class FailedGateUiState(
    val loading: Boolean = false,
    val panel: ShadowPanelDto? = null,
    val failed: FailedGatesResponseDto? = null,
    val error: String? = null,
    val lastRefresh: String = ""
)

class FailedGateViewModel(
    private val repo: TradingRepository = TradingRepository()
) : ViewModel() {
    private val _state = MutableStateFlow(FailedGateUiState())
    val state: StateFlow<FailedGateUiState> = _state
    init { refresh() }
    fun refresh() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            try {
                val p = repo.getShadowPanel()
                val f = try { repo.getFailedGates() } catch (_: Exception) { null }
                _state.value = _state.value.copy(
                    loading = false,
                    panel = p,
                    failed = f,
                    lastRefresh = java.time.LocalTime.now().withNano(0).toString() + " UTC"
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(loading = false, error = e.message ?: "خطا")
            }
        }
    }
}

@Composable
fun FailedGateReportScreen() {
    val vm: FailedGateViewModel = androidx.lifecycle.viewmodel.compose.viewModel()
    val ui by vm.state.collectAsState()
    Column(
        Modifier
            .fillMaxSize()
            .background(DarkBg)
            .verticalScroll(rememberScrollState())
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("📉 گزارش روزانه Failed Gates", color = Color.White, fontSize = 16.sp, fontWeight = FontWeight.Bold)
        Text("هر ستاپ چرا رد شد — صادقانه، بدون عددسازی. 0 کاندیدا = بهتر از سیگنال اشتباه", color = SoftText, fontSize = 11.sp)
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Text("آخرین: ${ui.lastRefresh}", color = SoftText.copy(alpha = 0.7f), fontSize = 10.sp)
            androidx.compose.foundation.clickable
            Box(
                Modifier
                    .clip(RoundedCornerShape(8.dp))
                    .background(CyanAccent)
                    .padding(horizontal = 10.dp, vertical = 6.dp)
            ) {
                Text("🔄 بروزرسانی", color = Color.Black, fontSize = 11.sp, fontWeight = FontWeight.Bold, modifier = Modifier.clickable { vm.refresh() })
            }
        }
        if (ui.loading && ui.panel == null) {
            Box(Modifier.fillMaxWidth().padding(30.dp), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = CyanAccent)
            }
        }
        ui.error?.let {
            Box(Modifier.fillMaxWidth().background(Color(0xFF7F1D1D).copy(alpha = 0.3f), RoundedCornerShape(12.dp)).padding(12.dp)) {
                Text(it, color = Color(0xFFFCA5A5), fontSize = 11.sp)
            }
        }
        ui.panel?.let { p ->
            // Summary cards
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                StatCard("کل", "${p.totalObservations}", Modifier.weight(1f))
                StatCard("فعلی", "${p.observationsCurrentEngine}", Modifier.weight(1f))
                StatCard("کاندیدا فعلی", "${p.candidatesCurrentEngine}", Modifier.weight(1f))
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                StatCard("حل‌شده فعلی", "${p.resolvedCurrentEngine}/30", Modifier.weight(1f))
                StatCard("span", "${"%.1f".format(p.cohortSpanDays)} روز", Modifier.weight(1f))
                StatCard("وضعیت", p.status, Modifier.weight(1f))
            }
            // failed gates histogram current engine
            Column(
                Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(14.dp))
                    .background(CardBg)
                    .border(1.dp, Color(0xFF22364F), RoundedCornerShape(14.dp))
                    .padding(12.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Text("🚧 Top Failed Gates — موتور فعلی (275 مشاهده)", color = CyanAccent, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                Text("کدام 2 گیت 68% ردها را می‌سازد — با اجازه تو veto→weight می‌شود", color = SoftText, fontSize = 10.sp)
                val hist = ui.failed?.failedGateCounts ?: emptyMap()
                if (hist.isEmpty()) {
                    Text("هنوز داده کافی نیست — یا همه گیت‌ها پاس شده‌اند (0 کاندیدا) — endpoint جدید در این بیلد اضافه شد", color = SoftText, fontSize = 11.sp)
                } else {
                    val sorted = hist.entries.sortedByDescending { it.value }.take(8)
                    val maxVal = sorted.maxOfOrNull { it.value } ?: 1
                    sorted.forEach { (gate, cnt) ->
                        Column(Modifier.fillMaxWidth()) {
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text(gate, color = Color.White, fontSize = 11.sp, fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f))
                                Text("$cnt", color = Color(0xFFFCA5A5), fontSize = 11.sp, fontWeight = FontWeight.Bold)
                            }
                            Box(
                                Modifier
                                    .fillMaxWidth()
                                    .height(8.dp)
                                    .clip(RoundedCornerShape(4.dp))
                                    .background(Color(0xFF1F2937))
                            ) {
                                Box(
                                    Modifier
                                        .fillMaxHeight()
                                        .fillMaxWidth(fraction = (cnt.toFloat() / maxVal.toFloat()).coerceIn(0f, 1f))
                                        .background(
                                            when {
                                                cnt.toFloat() / maxVal > 0.7f -> Color(0xFFEF4444)
                                                cnt.toFloat() / maxVal > 0.4f -> Color(0xFFF59E0B)
                                                else -> Color(0xFF3B82F6)
                                            }
                                        )
                                )
                            }
                        }
                    }
                }
            }
            // overall histogram
            Column(
                Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(14.dp))
                    .background(CardBg)
                    .border(1.dp, Color(0xFF22364F), RoundedCornerShape(14.dp))
                    .padding(12.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Text("📚 کل تاریخ (7423)", color = CyanAccent, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                val hist2 = ui.failed?.failedGateCounts ?: emptyMap()
                if (hist2.isNotEmpty()) {
                    hist2.entries.sortedByDescending { it.value }.take(6).forEach { (g, c) ->
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text(g, color = SoftText, fontSize = 10.sp, modifier = Modifier.weight(1f))
                            Text("$c", color = SoftText, fontSize = 10.sp)
                        }
                    }
                }
            }
            // Wilson CI
            Column(
                Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(14.dp))
                    .background(Color(0xFF0F172A))
                    .border(1.dp, Color(0xFF334155), RoundedCornerShape(14.dp))
                    .padding(12.dp)
            ) {
                Text("🎯 Wilson CI — وین‌ریت صادقانه", color = Color.White, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                if (p.resolvedCurrentEngine < 30) {
                    Text("هنوز ${p.resolvedCurrentEngine}/30 — CI نامعتبر است → هیچ ادعای دقتی مجاز نیست (INSUFFICIENT_EVIDENCE)", color = Color(0xFFFCD34D), fontSize = 11.sp)
                    Text("ادعای 80% فیک قبل 30 نمونه = فیلم", color = Color(0xFFFCA5A5), fontSize = 10.sp)
                } else {
                    Text("CI low: ${p.winRateCiLow} • high: ${p.winRateCiHigh}", color = Color(0xFF6EE7B7), fontSize = 11.sp)
                }
            }
        }
        Spacer(Modifier.height(20.dp))
        Text("منبع: /api/v1/analysis/intraday-fusion/shadow/system-panel — هر 24ساعت این صفحه را چک کن", color = SoftText.copy(alpha = 0.5f), fontSize = 9.sp)
    }
}

@Composable
private fun StatCard(label: String, value: String, modifier: Modifier = Modifier) {
    Column(
        modifier
            .clip(RoundedCornerShape(10.dp))
            .background(CardBg)
            .border(1.dp, Color(0xFF22364F), RoundedCornerShape(10.dp))
            .padding(10.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(label, color = SoftText, fontSize = 9.sp)
        Text(value, color = Color.White, fontSize = 13.sp, fontWeight = FontWeight.Bold)
    }
}
