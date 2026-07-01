package com.arena.smartmoney.ui.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.arena.smartmoney.BuildConfig
import com.arena.smartmoney.data.network.AppConfig
import com.arena.smartmoney.data.preferences.AppPreferencesManager

@Composable
fun SettingsScreen(onOpenReadiness: () -> Unit) {
    val context = LocalContext.current
    val prefs = remember { AppPreferencesManager(context) }

    var notificationsEnabled by remember { mutableStateOf(prefs.isNotificationsEnabled()) }
    var autoRefreshEnabled by remember { mutableStateOf(prefs.isAutoRefreshEnabled()) }
    var testnetOnlyEnabled by remember { mutableStateOf(prefs.isTestnetOnlyEnabled()) }
    var riskAcknowledged by remember { mutableStateOf(prefs.isRiskAcknowledged()) }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Text("Settings", style = MaterialTheme.typography.headlineSmall)
            Text("Final UX controls, execution safety and environment visibility")
        }
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    SettingToggle(
                        title = "Notifications",
                        description = "Allow local / FCM trading alerts when available.",
                        checked = notificationsEnabled,
                        onCheckedChange = {
                            notificationsEnabled = it
                            prefs.setNotificationsEnabled(it)
                        }
                    )
                    SettingToggle(
                        title = "Auto Refresh",
                        description = "Keep dashboards and monitoring workflows ready for refresh-heavy usage.",
                        checked = autoRefreshEnabled,
                        onCheckedChange = {
                            autoRefreshEnabled = it
                            prefs.setAutoRefreshEnabled(it)
                        }
                    )
                    SettingToggle(
                        title = "Testnet / Demo First",
                        description = "Recommended mode before any real execution enablement.",
                        checked = testnetOnlyEnabled,
                        onCheckedChange = {
                            testnetOnlyEnabled = it
                            prefs.setTestnetOnlyEnabled(it)
                        }
                    )
                    SettingToggle(
                        title = "Risk Disclaimer Accepted",
                        description = "Confirms you understand no profit is guaranteed and live trading carries serious risk.",
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
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("App Environment", style = MaterialTheme.typography.titleMedium)
                    Text("App Version: ${BuildConfig.VERSION_NAME}")
                    Text("API Base URL: ${AppConfig.apiBaseUrl}")
                    Text("WS Base URL: ${AppConfig.marketWsUrl}")
                    Text("Build Type aware configuration is ready for debug/release separation.")
                }
            }
        }
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Final Release Notes", style = MaterialTheme.typography.titleMedium)
                    Text("• Add google-services.json for full Firebase push")
                    Text("• Configure keystore.properties or environment variables for signing")
                    Text("• Keep ENABLE_LIVE_EXECUTION disabled until broker test passes")
                    Text("• Review docs/release_checklist_fa.md before publishing")
                    Text("• Review docs/deployment_guide_fa.md and docs/connector_setup_fa.md")
                    Text("• Use the System Readiness screen before real activation")
                }
            }
        }
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Launch Controls", style = MaterialTheme.typography.titleMedium)
                    Text("Open the readiness screen to verify Firebase, connectors, and production blockers.")
                    androidx.compose.material3.Button(onClick = onOpenReadiness) {
                        Text("Open System Readiness")
                    }
                }
            }
        }
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Risk Policy", style = MaterialTheme.typography.titleMedium)
                    Text("This app is an analysis and execution-support system, not a guarantee engine.")
                    Text("Always validate strategy quality with backtest, sweep, walk-forward and demo execution before live usage.")
                    Text("Large leverage and news volatility can invalidate otherwise good setups.")
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
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(title, style = MaterialTheme.typography.titleMedium)
        Text(description, style = MaterialTheme.typography.bodyMedium)
        Switch(checked = checked, onCheckedChange = onCheckedChange)
    }
}
