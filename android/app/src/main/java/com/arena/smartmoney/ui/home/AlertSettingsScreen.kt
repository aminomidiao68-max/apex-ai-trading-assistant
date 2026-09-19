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
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.os.Build
import android.widget.Toast
import androidx.core.app.NotificationCompat
import com.arena.smartmoney.R
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
        Spacer(Modifier.height(14.dp))
        SettingCard {
            Column {
                Text("🔔 تست هشدار لوکال", color = SoftText, fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
                Spacer(Modifier.height(4.dp))
                Text("یک نوتیف آزمایشی روی همین گوشی — بدون نیاز به سرور. برای چک کردن صدا/بنر و اینکه ۲۰ نماد جدید درست انتخاب شده‌اند.", color = SoftText.copy(alpha = 0.65f), fontSize = 12.sp, lineHeight = 17.sp)
                Spacer(Modifier.height(10.dp))
                androidx.compose.material3.Button(
                    onClick = {
                        val selected = AlertPrefs.symbols(context)
                        if (selected.isEmpty()) {
                            Toast.makeText(context, "هیچ نمادی انتخاب نشده", Toast.LENGTH_SHORT).show()
                        } else {
                            sendTestNotification(context, selected)
                            Toast.makeText(context, "تست برای ${selected.size} نماد ارسال شد — بنر را چک کنید", Toast.LENGTH_LONG).show()
                        }
                    },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("ارسال تست هشدار (${symbols.size} نماد انتخابی)")
                }
                Spacer(Modifier.height(6.dp))
                Text("کانالی: APEX_TEST • اگر بنر نیامد: تنظیمات گوشی → اعلان‌ها → APEX MARKET AI را چک کنید", color = SoftText.copy(alpha = 0.45f), fontSize = 10.sp)
            }
        }
        Spacer(Modifier.height(10.dp))
        SettingCard {
            Column {
                Text("📜 تاریخچهٔ هشدارها", color = SoftText, fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
                Spacer(Modifier.height(4.dp))
                val prefs = context.getSharedPreferences("tier_alert_prefs", Context.MODE_PRIVATE)
                val lastTest = prefs.getLong("last_test_notification_at", 0L)
                val lastRun = prefs.getLong("last_worker_run_at", 0L)
                val fmt: (Long) -> String = { ts ->
                    if (ts == 0L) "—"
                    else java.time.Instant.ofEpochMilli(ts).atZone(java.time.ZoneId.systemDefault()).format(java.time.format.DateTimeFormatter.ofPattern("MM-dd HH:mm"))
                }
                Text("آخرین تست لوکال: ${if (lastTest>0) fmt(lastTest) else "هنوز نه"} • آخرین اسکن Worker: ${fmt(lastRun)}", color = SoftText.copy(alpha = 0.7f), fontSize = 11.sp)
                Spacer(Modifier.height(4.dp))
                Text("هر ۱۵ دقیقه برای هر نماد+لایه چک می‌شود • هر کدام حداکثر هر ۴ ساعت یک‌بار", color = SoftText.copy(alpha = 0.55f), fontSize = 11.sp, lineHeight = 15.sp)
                Spacer(Modifier.height(8.dp))
                // Real history log (last 5)
                val histRaw = prefs.getString("alert_history_json", "[]") ?: "[]"
                val histList = try {
                    val arr = org.json.JSONArray(histRaw)
                    (0 until arr.length()).map { arr.getJSONObject(it) }.reversed().take(5)
                } catch (_: Exception) { emptyList() }
                if (histList.isEmpty()) {
                    Text("هنوز هشدار واقعی ارسال نشده — طبیعی است (سیستم سخت‌گیر است؛ بعضی هفته‌ها هیچ).", color = SoftText.copy(alpha = 0.6f), fontSize = 11.sp, lineHeight = 15.sp)
                } else {
                    Text("۵ هشدار اخیر (واقعی):", color = CyanAccent, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                    Spacer(Modifier.height(4.dp))
                    for (obj in histList) {
                        val at = try { fmt(obj.getLong("at")) } catch (_: Exception) { "—" }
                        val sym = try { obj.getString("symbol") } catch (_: Exception) { "?" }
                        val tier = try { obj.getString("tier") } catch (_: Exception) { "?" }
                        val prob = try { obj.getInt("prob") } catch (_: Exception) { 0 }
                        val tierFa = when (tier) { "ACTIONABLE" -> "🟢 اکشن"; "HIGH_CONFIDENCE_WATCH" -> "🟡 ≥80٪"; else -> "🔵 ≥70٪" }
                        Text("• $at — $sym $tierFa ${prob}٪", color = SoftText.copy(alpha = 0.8f), fontSize = 11.sp)
                    }
                }
                Spacer(Modifier.height(6.dp))
                val selected = AlertPrefs.symbols(context)
                Text("واچ‌لیست فعال (${selected.size}/20): ${selected.sorted().joinToString(" • ").ifEmpty { "—" }}", color = CyanAccent.copy(alpha = 0.65f), fontSize = 10.sp, lineHeight = 14.sp)
                Spacer(Modifier.height(8.dp))
                androidx.compose.material3.OutlinedButton(
                    onClick = {
                        val csv = buildAlertHistoryCsv(context)
                        val intent = Intent(Intent.ACTION_SEND).apply {
                            type = "text/csv"
                            putExtra(Intent.EXTRA_SUBJECT, "APEX Alert History — ${java.time.LocalDate.now()}")
                            putExtra(Intent.EXTRA_TEXT, csv)
                        }
                        context.startActivity(Intent.createChooser(intent, "اشتراک CSV تاریخچه"))
                    },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("📤 خروجی CSV تاریخچه (۲۰ هشدار اخیر)", fontSize = 12.sp)
                }
            }
        }
    }
}

private fun buildAlertHistoryCsv(context: Context): String {
    val prefs = context.getSharedPreferences("tier_alert_prefs", Context.MODE_PRIVATE)
    val raw = prefs.getString("alert_history_json", "[]") ?: "[]"
    val sb = StringBuilder()
    sb.append("time,symbol,tier,prob,side\n")
    try {
        val arr = org.json.JSONArray(raw)
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            val at = try {
                val ts = o.getLong("at")
                java.time.Instant.ofEpochMilli(ts).atZone(java.time.ZoneId.systemDefault()).format(java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"))
            } catch (_: Exception) { "" }
            val sym = try { o.getString("symbol") } catch (_: Exception) { "" }
            val tier = try { o.getString("tier") } catch (_: Exception) { "" }
            val prob = try { o.getInt("prob").toString() } catch (_: Exception) { "" }
            val side = try { o.getString("side") } catch (_: Exception) { "" }
            sb.append("$at,$sym,$tier,$prob,$side\n")
        }
    } catch (_: Exception) {}
    if (sb.toString().trim().endsWith("time,symbol,tier,prob,side")) {
        sb.append("— no history yet —,,,\n")
    }
    return sb.toString()
}

private fun sendTestNotification(context: Context, symbols: Set<String>) {
    val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
    val channelId = "apex_test"
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
        val ch = NotificationChannel(channelId, "APEX Test Alerts", NotificationManager.IMPORTANCE_HIGH).apply {
            description = "Local test for tier alerts — 20 symbols"
        }
        nm.createNotificationChannel(ch)
    }
    val preview = symbols.sorted().take(5).joinToString(" • ")
    val more = if (symbols.size > 5) " +${symbols.size - 5} دیگر" else ""
    val title = "🔔 تست هشدار APEX — ${symbols.size} نماد"
    val body = "واچ‌لیست فعال: $preview$more — اگر این را می‌بینید، هشدارهای پس‌زمینه برای ۲۰ نماد جدید آماده است. (اکشن همیشه، ≥۸۰٪ و ≥۷۰٪ طبق سوییچ‌ها)"
    val notif = NotificationCompat.Builder(context, channelId)
        .setSmallIcon(R.mipmap.ic_launcher)
        .setContentTitle(title)
        .setContentText(body)
        .setStyle(NotificationCompat.BigTextStyle().bigText(body))
        .setPriority(NotificationCompat.PRIORITY_HIGH)
        .setAutoCancel(true)
        .build()
    nm.notify(9001, notif)
    context.getSharedPreferences("tier_alert_prefs", Context.MODE_PRIVATE).edit().putLong("last_test_notification_at", System.currentTimeMillis()).apply()
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
