package com.arena.smartmoney.ui.broker

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.weight
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.arena.smartmoney.ui.i18n.rememberTranslator

@Composable
fun BrokerScreen(viewModel: BrokerViewModel = viewModel()) {
    val state by viewModel.uiState.collectAsState()
    val readyCount = state.connectors.count { it.ready }
    val dryRunCount = state.connectors.count { it.mode.contains("dry", ignoreCase = true) }
    val t = rememberTranslator()

    androidx.compose.foundation.lazy.LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Text(
                t("Broker & Exchange Lab", "آزمایشگاه بروکر و اکسچنج"),
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold
            )
            Text(
                t(
                    "Execution remains protected by score threshold and server-side risk approval.",
                    "اجرا همچنان با آستانه امتیاز و تایید ریسک سمت سرور محافظت می‌شود."
                )
            )
        }
        item {
            Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(22.dp)) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(t("Execution Status", "وضعیت اجرا"), style = MaterialTheme.typography.titleLarge)
                    Text(
                        if (state.liveExecutionEnabled) {
                            t("LIVE ENABLED", "اجرای زنده فعال است")
                        } else {
                            t("DRY RUN / SAFE MODE", "حالت امن / شبیه‌سازی")
                        },
                        color = if (state.liveExecutionEnabled) Color(0xFF2ECC71) else Color(0xFFFFC857)
                    )
                    Text(t("Ready Connectors", "کانکتورهای آماده") + ": $readyCount / ${state.connectors.size}")
                    Text(t("Dry-run Connectors", "کانکتورهای شبیه‌سازی") + ": $dryRunCount")
                    state.error?.let {
                        Text(t("Error", "خطا") + ": $it", color = MaterialTheme.colorScheme.error)
                    }
                    Button(onClick = viewModel::loadStatus, modifier = Modifier.fillMaxWidth()) {
                        Text(if (state.loading) t("Checking...", "در حال بررسی...") else t("Check Connector Status", "بررسی وضعیت کانکتورها"))
                    }
                }
            }
        }
        item {
            Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(22.dp)) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Text(t("Connector Roadmap", "نقشه راه کانکتورها"), style = MaterialTheme.typography.titleLarge)
                    Text("• " + t("Binance Futures and OANDA execution endpoints are available now", "اندپوینت‌های اجرای Binance Futures و OANDA اکنون آماده هستند"))
                    Text("• " + t("Bybit route is ready when credentials exist", "مسیر Bybit در صورت وجود اطلاعات ورود آماده است"))
                    Text("• " + t("MT5 and cTrader foundations are prepared for bridge / API integration", "زیرساخت MT5 و cTrader برای اتصال Bridge / API آماده است"))
                    Text("• " + t("Always test on testnet or demo before any live usage", "همیشه قبل از استفاده واقعی روی تست‌نت یا دمو تست بگیر"))
                }
            }
        }
        item {
            Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(22.dp)) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Text(t("Execution Preview & Dry-Run Lab", "پیش‌نمایش اجرا و آزمایشگاه شبیه‌سازی"), style = MaterialTheme.typography.titleLarge)
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.selectConnector("binance_futures") }, modifier = Modifier.weight(1f)) { Text("Binance") }
                        Button(onClick = { viewModel.selectConnector("bybit") }, modifier = Modifier.weight(1f)) { Text("Bybit") }
                    }
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.selectConnector("oanda") }, modifier = Modifier.weight(1f)) { Text("OANDA") }
                        Button(onClick = { viewModel.selectConnector("mt5") }, modifier = Modifier.weight(1f)) { Text("MT5") }
                        Button(onClick = { viewModel.selectConnector("ctrader") }, modifier = Modifier.weight(1f)) { Text("cTrader") }
                    }
                    Text(t("Selected Connector", "کانکتور انتخاب‌شده") + ": ${state.selectedConnector}")
                    OutlinedTextField(
                        value = state.symbol,
                        onValueChange = viewModel::updateSymbol,
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text(t("Symbol / Instrument", "نماد / ابزار")) }
                    )
                    OutlinedTextField(
                        value = state.quantity,
                        onValueChange = viewModel::updateQuantity,
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text(t("Quantity / Units / Volume", "مقدار / واحد / حجم")) }
                    )
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.updateSide("buy") }, modifier = Modifier.weight(1f)) {
                            Text(t("BUY", "خرید"))
                        }
                        Button(onClick = { viewModel.updateSide("sell") }, modifier = Modifier.weight(1f)) {
                            Text(t("SELL", "فروش"))
                        }
                    }
                    Text(t("Current Side", "سمت فعلی") + ": ${state.side.uppercase()}")
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.previewSelectedConnector() }, modifier = Modifier.weight(1f)) {
                            Text(t("Preview Route", "پیش‌نمایش مسیر"))
                        }
                        Button(onClick = { viewModel.executeSelectedConnector() }, modifier = Modifier.weight(1f)) {
                            Text(t("Execute / Dry-Run", "اجرا / شبیه‌سازی"))
                        }
                    }
                    state.preview?.let { preview ->
                        Text(t("Preview Result", "نتیجه پیش‌نمایش"), style = MaterialTheme.typography.titleMedium)
                        Text(t("Route", "مسیر") + ": ${preview.route}")
                        Text(t("Eligible", "مجاز") + ": ${preview.eligible}")
                        Text(t("Mode", "حالت") + ": ${preview.mode}")
                        Text(t("Payload", "پِی‌لود") + ": ${preview.preview_payload}")
                        if (preview.warnings.isNotEmpty()) {
                            preview.warnings.forEach { warning ->
                                Text("• $warning")
                            }
                        }
                    }
                    state.executionResult?.let { result ->
                        Text(t("Execution Result", "نتیجه اجرا"), style = MaterialTheme.typography.titleMedium)
                        Text("OK: ${result.ok}")
                        Text(t("Mode", "حالت") + ": ${result.mode ?: "-"}")
                        Text(t("Exchange", "صرافی") + ": ${result.exchange ?: "-"}")
                        Text(t("Reason", "دلیل") + ": ${result.reason ?: "-"}")
                        result.payload?.let { Text(t("Payload", "پِی‌لود") + ": $it") }
                        result.request?.let { Text(t("Request", "درخواست") + ": $it") }
                    }
                }
            }
        }
        item {
            Text(t("Connector Capabilities", "قابلیت‌های کانکتورها"), style = MaterialTheme.typography.titleLarge)
        }
        items(state.capabilities.size) { index ->
            val capability = state.capabilities[index]
            Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(18.dp)) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Text(capability.connector, style = MaterialTheme.typography.titleMedium)
                    Text(t("Market", "بازار") + ": ${capability.market_type}")
                    Text(t("Maturity", "بلوغ") + ": ${capability.maturity}")
                    Text(t("Live Route", "مسیر زنده") + ": ${capability.supports_live_route}")
                    Text(t("Status API", "API وضعیت") + ": ${capability.status_endpoint}")
                    Text(t("Execution API", "API اجرا") + ": ${capability.execution_endpoint ?: "-"}")
                    capability.notes.forEach { note -> Text("• $note") }
                }
            }
        }
        item {
            Text(t("Connector Status Details", "جزئیات وضعیت کانکتورها"), style = MaterialTheme.typography.titleLarge)
        }
        items(state.connectors.size) { index ->
            val connector = state.connectors[index]
            Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(18.dp)) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Text(connector.connector, style = MaterialTheme.typography.titleMedium)
                    Text(t("Ready", "آماده") + ": ${connector.ready}")
                    Text(t("Mode", "حالت") + ": ${connector.mode}")
                    connector.notes.forEach { note -> Text("• $note") }
                }
            }
        }
    }
}
