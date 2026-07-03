package com.arena.smartmoney.ui.journal

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.arena.smartmoney.data.model.TradeJournalCloseRequestDto
import com.arena.smartmoney.data.model.TradeJournalItemDto
import com.arena.smartmoney.data.model.TradeJournalStatsDto
import com.arena.smartmoney.data.repository.TradingRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class JournalUiState(
    val loading: Boolean = false,
    val items: List<TradeJournalItemDto> = emptyList(),
    val stats: TradeJournalStatsDto? = null,
    val filter: String = "all",
    val error: String? = null,
    val message: String = ""
)

class JournalViewModel(
    private val repository: TradingRepository = TradingRepository()
) : ViewModel() {
    private val _uiState = MutableStateFlow(JournalUiState())
    val uiState: StateFlow<JournalUiState> = _uiState

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, error = null, message = "")
            runCatching {
                Pair(repository.getTrades(limit = 50), repository.getTradeStats())
            }.onSuccess { (trades, stats) ->
                _uiState.value = _uiState.value.copy(
                    loading = false,
                    items = trades.items,
                    stats = stats,
                    error = null
                )
            }.onFailure { throwable ->
                _uiState.value = _uiState.value.copy(
                    loading = false,
                    error = throwable.message ?: "Failed to load journal / خطا در بارگذاری ژورنال"
                )
            }
        }
    }

    fun setFilter(filter: String) {
        _uiState.value = _uiState.value.copy(filter = filter)
    }

    fun closeTradeAsWin(trade: TradeJournalItemDto) {
        val exit = trade.take_profit ?: return
        closeTrade(trade, exit, "Closed at take profit / بسته شد با حد سود")
    }

    fun closeTradeAsLoss(trade: TradeJournalItemDto) {
        closeTrade(trade, trade.stop_loss, "Closed at stop loss / بسته شد با حد ضرر")
    }

    private fun closeTrade(trade: TradeJournalItemDto, exitPrice: Double, note: String) {
        val pnl = calculatePnl(trade, exitPrice)
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, error = null, message = "")
            runCatching {
                repository.closeTrade(
                    tradeId = trade.id,
                    request = TradeJournalCloseRequestDto(
                        exit_price = exitPrice,
                        pnl_amount = pnl,
                        notes = note
                    )
                )
            }.onSuccess {
                refresh()
                _uiState.value = _uiState.value.copy(
                    message = "Trade #${trade.id} closed / معامله #${trade.id} بسته شد"
                )
            }.onFailure { throwable ->
                _uiState.value = _uiState.value.copy(
                    loading = false,
                    error = throwable.message ?: "Failed to close trade / بستن معامله ناموفق بود"
                )
            }
        }
    }

    private fun calculatePnl(trade: TradeJournalItemDto, exitPrice: Double): Double {
        return if (trade.direction.lowercase() == "buy") {
            (exitPrice - trade.entry_price) * trade.size
        } else {
            (trade.entry_price - exitPrice) * trade.size
        }
    }
}
