package com.arena.smartmoney.ui.home

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.arena.smartmoney.ui.theme.CardBg
import com.arena.smartmoney.ui.theme.CyanAccent
import com.arena.smartmoney.ui.theme.DarkBg
import com.arena.smartmoney.ui.theme.SoftText
import com.arena.smartmoney.util.AlertPrefs

@Composable
fun AlertSettingsScreen() {
    val context = LocalContext.current
    var alertsEnabled by remember { mutableStateOf(AlertPrefs.alertsEnabled(context)) }
    var notifyHigh by remember { mutableStateOf(AlertPrefs.notifyHighConfidence(context)) }
    var notifyProb70 by remember { mutableStateOf(AlertPrefs.notifyProb70(context)) }
    var symbols by remember { mutableStateOf(AlertPrefs.symbols(context)) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkBg)
            .verticalScroll(rememberScrollState())
            .padding(PaddingValues(start = 16.dp, top = 14.dp, end = 16.dp, bottom = 24.dp)),
    ) {
        Text("🔔 تنظیمات هشدارها", color = SoftText, fontSize = 20.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(6.dp))
        Text(
            "اسکن پس‌زمینه هر ≥۱۵ دقیقه (زمان‌بندی دقیق با اندروید است). هشدارها فقط اطلاع‌رسانی " +
                "هستند — مجوز ورود نیستند. احتمال برد، تخمین غیرکالیبرهٔ مدل است.",
            color = SoftText.copy(alpha = 0.7f),
            fontSize = 12.sp,
            lineHeight = 19.sp,
        )
        Spacer(Modifier.height(14.dp))

        SettingCard {
            SwitchRow(
                title = "هشدارهای پس‌زمینه",
                subtitle = "کلید اصلی — اگر خاموش باشد هیچ هشداری ارسال نمی‌شود",
                checked = alertsEnabled,
                onCheckedChange = {
                    alertsEnabled = it
                    AlertPrefs.setAlertsEnabled(context, it)
                },
            )
        }
        Spacer(Modifier.height(10.dp))

        SettingCard {
            Column {
                Text(
                    "لایه‌هایی که هشدار می‌دهند",
                    color = SoftText,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold,
                )
                Spacer(Modifier.height(4.dp))
                Text(
                    "🟢 اکشن (همهٔ ۲۷ گیت پاس) — همیشه وقتی کلید اصلی روشن است",
                    color = SoftText.copy(alpha = 0.6f),
                    fontSize = 12.sp,
                )
                SwitchRow(
                    title = "🟡 تماشای اطمینان بالا (≥۸۰٪)",
                    subtitle = "پیش‌فرض: روشن",
                    checked = notifyHigh,
                    enabled = alertsEnabled,
                    onCheckedChange = {
                        notifyHigh = it
                        AlertPrefs.setNotifyHighConfidence(context, it)
                    },
                )
                SwitchRow(
                    title = "🔵 ستاپ محتمل (≥۷۰٪)",
                    subtitle = "پیش‌فرض: خاموش — فقط درون اپ نمایش داده می‌شود",
                    checked = notifyProb70,
                    enabled = alertsEnabled,
                    onCheckedChange = {
                        notifyProb70 = it
                        AlertPrefs.setNotifyProb70(context, it)
                    },
                )
            }
        }
        Spacer(Modifier.height(10.dp))

        SettingCard {
            Column {
                Text(
                    "نمادهای واچ‌لیست (${symbols.size} از ${AlertPrefs.watchlist.size})",
                    color = SoftText,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold,
                )
                Spacer(Modifier.height(4.dp))
                for (item in AlertPrefs.watchlist) {
                    val sym = item.first
                    val checked = sym in symbols
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable(enabled = alertsEnabled) {
                                val next = if (checked) symbols - sym else symbols + sym
                                symbols = next
                                AlertPrefs.setSymbols(context, next)
                            }
                            .padding(PaddingValues(vertical = 2.dp)),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Checkbox(
                            checked = checked,
                            enabled = alertsEnabled,
                            onCheckedChange = {
                                val next = if (checked) symbols - sym else symbols + sym
                                symbols = next
                                AlertPrefs.setSymbols(context, next)
                            },
                            colors = CheckboxDefaults.colors(checkedColor = CyanAccent),
                        )
                        Text(sym, color = SoftText.copy(alpha = if (alertsEnabled) 0.9f else 0.4f), fontSize = 13.sp)
                    }
                }
            }
        }
        Spacer(Modifier.height(12.dp))
        Text(
            "ضد اسپم: هر نماد+لایه حداکثر هر ۴ ساعت یک‌بار هشدار می‌دهد.",
            color = SoftText.copy(alpha = 0.5f),
            fontSize = 11.sp,
        )
    }
}

@Composable
private fun SettingCard(content: @Composable () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(CardBg, RoundedCornerShape(16.dp))
            .border(1.dp, Color.White.copy(alpha = 0.06f), RoundedCornerShape(16.dp))
            .padding(PaddingValues(all = 14.dp)),
    ) {
        content()
    }
}

@Composable
private fun SwitchRow(
    title: String,
    subtitle: String,
    checked: Boolean,
    enabled: Boolean = true,
    onCheckedChange: (Boolean) -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(PaddingValues(vertical = 4.dp)),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                title,
                color = SoftText.copy(alpha = if (enabled) 1f else 0.4f),
                fontSize = 13.sp,
                fontWeight = FontWeight.SemiBold,
            )
            Text(
                subtitle,
                color = SoftText.copy(alpha = if (enabled) 0.55f else 0.3f),
                fontSize = 11.sp,
            )
        }
        Switch(
            checked = checked,
            enabled = enabled,
            onCheckedChange = onCheckedChange,
            colors = SwitchDefaults.colors(checkedTrackColor = CyanAccent),
        )
    }
}
