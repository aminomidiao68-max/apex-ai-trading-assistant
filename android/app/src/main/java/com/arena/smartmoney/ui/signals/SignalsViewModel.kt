package com.arena.smartmoney.ui.signals

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.arena.smartmoney.data.model.LiveSignalScanRequestDto
import com.arena.smartmoney.data.model.RiskSettingsDto
import com.arena.smartmoney.data.model.SignalHistoryItemDto
import com.arena.smartmoney.data.model.TradeJournalCreateRequestDto
import com.arena.smartmoney.data.model.TradeStatsDto
import com.arena.smartmoney.data.repository.TradingRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class SignalsUiState(
    val loading: Boolean = false,
    val items: List<SignalHistoryItemDto> = emptyList(),
    val error: String? = null,
    val notificationSignal: SignalHistoryItemDto? = null,
    val scanMessage: String = "",
    val journalMessage: String = ""
)

class SignalsViewModel(
    private val repository: TradingRepository = TradingRepository()
) : ViewModel() {
    private val _uiState = MutableStateFlow(SignalsUiState())
    val uiState: StateFlow<SignalsUiState> = _uiState

    init {
        loadHistory()
    }

    fun loadHistory() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, error = null)
            runCatching { repository.getSignalHistory(limit = 30) }
                .onSuccess { response ->
                    _uiState.value = _uiState.value.copy(
                        loading = false,
                        items = response.items,
                        error = null
                    )
                }
                .onFailure { throwable ->
                    _uiState.value = _uiState.value.copy(
                        loading = false,
                        error = throwable.message ?: "Failed to load signal history"
                    )
                }
        }
    }

    fun scanMarket(symbol: String, market: String, timeframe: String = "15m") {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                loading = true,
                error = null,
                scanMessage = "Scanning $symbol ...",
                journalMessage = ""
            )
            val request = LiveSignalScanRequestDto(
                symbol = symbol,
                market = market,
                timeframe = timeframe,
                risk_settings = RiskSettingsDto(
                    account_balance = 5000.0,
                    risk_per_trade_pct = 1.0,
                    max_daily_loss_pct = 3.0,
                    max_trades_per_day = 4,
                    max_consecutive_losses = 3,
                    max_open_positions = 2,
                    value_per_point = 1.0,
                    breakeven_rr = 1.0,
                    partial_tp_rr = listOf(1.0, 2.0, 3.0)
                ),
                trade_stats = TradeStatsDto(
                    trades_today = 1,
                    consecutive_losses = 0,
                    daily_loss_pct = 0.5,
                    open_positions = 0
                )
            )

            runCatching { repository.liveScanSignal(request) }
                .onSuccess { signal ->
                    _uiState.value = _uiState.value.copy(
                        loading = false,
                        items = listOf(signal) + _uiState.value.items,
                        notificationSignal = signal,
                        scanMessage = "Latest scan saved for ${signal.symbol}"
                    )
                }
                .onFailure { throwable ->
                    _uiState.value = _uiState.value.copy(
                        loading = false,
                        error = throwable.message ?: "Signal scan failed",
                        scanMessage = ""
                    )
                }
        }
    }

    fun createTradeFromSignal(signal: SignalHistoryItemDto) {
        val entryLow = signal.entry_low
        val entryHigh = signal.entry_high
        val stopLoss = signal.stop_loss
        if (entryLow == null || entryHigh == null || stopLoss == null) {
            _uiState.value = _uiState.value.copy(journalMessage = "Signal is missing entry/SL data")
            return
        }

        val entry = (entryLow + entryHigh) / 2.0
        val takeProfit = signal.take_profits.firstOrNull()

        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, journalMessage = "")
            runCatching {
                repository.createTrade(
                    TradeJournalCreateRequestDto(
                        symbol = signal.symbol,
                        market = signal.market,
                        direction = signal.direction,
                        entry_price = entry,
                        stop_loss = stopLoss,
                        take_profit = takeProfit,
                        size = 1.0,
                        notes = "Created from signal ${signal.id} with score ${signal.score}"
                    )
                )
            }.onSuccess { trade ->
                _uiState.value = _uiState.value.copy(
                    loading = false,
                    journalMessage = "Trade #${trade.id} added to journal"
                )
            }.onFailure { throwable ->
                _uiState.value = _uiState.value.copy(
                    loading = false,
                    journalMessage = throwable.message ?: "Failed to add trade"
                )
            }
        }
    }

    fun consumeNotification() {
        _uiState.value = _uiState.value.copy(notificationSignal = null)
    }
}
