package com.arena.smartmoney.ui.home

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.arena.smartmoney.ui.theme.CardBg
import com.arena.smartmoney.ui.theme.CyanAccent
import com.arena.smartmoney.ui.theme.SoftText
import java.time.ZonedDateTime
import java.time.ZoneOffset

private data class SessionRow(
    val fa: String,
    val en: String,
    val utc: String,
    val from: Int,
    val to: Int,
    val killzone: Boolean = false,
    val weekendVeto: Boolean = false,
)

private val ROWS = listOf(
    SessionRow("سیدنی", "Sydney", "22:00 – 07:00 UTC", 22, 31),
    SessionRow("توکیو", "Tokyo", "00:00 – 09:00 UTC", 0, 9),
    SessionRow("لندن", "London", "07:00 – 16:00 UTC", 7, 16),
    SessionRow("هم‌پوشانی لندن/نیویورک — کیل‌زون", "London/NY Overlap — KILLZONE", "12:00 – 16:00 UTC", 12, 16, killzone = true),
    SessionRow("نیویورک", "New York", "12:00 – 21:00 UTC", 12, 21),
    SessionRow("آخر هفته", "Weekend", "Sat/Sun — وتوی نقدینگی", -1, -1, weekendVeto = true),
)

@Composable
fun SessionsScreen() {
    var now by remember { mutableStateOf(ZonedDateTime.now(ZoneOffset.UTC)) }
    LaunchedEffect(Unit) {
        while (true) {
            kotlinx.coroutines.delay(30_000)
            now = ZonedDateTime.now(ZoneOffset.UTC)
        }
    }
    val hour = now.hour
    val weekend = sessionInfo(now).weekend

    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(14.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Text(
            "سشن‌های جهانی بازار و کیل‌زون‌ها",
            color = Color.White,
            fontSize = 16.sp,
            fontWeight = FontWeight.Bold,
        )
        Text(
            "ساعت سرور: " + now.toLocalTime().withNano(0).toString() + " UTC",
            color = SoftText.copy(alpha = 0.7f),
            fontSize = 11.sp,
        )
        ROWS.forEach { row ->
            val active = if (row.weekendVeto) weekend
            else if (row.from <= row.to) hour in row.from until row.to
            else hour >= row.from || hour < (row.to % 24)
            val accent = when {
                row.weekendVeto -> Color(0xFFE85B5B)
                row.killzone -> CyanAccent
                else -> Color(0xFF2E7BFF)
            }
            Column(
                Modifier
                    .fillMaxWidth()
                    .border(
                        if (active) 1.5.dp else 1.dp,
                        if (active) accent else Color(0xFF22364F),
                        RoundedCornerShape(16.dp),
                    )
                    .background(if (active) accent.copy(alpha = 0.12f) else CardBg, RoundedCornerShape(16.dp))
                    .padding(14.dp),
            ) {
                Row {
                    Column(Modifier.fillMaxWidth(0.72f)) {
                        Text(row.fa, color = if (active) accent else Color.White, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                        Text(row.en, color = SoftText.copy(alpha = 0.6f), fontSize = 10.sp)
                    }
                    Text(row.utc, color = SoftText.copy(alpha = 0.8f), fontSize = 11.sp)
                }
                if (active) {
                    Spacer(Modifier.height(6.dp))
                    Text(
                        if (row.weekendVeto) "⛔ اکنون: وتوی آخر هفته فعال است"
                        else if (row.killzone) "🔥 اکنون: کیل‌زون فعال — پنجرهٔ مجاز سیگنال"
                        else "● اکنون فعال",
                        color = accent,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
        }
        Spacer(Modifier.height(4.dp))
        Column(
            Modifier
                .fillMaxWidth()
                .background(Color(0xFF0B1626), RoundedCornerShape(16.dp))
                .padding(14.dp),
        ) {
            Text("منطق نهادی این ساعت‌ها", color = CyanAccent, fontSize = 12.5.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(6.dp))
            Text(
                "حجم و کیفیت نقدینگی در هم‌پوشانی لندن/نیویورک (12–16 UTC) بیشینه است؛ " +
                    "موتور v3.26 به بعد فقط در همین پنجره و فقط در روزهای دوشنبه تا جمعه اجازهٔ " +
                    "صدور ستاپ دارد. آخر هفته‌ها به‌دلیل نقدینگی خرد و اسپرد باز، وتو می‌شوند. " +
                    "رویدادهای خبری پراثر نیز ۹۰ دقیقه قبل تا ۴۵ دقیقه بعد بلوک می‌شوند.",
                color = SoftText.copy(alpha = 0.85f),
                fontSize = 11.5.sp,
            )
        }
    }
}
