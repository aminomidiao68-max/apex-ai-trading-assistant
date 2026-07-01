package com.arena.smartmoney.ui.journal

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
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import java.util.Locale

@Composable
fun JournalScreen(viewModel: JournalViewModel = viewModel()) {
    val state by viewModel.uiState.collectAsState()
    val filteredItems = when (state.filter) {
        "open" -> state.items.filter { it.status == "open" }
        "closed" -> state.items.filter { it.status == "closed" }
        else -> state.items
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Text("Trade Journal", style = MaterialTheme.typography.headlineSmall)
            Text("Track open and closed trades from saved signals")
        }
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    val stats = state.stats
                    Text("Total: ${stats?.total_trades ?: 0}")
                    Text("Open: ${stats?.open_trades ?: 0} • Closed: ${stats?.closed_trades ?: 0}")
                    Text("Wins: ${stats?.wins ?: 0} • Losses: ${stats?.losses ?: 0}")
                    Text("Win Rate: ${stats?.win_rate ?: 0.0}%")
                    Text("Net PnL: ${stats?.net_pnl ?: 0.0}")
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.setFilter("all") }) { Text("All") }
                        Button(onClick = { viewModel.setFilter("open") }) { Text("Open") }
                        Button(onClick = { viewModel.setFilter("closed") }) { Text("Closed") }
                        Button(onClick = { viewModel.refresh() }) {
                            Text(if (state.loading) "Refreshing..." else "Refresh")
                        }
                    }
                    if (state.message.isNotBlank()) Text(state.message)
                    state.error?.let { Text("Error: $it", color = MaterialTheme.colorScheme.error) }
                }
            }
        }
        items(filteredItems) { trade ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("${trade.symbol} • ${trade.direction.uppercase(Locale.getDefault())}", style = MaterialTheme.typography.titleMedium)
                    Text("Status: ${trade.status}")
                    Text("Entry: ${trade.entry_price} • SL: ${trade.stop_loss} • TP: ${trade.take_profit ?: "-"}")
                    Text("Size: ${trade.size} • PnL: ${trade.pnl_amount ?: 0.0}")
                    if (trade.notes.isNotBlank()) Text("Notes: ${trade.notes}")
                    if (trade.status == "open") {
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            if (trade.take_profit != null) {
                                Button(onClick = { viewModel.closeTradeAsWin(trade) }) { Text("Close TP") }
                            }
                            Button(onClick = { viewModel.closeTradeAsLoss(trade) }) { Text("Close SL") }
                        }
                    }
                }
            }
        }
    }
}
