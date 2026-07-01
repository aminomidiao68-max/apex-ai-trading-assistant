package com.arena.smartmoney.ui.analytics

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

@Composable
fun AnalyticsScreen(viewModel: AnalyticsViewModel = viewModel()) {
    val state by viewModel.uiState.collectAsState()
    val report = state.report
    val summary = report?.summary

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Text("Analytics Center", style = MaterialTheme.typography.headlineSmall)
            Text("Signal quality, activity summary and journal performance")
        }
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = { viewModel.load() }) {
                        Text(if (state.loading) "Refreshing..." else "Refresh Analytics")
                    }
                    state.error?.let { Text("Error: $it", color = MaterialTheme.colorScheme.error) }
                    if (summary != null) {
                        Text("Saved Signals: ${summary.total_saved_signals}")
                        Text("Last 24h Signals: ${summary.recent_signals_24h}")
                        Text("Average Signal Score: ${summary.average_signal_score}")
                        Text("Buy/Sell/Neutral: ${summary.buy_signals} / ${summary.sell_signals} / ${summary.neutral_signals}")
                        Text("Recent Notification Events 7d: ${report.recent_notification_events_7d}")
                    }
                }
            }
        }
        summary?.let { data ->
            item {
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text("Journal Performance", style = MaterialTheme.typography.titleMedium)
                        Text("Total Trades: ${data.trade_stats.total_trades}")
                        Text("Open/Closed: ${data.trade_stats.open_trades} / ${data.trade_stats.closed_trades}")
                        Text("Win Rate: ${data.trade_stats.win_rate}%")
                        Text("Net PnL: ${data.trade_stats.net_pnl}")
                    }
                }
            }
            item {
                Text("Top Signal Symbols", style = MaterialTheme.typography.titleMedium)
            }
            items(data.top_signal_symbols) { item ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Row(
                        modifier = Modifier.padding(16.dp),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(item.symbol)
                        Text("Count: ${item.count}")
                    }
                }
            }
            item {
                Text("Signal Stats by Symbol", style = MaterialTheme.typography.titleMedium)
            }
            items(report.signal_stats_by_symbol) { item ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(item.symbol, style = MaterialTheme.typography.titleMedium)
                        Text("Signals: ${item.count}")
                        Text("Average Score: ${item.average_score}")
                    }
                }
            }
            item {
                Text("Trade Performance by Symbol", style = MaterialTheme.typography.titleMedium)
            }
            items(report.trade_performance_by_symbol) { item ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(item.symbol, style = MaterialTheme.typography.titleMedium)
                        Text("Trades: ${item.trade_count} • Wins/Losses: ${item.wins}/${item.losses}")
                        Text("Win Rate: ${item.win_rate}% • Net PnL: ${item.net_pnl}")
                    }
                }
            }
        }
    }
}
