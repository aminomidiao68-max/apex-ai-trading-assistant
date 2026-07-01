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
import com.arena.smartmoney.data.repository.TradingRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

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
    val error: String? = null
)

class BrokerViewModel(
    private val repository: TradingRepository = TradingRepository()
) : ViewModel() {
    private val _uiState = MutableStateFlow(BrokerUiState())
    val uiState: StateFlow<BrokerUiState> = _uiState

    init {
        loadStatus()
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
            _uiState.value = current.copy(error = "Quantity must be a valid positive number")
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
            _uiState.value = current.copy(error = "Quantity must be a valid positive number")
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
}
