package com.arena.smartmoney.ui.broker

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
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
import com.arena.smartmoney.ui.components.PremiumGlassCard
import com.arena.smartmoney.ui.components.PremiumScreenBackground
import com.arena.smartmoney.ui.components.PremiumSectionHeader
import com.arena.smartmoney.ui.components.premiumTextFieldColors
import com.arena.smartmoney.ui.components.premiumTextFieldStyle
import com.arena.smartmoney.ui.i18n.rememberTranslator

@Composable
fun BrokerScreen(viewModel: BrokerViewModel = viewModel()) {
    val state by viewModel.uiState.collectAsState()
    val readyCount = state.connectors.count { it.ready }
    val dryRunCount = state.connectors.count { it.mode.contains("dry", ignoreCase = true) }
    val t = rememberTranslator()

    PremiumScreenBackground {
        androidx.compose.foundation.lazy.LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                PremiumSectionHeader(
                    title = t("Broker & Exchange Lab", "آزمایشگاه بروکر و اکسچنج"),
                    subtitle = t(
                        "Execution remains protected by score threshold and server-side risk approval.",
                        "اجرا همچنان با آستانه امتیاز و تایید ریسک سمت سرور محافظت می‌شود."
                    )
                )
            }
            item {
                PremiumGlassCard {
                    Text(t("Execution Status", "وضعیت اجرا"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
                    Text(
                        if (state.liveExecutionEnabled) t("LIVE ENABLED", "اجرای زنده فعال است") else t("DRY RUN / SAFE MODE", "حالت امن / شبیه‌سازی"),
                        color = if (state.liveExecutionEnabled) Color(0xFF33E6A6) else Color(0xFFFFD27A),
                        fontWeight = FontWeight.Bold
                    )
                    Text(t("Ready Connectors", "کانکتورهای آماده") + ": $readyCount / ${state.connectors.size}", color = Color.White)
                    Text(t("Dry-run Connectors", "کانکتورهای شبیه‌سازی") + ": $dryRunCount", color = Color.White)
                    state.error?.let { Text(t("Error", "خطا") + ": $it", color = MaterialTheme.colorScheme.error) }
                    Button(onClick = viewModel::loadStatus, modifier = Modifier.fillMaxWidth()) {
                        Text(if (state.loading) t("Checking...", "در حال بررسی...") else t("Check Connector Status", "بررسی وضعیت کانکتورها"))
                    }
                }
            }
            item {
                PremiumGlassCard {
                    Text(t("Execution Preview & Dry-Run Lab", "پیش‌نمایش اجرا و آزمایشگاه شبیه‌سازی"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.selectConnector("binance_futures") }, modifier = Modifier.weight(1f)) { Text("Binance") }
                        OutlinedButton(onClick = { viewModel.selectConnector("bybit") }, modifier = Modifier.weight(1f)) { Text("Bybit") }
                    }
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedButton(onClick = { viewModel.selectConnector("oanda") }, modifier = Modifier.weight(1f)) { Text("OANDA") }
                        OutlinedButton(onClick = { viewModel.selectConnector("mt5") }, modifier = Modifier.weight(1f)) { Text("MT5") }
                        OutlinedButton(onClick = { viewModel.selectConnector("ctrader") }, modifier = Modifier.weight(1f)) { Text("cTrader") }
                    }
                    Text(t("Selected Connector", "کانکتور انتخاب‌شده") + ": ${state.selectedConnector}", color = Color(0xFF67ECFF), fontWeight = FontWeight.Bold)
                    OutlinedTextField(
                        value = state.symbol,
                        onValueChange = viewModel::updateSymbol,
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text(t("Symbol / Instrument", "نماد / ابزار")) },
                        shape = RoundedCornerShape(18.dp),
                        singleLine = true,
                        textStyle = premiumTextFieldStyle(),
                        colors = premiumTextFieldColors()
                    )
                    OutlinedTextField(
                        value = state.quantity,
                        onValueChange = viewModel::updateQuantity,
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text(t("Quantity / Units / Volume", "مقدار / واحد / حجم")) },
                        shape = RoundedCornerShape(18.dp),
                        singleLine = true,
                        textStyle = premiumTextFieldStyle(),
                        colors = premiumTextFieldColors()
                    )
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.updateSide("buy") }, modifier = Modifier.weight(1f)) { Text(t("BUY", "خرید")) }
                        OutlinedButton(onClick = { viewModel.updateSide("sell") }, modifier = Modifier.weight(1f)) { Text(t("SELL", "فروش")) }
                    }
                    Text(t("Current Side", "سمت فعلی") + ": ${state.side.uppercase()}", color = Color.White)
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.previewSelectedConnector() }, modifier = Modifier.weight(1f)) { Text(t("Preview Route", "پیش‌نمایش مسیر")) }
                        Button(onClick = { viewModel.executeSelectedConnector() }, modifier = Modifier.weight(1f)) { Text(t("Execute / Dry-Run", "اجرا / شبیه‌سازی")) }
                    }
                    state.preview?.let { preview ->
                        Text(t("Preview Result", "نتیجه پیش‌نمایش"), style = MaterialTheme.typography.titleMedium, color = Color.White, fontWeight = FontWeight.Bold)
                        Text(t("Route", "مسیر") + ": ${preview.route}", color = Color.White)
                        Text(t("Eligible", "مجاز") + ": ${preview.eligible}", color = Color.White)
                        Text(t("Mode", "حالت") + ": ${preview.mode}", color = Color.White)
                        Text(t("Payload", "پِی‌لود") + ": ${preview.preview_payload}", color = Color(0xFFBCEEFF))
                        if (preview.warnings.isNotEmpty()) preview.warnings.forEach { warning -> Text("• $warning", color = Color(0xFFFFD27A)) }
                    }
                    state.executionResult?.let { result ->
                        Text(t("Execution Result", "نتیجه اجرا"), style = MaterialTheme.typography.titleMedium, color = Color.White, fontWeight = FontWeight.Bold)
                        Text("OK: ${result.ok}", color = Color.White)
                        Text(t("Mode", "حالت") + ": ${result.mode ?: "-"}", color = Color.White)
                        Text(t("Exchange", "صرافی") + ": ${result.exchange ?: "-"}", color = Color.White)
                        Text(t("Reason", "دلیل") + ": ${result.reason ?: "-"}", color = Color.White)
                        result.payload?.let { Text(t("Payload", "پِی‌لود") + ": $it", color = Color(0xFFBCEEFF)) }
                        result.request?.let { Text(t("Request", "درخواست") + ": $it", color = Color(0xFFBCEEFF)) }
                    }
                }
            }
            item {
                Text(t("Connector Capabilities", "قابلیت‌های کانکتورها"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
            }
            items(state.capabilities) { capability ->
                PremiumGlassCard {
                    Text(capability.connector, style = MaterialTheme.typography.titleMedium, color = Color.White, fontWeight = FontWeight.Bold)
                    Text(t("Market", "بازار") + ": ${capability.market_type}", color = Color.White)
                    Text(t("Maturity", "بلوغ") + ": ${capability.maturity}", color = Color.White)
                    Text(t("Live Route", "مسیر زنده") + ": ${capability.supports_live_route}", color = Color.White)
                    Text(t("Status API", "API وضعیت") + ": ${capability.status_endpoint}", color = Color.White)
                    Text(t("Execution API", "API اجرا") + ": ${capability.execution_endpoint ?: "-"}", color = Color.White)
                    capability.notes.forEach { note -> Text("• $note", color = Color(0xFFDDF8FF)) }
                }
            }
            item {
                Text(t("Connector Status Details", "جزئیات وضعیت کانکتورها"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
            }
            items(state.connectors) { connector ->
                PremiumGlassCard {
                    Text(connector.connector, style = MaterialTheme.typography.titleMedium, color = Color.White, fontWeight = FontWeight.Bold)
                    Text(t("Ready", "آماده") + ": ${connector.ready}", color = Color.White)
                    Text(t("Mode", "حالت") + ": ${connector.mode}", color = Color.White)
                    connector.notes.forEach { note -> Text("• $note", color = Color(0xFFDDF8FF)) }
                }
            }
        }
    }
}
