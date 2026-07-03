package com.arena.smartmoney.ui.auth

import androidx.compose.foundation.Image
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
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.arena.smartmoney.R
import com.arena.smartmoney.data.repository.TradingRepository
import com.arena.smartmoney.data.session.SessionManager
import com.arena.smartmoney.push.PushRegistrationHelper
import com.arena.smartmoney.ui.components.PremiumGlassCard
import com.arena.smartmoney.ui.components.PremiumScreenBackground
import com.arena.smartmoney.ui.components.PremiumSectionHeader
import com.arena.smartmoney.ui.components.premiumTextFieldColors
import com.arena.smartmoney.ui.components.premiumTextFieldStyle
import com.arena.smartmoney.ui.i18n.rememberTranslator
import kotlinx.coroutines.launch

@Composable
fun AuthScreen(onAuthSuccess: () -> Unit) {
    val context = LocalContext.current
    val repository = remember { TradingRepository() }
    val sessionManager = remember { SessionManager(context) }
    val scope = rememberCoroutineScope()
    val t = rememberTranslator()

    var isRegisterMode by rememberSaveable { mutableStateOf(false) }
    var name by rememberSaveable { mutableStateOf("") }
    var email by rememberSaveable { mutableStateOf("demo@apexai.app") }
    var password by rememberSaveable { mutableStateOf("Demo12345!") }
    var loading by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }

    fun humanizeAuthError(raw: String?): String {
        val msg = raw.orEmpty()
        return when {
            "409" in msg || msg.contains("already registered", ignoreCase = true) ->
                t("This email is already registered. Please log in instead.", "این ایمیل قبلاً ثبت شده است. لطفاً وارد شوید.")
            "401" in msg || msg.contains("invalid email or password", ignoreCase = true) ->
                t("Email or password is incorrect.", "ایمیل یا رمز عبور اشتباه است.")
            msg.isBlank() -> t("Authentication failed", "ورود/ثبت‌نام ناموفق بود")
            else -> msg
        }
    }

    fun switchToLogin() {
        isRegisterMode = false
        error = null
        if (email.isBlank()) email = "demo@apexai.app"
        if (password.isBlank()) password = "Demo12345!"
    }

    fun switchToRegister() {
        isRegisterMode = true
        error = null
        name = ""
        email = ""
        password = ""
    }

    PremiumScreenBackground {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Image(
                painter = painterResource(id = R.drawable.ic_apex_ai_logo),
                contentDescription = "APEX AI Logo",
                modifier = Modifier.fillMaxWidth(0.38f)
            )
            Spacer(Modifier.height(14.dp))
            PremiumSectionHeader(
                title = "APEX AI PREMIUM",
                subtitle = t("Neon AI trading access portal", "درگاه ورود نئونی هوش مصنوعی معاملات")
            )
            Spacer(Modifier.height(18.dp))

            PremiumGlassCard(modifier = Modifier.fillMaxWidth()) {
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    TextButton(onClick = { switchToLogin() }) {
                        Text(t("Login", "ورود"), color = if (!isRegisterMode) Color(0xFF67ECFF) else Color.White)
                    }
                    TextButton(onClick = { switchToRegister() }) {
                        Text(t("Register", "ثبت‌نام"), color = if (isRegisterMode) Color(0xFF67ECFF) else Color.White)
                    }
                }

                Spacer(Modifier.height(8.dp))

                if (isRegisterMode) {
                    OutlinedTextField(
                        value = name,
                        onValueChange = { name = it },
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text(t("Full Name", "نام کامل")) },
                        shape = RoundedCornerShape(18.dp),
                        singleLine = true,
                        textStyle = premiumTextFieldStyle(),
                        colors = premiumTextFieldColors()
                    )
                    Spacer(Modifier.height(10.dp))
                }

                OutlinedTextField(
                    value = email,
                    onValueChange = { email = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text(t("Email", "ایمیل")) },
                    shape = RoundedCornerShape(18.dp),
                    singleLine = true,
                    textStyle = premiumTextFieldStyle(),
                    colors = premiumTextFieldColors()
                )
                Spacer(Modifier.height(10.dp))

                OutlinedTextField(
                    value = password,
                    onValueChange = { password = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text(t("Password", "رمز عبور")) },
                    visualTransformation = PasswordVisualTransformation(),
                    shape = RoundedCornerShape(18.dp),
                    singleLine = true,
                    textStyle = premiumTextFieldStyle(),
                    colors = premiumTextFieldColors()
                )

                Spacer(Modifier.height(12.dp))
                error?.let { Text(humanizeAuthError(it), color = MaterialTheme.colorScheme.error) }

                Button(
                    onClick = {
                        if (loading) return@Button
                        loading = true
                        error = null
                        scope.launch {
                            runCatching {
                                if (isRegisterMode) {
                                    repository.register(
                                        name = if (name.isBlank()) "Trader" else name.trim(),
                                        email = email.trim(),
                                        password = password
                                    )
                                } else {
                                    repository.login(email.trim(), password)
                                }
                            }.onSuccess { response ->
                                sessionManager.saveSession(
                                    token = response.access_token,
                                    name = response.user.name,
                                    email = response.user.email
                                )
                                PushRegistrationHelper.registerCurrentDevice(sessionManager)
                                loading = false
                                onAuthSuccess()
                            }.onFailure { throwable ->
                                loading = false
                                error = humanizeAuthError(throwable.message)
                            }
                        }
                    },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    if (loading) {
                        CircularProgressIndicator(modifier = Modifier.padding(4.dp), color = Color.White)
                    } else {
                        Text(if (isRegisterMode) t("Create Account", "ایجاد حساب") else t("Enter App", "ورود به برنامه"))
                    }
                }

                Spacer(Modifier.height(12.dp))
                Text(t("Demo account:", "حساب دمو:"), color = Color(0xFF67ECFF), fontWeight = FontWeight.Bold)
                Text("Email: demo@apexai.app", color = Color.White)
                Text("Password: Demo12345!", color = Color.White)
            }
        }
    }
}
