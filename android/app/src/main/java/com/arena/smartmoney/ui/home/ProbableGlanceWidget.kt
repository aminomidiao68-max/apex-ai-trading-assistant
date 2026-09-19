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
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.arena.smartmoney.ui.theme.BlueAccent
import com.arena.smartmoney.ui.theme.CardBg
import com.arena.smartmoney.ui.theme.CyanAccent
import com.arena.smartmoney.ui.theme.DangerRed
import com.arena.smartmoney.ui.theme.SoftText
import com.arena.smartmoney.ui.theme.SuccessGreen

@Composable
fun ProbableGlanceWidget(
    viewModel: ProbableSetupsViewModel = viewModel(),
    onOpenProbable: () -> Unit
) {
    val state by viewModel.uiState.collectAsState()
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(CardBg, RoundedCornerShape(18.dp))
            .border(1.dp, CyanAccent.copy(alpha = 0.35f), RoundedCornerShape(18.dp))
            .clickable(onClick = onOpenProbable)
            .padding(14.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text("🎖 ستاپ‌های محتمل — نگاه سریع", color = Color.White, fontSize = 13.5.sp, fontWeight = FontWeight.Bold)
                Text(
                    "۲۰ نماد • احتمال ≥70٪ • بروزرسانی زنده از بک‌اند قطعی",
                    color = SoftText.copy(alpha = 0.6f),
                    fontSize = 10.sp
                )
            }
            Text(
                if (state.loading) "…" else "↻",
                color = CyanAccent,
                fontSize = 18.sp,
                modifier = Modifier
                    .clickable(enabled = !state.loading) { viewModel.scan() }
                    .padding(6.dp)
            )
        }
        Spacer(Modifier.height(10.dp))
        when {
            state.loading && state.items.isEmpty() -> {
                Box(modifier = Modifier.fillMaxWidth().height(54.dp), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = CyanAccent, strokeWidth = 2.dp, modifier = Modifier.width(22.dp).height(22.dp))
                }
                Text("در حال اسکن ۲۰ نماد از بک‌اند قطعی…", color = SoftText.copy(alpha = 0.65f), fontSize = 11.sp)
            }
            state.items.isEmpty() -> {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(Color(0xFF0B1626), RoundedCornerShape(12.dp))
                        .border(1.dp, Color.White.copy(alpha = 0.06f), RoundedCornerShape(12.dp))
                        .padding(12.dp)
                ) {
                    Column {
                        Text(
                            "فعلاً هیچ ستاپی ≥70٪ نیست — طبیعی است.",
                            color = SoftText,
                            fontSize = 12.5.sp,
                            fontWeight = FontWeight.SemiBold
                        )
                        Spacer(Modifier.height(4.dp))
                        Text(
                            "سیستم ۲۷ گیت را ۱۰۰٪ سخت‌گیرانه چک می‌کند؛ «هیچ» بهتر از «اشتباه» است. ${state.scanned} نماد اسکن شد" + if (state.lastScan.isNotEmpty()) " • ${state.lastScan} UTC" else "",
                            color = SoftText.copy(alpha = 0.65f),
                            fontSize = 11.sp,
                            lineHeight = 15.sp
                        )
                    }
                }
                if (state.error != null) {
                    Spacer(Modifier.height(6.dp))
                    Text(state.error ?: "", color = DangerRed, fontSize = 11.sp)
                }
            }
            else -> {
                // Show up to 3 best
                val top = state.items.take(3)
                for (item in top) {
                    GlanceRow(item)
                    Spacer(Modifier.height(8.dp))
                }
                if (state.items.size > 3) {
                    Text(
                        "+ ${state.items.size - 3} ستاپ دیگر — برای دیدن همه ضربه بزنید →",
                        color = CyanAccent.copy(alpha = 0.85f),
                        fontSize = 11.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                    Spacer(Modifier.height(6.dp))
                }
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(
                        "${state.items.size} ستاپ از ${state.scanned} نماد",
                        color = SoftText.copy(alpha = 0.55f),
                        fontSize = 11.sp
                    )
                    Text(
                        if (state.lastScan.isNotEmpty()) state.lastScan + " UTC" else "",
                        color = SoftText.copy(alpha = 0.45f),
                        fontSize = 11.sp
                    )
                }
            }
        }
    }
}

@Composable
private fun GlanceRow(item: ProbableItem) {
    val tierColor = when (item.tier) {
        "ACTIONABLE" -> SuccessGreen
        "HIGH_CONFIDENCE_WATCH" -> CyanAccent
        else -> BlueAccent
    }
    val tierShort = when (item.tier) {
        "ACTIONABLE" -> "اکشن"
        "HIGH_CONFIDENCE_WATCH" -> "≥80٪"
        else -> "≥70٪"
    }
    val sideFa = if (item.side == "long") "خرید" else "فروش"
    val sideColor = if (item.side == "long") SuccessGreen else DangerRed
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(Color(0xFF0B1626), RoundedCornerShape(12.dp))
            .border(1.dp, tierColor.copy(alpha = 0.35f), RoundedCornerShape(12.dp))
            .padding(horizontal = 10.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(item.symbol, color = Color.White, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                Spacer(Modifier.width(8.dp))
                Box(
                    modifier = Modifier
                        .background(tierColor.copy(alpha = 0.16f), RoundedCornerShape(8.dp))
                        .border(1.dp, tierColor.copy(alpha = 0.45f), RoundedCornerShape(8.dp))
                        .padding(horizontal = 7.dp, vertical = 2.dp)
                ) {
                    Text(tierShort, color = tierColor, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                }
            }
            Spacer(Modifier.height(3.dp))
            Text(
                "$sideFa • RR ${"%.1f".format(item.rr)} • ${item.grade}",
                color = SoftText.copy(alpha = 0.7f),
                fontSize = 11.sp
            )
        }
        Column(horizontalAlignment = Alignment.End) {
            Text("${item.probability}٪", color = tierColor, fontSize = 18.sp, fontWeight = FontWeight.ExtraBold)
            Text(sideFa, color = sideColor, fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
        }
    }
}
