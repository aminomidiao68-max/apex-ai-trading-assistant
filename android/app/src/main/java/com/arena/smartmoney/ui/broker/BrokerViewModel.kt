package com.arena.smartmoney.ui.broker

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.arena.smartmoney.data.model.BinanceFuturesOrderRequestDto
import com.arena.smartmoney.data.model.BybitOrderRequestDto
import com.arena.smartmoney.data.model.CTraderOrderRequestDto
import com.arena.smartmoney.data.model.ConnectorCapabilityDto
import com.arena.smartmoney.data.model.ConnectorStatusDto
import com.arena.smartmoney.data.model.ExecutionActionResponseDto
import com.arena.smartmoney.data.model.ExecutionPreviewResponseDto
import com.arena.smartmoney.data.model.Mt5OrderRequestDto
import com.arena.smartmoney.data.model.OandaOrderRequestDto
import com.arena.smartmoney.data.model.PaperExecutionControlDto
import com.arena.smartmoney.data.model.PaperExecutionControlUpdateDto
import com.arena.smartmoney.data.model.PaperConnectorCheckpointDto
import com.arena.smartmoney.data.model.PaperLedgerAuditDto
import com.arena.smartmoney.data.model.PaperFeedStatusDto
import com.arena.smartmoney.data.model.PaperFeedSubscriptionDto
import com.arena.smartmoney.data.model.PaperFeedSubscriptionUpsertDto
import com.arena.smartmoney.data.model.PaperOrderCreateRequestDto
import com.arena.smartmoney.data.model.PaperOrderDto
import com.arena.smartmoney.data.model.PaperPortfolioDto
import com.arena.smartmoney.data.model.PaperReconciliationResponseDto
import com.arena.smartmoney.data.repository.TradingRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import java.util.UUID

data class BrokerUiState(
    val loading: Boolean = true,
    val liveExecutionEnabled: Boolean = false,
    val connectors: List<ConnectorStatusDto> = emptyList(),
    val capabilities: List<ConnectorCapabilityDto> = emptyList(),
    val selectedConnector: String = "binance_futures",
    val symbol: String = "BTCUSDT",
    val side: String = "buy",
    val quantity: String = "0.01",
    val preview: ExecutionPreviewResponseDto? = null,
    val executionResult: ExecutionActionResponseDto? = null,
    val paperControl: PaperExecutionControlDto? = null,
    val paperPortfolio: PaperPortfolioDto? = null,
    val paperOrders: List<PaperOrderDto> = emptyList(),
    val paperFeedStatus: PaperFeedStatusDto? = null,
    val paperFeedSubscriptions: List<PaperFeedSubscriptionDto> = emptyList(),
    val paperTestnetCheckpoints: List<PaperConnectorCheckpointDto> = emptyList(),
    val paperLedgerAudit: PaperLedgerAuditDto? = null,
    val paperPrice: String = "100.0",
    val paperLimitPrice: String = "",
    val paperLeverage: String = "5",
    val paperMarginMode: String = "isolated",
    val paperOrderType: String = "market",
    val paperMessage: String = "",
    val paperReconciliation: PaperReconciliationResponseDto? = null,
    val error: String? = null
)

private data class PaperStateBundle(
    val control: PaperExecutionControlDto,
    val portfolio: PaperPortfolioDto,
    val orders: List<PaperOrderDto>,
    val feedStatus: PaperFeedStatusDto,
    val subscriptions: List<PaperFeedSubscriptionDto>,
    val checkpoints: List<PaperConnectorCheckpointDto>,
    val audit: PaperLedgerAuditDto,
)

