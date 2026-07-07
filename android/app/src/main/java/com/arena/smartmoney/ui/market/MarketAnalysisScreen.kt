
package com.arena.smartmoney.ui.market

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.weight
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.arena.smartmoney.ui.components.PremiumGlassCard
import com.arena.smartmoney.ui.components.PremiumScreenBackground
import com.arena.smartmoney.ui.components.PremiumSectionHeader
import com.arena.smartmoney.ui.i18n.rememberTranslator

@Composable
fun MarketAnalysisScreen(
    onOpenChart: () -> Unit,
    onOpenAnalytics: () -> Unit,
    onOpenSignals: () -> Unit,
) {
    val t = rememberTranslator()

    PremiumScreenBackground {
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                PremiumSectionHeader(
                    title = t("Market Analysis Pro", "تحلیل بازار حرفه‌ای"),
                    subtitle = t(
                        "Precision workspace for chart structure, institutional analytics and live signal validation.",
                        "فضای دقیق برای ساختار نمودار، آنالیتیکس نهادی و اعتبارسنجی زنده سیگنال‌ها."
                    )
                )
            }
            item {
                PremiumGlassCard(borderColor = Color(0x4059C7FF)) {
                    Text(t("Executive Overview", "نمای اجرایی"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
                    Text(
                        t(
                            "Use this page as the central hub for serious market study before any execution decision.",
                            "این صفحه را به‌عنوان هاب مرکزی برای مطالعه جدی بازار قبل از هر تصمیم اجرایی استفاده کن."
                        ),
                        color = Color(0xFFDDF8FF)
                    )
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        IntelChip(t("Structure", "ساختار"), t("Live", "زنده"), Modifier.weight(1f))
                        IntelChip(t("Flow", "جریان"), t("Tracked", "رصدشده"), Modifier.weight(1f))
                        IntelChip(t("Validation", "اعتبارسنجی"), t("Ready", "آماده"), Modifier.weight(1f))
                    }
                }
            }
            item {
                PremiumGlassCard {
                    Text(t("Professional Modules", "ماژول‌های حرفه‌ای"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
                    ModuleLine(
                        title = t("Live Chart", "نمودار زنده"),
                        body = t(
                            "Inspect candles, zoom, pan, crosshair levels and live price behavior.",
                            "کندل‌ها، زوم، پن، کراس‌هِر و رفتار قیمت لحظه‌ای را دقیق بررسی کن."
                        )
                    )
                    ModuleLine(
                        title = t("Institutional Analytics", "آنالیتیکس نهادی"),
                        body = t(
                            "Review symbol leadership, score distribution and journal efficiency.",
                            "رهبری نمادها، توزیع امتیاز و کارایی ژورنال را مرور کن."
                        )
                    )
                    ModuleLine(
                        title = t("Signal Validation", "اعتبارسنجی سیگنال"),
                        body = t(
                            "Confirm whether the live setup deserves observation, execution or rejection.",
                            "تأیید کن که ستاپ زنده باید فقط رصد شود، اجرا شود یا رد شود."
                        )
                    )
                }
            }
            item {
                PremiumGlassCard(borderColor = Color(0x4033E6A6)) {
                    Text(t("Open Analysis Tools", "باز کردن ابزارهای تحلیل"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = onOpenChart, modifier = Modifier.weight(1f)) {
                            Text(t("Open Live Chart", "باز کردن نمودار زنده"))
                        }
                    }
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedButton(onClick = onOpenAnalytics, modifier = Modifier.weight(1f)) {
                            Text(t("Open Analytics", "باز کردن آنالیتیکس"))
                        }
                        OutlinedButton(onClick = onOpenSignals, modifier = Modifier.weight(1f)) {
                            Text(t("Open Signals", "باز کردن سیگنال‌ها"))
                        }
                    }
                }
            }
            item {
                PremiumGlassCard {
                    Text(t("Trading Note", "یادداشت معاملاتی"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
                    Text(
                        t(
                            "This module improves market reading, but it never guarantees profit. Always confirm risk before execution.",
                            "این ماژول خوانش بازار را بهتر می‌کند، اما هرگز سود را تضمین نمی‌کند. همیشه قبل از اجرا ریسک را تأیید کن."
                        ),
                        color = Color(0xFFFFD27A)
                    )
                }
            }
        }
    }
}

@Composable
private fun IntelChip(title: String, value: String, modifier: Modifier = Modifier) {
    Box(
        modifier = modifier
            .background(
                Brush.linearGradient(listOf(Color(0x2611D9FF), Color(0x2217FFB3))),
                RoundedCornerShape(16.dp)
            )
            .padding(horizontal = 12.dp, vertical = 10.dp)
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(title, color = Color(0xFFBCEEFF), style = MaterialTheme.typography.bodySmall)
            Text(value, color = Color.White, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun ModuleLine(title: String, body: String) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp), modifier = Modifier.fillMaxWidth()) {
        Text(title, color = Color(0xFF67ECFF), fontWeight = FontWeight.Bold)
        Text(body, color = Color(0xFFDDF8FF))
    }
}
