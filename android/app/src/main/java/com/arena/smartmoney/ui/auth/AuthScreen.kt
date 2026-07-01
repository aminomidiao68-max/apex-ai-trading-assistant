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
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.arena.smartmoney.R
import com.arena.smartmoney.data.repository.TradingRepository
import com.arena.smartmoney.data.session.SessionManager
import com.arena.smartmoney.push.PushRegistrationHelper
import kotlinx.coroutines.launch

@Composable
fun AuthScreen(onAuthSuccess: () -> Unit) {
    val context = LocalContext.current
    val repository = remember { TradingRepository() }
    val sessionManager = remember { SessionManager(context) }
    val scope = rememberCoroutineScope()

    var isRegisterMode by rememberSaveable { mutableStateOf(false) }
    var name by rememberSaveable { mutableStateOf("") }
    var email by rememberSaveable { mutableStateOf("demo@apexai.app") }
    var password by rememberSaveable { mutableStateOf("Demo12345!") }
    var loading by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }

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
            modifier = Modifier.fillMaxWidth(0.42f)
        )
        Spacer(Modifier.height(16.dp))
        Text("APEX AI", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Text(
            "Crypto & Forex Trading Assistant",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(Modifier.height(20.dp))

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    TextButton(onClick = { isRegisterMode = false }) { Text("Login") }
                    TextButton(onClick = { isRegisterMode = true }) { Text("Register") }
                }

                if (isRegisterMode) {
                    OutlinedTextField(
                        value = name,
                        onValueChange = { name = it },
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text("Full Name") }
                    )
                }

                OutlinedTextField(
                    value = email,
                    onValueChange = { email = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Email") }
                )

                OutlinedTextField(
                    value = password,
                    onValueChange = { password = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Password") },
                    visualTransformation = PasswordVisualTransformation()
                )

                error?.let { Text(it, color = MaterialTheme.colorScheme.error) }

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
                                error = throwable.message ?: "Authentication failed"
                            }
                        }
                    },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    if (loading) {
                        CircularProgressIndicator(modifier = Modifier.padding(4.dp))
                    } else {
                        Text(if (isRegisterMode) "Create Account" else "Enter App")
                    }
                }

                Spacer(Modifier.height(4.dp))
                Text("Demo account:", fontWeight = FontWeight.SemiBold)
                Text("Email: demo@apexai.app")
                Text("Password: Demo12345!")
            }
        }
    }
}