class BrokerViewModel(
    private val repository: TradingRepository = TradingRepository()
) : ViewModel() {
    private val _uiState = MutableStateFlow(BrokerUiState())
    val uiState: StateFlow<BrokerUiState> = _uiState

    init {
        loadStatus()
        loadPaperState()
    }

    fun loadPaperState() {
        viewModelScope.launch {
            runCatching {
                val control = async { repository.getPaperControl() }
                val portfolio = async { repository.getPaperPortfolio() }
                val orders = async { repository.getPaperOrders(30) }
                val feedStatus = async { repository.getPaperFeedStatus() }
                val subscriptions = async { repository.getPaperFeedSubscriptions() }
                val checkpoints = async { repository.getPaperTestnetCheckpoints() }
                val audit = async { repository.auditPaperLedger() }
                PaperStateBundle(
                    control = control.await(),
                    portfolio = portfolio.await(),
                    orders = orders.await().items,
                    feedStatus = feedStatus.await(),
                    subscriptions = subscriptions.await().items,
                    checkpoints = checkpoints.await().items,
                    audit = audit.await(),
                )
            }.onSuccess { state ->
                _uiState.value = _uiState.value.copy(
                    paperControl = state.control,
                    paperPortfolio = state.portfolio,
                    paperOrders = state.orders,
                    paperFeedStatus = state.feedStatus,
                    paperFeedSubscriptions = state.subscriptions,
                    paperTestnetCheckpoints = state.checkpoints,
                    paperLedgerAudit = state.audit,
                )
            }
        }
    }

    fun loadStatus() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, error = null)
            runCatching {
                val statusDeferred = async { repository.getExecutionStatus() }
                val capabilityDeferred = async { repository.getExecutionCapabilities() }
                Pair(statusDeferred.await(), capabilityDeferred.await())
            }.onSuccess { (status, capabilities) ->
                _uiState.value = _uiState.value.copy(
                    loading = false,
                    liveExecutionEnabled = status.live_execution_enabled,
                    connectors = status.connectors,
                    capabilities = capabilities.items,
                    error = null
                )
            }.onFailure { e ->
                _uiState.value = _uiState.value.copy(loading = false, error = e.message)
            }
        }
    }

    fun selectConnector(connector: String) {
        val defaultSymbol = when (connector) {
            "binance_futures", "bybit" -> "BTCUSDT"
            "oanda" -> "EUR_USD"
            "mt5" -> "XAUUSD"
            else -> "EURUSD"
        }
        val defaultQty = when (connector) {
            "binance_futures", "bybit" -> "0.01"
            "mt5" -> "0.10"
            else -> "1000"
        }
        _uiState.value = _uiState.value.copy(
            selectedConnector = connector,
            symbol = defaultSymbol,
            quantity = defaultQty,
            preview = null,
            executionResult = null
        )
    }

    fun updateSymbol(value: String) {
        _uiState.value = _uiState.value.copy(symbol = value)
    }

    fun updateQuantity(value: String) {
        _uiState.value = _uiState.value.copy(quantity = value)
    }

    fun updateSide(value: String) {
        _uiState.value = _uiState.value.copy(side = value)
    }

    fun previewSelectedConnector() {
        val current = _uiState.value
        val qty = current.quantity.toDoubleOrNull()
        if (qty == null || qty <= 0) {
            _uiState.value = current.copy(
                error = "Quantity must be a valid positive number / مقدار باید عدد مثبت معتبر باشد"
            )
            return
        }

        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, error = null, executionResult = null)
            runCatching {
                repository.previewExecution(
                    connector = current.selectedConnector,
                    symbol = current.symbol,
                    side = current.side,
                    quantity = qty,
                    signalScore = 82.0,
                    riskApproved = true
                )
            }.onSuccess { preview ->
                _uiState.value = _uiState.value.copy(loading = false, preview = preview)
            }.onFailure { e ->
                _uiState.value = _uiState.value.copy(loading = false, error = e.message)
            }
        }
    }

    fun executeSelectedConnector() {
        val current = _uiState.value
        val qty = current.quantity.toDoubleOrNull()
        if (qty == null || qty <= 0) {
            _uiState.value = current.copy(
                error = "Quantity must be a valid positive number / مقدار باید عدد مثبت معتبر باشد"
            )
            return
        }

        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, error = null)
            runCatching {
                when (current.selectedConnector) {
                    "binance_futures" -> repository.placeBinanceOrder(
                        BinanceFuturesOrderRequestDto(
                            symbol = current.symbol,
                            side = current.side.uppercase(),
                            quantity = qty,
                            signal_score = 82.0,
                            risk_approved = true
                        )
                    )
                    "bybit" -> repository.placeBybitOrder(
                        BybitOrderRequestDto(
                            symbol = current.symbol,
                            side = if (current.side == "buy") "Buy" else "Sell",
                            quantity = qty,
                            signal_score = 82.0,
                            risk_approved = true
                        )
                    )
                    "oanda" -> repository.placeOandaOrder(
                        OandaOrderRequestDto(
                            instrument = current.symbol,
                            units = if (current.side == "buy") qty.toInt() else -qty.toInt(),
                            signal_score = 82.0,
                            risk_approved = true
                        )
                    )
                    "mt5" -> repository.placeMt5Order(
                        Mt5OrderRequestDto(
                            symbol = current.symbol,
                            side = current.side,
                            volume = qty,
                            signal_score = 82.0,
                            risk_approved = true
                        )
                    )
                    else -> repository.placeCTraderOrder(
                        CTraderOrderRequestDto(
                            symbol = current.symbol,
                            side = current.side,
                            volume = qty,
                            signal_score = 82.0,
                            risk_approved = true
                        )
                    )
                }
            }.onSuccess { result ->
                _uiState.value = _uiState.value.copy(loading = false, executionResult = result)
            }.onFailure { e ->
                _uiState.value = _uiState.value.copy(loading = false, error = e.message)
            }
        }
    }

    fun updatePaperPrice(value: String) {
        _uiState.value = _uiState.value.copy(paperPrice = value)
    }

    fun updatePaperLimitPrice(value: String) {
        _uiState.value = _uiState.value.copy(paperLimitPrice = value)
    }

    fun selectPaperOrderType(value: String) {
        _uiState.value = _uiState.value.copy(paperOrderType = value)
    }

    fun updatePaperLeverage(value: String) {
        _uiState.value = _uiState.value.copy(paperLeverage = value)
    }

    fun selectPaperMarginMode(value: String) {
        _uiState.value = _uiState.value.copy(paperMarginMode = value)
    }

    fun armPaperMode() {
        updatePaperControl(enabled = true, killSwitch = false, automatedFeed = false)
    }

    fun engagePaperKillSwitch() {
        updatePaperControl(enabled = true, killSwitch = true, automatedFeed = false)
    }

    fun disablePaperMode() {
        updatePaperControl(enabled = false, killSwitch = true, automatedFeed = false)
    }

    fun enableAutomatedFeed() {
        updatePaperControl(enabled = true, killSwitch = false, automatedFeed = true)
    }

    fun disableAutomatedFeed() {
        val control = _uiState.value.paperControl
        updatePaperControl(
            enabled = control?.paper_trading_enabled == true,
            killSwitch = control?.kill_switch_engaged != false,
            automatedFeed = false,
        )
    }

    private fun updatePaperControl(
        enabled: Boolean,
        killSwitch: Boolean,
        automatedFeed: Boolean,
    ) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, paperMessage = "")
            val current = _uiState.value.paperControl
            runCatching {
                repository.updatePaperControl(
                    PaperExecutionControlUpdateDto(
                        paper_trading_enabled = enabled,
                        kill_switch_engaged = killSwitch,
                        automated_feed_enabled = automatedFeed,
                        max_open_orders = current?.max_open_orders ?: 5,
                        max_order_notional = current?.max_order_notional ?: 10000.0,
                        default_fee_bps = current?.default_fee_bps ?: 4.0,
                        default_slippage_bps = current?.default_slippage_bps ?: 1.0,
                        max_daily_drawdown_pct = current?.max_daily_drawdown_pct ?: 3.0,
                        max_tick_age_seconds = current?.max_tick_age_seconds ?: 30,
                        max_leverage = current?.max_leverage ?: 10.0,
                        default_maintenance_margin_rate = current?.default_maintenance_margin_rate ?: 0.005,
                        liquidation_fee_bps = current?.liquidation_fee_bps ?: 20.0,
                        max_margin_utilization_pct = current?.max_margin_utilization_pct ?: 70.0,
                        max_symbol_margin_pct = current?.max_symbol_margin_pct ?: 30.0,
                        max_risk_group_margin_pct = current?.max_risk_group_margin_pct ?: 50.0,
                        max_directional_notional_multiple = current?.max_directional_notional_multiple ?: 3.0,
                        acknowledgement = if (enabled) "I_UNDERSTAND_PAPER_ONLY" else null,
                    )
                )
            }.onSuccess { control ->
                _uiState.value = _uiState.value.copy(
                    loading = false,
                    paperControl = control,
                    paperMessage = if (control.kill_switch_engaged) {
                        "Paper kill switch engaged / کلید توقف شبیه‌سازی فعال شد"
                    } else {
                        "Paper mode armed / حالت شبیه‌سازی فعال شد"
                    }
                )
                loadPaperState()
            }.onFailure { error ->
                _uiState.value = _uiState.value.copy(
                    loading = false,
                    paperMessage = error.message ?: "Paper control update failed"
                )
            }
        }
    }

    fun subscribeCurrentSymbolToPaperFeed() {
        val symbol = _uiState.value.symbol.uppercase()
        if (!symbol.endsWith("USDT")) {
            _uiState.value = _uiState.value.copy(
                paperMessage = "Automated real quote feed currently supports Crypto/USDT only"
            )
            return
        }
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, paperMessage = "")
            runCatching {
                repository.upsertPaperFeedSubscription(
                    PaperFeedSubscriptionUpsertDto(symbol = symbol)
                )
            }.onSuccess { subscription ->
                _uiState.value = _uiState.value.copy(
                    loading = false,
                    paperMessage = "Real OKX feed subscribed: ${subscription.symbol}",
                )
                loadPaperState()
            }.onFailure { error ->
                _uiState.value = _uiState.value.copy(
                    loading = false,
                    paperMessage = error.message ?: "Paper feed subscription failed",
                )
            }
        }
    }

    fun syncPaperFeedNow() {
        val symbol = _uiState.value.symbol.uppercase()
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, paperMessage = "")
            runCatching { repository.syncPaperFeed(listOf(symbol)) }
                .onSuccess { result ->
                    val item = result.items.firstOrNull()
                    val midpoint = if (item?.bid != null && item.ask != null) {
                        (item.bid + item.ask) / 2.0
                    } else null
                    _uiState.value = _uiState.value.copy(
                        loading = false,
                        paperPrice = midpoint?.toString() ?: _uiState.value.paperPrice,
                        paperMessage = if (item?.ok == true) {
                            "Real quote synced: ${item.provider}; duplicate=${item.duplicate_tick}"
                        } else {
                            "Feed sync failed: ${item?.error_code ?: "no_enabled_subscription"}"
                        },
                    )
                    loadPaperState()
                }
                .onFailure { error ->
                    _uiState.value = _uiState.value.copy(
                        loading = false,
                        paperMessage = error.message ?: "Paper feed sync failed",
                    )
                }
        }
    }

    fun disableCurrentPaperFeedSubscription() {
        val symbol = _uiState.value.symbol.uppercase()
        viewModelScope.launch {
            runCatching { repository.disablePaperFeedSubscription(symbol) }
                .onSuccess {
                    _uiState.value = _uiState.value.copy(paperMessage = "Paper feed subscription disabled")
                    loadPaperState()
                }
                .onFailure { error ->
                    _uiState.value = _uiState.value.copy(
                        paperMessage = error.message ?: "Paper feed disable failed"
                    )
                }
        }
    }

    fun probePaperTestnet(connector: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, paperMessage = "")
            runCatching { repository.probePaperTestnetConnector(connector, force = true) }
                .onSuccess { checkpoint ->
                    _uiState.value = _uiState.value.copy(
                        loading = false,
                        paperMessage = "${checkpoint.connector}: ${checkpoint.state}; public connectivity only",
                    )
                    loadPaperState()
                }
                .onFailure { error ->
                    _uiState.value = _uiState.value.copy(
                        loading = false,
                        paperMessage = error.message ?: "Testnet public probe failed",
                    )
                }
        }
    }

    fun runPaperLedgerAudit() {
        viewModelScope.launch {
            runCatching { repository.auditPaperLedger() }
                .onSuccess { audit ->
                    _uiState.value = _uiState.value.copy(
                        paperLedgerAudit = audit,
                        paperMessage = if (audit.consistent) {
                            "Paper ledger audit passed"
                        } else {
                            "Paper ledger issues: ${audit.issues.take(3).joinToString()}"
                        },
                    )
                }
                .onFailure { error ->
                    _uiState.value = _uiState.value.copy(
                        paperMessage = error.message ?: "Paper ledger audit failed"
                    )
                }
        }
    }

    fun submitPaperOrder() {
        val state = _uiState.value
        val quantity = state.quantity.toDoubleOrNull()
        val price = state.paperPrice.toDoubleOrNull()
        val limitPrice = state.paperLimitPrice.toDoubleOrNull()
        val leverage = state.paperLeverage.toDoubleOrNull()
        val maxLeverage = state.paperControl?.max_leverage ?: 10.0
        if (quantity == null || quantity <= 0 || price == null || price <= 0) {
            _uiState.value = state.copy(paperMessage = "Paper quantity and price must be positive")
            return
        }
        if (leverage == null || leverage < 1.0 || leverage > maxLeverage) {
            _uiState.value = state.copy(
                paperMessage = "Leverage must be between 1 and ${maxLeverage.toInt()}"
            )
            return
        }
        if (state.paperOrderType == "limit" && (limitPrice == null || limitPrice <= 0)) {
            _uiState.value = state.copy(paperMessage = "Limit price is required")
            return
        }
        val spreadHalf = price * 0.0005
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, paperMessage = "")
            runCatching {
                repository.submitPaperOrder(
                    PaperOrderCreateRequestDto(
                        idempotency_key = "android-${UUID.randomUUID()}",
                        symbol = state.symbol.uppercase(),
                        market = if (state.symbol.uppercase().endsWith("USDT")) "crypto" else "forex",
                        side = state.side,
                        order_type = state.paperOrderType,
                        quantity = quantity,
                        reference_bid = price - spreadHalf,
                        reference_ask = price + spreadHalf,
                        available_quantity = quantity,
                        limit_price = if (state.paperOrderType == "limit") limitPrice else null,
                        leverage = leverage,
                        margin_mode = state.paperMarginMode,
                        signal_score = 82.0,
                        risk_approved = true,
                        strategy_id = "android-paper-manual",
                    )
                )
            }.onSuccess { order ->
                _uiState.value = _uiState.value.copy(
                    loading = false,
                    paperMessage = "Paper order ${order.status}: ${order.order_id.take(8)}",
                )
                loadPaperState()
            }.onFailure { error ->
                _uiState.value = _uiState.value.copy(
                    loading = false,
                    paperMessage = error.message ?: "Paper order failed"
                )
            }
        }
    }

    fun cancelPaperOrder(orderId: String) {
        viewModelScope.launch {
            runCatching { repository.cancelPaperOrder(orderId) }
                .onSuccess {
                    _uiState.value = _uiState.value.copy(paperMessage = "Paper order canceled")
                    loadPaperState()
                }
                .onFailure { error ->
                    _uiState.value = _uiState.value.copy(
                        paperMessage = error.message ?: "Paper cancel failed"
                    )
                }
        }
    }

    fun reconcilePaperOrder(orderId: String) {
        viewModelScope.launch {
            runCatching { repository.reconcilePaperOrder(orderId) }
                .onSuccess { result ->
                    _uiState.value = _uiState.value.copy(
                        paperReconciliation = result,
                        paperMessage = if (result.consistent) {
                            "Paper ledger reconciliation passed"
                        } else {
                            "Paper reconciliation issues: ${result.issues.joinToString()}"
                        }
                    )
                }
                .onFailure { error ->
                    _uiState.value = _uiState.value.copy(
                        paperMessage = error.message ?: "Paper reconciliation failed"
                    )
                }
        }
    }
}
