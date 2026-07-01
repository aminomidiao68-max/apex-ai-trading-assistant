package com.arena.smartmoney.ui.profile

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.arena.smartmoney.data.repository.TradingRepository
import com.arena.smartmoney.data.session.SessionManager
import com.arena.smartmoney.push.PushRegistrationHelper
import kotlinx.coroutines.launch

@Composable
fun ProfileScreen(onLogout: () -> Unit, onOpenSettings: () -> Unit) {
    val context = LocalContext.current
    val repository = remember { TradingRepository() }
    val sessionManager = remember { SessionManager(context) }
    val scope = rememberCoroutineScope()

    var name by remember { mutableStateOf(sessionManager.getName()) }
    var email by remember { mutableStateOf(sessionManager.getEmail()) }
    var error by remember { mutableStateOf<String?>(null) }
    var loading by remember { mutableStateOf(false) }
    var pushMessage by remember { mutableStateOf("") }

    fun loadProfile() {
        val token = sessionManager.getToken() ?: return
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
                    error = throwable.message ?: "Failed to load profile"
                }
        }
    }

    LaunchedEffect(Unit) {
        loadProfile()
        PushRegistrationHelper.registerCurrentDevice(sessionManager)
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("Profile", style = MaterialTheme.typography.headlineSmall)
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Name: $name")
                Text("Email: $email")
                Text(if (loading) "Status: Syncing profile..." else "Status: Active")
                error?.let { Text("Error: $it", color = MaterialTheme.colorScheme.error) }
            }
        }

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Security & Access", style = MaterialTheme.typography.titleMedium)
                Text("• Login required before entering the main app")
                Text("• Token is stored locally on this device")
                Text("• Live order execution still remains protected by server-side checks")
                Text("• FCM registration foundation is enabled for future real push delivery")
            }
        }

        Button(onClick = { loadProfile() }, modifier = Modifier.fillMaxWidth()) {
            Text(if (loading) "Refreshing..." else "Refresh Profile")
        }

        Button(onClick = onOpenSettings, modifier = Modifier.fillMaxWidth()) {
            Text("Open Settings")
        }

        Button(
            onClick = {
                pushMessage = ""
                PushRegistrationHelper.registerCurrentDevice(sessionManager)
                pushMessage = "Device token registration attempted"
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Register Device for Push")
        }

        Button(
            onClick = {
                val token = sessionManager.getToken() ?: return@Button
                pushMessage = ""
                scope.launch {
                    runCatching {
                        repository.sendTestNotification(
                            authorization = "Bearer $token",
                            title = "APEX AI Test",
                            body = "Backend notification event created"
                        )
                    }.onSuccess { result ->
                        pushMessage = result.message
                    }.onFailure { throwable ->
                        pushMessage = throwable.message ?: "Failed to trigger test notification"
                    }
                }
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Send Test Push Event")
        }

        if (pushMessage.isNotBlank()) {
            Text(pushMessage)
        }

        Spacer(Modifier.height(8.dp))

        Button(
            onClick = {
                val token = sessionManager.getToken()
                scope.launch {
                    runCatching {
                        if (token != null) repository.logout("Bearer $token")
                    }
                    sessionManager.clearSession()
                    onLogout()
                }
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Logout")
        }
    }
}
