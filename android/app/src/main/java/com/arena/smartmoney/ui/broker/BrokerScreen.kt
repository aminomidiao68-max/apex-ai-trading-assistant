package com.arena.smartmoney.ui.broker

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel

@Composable
fun BrokerScreen(viewModel: BrokerViewModel = viewModel()) {
    val state by viewModel.uiState.collectAsState()
    val readyCount = state.connectors.count { it.ready }
    val dryRunCount = state.connectors.count { it.mode.contains("dry", ignoreCase = true) }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Text("Broker & Exchange Connectors", style = MaterialTheme.typography.headlineSmall)
            Text("Live execution is protected by score threshold and server-side risk approval.")
        }
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("Execution Mode", style = MaterialTheme.typography.titleMedium)
                    Spacer(Modifier.height(8.dp))
                    Text(if (state.liveExecutionEnabled) "LIVE ENABLED" else "DRY RUN / SAFE MODE")
                    Text("Ready connectors: $readyCount / ${state.connectors.size}")
                    Text("Dry-run connectors: $dryRunCount")
                    state.error?.let { Text("Error: $it") }
                    Spacer(Modifier.height(8.dp))
                    Button(onClick = viewModel::loadStatus) {
                        Text(if (state.loading) "Checking..." else "Check Connector Status")
                    }
                }
            }
        }
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("Connector Roadmap", style = MaterialTheme.typography.titleMedium)
                    Text("• Binance Futures and OANDA have execution endpoints available now")
                    Text("• Bybit order route is enabled on the backend when credentials are present")
                    Text("• MT5 and cTrader foundations are ready for bridge/API integration")
                    Text("• Always test on testnet/demo before enabling live execution")
                }
            }
        }
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Execution Preview & Dry-Run Lab", style = MaterialTheme.typography.titleMedium)
                    Button(onClick = { viewModel.selectConnector("binance_futures") }) { Text("Select Binance Futures") }
                    Button(onClick = { viewModel.selectConnector("bybit") }) { Text("Select Bybit") }
                    Button(onClick = { viewModel.selectConnector("oanda") }) { Text("Select OANDA") }
                    Button(onClick = { viewModel.selectConnector("mt5") }) { Text("Select MT5") }
                    Button(onClick = { viewModel.selectConnector("ctrader") }) { Text("Select cTrader") }
                    Text("Selected: ${state.selectedConnector}")
                    OutlinedTextField(
                        value = state.symbol,
                        onValueChange = viewModel::updateSymbol,
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text("Symbol / Instrument") }
                    )
                    OutlinedTextField(
                        value = state.quantity,
                        onValueChange = viewModel::updateQuantity,
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text("Quantity / Units / Volume") }
                    )
                    Button(onClick = { viewModel.updateSide("buy") }) { Text("Side: BUY") }
                    Button(onClick = { viewModel.updateSide("sell") }) { Text("Side: SELL") }
                    Text("Current side: ${state.side}")
                    Button(onClick = { viewModel.previewSelectedConnector() }) { Text("Preview Order Route") }
                    Button(onClick = { viewModel.executeSelectedConnector() }) { Text("Execute / Dry-Run") }
                    state.preview?.let { preview ->
                        Text("Preview Route: ${preview.route}")
                        Text("Eligible: ${preview.eligible} • Mode: ${preview.mode}")
                        Text("Payload Preview: ${preview.preview_payload}")
                        if (preview.warnings.isNotEmpty()) {
                            preview.warnings.forEach { warning -> Text("• $warning") }
                        }
                    }
                    state.executionResult?.let { result ->
                        Text("Execution Result")
                        Text("OK: ${result.ok}")
                        Text("Mode: ${result.mode ?: "-"}")
                        Text("Exchange: ${result.exchange ?: "-"}")
                        Text("Reason: ${result.reason ?: "-"}")
                        result.payload?.let { Text("Payload: $it") }
                        result.request?.let { Text("Request: $it") }
                    }
                }
            }
        }
        item {
            Text("Connector Capabilities", style = MaterialTheme.typography.titleMedium)
        }
        items(state.capabilities) { capability ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(capability.connector, style = MaterialTheme.typography.titleMedium)
                    Text("Market: ${capability.market_type}")
                    Text("Maturity: ${capability.maturity}")
                    Text("Live Route: ${capability.supports_live_route}")
                    Text("Status API: ${capability.status_endpoint}")
                    Text("Execution API: ${capability.execution_endpoint ?: "-"}")
                    capability.notes.forEach { note ->
                        Text("• $note")
                    }
                }
            }
        }
        item {
            Text("Connector Status Details", style = MaterialTheme.typography.titleMedium)
        }
        items(state.connectors) { connector ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(connector.connector, style = MaterialTheme.typography.titleMedium)
                    Text("Ready: ${connector.ready}")
                    Text("Mode: ${connector.mode}")
                    connector.notes.forEach { note ->
                        Text("• $note")
                    }
                }
            }
        }
    }
}
