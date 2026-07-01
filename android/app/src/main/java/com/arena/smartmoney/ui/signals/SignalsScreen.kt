package com.arena.smartmoney.ui.signals

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.arena.smartmoney.util.NotificationHelper
import java.util.Locale

@Composable
fun SignalsScreen(
    onOpenJournal: () -> Unit,
    viewModel: SignalsViewModel = viewModel()
) {
    val state by viewModel.uiState.collectAsState()
    val context = LocalContext.current

    LaunchedEffect(state.notificationSignal?.id) {
        val signal = state.notificationSignal ?: return@LaunchedEffect
        if (signal.direction.lowercase(Locale.getDefault()) != "neutral" && signal.score >= 65.0) {
            NotificationHelper.showSignalNotification(
                context = context,
                title = "${signal.symbol} ${signal.direction.uppercase(Locale.getDefault())}",
                body = "Score ${signal.score} • ${signal.session_name}",
                id = signal.id
            )
        }
        viewModel.consumeNotification()
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Text("Signal Center", style = MaterialTheme.typography.headlineSmall)
            Text("Live scan + database history + local notifications")
        }
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Quick Live Scan", style = MaterialTheme.typography.titleMedium)
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.scanMarket("BTCUSDT", "crypto") }) { Text("BTC") }
                        Button(onClick = { viewModel.scanMarket("ETHUSDT", "crypto") }) { Text("ETH") }
                        Button(onClick = { viewModel.scanMarket("EURUSD", "forex") }) { Text("EURUSD") }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.scanMarket("XAUUSD", "forex") }) { Text("XAUUSD") }
                        Button(onClick = { viewModel.loadHistory() }) { Text(if (state.loading) "Loading..." else "Refresh") }
                        Button(onClick = onOpenJournal) { Text("Journal") }
                    }
                    if (state.scanMessage.isNotBlank()) Text(state.scanMessage)
                    if (state.journalMessage.isNotBlank()) Text(state.journalMessage)
                    state.error?.let { Text("Error: $it", color = MaterialTheme.colorScheme.error) }
                    Text("Note: forex live scan needs TwelveData API key on backend.")
                }
            }
        }
        items(state.items) { signal ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(signal.symbol, style = MaterialTheme.typography.titleMedium)
                    Text("${signal.direction.uppercase(Locale.getDefault())} • Score ${signal.score} • ${signal.timeframe}")
                    Text("Session: ${signal.session_name} • Confidence: ${signal.confidence}")
                    Text("Entry: ${signal.entry_low ?: "-"} - ${signal.entry_high ?: "-"}")
                    Text("SL: ${signal.stop_loss ?: "-"} • TP: ${signal.take_profits.joinToString()}")
                    if (signal.reasons.isNotEmpty()) {
                        Text(signal.reasons.joinToString(separator = " | "))
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.createTradeFromSignal(signal) }) {
                            Text("Add to Journal")
                        }
                        Button(onClick = onOpenJournal) {
                            Text("Open Journal")
                        }
                    }
                    Text("Saved: ${signal.created_at}")
                }
            }
        }
    }
}
