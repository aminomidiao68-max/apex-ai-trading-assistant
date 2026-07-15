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
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.arena.smartmoney.BuildConfig
import com.arena.smartmoney.data.model.ProviderSecretStatusDto
import com.arena.smartmoney.data.network.AppConfig
import com.arena.smartmoney.data.preferences.AppPreferencesManager
import com.arena.smartmoney.data.repository.TradingRepository
import com.arena.smartmoney.data.session.SessionManager
import com.arena.smartmoney.ui.components.PremiumGlassCard
import com.arena.smartmoney.ui.components.PremiumScreenBackground
import com.arena.smartmoney.ui.components.PremiumSectionHeader
import com.arena.smartmoney.ui.i18n.AppLanguageState
import com.arena.smartmoney.ui.i18n.rememberTranslator
import kotlinx.coroutines.launch

@Composable
fun SettingsScreen(onOpenReadiness: () -> Unit) {
    val context = LocalContext.current
    val prefs = remember { AppPreferencesManager(context) }
    val repository = remember { TradingRepository() }
    val sessionManager = remember { SessionManager(context) }
    val scope = rememberCoroutineScope()
    val t = rememberTranslator()

    var providerStatuses by remember { mutableStateOf<List<ProviderSecretStatusDto>>(emptyList()) }
    var vaultConfigured by remember { mutableStateOf(false) }
    var selectedProvider by remember { mutableStateOf("groq") }
    var providerApiKey by remember { mutableStateOf("") }
    var providerAccountId by remember { mutableStateOf("") }
    var providerModel by remember { mutableStateOf("") }
    var providerEnabled by remember { mutableStateOf(true) }
    var providerLoading by remember { mutableStateOf(false) }
    var providerMessage by remember { mutableStateOf("") }

    fun refreshProviderStatus() {
        if (sessionManager.isLocalDemoSession() || sessionManager.getToken().isNullOrBlank()) return
        scope.launch {
            providerLoading = true
            runCatching { repository.getProviderSecretStatus() }
                .onSuccess { response ->
                    vaultConfigured = response.vault_configured
                    providerStatuses = response.providers
                    providerLoading = false
                }
                .onFailure {
                    providerLoading = false
                    providerMessage = t(
                        "Provider status is temporarily unavailable.",
                        "وضعیت ارائه‌دهنده‌ها موقتاً در دسترس نیست."
                    )
                }
        }
    }

    LaunchedEffect(Unit) {
        refreshProviderStatus()
    }

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
    val selectedProviderDefinition = providerDefinitions.first { it.id == selectedProvider }
    val selectedProviderStatus = providerStatuses.firstOrNull { it.provider == selectedProvider }

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
                PremiumGlassCard(borderColor = Color(0x4059C7FF)) {
                    Text(
                        t("Secure API Vault", "گاوصندوق امن API"),
                        style = MaterialTheme.typography.titleLarge,
                        color = Color.White,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        t(
                            "Keys are encrypted on the backend and are never stored in Android preferences or returned to the app.",
                            "کلیدها در بک‌اند رمزنگاری می‌شوند، در تنظیمات محلی اندروید ذخیره نمی‌شوند و هیچ‌وقت به برنامه برگردانده نمی‌شوند."
                        ),
                        color = Color(0xFFBCEEFF)
                    )
                    Text(
                        t(
                            "Previously exposed keys should be rotated before entry.",
                            "کلیدهایی که قبلاً افشا شده‌اند باید پیش از ورود تعویض شوند."
                        ),
                        color = Color(0xFFFFD27A),
                        fontWeight = FontWeight.Bold
                    )
                    if (sessionManager.isLocalDemoSession()) {
                        Text(
                            t(
                                "Secure provider settings require a server account.",
                                "تنظیمات امن ارائه‌دهنده نیازمند حساب متصل به سرور است."
                            ),
                            color = Color(0xFFFF8A8A)
                        )
                    } else {
                        Text(
                            t("Vault", "گاوصندوق") + ": " + when {
                                providerLoading -> t("Checking...", "در حال بررسی...")
                                vaultConfigured -> t("Ready", "آماده")
                                else -> t("Server setup required", "نیازمند تنظیم سرور")
                            },
                            color = if (vaultConfigured) Color(0xFF33E6A6) else Color(0xFFFFD27A),
                            fontWeight = FontWeight.Bold
                        )
                        providerDefinitions.chunked(3).forEach { rowProviders ->
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.spacedBy(6.dp)
                            ) {
                                rowProviders.forEach { definition ->
                                    ProviderButton(
                                        title = definition.title,
                                        selected = selectedProvider == definition.id,
                                        configured = providerStatuses.firstOrNull {
                                            it.provider == definition.id
                                        }?.configured == true,
                                        modifier = Modifier.weight(1f)
                                    ) {
                                        selectedProvider = definition.id
                                        providerApiKey = ""
                                        providerAccountId = ""
                                        providerModel = providerStatuses.firstOrNull {
                                            it.provider == definition.id
                                        }?.model ?: definition.defaultModel.orEmpty()
                                        providerEnabled = providerStatuses.firstOrNull {
                                            it.provider == definition.id
                                        }?.enabled ?: true
                                        providerMessage = ""
                                    }
                                }
                                repeat(3 - rowProviders.size) { Spacer(Modifier.weight(1f)) }
                            }
                        }
                        Text(
                            selectedProviderDefinition.descriptionFa,
                            color = Color(0xFFDDF8FF)
                        )
                        Text(
                            t("Status", "وضعیت") + ": " + when {
                                selectedProviderStatus?.configured == true && selectedProviderStatus.enabled -> t("Configured", "تنظیم‌شده")
                                selectedProviderStatus?.configured == true -> t("Saved but disabled", "ذخیره‌شده ولی غیرفعال")
                                else -> t("Not configured", "تنظیم‌نشده")
                            },
                            color = Color(0xFF67ECFF),
                            fontWeight = FontWeight.Bold
                        )
                        selectedProviderStatus?.last_test_status?.let { testStatus ->
                            Text(
                                t("Last connection test", "آخرین تست اتصال") + ": $testStatus",
                                color = Color(0xFFBCEEFF)
                            )
                        }
                        OutlinedTextField(
                            value = providerApiKey,
                            onValueChange = { providerApiKey = it },
                            modifier = Modifier.fillMaxWidth(),
                            label = { Text(t("New API key / token", "کلید یا توکن جدید API")) },
                            singleLine = true,
                            visualTransformation = PasswordVisualTransformation(),
                            shape = RoundedCornerShape(16.dp),
                            supportingText = {
                                Text(t("The value is cleared after save.", "مقدار پس از ذخیره پاک می‌شود."))
                            }
                        )
                        if (selectedProviderDefinition.requiresAccountId) {
                            OutlinedTextField(
                                value = providerAccountId,
                                onValueChange = { providerAccountId = it },
                                modifier = Modifier.fillMaxWidth(),
                                label = { Text(t("OANDA Account ID", "شناسه حساب OANDA")) },
                                singleLine = true,
                                visualTransformation = PasswordVisualTransformation(),
                                shape = RoundedCornerShape(16.dp)
                            )
                        }
                        if (selectedProviderDefinition.defaultModel != null) {
                            OutlinedTextField(
                                value = providerModel,
                                onValueChange = { providerModel = it },
                                modifier = Modifier.fillMaxWidth(),
                                label = { Text(t("Explanation model", "مدل توضیح‌دهنده")) },
                                singleLine = true,
                                shape = RoundedCornerShape(16.dp)
                            )
                        }
                        SettingToggle(
                            title = t("Provider enabled", "ارائه‌دهنده فعال باشد"),
                            description = t(
                                "Enabled providers can be used only for your authenticated requests.",
                                "ارائه‌دهنده فعال فقط برای درخواست‌های احراز‌شده خودت استفاده می‌شود."
                            ),
                            checked = providerEnabled,
                            onCheckedChange = { providerEnabled = it }
                        )
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            Button(
                                enabled = !providerLoading && vaultConfigured &&
                                    providerApiKey.trim().length >= 8 &&
                                    (!selectedProviderDefinition.requiresAccountId || providerAccountId.isNotBlank()),
                                onClick = {
                                    providerLoading = true
                                    providerMessage = ""
                                    scope.launch {
                                        runCatching {
                                            repository.saveProviderSecret(
                                                provider = selectedProvider,
                                                apiKey = providerApiKey.trim(),
                                                accountId = providerAccountId.trim().ifBlank { null },
                                                model = providerModel.trim().ifBlank { null },
                                                enabled = providerEnabled,
                                            )
                                        }.onSuccess {
                                            providerApiKey = ""
                                            providerAccountId = ""
                                            providerLoading = false
                                            providerMessage = t("Encrypted provider secret saved.", "کلید ارائه‌دهنده به‌صورت رمزنگاری‌شده ذخیره شد.")
                                            refreshProviderStatus()
                                        }.onFailure {
                                            providerApiKey = ""
                                            providerAccountId = ""
                                            providerLoading = false
                                            providerMessage = t("Secure save failed.", "ذخیره امن ناموفق بود.")
                                        }
                                    }
                                },
                                modifier = Modifier.weight(1f)
                            ) { Text(t("Save", "ذخیره")) }
                            OutlinedButton(
                                enabled = !providerLoading && selectedProviderStatus?.configured == true,
                                onClick = {
                                    providerLoading = true
                                    providerMessage = ""
                                    scope.launch {
                                        runCatching { repository.testProviderSecret(selectedProvider) }
                                            .onSuccess { result ->
                                                providerLoading = false
                                                providerMessage = t("Connection", "اتصال") + ": ${result.status}"
                                                refreshProviderStatus()
                                            }
                                            .onFailure {
                                                providerLoading = false
                                                providerMessage = t("Connection test failed.", "تست اتصال ناموفق بود.")
                                            }
                                    }
                                },
                                modifier = Modifier.weight(1f)
                            ) { Text(t("Test", "تست")) }
                            OutlinedButton(
                                enabled = !providerLoading && selectedProviderStatus?.configured == true,
                                onClick = {
                                    providerLoading = true
                                    scope.launch {
                                        runCatching { repository.deleteProviderSecret(selectedProvider) }
                                            .onSuccess {
                                                providerApiKey = ""
                                                providerAccountId = ""
                                                providerLoading = false
                                                providerMessage = t("Provider secret deleted.", "کلید ارائه‌دهنده حذف شد.")
                                                refreshProviderStatus()
                                            }
                                            .onFailure {
                                                providerLoading = false
                                                providerMessage = t("Delete failed.", "حذف ناموفق بود.")
                                            }
                                    }
                                },
                                modifier = Modifier.weight(1f)
                            ) { Text(t("Delete", "حذف")) }
                        }
                        if (providerMessage.isNotBlank()) {
                            Text(providerMessage, color = Color(0xFF67ECFF), fontWeight = FontWeight.Bold)
                        }
                        Text(
                            t(
                                "Groq/OpenAI can explain evidence only. OANDA remains dry-run while Live Execution is disabled.",
                                "Groq/OpenAI فقط شواهد را توضیح می‌دهند. OANDA تا زمان خاموش بودن اجرای زنده در حالت Dry-run می‌ماند."
                            ),
                            color = Color(0xFFFFD27A)
                        )
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

private data class ProviderDefinition(
    val id: String,
    val title: String,
    val descriptionFa: String,
    val defaultModel: String? = null,
    val requiresAccountId: Boolean = false,
)

private val providerDefinitions = listOf(
    ProviderDefinition("groq", "Groq", "مدل توضیح‌دهنده سریع و سازگار با OpenAI؛ تصمیم‌گیر نیست.", "llama-3.3-70b-versatile"),
    ProviderDefinition("openai", "OpenAI", "مدل توضیح‌دهنده اختیاری؛ موتور قطعی را Override نمی‌کند.", "gpt-4.1-mini"),
    ProviderDefinition("twelvedata", "Twelve", "داده Forex/Gold و Historical برای درخواست‌های حساب شما."),
    ProviderDefinition("finnhub", "Finnhub", "خبر و داده عمومی مالی برای حساب شما."),
    ProviderDefinition("newsapi", "NewsAPI", "منبع جایگزین خبرهای Business؛ جای Economic Calendar نیست."),
    ProviderDefinition("oanda", "OANDA", "توکن Practice به‌همراه Account ID؛ اجرای Live خاموش باقی می‌ماند.", requiresAccountId = true),
)

@Composable
private fun ProviderButton(
    title: String,
    selected: Boolean,
    configured: Boolean,
    modifier: Modifier = Modifier,
    onClick: () -> Unit,
) {
    val label = if (configured) "$title ✓" else title
    if (selected) {
        Button(onClick = onClick, modifier = modifier) { Text(label) }
    } else {
        OutlinedButton(onClick = onClick, modifier = modifier) { Text(label) }
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
