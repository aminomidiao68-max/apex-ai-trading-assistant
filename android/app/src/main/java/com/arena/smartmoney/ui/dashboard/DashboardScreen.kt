package com.arena.smartmoney.ui.dashboard

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
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
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import java.util.Locale

@Composable
fun DashboardScreen(
    onOpenBacktest: () -> Unit,
    onOpenAnalytics: () -> Unit,
    viewModel: DashboardViewModel = viewModel()
) {
    val state by viewModel.uiState.collectAsState()

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Text("APEX AI", style = MaterialTheme.typography.headlineSmall)
            Text("Live Dashboard", style = MaterialTheme.typography.titleMedium)
        }
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("Current Session", style = MaterialTheme.typography.titleMedium)
                    Spacer(Modifier.height(8.dp))
                    Text("Session: ${state.sessionName}")
                    Text("Quality: ${state.marketQuality}")
                    Text("Score: ${state.sessionScore}")
                    if (state.error != null) {
                        Spacer(Modifier.height(8.dp))
                        Text("Mode: Demo (${state.error})")
                    }
                    Spacer(Modifier.height(8.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.refreshAll() }) {
                            Text(if (state.loading) "Refreshing..." else "Refresh Live Data")
                        }
                        Button(onClick = onOpenBacktest) {
                            Text("Backtest Lab")
                        }
                        Button(onClick = onOpenAnalytics) {
                            Text("Analytics")
                        }
                    }
                }
            }
        }
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Live Market Stream", style = MaterialTheme.typography.titleMedium)
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.selectStreamSymbol("BTCUSDT") }) { Text("BTC") }
                        Button(onClick = { viewModel.selectStreamSymbol("ETHUSDT") }) { Text("ETH") }
                        Button(onClick = { viewModel.selectStreamSymbol("EURUSD") }) { Text("EURUSD") }
                        Button(onClick = { viewModel.selectStreamSymbol("XAUUSD") }) { Text("XAU") }
                    }
                    Button(onClick = { viewModel.reconnectStream() }) { Text("Reconnect Stream") }
                    val live = state.liveSnapshot
                    Text("Symbol: ${state.streamSymbol}")
                    Text("Stream Status: ${state.streamStatus}")
                    live?.let {
                        Text(
                            "Live Price: ${it.last_price ?: "-"} • 24h: ${it.change_pct ?: "-"}%",
                            color = when {
                                (it.change_pct ?: 0.0) > 0 -> Color(0xFF2ECC71)
                                (it.change_pct ?: 0.0) < 0 -> Color(0xFFE74C3C)
                                else -> MaterialTheme.colorScheme.onSurface
                            }
                        )
                        it.error?.let { message ->
                            Text("Stream Error: $message", color = MaterialTheme.colorScheme.error)
                        }
                    }
                }
            }
        }
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("Trading Journal Summary", style = MaterialTheme.typography.titleMedium)
                    Spacer(Modifier.height(8.dp))
                    val stats = state.tradeStats
                    Text("Total Trades: ${stats?.total_trades ?: 0}")
                    Text("Open Trades: ${stats?.open_trades ?: 0}")
                    Text("Closed Trades: ${stats?.closed_trades ?: 0}")
                    Text("Wins/Losses: ${stats?.wins ?: 0} / ${stats?.losses ?: 0}")
                    Text("Win Rate: ${stats?.win_rate ?: 0.0}%")
                    Text("Net PnL: ${stats?.net_pnl ?: 0.0}")
                }
            }
        }
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("Professional Risk Rules", style = MaterialTheme.typography.titleMedium)
                    Spacer(Modifier.height(8.dp))
                    Text("• Fixed risk per trade")
                    Text("• Daily loss limit")
                    Text("• Max consecutive losses")
                    Text("• Max simultaneous positions")
                    Text("• Breakeven & partial TP planning")
                }
            }
        }
        item {
            Text("Live Watchlist", style = MaterialTheme.typography.titleMedium)
        }
        val listToShow = if (state.watchlist.isEmpty()) {
            state.watchlistSymbols.map {
                com.arena.smartmoney.data.model.MarketOverviewItem(
                    symbol = it,
                    market = if (it.endsWith("USDT")) "crypto" else "forex",
                    last_price = null,
                    change_pct = null,
                    source = "offline",
                    status = "waiting_for_backend"
                )
            }
        } else state.watchlist

        items(listToShow) { item ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Row(modifier = Modifier.padding(16.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                    Column {
                        Text(item.symbol, style = MaterialTheme.typography.titleMedium)
                        Text("${item.market.uppercase(Locale.getDefault())} • ${item.source}")
                        Text("Status: ${item.status}")
                    }
                    Column {
                        Text("Price: ${item.last_price?.toString() ?: "-"}")
                        Text("24h: ${item.change_pct?.toString() ?: "-"}%")
                    }
                }
            }
        }
    }
}
