package com.arena.smartmoney.ui.broker

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
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
import androidx.compose.ui.graphics.Brush
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
import java.util.Locale

@Composable
fun BrokerScreen(viewModel: BrokerViewModel = viewModel()) {
    val state by viewModel.uiState.collectAsState()
    val readyCount = state.connectors.count { it.ready }
    val dryRunCount = state.connectors.count { it.mode.contains("dry", ignoreCase = true) }
    val t = rememberTranslator()

    val selectedCapability = state.capabilities.firstOrNull { it.connector == state.selectedConnector }
    val selectedConnectorStatus = state.connectors.firstOrNull { it.connector == state.selectedConnector }
    val readinessLabel = brokerReadinessLabel(
        liveEnabled = state.liveExecutionEnabled,
        connectorReady = selectedConnectorStatus?.ready == true,
        previewEligible = state.preview?.eligible == true,
        t = t,
    )
    val routeLabel = state.preview?.route ?: selectedCapability?.execution_endpoint ?: "-"
    val riskGateLabel = when {
        state.preview?.warnings?.any { it.contains("threshold", ignoreCase = true) } == true -> t("Score blocked", "مسدود به‌خاطر امتیاز")
        state.preview?.warnings?.any { it.contains("Risk engine", ignoreCase = true) } == true -> t("Risk blocked", "مسدود به‌خاطر ریسک")
        state.preview?.eligible == true -> t("Eligible", "مجاز")
        else -> t("Waiting", "در انتظار")
    }

    PremiumScreenBackground {
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                PremiumSectionHeader(
                    title = t("Broker Execution Pro", "اجرای حرفه‌ای بروکر"),
                    subtitle = t(
                        "Execution remains protected by score threshold, route preview and server-side risk approval.",
                        "اجرا همچنان با آستانه امتیاز، پیش‌نمایش مسیر و تایید ریسک سمت سرور محافظت می‌شود."
                    )
                )
            }
            item {
                PremiumGlassCard {
                    Text(t("Execution Command Board", "برد فرمان اجرا"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        BrokerChip(t("Readiness", "آمادگی"), readinessLabel, Modifier.weight(1f))
                        BrokerChip(t("Connector", "کانکتور"), readyCount.toString() + "/" + state.connectors.size, Modifier.weight(1f))
                        BrokerChip(t("Dry Mode", "حالت خشک"), dryRunCount.toString(), Modifier.weight(1f))
                    }
                    Text(
                        if (state.liveExecutionEnabled) t("LIVE ENABLED", "اجرای زنده فعال است") else t("DRY RUN / SAFE MODE", "حالت امن / شبیه‌سازی"),
                        color = if (state.liveExecutionEnabled) Color(0xFF33E6A6) else Color(0xFFFFD27A),
                        fontWeight = FontWeight.Bold
                    )
                    Text(t("Selected Route", "مسیر انتخابی") + ": $routeLabel", color = Color(0xFFBCEEFF))
                    Text(t("Risk Gate", "گیت ریسک") + ": $riskGateLabel", color = Color.White)
                    state.error?.let { Text(t("Error", "خطا") + ": $it", color = MaterialTheme.colorScheme.error) }
                    Button(onClick = viewModel::loadStatus, modifier = Modifier.fillMaxWidth()) {
                        Text(if (state.loading) t("Checking...", "در حال بررسی...") else t("Check Connector Status", "بررسی وضعیت کانکتورها"))
                    }
                }
            }
            item {
                PremiumGlassCard {
                    Text(t("Connector Selection", "انتخاب کانکتور"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        ConnectorPickButton("binance_futures", "Binance", state.selectedConnector, Modifier.weight(1f)) { viewModel.selectConnector("binance_futures") }
                        ConnectorPickButton("bybit", "Bybit", state.selectedConnector, Modifier.weight(1f)) { viewModel.selectConnector("bybit") }
                    }
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        ConnectorPickButton("oanda", "OANDA", state.selectedConnector, Modifier.weight(1f)) { viewModel.selectConnector("oanda") }
                        ConnectorPickButton("mt5", "MT5", state.selectedConnector, Modifier.weight(1f)) { viewModel.selectConnector("mt5") }
                        ConnectorPickButton("ctrader", "cTrader", state.selectedConnector, Modifier.weight(1f)) { viewModel.selectConnector("ctrader") }
                    }
                    Text(t("Selected Connector", "کانکتور انتخاب‌شده") + ": ${state.selectedConnector}", color = Color(0xFF67ECFF), fontWeight = FontWeight.Bold)
                    selectedCapability?.let {
                        Text(t("Maturity", "بلوغ") + ": ${it.maturity}", color = Color.White)
                        Text(t("Live Route", "مسیر زنده") + ": ${it.supports_live_route}", color = Color.White)
                    }
                }
            }
            item {
                PremiumGlassCard {
                    Text(t("Execution Preview Lab", "آزمایشگاه پیش‌نمایش اجرا"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
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
                        SideButton(state.side == "buy", t("BUY", "خرید"), Modifier.weight(1f)) { viewModel.updateSide("buy") }
                        SideButton(state.side == "sell", t("SELL", "فروش"), Modifier.weight(1f)) { viewModel.updateSide("sell") }
                    }
                    Text(t("Current Side", "سمت فعلی") + ": ${state.side.uppercase(Locale.getDefault())}", color = Color.White)
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.previewSelectedConnector() }, modifier = Modifier.weight(1f)) { Text(t("Preview Route", "پیش‌نمایش مسیر")) }
                        Button(onClick = { viewModel.executeSelectedConnector() }, modifier = Modifier.weight(1f)) { Text(t("Execute / Dry-Run", "اجرا / شبیه‌سازی")) }
                    }
                    state.preview?.let { preview ->
                        PremiumGlassCard(borderColor = Color(0x4059C7FF)) {
                            Text(t("Preview Result", "نتیجه پیش‌نمایش"), style = MaterialTheme.typography.titleMedium, color = Color.White, fontWeight = FontWeight.Bold)
                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                BrokerChip(t("Eligible", "مجاز"), preview.eligible.toString(), Modifier.weight(1f))
                                BrokerChip(t("Mode", "حالت"), preview.mode, Modifier.weight(1f))
                                BrokerChip(t("Live", "زنده"), preview.live_execution_enabled.toString(), Modifier.weight(1f))
                            }
                            Text(t("Route", "مسیر") + ": ${preview.route}", color = Color.White)
                            Text(t("Payload", "پِی‌لود") + ": ${preview.preview_payload}", color = Color(0xFFBCEEFF))
                            if (preview.warnings.isNotEmpty()) preview.warnings.forEach { warning -> Text("• $warning", color = Color(0xFFFFD27A)) }
                        }
                    }
                    state.executionResult?.let { result ->
                        PremiumGlassCard(borderColor = Color(0x4033E6A6)) {
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
            }
            item {
                PremiumGlassCard(borderColor = Color(0x4059C7FF)) {
                    Text(
                        t("Paper OMS Command", "فرماندهی سفارش شبیه‌سازی"),
                        style = MaterialTheme.typography.titleLarge,
                        color = Color.White,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        t(
                            "Paper orders use an isolated event ledger and never route to a broker.",
                            "سفارش‌های شبیه‌سازی در دفتر رویداد مستقل ثبت می‌شوند و هرگز به بروکر ارسال نمی‌شوند."
                        ),
                        color = Color(0xFFBCEEFF)
                    )
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        BrokerChip(
                            t("Paper", "شبیه‌سازی"),
                            if (state.paperControl?.paper_trading_enabled == true) t("Enabled", "فعال") else t("Disabled", "خاموش"),
                            Modifier.weight(1f)
                        )
                        BrokerChip(
                            t("Kill Switch", "کلید توقف"),
                            if (state.paperControl?.kill_switch_engaged != false) t("Engaged", "درگیر") else t("Released", "آزاد"),
                            Modifier.weight(1f)
                        )
                        BrokerChip(
                            t("Live Routed", "ارسال زنده"),
                            "FALSE",
                            Modifier.weight(1f)
                        )
                    }
                    state.paperFeedStatus?.let { feed ->
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            BrokerChip(
                                t("Auto Feed", "خوراک خودکار"),
                                if (feed.automated_feed_enabled) t("Enabled", "فعال") else t("Disabled", "خاموش"),
                                Modifier.weight(1f)
                            )
                            BrokerChip(t("Provider", "منبع"), feed.providers.firstOrNull() ?: "OKX", Modifier.weight(1f))
                            BrokerChip(t("Real Quote", "قیمت واقعی"), feed.is_real_market_quote.toString(), Modifier.weight(1f))
                        }
                        Text(
                            t("Subscriptions / Due", "اشتراک / آماده پردازش") +
                                ": ${feed.subscription_count} / ${feed.due_subscription_count}",
                            color = Color(0xFFBCEEFF)
                        )
                        feed.latest_error_code?.let { code ->
                            Text(t("Feed error", "خطای خوراک") + ": $code", color = Color(0xFFFFD27A))
                        }
                    }
                    state.paperFeedSubscriptions.firstOrNull { it.symbol == state.symbol.uppercase() }?.let { subscription ->
                        Text(
                            "${subscription.symbol} • ${subscription.provider} • ${if (subscription.enabled) "ACTIVE" else "DISABLED"} • failures ${subscription.consecutive_failures}",
                            color = Color.White
                        )
                        Text(
                            t("Last real quote", "آخرین قیمت واقعی") + ": ${subscription.last_success_at ?: "-"}",
                            color = Color(0xFFBCEEFF)
                        )
                    }
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedButton(
                            onClick = viewModel::subscribeCurrentSymbolToPaperFeed,
                            enabled = state.paperControl?.paper_trading_enabled == true &&
                                state.paperControl?.kill_switch_engaged == false,
                            modifier = Modifier.weight(1f)
                        ) { Text(t("Subscribe", "اشتراک قیمت")) }
                        Button(
                            onClick = viewModel::enableAutomatedFeed,
                            enabled = state.paperControl?.paper_trading_enabled == true &&
                                state.paperControl?.kill_switch_engaged == false,
                            modifier = Modifier.weight(1f)
                        ) { Text(t("Auto ON", "خودکار روشن")) }
                        OutlinedButton(
                            onClick = viewModel::syncPaperFeedNow,
                            enabled = state.paperControl?.automated_feed_enabled == true,
                            modifier = Modifier.weight(1f)
                        ) { Text(t("Sync", "همگام‌سازی")) }
                    }
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedButton(
                            onClick = viewModel::disableAutomatedFeed,
                            modifier = Modifier.weight(1f)
                        ) { Text(t("Auto OFF", "خودکار خاموش")) }
                        OutlinedButton(
                            onClick = viewModel::disableCurrentPaperFeedSubscription,
                            modifier = Modifier.weight(1f)
                        ) { Text(t("Unsubscribe", "لغو اشتراک")) }
                    }
                    Text(
                        t(
                            "Automated feed uses real public OKX best bid/ask for Crypto only; it never routes live orders.",
                            "خوراک خودکار فقط برای کریپتو از بهترین Bid/Ask عمومی و واقعی OKX استفاده می‌کند و هیچ سفارش زنده‌ای ارسال نمی‌کند."
                        ),
                        color = Color(0xFFFFD27A)
                    )
                    state.paperPortfolio?.let { portfolio ->
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            BrokerChip(t("Equity", "اکوئیتی"), String.format(Locale.US, "%.2f", portfolio.equity), Modifier.weight(1f))
                            BrokerChip(t("Unrealized", "تحقق‌نیافته"), String.format(Locale.US, "%.2f", portfolio.unrealized_pnl), Modifier.weight(1f))
                            BrokerChip(t("Daily DD", "افت روزانه"), String.format(Locale.US, "%.2f%%", portfolio.daily_drawdown_pct), Modifier.weight(1f))
                        }
                        Text(
                            t("Cash / Realized / Fees", "نقد / تحقق‌یافته / کارمزد") + ": " +
                                "${String.format(Locale.US, "%.2f", portfolio.cash_balance)} / " +
                                "${String.format(Locale.US, "%.2f", portfolio.realized_pnl)} / " +
                                String.format(Locale.US, "%.2f", portfolio.total_fees),
                            color = Color(0xFFBCEEFF)
                        )
                        portfolio.positions.filter { it.quantity != 0.0 }.take(5).forEach { position ->
                            Text(
                                "${position.symbol} • qty ${position.quantity} • mark ${position.mark_price ?: "-"} • uPnL ${String.format(Locale.US, "%.2f", position.unrealized_pnl)}",
                                color = Color.White
                            )
                        }
                    }
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = viewModel::armPaperMode, modifier = Modifier.weight(1f)) {
                            Text(t("Arm Paper", "فعال‌سازی شبیه‌سازی"))
                        }
                        OutlinedButton(onClick = viewModel::engagePaperKillSwitch, modifier = Modifier.weight(1f)) {
                            Text(t("KILL", "توقف"))
                        }
                        OutlinedButton(onClick = viewModel::disablePaperMode, modifier = Modifier.weight(1f)) {
                            Text(t("Disable", "خاموش"))
                        }
                    }
                    OutlinedTextField(
                        value = state.paperPrice,
                        onValueChange = viewModel::updatePaperPrice,
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text(t("Paper reference price", "قیمت مرجع شبیه‌سازی")) },
                        singleLine = true,
                        shape = RoundedCornerShape(18.dp),
                        textStyle = premiumTextFieldStyle(),
                        colors = premiumTextFieldColors()
                    )
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        ConnectorPickButton(
                            "market", t("Market", "مارکت"), state.paperOrderType,
                            Modifier.weight(1f)
                        ) { viewModel.selectPaperOrderType("market") }
                        ConnectorPickButton(
                            "limit", t("Limit", "لیمیت"), state.paperOrderType,
                            Modifier.weight(1f)
                        ) { viewModel.selectPaperOrderType("limit") }
                    }
                    if (state.paperOrderType == "limit") {
                        OutlinedTextField(
                            value = state.paperLimitPrice,
                            onValueChange = viewModel::updatePaperLimitPrice,
                            modifier = Modifier.fillMaxWidth(),
                            label = { Text(t("Paper limit price", "قیمت لیمیت شبیه‌سازی")) },
                            singleLine = true,
                            shape = RoundedCornerShape(18.dp),
                            textStyle = premiumTextFieldStyle(),
                            colors = premiumTextFieldColors()
                        )
                    }
                    Button(
                        onClick = viewModel::submitPaperOrder,
                        enabled = state.paperControl?.paper_trading_enabled == true &&
                            state.paperControl?.kill_switch_engaged == false,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(t("Submit Paper Order", "ثبت سفارش شبیه‌سازی"))
                    }
                    if (state.paperMessage.isNotBlank()) {
                        Text(state.paperMessage, color = Color(0xFF67ECFF), fontWeight = FontWeight.Bold)
                    }
                    state.paperReconciliation?.let { reconciliation ->
                        Text(
                            t("Ledger consistent", "سازگاری دفتر") + ": ${reconciliation.consistent}",
                            color = if (reconciliation.consistent) Color(0xFF33E6A6) else Color(0xFFFF8A8A),
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }
            if (state.paperOrders.isNotEmpty()) {
                item {
                    Text(
                        t("Recent Paper Orders", "سفارش‌های شبیه‌سازی اخیر"),
                        style = MaterialTheme.typography.titleLarge,
                        color = Color.White,
                        fontWeight = FontWeight.Bold
                    )
                }
                items(state.paperOrders.take(10)) { order ->
                    PremiumGlassCard {
                        Text(
                            "${order.symbol} • ${order.side.uppercase()} • ${order.order_type.uppercase()}",
                            color = Color.White,
                            fontWeight = FontWeight.Bold
                        )
                        Text(t("Status", "وضعیت") + ": ${order.status}", color = Color(0xFF67ECFF))
                        Text(
                            t("Filled / Total", "پرشده / کل") + ": ${order.filled_quantity} / ${order.quantity}",
                            color = Color.White
                        )
                        Text(
                            t("Average / Fees", "میانگین / کارمزد") + ": ${order.average_fill_price ?: "-"} / ${order.total_fees}",
                            color = Color(0xFFBCEEFF)
                        )
                        Text("Live routed: ${order.live_routed}", color = Color(0xFFFFD27A))
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            OutlinedButton(
                                onClick = { viewModel.reconcilePaperOrder(order.order_id) },
                                modifier = Modifier.weight(1f)
                            ) { Text(t("Reconcile", "تطبیق دفتر")) }
                            OutlinedButton(
                                onClick = { viewModel.cancelPaperOrder(order.order_id) },
                                enabled = order.status in listOf("accepted", "working", "partially_filled"),
                                modifier = Modifier.weight(1f)
                            ) { Text(t("Cancel", "لغو")) }
                        }
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

@Composable
private fun BrokerChip(title: String, value: String, modifier: Modifier = Modifier) {
    Box(
        modifier = modifier
            .background(
                Brush.linearGradient(listOf(Color(0x2611D9FF), Color(0x2217FFB3))),
                RoundedCornerShape(16.dp)
            )
            .padding(horizontal = 12.dp, vertical = 10.dp)
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(title, color = Color(0xFFBCEEFF), style = MaterialTheme.typography.bodySmall)
            Text(value, color = Color.White, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun ConnectorPickButton(
    key: String,
    title: String,
    selectedConnector: String,
    modifier: Modifier = Modifier,
    onClick: () -> Unit,
) {
    if (selectedConnector == key) {
        Button(onClick = onClick, modifier = modifier) { Text(title) }
    } else {
        OutlinedButton(onClick = onClick, modifier = modifier) { Text(title) }
    }
}

@Composable
private fun SideButton(selected: Boolean, title: String, modifier: Modifier = Modifier, onClick: () -> Unit) {
    if (selected) {
        Button(onClick = onClick, modifier = modifier) { Text(title) }
    } else {
        OutlinedButton(onClick = onClick, modifier = modifier) { Text(title) }
    }
}

private fun brokerReadinessLabel(
    liveEnabled: Boolean,
    connectorReady: Boolean,
    previewEligible: Boolean,
    t: (String, String) -> String,
): String {
    return when {
        liveEnabled && connectorReady && previewEligible -> t("Armed", "مسلح")
        connectorReady -> t("Standby", "آماده‌باش")
        else -> t("Blocked", "مسدود")
    }
}
