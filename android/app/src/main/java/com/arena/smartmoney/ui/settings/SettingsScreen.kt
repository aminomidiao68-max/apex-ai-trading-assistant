package com.arena.smartmoney.ui.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.weight
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.arena.smartmoney.BuildConfig
import com.arena.smartmoney.data.network.AppConfig
import com.arena.smartmoney.data.preferences.AppPreferencesManager
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

    androidx.compose.foundation.lazy.LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Text(
                t("Settings Center", "مرکز تنظیمات"),
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold
            )
            Text(
                t(
                    "Language, safety controls, environment visibility and final release checks.",
                    "زبان، کنترل‌های ایمنی، مشاهده محیط اجرا و بررسی‌های نهایی انتشار."
                )
            )
        }
        item {
            Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(22.dp)) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Text(t("Language", "زبان"), style = MaterialTheme.typography.titleLarge)
                    Text(
                        t(
                            "Switch the full app between Persian and English instantly.",
                            "کل برنامه را به‌صورت لحظه‌ای بین فارسی و انگلیسی تغییر بده."
                        )
                    )
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        LanguageButton(
                            modifier = Modifier.weight(1f),
                            title = "فارسی",
                            selected = currentLanguage == "fa",
                            onClick = { applyLanguage("fa") }
                        )
                        LanguageButton(
                            modifier = Modifier.weight(1f),
                            title = "English",
                            selected = currentLanguage == "en",
                            onClick = { applyLanguage("en") }
                        )
                    }
                    Text(
                        t(
                            "Current language: ${if (currentLanguage == "fa") "Persian" else "English"}",
                            "زبان فعلی: ${if (currentLanguage == "fa") "فارسی" else "انگلیسی"}"
                        ),
                        color = MaterialTheme.colorScheme.primary
                    )
                }
            }
        }
        item {
            Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(22.dp)) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Text(t("Smart Controls", "کنترل‌های هوشمند"), style = MaterialTheme.typography.titleLarge)
                    SettingToggle(
                        title = t("Notifications", "نوتیفیکیشن‌ها"),
                        description = t(
                            "Allow local and Firebase trading alerts when available.",
                            "در صورت آماده بودن، هشدارهای محلی و فایربیس معاملات فعال شوند."
                        ),
                        checked = notificationsEnabled,
                        onCheckedChange = {
                            notificationsEnabled = it
                            prefs.setNotificationsEnabled(it)
                        }
                    )
                    SettingToggle(
                        title = t("Auto Refresh", "بروزرسانی خودکار"),
                        description = t(
                            "Keep dashboard and monitoring sections ready for refresh-heavy usage.",
                            "داشبورد و بخش‌های مانیتورینگ برای بروزرسانی مداوم آماده بمانند."
                        ),
                        checked = autoRefreshEnabled,
                        onCheckedChange = {
                            autoRefreshEnabled = it
                            prefs.setAutoRefreshEnabled(it)
                        }
                    )
                    SettingToggle(
                        title = t("Testnet / Demo First", "اول تست‌نت / دمو"),
                        description = t(
                            "Recommended before enabling any real execution workflow.",
                            "پیش از فعال‌سازی هر نوع اجرای واقعی سفارش، این حالت پیشنهاد می‌شود."
                        ),
                        checked = testnetOnlyEnabled,
                        onCheckedChange = {
                            testnetOnlyEnabled = it
                            prefs.setTestnetOnlyEnabled(it)
                        }
                    )
                    SettingToggle(
                        title = t("Risk Disclaimer Accepted", "پذیرش هشدار ریسک"),
                        description = t(
                            "Confirms you understand trading has serious risk and no profit is guaranteed.",
                            "تایید می‌کند که می‌دانید معامله ریسک جدی دارد و هیچ سودی تضمین‌شده نیست."
                        ),
                        checked = riskAcknowledged,
                        onCheckedChange = {
                            riskAcknowledged = it
                            prefs.setRiskAcknowledged(it)
                        }
                    )
                }
            }
        }
        item {
            Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(22.dp)) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(t("App Environment", "محیط برنامه"), style = MaterialTheme.typography.titleLarge)
                    Text(t("App Version", "نسخه برنامه") + ": ${BuildConfig.VERSION_NAME}")
                    Text(t("API Base URL", "آدرس پایه API") + ": ${AppConfig.apiBaseUrl}")
                    Text(t("WS Base URL", "آدرس پایه WS") + ": ${AppConfig.marketWsUrl}")
                    Text(
                        t(
                            "Build configuration is ready for debug / release separation.",
                            "پیکربندی ساخت برای جداسازی نسخه دیباگ و ریلیز آماده است."
                        )
                    )
                }
            }
        }
        item {
            Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(22.dp)) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(t("Release Checklist", "چک‌لیست انتشار"), style = MaterialTheme.typography.titleLarge)
                    Text("• " + t("Add google-services.json for full Firebase push", "برای پوش کامل فایربیس، google-services.json را اضافه کن"))
                    Text("• " + t("Configure keystore or signing environment variables", "کی‌استور یا متغیرهای امضای نسخه نهایی را تنظیم کن"))
                    Text("• " + t("Keep live execution disabled until broker tests pass", "تا زمان موفق شدن تست بروکر، اجرای زنده را غیرفعال نگه دار"))
                    Text("• " + t("Review release and deployment docs before publishing", "قبل از انتشار، مستندات ریلیز و دیپلوی را بررسی کن"))
                    Text("• " + t("Use the readiness screen before any real activation", "قبل از هر فعال‌سازی واقعی، صفحه آمادگی سیستم را بررسی کن"))
                }
            }
        }
        item {
            Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(22.dp)) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(t("Launch Controls", "کنترل‌های لانچ"), style = MaterialTheme.typography.titleLarge)
                    Text(
                        t(
                            "Open the readiness screen to verify Firebase, connectors and production blockers.",
                            "برای بررسی فایربیس، کانکتورها و موانع نسخه عملیاتی، صفحه آمادگی سیستم را باز کن."
                        )
                    )
                    Button(onClick = onOpenReadiness, modifier = Modifier.fillMaxWidth()) {
                        Text(t("Open System Readiness", "باز کردن آمادگی سیستم"))
                    }
                }
            }
        }
        item {
            Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(22.dp)) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(t("Risk Policy", "سیاست ریسک"), style = MaterialTheme.typography.titleLarge)
                    Text(t("This app is an analysis and execution-support system, not a guarantee machine.", "این برنامه یک سیستم تحلیل و کمک‌اجرایی است، نه ماشین تضمین سود."))
                    Text(t("Always validate strategy quality with backtest, sweep, walk-forward and demo execution first.", "همیشه قبل از استفاده واقعی، کیفیت استراتژی را با بک‌تست، سوییپ، واک‌فوروارد و اجرای دمو بررسی کن."))
                    Text(t("High leverage and major news can invalidate even strong-looking setups.", "اهرم بالا و اخبار مهم می‌توانند حتی ستاپ‌های ظاهراً قوی را بی‌اعتبار کنند."))
                }
            }
        }
    }
}

@Composable
private fun SettingToggle(
    title: String,
    description: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(title, style = MaterialTheme.typography.titleMedium)
                Text(description, style = MaterialTheme.typography.bodyMedium)
            }
            Switch(checked = checked, onCheckedChange = onCheckedChange)
        }
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
        Button(onClick = onClick, modifier = modifier) {
            Text(title)
        }
    } else {
        OutlinedButton(onClick = onClick, modifier = modifier) {
            Text(title)
        }
    }
}
