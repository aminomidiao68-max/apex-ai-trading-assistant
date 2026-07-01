package com.arena.smartmoney.ui.readiness

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel

@Composable
fun ReadinessScreen(viewModel: ReadinessViewModel = viewModel()) {
    val state by viewModel.uiState.collectAsState()
    val readiness = state.readiness

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Text("System Readiness", style = MaterialTheme.typography.headlineSmall)
            Text("Production and live-activation readiness overview")
        }
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = { viewModel.load() }) {
                        Text(if (state.loading) "Refreshing..." else "Refresh Readiness")
                    }
                    state.error?.let { Text("Error: $it", color = MaterialTheme.colorScheme.error) }
                    readiness?.let {
                        val color = when (it.overall_status) {
                            "ready" -> Color(0xFF2ECC71)
                            "partial" -> Color(0xFFFFC857)
                            else -> Color(0xFFE74C3C)
                        }
                        Text("Overall Status: ${it.overall_status}", color = color)
                        Text("Ready: ${it.ready_count} • Warning: ${it.warning_count} • Missing: ${it.missing_count}")
                    }
                }
            }
        }
        readiness?.let { data ->
            items(data.items) { item ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(item.key, style = MaterialTheme.typography.titleMedium)
                        Text("Category: ${item.category}")
                        Text(
                            "Status: ${item.status}",
                            color = when (item.status) {
                                "ready" -> Color(0xFF2ECC71)
                                "warning" -> Color(0xFFFFC857)
                                else -> Color(0xFFE74C3C)
                            }
                        )
                        Text(item.message)
                    }
                }
            }
        }
    }
}
