package com.arena.smartmoney.ui.risk

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
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
fun RiskCalculatorScreen(viewModel: RiskCalculatorViewModel = viewModel()) {
    val state by viewModel.uiState.collectAsState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Text("Professional Risk Manager", style = MaterialTheme.typography.headlineSmall)
        Text("Position size, max loss, breakeven and partial TP planning")

        OutlinedTextField(
            value = state.entry,
            onValueChange = viewModel::onEntryChange,
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Entry Price") }
        )
        OutlinedTextField(
            value = state.stop,
            onValueChange = viewModel::onStopChange,
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Stop Loss") }
        )
        OutlinedTextField(
            value = state.balance,
            onValueChange = viewModel::onBalanceChange,
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Account Balance") }
        )
        OutlinedTextField(
            value = state.riskPct,
            onValueChange = viewModel::onRiskPctChange,
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Risk % per Trade") }
        )

        Button(onClick = viewModel::calculate, modifier = Modifier.fillMaxWidth()) {
            Text(if (state.loading) "Calculating..." else "Calculate")
        }

        state.error?.let {
            Text(it)
        }

        state.result?.let { result ->
            Spacer(Modifier.height(8.dp))
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("Trade Allowed: ${result.is_trade_allowed}")
                    Text("Risk Amount: ${result.risk_amount}")
                    Text("Position Size Units: ${result.position_size_units}")
                    Text("Stop Distance: ${result.stop_distance}")
                    Text("Breakeven RR: ${result.breakeven_rr}")
                    Text("Partial TPs: ${result.partial_take_profit_rr.joinToString()}")
                    if (result.warnings.isNotEmpty()) {
                        Text("Warnings: ${result.warnings.joinToString()}")
                    }
                }
            }
        }
    }
}
