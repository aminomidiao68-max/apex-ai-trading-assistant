package com.arena.smartmoney.ui.settings

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.arena.smartmoney.BuildConfig
import com.arena.smartmoney.data.network.AppConfig
import com.arena.smartmoney.data.preferences.AppPreferencesManager
import com.arena.smartmoney.ui.components.PremiumGlassCard
import com.arena.smartmoney.ui.components.PremiumScreenBackground
import com.arena.smartmoney.ui.components.PremiumSectionHeader
import com.arena.smartmoney.ui.i18n.AppLanguageState
import com.arena.smartmoney.ui.i18n.rememberTranslator

@Composable
fun SettingsScreen(onOpenReadiness: () -> Unit) {
    val context = LocalContext.current
    val prefs = remember { AppPreferencesManager(context) }
    val t = rememberTranslator()

    var notificationsEnabled by remember { mutableStateOf(prefs.isNotificationsEnabled()) }
    var autoRefreshEnabled by remember { mutableStateOf(prefs.isAutoRefreshEnabled()) }
    var testnetOnlyEnabled by remember { mutableStateOf(prefs.isTestnetOnlyEnabled()) }
    var riskAcknowledged by remember { mutableStateOf(prefs.isRiskAcknowledged()) }
    var currentLanguage by remember { mutableStateOf(prefs.getLanguage()) }

    fun applyLanguage(language: String) {
        currentLanguage = language
        prefs.setLanguage(language)
        AppLanguageState.current = language
    }

    val alertProfile = alertProfileLabel(
        notificationsEnabled = notificationsEnabled,
        autoRefreshEnabled = autoRefreshEnabled,
        testnetOnlyEnabled = testnetOnlyEnabled,
        riskAcknowledged = riskAcknowledged,
    )

    PremiumScreenBackground {
        androidx.compose.foundation.lazy.LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                PremiumSectionHeader(
                    title = t("Settings Center", "مرکز تنظیمات"),
                    subtitle = t(
                        "Language, smart alerts, safety controls and premium system configuration.",
                        "زبان، هشدارهای هوشمند، کنترل‌های ایمنی و تنظیمات پرمیوم سیستم."
                    )
                )
            }
            item {
                PremiumGlassCard {
                    Text(t("Language", "زبان"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
                    Text(t("Switch the app instantly between Persian and English.", "کل برنامه را فوراً بین فارسی و انگلیسی جابه‌جا کن."), color = Color(0xFFBCEEFF))
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        LanguageButton(modifier = Modifier.weight(1f), title = "فارسی", selected = currentLanguage == "fa") { applyLanguage("fa") }
                        LanguageButton(modifier = Modifier.weight(1f), title = "English", selected = currentLanguage == "en") { applyLanguage("en") }
                    }
                    Text(
                        t(
                            "Current language: ${if (currentLanguage == "fa") "Persian" else "English"}",
                            "زبان فعلی: ${if (currentLanguage == "fa") "فارسی" else "انگلیسی"}"
                        ),
                        color = Color(0xFF67ECFF),
                        fontWeight = FontWeight.Bold
                    )
                }
            }
            item {
                PremiumGlassCard(borderColor = Color(0x4059C7FF)) {
                    Text(t("Smart Alerts Pro", "اسمارت الرتس پرو"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
                    Text(t("Alert profile", "پروفایل هشدار") + ": $alertProfile", color = Color(0xFF67ECFF), fontWeight = FontWeight.Bold)
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        AlertProfileChip(t("Execution", "اجرا"), if (notificationsEnabled) t("Enabled", "فعال") else t("Muted", "بی‌صدا"), Modifier.weight(1f))
                        AlertProfileChip(t("Refresh", "رفرش"), if (autoRefreshEnabled) t("Live", "زنده") else t("Manual", "دستی"), Modifier.weight(1f))
                        AlertProfileChip(t("Mode", "حالت"), if (testnetOnlyEnabled) t("Safe", "ایمن") else t("Aggressive", "تهاجمی"), Modifier.weight(1f))
                    }
                    Text(
                        when {
                            notificationsEnabled && autoRefreshEnabled && riskAcknowledged -> t(
                                "Alert engine is armed for market focus monitoring. Keep risk discipline active.",
                                "موتور هشدار برای مانیتورینگ تمرکز بازار مسلح است. نظم ریسک را حفظ کن."
                            )
                            !notificationsEnabled -> t(
                                "Notifications are muted, so only on-screen alert boards will guide you.",
                                "نوتیفیکیشن‌ها خاموش هستند و فقط بردهای داخل برنامه راهنمایی می‌کنند."
                            )
                            else -> t(
                                "Smart alerts are partially configured. Complete safety controls for full readiness.",
                                "هشدارهای هوشمند به‌صورت ناقص تنظیم شده‌اند. برای آمادگی کامل، کنترل‌های ایمنی را تکمیل کن."
                            )
                        },
                        color = Color(0xFFDDF8FF)
                    )
                }
            }
            item {
                PremiumGlassCard {
                    Text(t("Smart Controls", "کنترل‌های هوشمند"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
                    SettingToggle(
                        title = t("Notifications", "نوتیفیکیشن‌ها"),
                        description = t("Enable local and Firebase alerts when available.", "در صورت آماده بودن، هشدارهای محلی و فایربیس فعال شوند."),
                        checked = notificationsEnabled
                    ) {
                        notificationsEnabled = it
                        prefs.setNotificationsEnabled(it)
                    }
                    SettingToggle(
                        title = t("Auto Refresh", "بروزرسانی خودکار"),
                        description = t("Keep market views ready for heavy monitoring.", "نماهای بازار را برای مانیتورینگ سنگین آماده نگه دار."),
                        checked = autoRefreshEnabled
                    ) {
                        autoRefreshEnabled = it
                        prefs.setAutoRefreshEnabled(it)
                    }
                    SettingToggle(
                        title = t("Testnet / Demo First", "اول تست‌نت / دمو"),
                        description = t("Recommended before any real execution workflow.", "قبل از هر اجرای واقعی سفارش، این حالت پیشنهاد می‌شود."),
                        checked = testnetOnlyEnabled
                    ) {
                        testnetOnlyEnabled = it
                        prefs.setTestnetOnlyEnabled(it)
                    }
                    SettingToggle(
                        title = t("Risk Disclaimer Accepted", "پذیرش هشدار ریسک"),
                        description = t("Confirms you understand trading risk and no guaranteed profit exists.", "تأیید می‌کند که ریسک معامله را می‌دانی و سود تضمینی وجود ندارد."),
                        checked = riskAcknowledged
                    ) {
                        riskAcknowledged = it
                        prefs.setRiskAcknowledged(it)
                    }
                }
            }
            item {
                PremiumGlassCard {
                    Text(t("App Environment", "محیط برنامه"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
                    Text(t("App Version", "نسخه برنامه") + ": ${BuildConfig.VERSION_NAME}", color = Color(0xFF67ECFF), fontWeight = FontWeight.Bold)
                    Text(t("API Base URL", "آدرس پایه API") + ": ${AppConfig.apiBaseUrl}", color = Color.White)
                    Text(t("WS Base URL", "آدرس پایه WS") + ": ${AppConfig.marketWsUrl}", color = Color.White)
                }
            }
            item {
                PremiumGlassCard {
                    Text(t("Launch Controls", "کنترل‌های لانچ"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
                    Text(t("Open readiness to verify Firebase, connectors and blockers.", "برای بررسی فایربیس، کانکتورها و موانع، صفحه آمادگی را باز کن."), color = Color(0xFFBCEEFF))
                    Button(onClick = onOpenReadiness, modifier = Modifier.fillMaxWidth()) {
                        Text(t("Open System Readiness", "باز کردن آمادگی سیستم"))
                    }
                }
            }
            item {
                PremiumGlassCard {
                    Text(t("Risk Policy", "سیاست ریسک"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
                    Text(t("This app is an analysis and execution-support system, not a guarantee machine.", "این برنامه یک سیستم تحلیل و کمک‌اجرایی است، نه ماشین تضمین سود."), color = Color(0xFFDDF8FF))
                    Text(t("Always validate strategy quality with backtest, sweep, walk-forward and demo execution first.", "همیشه قبل از استفاده واقعی، کیفیت استراتژی را با بک‌تست، سوییپ، واک‌فوروارد و اجرای دمو بررسی کن."), color = Color(0xFFDDF8FF))
                }
            }
        }
    }
}

@Composable
private fun AlertProfileChip(title: String, value: String, modifier: Modifier = Modifier) {
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

private fun alertProfileLabel(
    notificationsEnabled: Boolean,
    autoRefreshEnabled: Boolean,
    testnetOnlyEnabled: Boolean,
    riskAcknowledged: Boolean,
): String {
    return when {
        notificationsEnabled && autoRefreshEnabled && !testnetOnlyEnabled && riskAcknowledged -> "Aggressive"
        notificationsEnabled && autoRefreshEnabled && riskAcknowledged -> "Balanced"
        notificationsEnabled || autoRefreshEnabled -> "Defensive"
        else -> "Silent"
    }
}

@Composable
private fun SettingToggle(
    title: String,
    description: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit
) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Column(modifier = Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.titleMedium, color = Color.White)
            Text(description, style = MaterialTheme.typography.bodyMedium, color = Color(0xFFBCEEFF))
        }
        Switch(checked = checked, onCheckedChange = onCheckedChange)
    }
}

@Composable
private fun LanguageButton(
    modifier: Modifier = Modifier,
    title: String,
    selected: Boolean,
    onClick: () -> Unit
) {
    if (selected) {
        Button(onClick = onClick, modifier = modifier) { Text(title) }
    } else {
        OutlinedButton(onClick = onClick, modifier = modifier) { Text(title) }
    }
}
