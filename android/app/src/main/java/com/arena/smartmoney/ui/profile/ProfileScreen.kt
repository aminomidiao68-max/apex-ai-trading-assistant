package com.arena.smartmoney.ui.profile

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.arena.smartmoney.data.repository.TradingRepository
import com.arena.smartmoney.data.session.SessionManager
import com.arena.smartmoney.push.PushRegistrationHelper
import com.arena.smartmoney.ui.components.PremiumGlassCard
import com.arena.smartmoney.ui.components.PremiumScreenBackground
import com.arena.smartmoney.ui.components.PremiumSectionHeader
import com.arena.smartmoney.ui.i18n.rememberTranslator
import kotlinx.coroutines.launch

@Composable
fun ProfileScreen(onLogout: () -> Unit, onOpenSettings: () -> Unit) {
    val context = LocalContext.current
    val repository = remember { TradingRepository() }
    val sessionManager = remember { SessionManager(context) }
    val scope = rememberCoroutineScope()
    val t = rememberTranslator()

    var name by remember { mutableStateOf(sessionManager.getName()) }
    var email by remember { mutableStateOf(sessionManager.getEmail()) }
    var error by remember { mutableStateOf<String?>(null) }
    var loading by remember { mutableStateOf(false) }
    var pushMessage by remember { mutableStateOf("") }

    fun loadProfile() {
        val token = sessionManager.getToken() ?: return
        if (sessionManager.isLocalDemoSession()) {
            name = sessionManager.getName()
            email = sessionManager.getEmail()
            loading = false
            error = null
            return
        }
        loading = true
        error = null
        scope.launch {
            runCatching { repository.getMe("Bearer $token") }
                .onSuccess { user ->
                    name = user.name
                    email = user.email
                    sessionManager.saveSession(token, user.name, user.email)
                    loading = false
                }
                .onFailure { throwable ->
                    loading = false
                    error = throwable.message ?: t("Failed to load profile", "بارگذاری پروفایل ناموفق بود")
                }
        }
    }

    LaunchedEffect(Unit) {
        loadProfile()
        PushRegistrationHelper.registerCurrentDevice(sessionManager)
    }

    PremiumScreenBackground {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            PremiumSectionHeader(
                title = t("Profile", "پروفایل"),
                subtitle = t("Identity, security and device registration.", "هویت، امنیت و ثبت دستگاه.")
            )

            PremiumGlassCard {
                Text(t("Name", "نام") + ": $name", color = Color.White)
                Text(t("Email", "ایمیل") + ": $email", color = Color.White)
                Text(
                    when {
                        loading -> t("Status: syncing profile...", "وضعیت: همگام‌سازی پروفایل...")
                        sessionManager.isLocalDemoSession() -> t("Status: local demo mode", "وضعیت: حالت دمو محلی")
                        else -> t("Status: active", "وضعیت: فعال")
                    },
                    color = Color(0xFF67ECFF),
                    fontWeight = FontWeight.Bold
                )
                error?.let { Text(t("Error", "خطا") + ": $it", color = MaterialTheme.colorScheme.error) }
            }

            PremiumGlassCard {
                Text(t("Security & Access", "امنیت و دسترسی"), style = MaterialTheme.typography.titleMedium, color = Color.White, fontWeight = FontWeight.Bold)
                Text("• " + t("Login required before entering the main app", "ورود قبل از دسترسی به برنامه اصلی الزامی است"), color = Color(0xFFDDF8FF))
                Text("• " + t("Token is stored locally on this device", "توکن روی همین دستگاه ذخیره می‌شود"), color = Color(0xFFDDF8FF))
                Text("• " + t("Live order execution remains protected by server-side checks", "اجرای زنده سفارش هنوز با کنترل‌های سمت سرور محافظت می‌شود"), color = Color(0xFFDDF8FF))
                Text("• " + t("FCM foundation is enabled for future real push delivery", "زیرساخت FCM برای پوش واقعی در آینده فعال است"), color = Color(0xFFDDF8FF))
            }

            Button(onClick = { loadProfile() }, modifier = Modifier.fillMaxWidth()) {
                Text(if (loading) t("Refreshing...", "در حال بروزرسانی...") else t("Refresh Profile", "بروزرسانی پروفایل"))
            }

            OutlinedButton(onClick = onOpenSettings, modifier = Modifier.fillMaxWidth()) {
                Text(t("Open Settings", "باز کردن تنظیمات"))
            }

            Button(
                onClick = {
                    pushMessage = ""
                    PushRegistrationHelper.registerCurrentDevice(sessionManager)
                    pushMessage = t("Device token registration attempted", "تلاش برای ثبت توکن دستگاه انجام شد")
                },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(t("Register Device for Push", "ثبت دستگاه برای پوش"))
            }

            Button(
                onClick = {
                    val token = sessionManager.getToken() ?: return@Button
                    pushMessage = ""
                    scope.launch {
                        if (sessionManager.isLocalDemoSession()) {
                            pushMessage = t("Local demo mode does not send remote push tests.", "در حالت دمو محلی، تست پوش از راه دور ارسال نمی‌شود.")
                            return@launch
                        }
                        runCatching {
                            repository.sendTestNotification(
                                authorization = "Bearer $token",
                                title = "APEX AI Test",
                                body = "Backend notification event created"
                            )
                        }.onSuccess { result ->
                            pushMessage = result.message
                        }.onFailure { throwable ->
                            pushMessage = throwable.message ?: t("Failed to trigger test notification", "ارسال تست نوتیفیکیشن ناموفق بود")
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(t("Send Test Push Event", "ارسال تست نوتیفیکیشن"))
            }

            if (pushMessage.isNotBlank()) {
                PremiumGlassCard {
                    Text(pushMessage, color = Color(0xFF67ECFF), fontWeight = FontWeight.Bold)
                }
            }

            Spacer(Modifier.height(8.dp))

            OutlinedButton(
                onClick = {
                    val token = sessionManager.getToken()
                    scope.launch {
                        runCatching {
                            if (token != null && !sessionManager.isLocalDemoSession()) {
                                repository.logout("Bearer $token")
                            }
                        }
                        sessionManager.clearSession()
                        onLogout()
                    }
                },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(t("Logout", "خروج"))
            }
        }
    }
}
