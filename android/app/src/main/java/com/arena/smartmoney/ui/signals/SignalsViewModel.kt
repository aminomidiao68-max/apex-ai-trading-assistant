package com.arena.smartmoney.ui.signals

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.arena.smartmoney.data.model.LiveSignalScanRequestDto
import com.arena.smartmoney.data.model.RiskSettingsDto
import com.arena.smartmoney.data.model.SignalHistoryItemDto
import com.arena.smartmoney.data.model.TradeJournalCreateRequestDto
import com.arena.smartmoney.data.model.TradeStatsDto
import com.arena.smartmoney.data.repository.TradingRepository
import com.arena.smartmoney.ui.i18n.AppLanguageState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class SignalsUiState(
    val loading: Boolean = false,
    val items: List<SignalHistoryItemDto> = emptyList(),
    val error: String? = null,
    val notificationSignal: SignalHistoryItemDto? = null,
    val scanMessage: String = "",
    val journalMessage: String = "",
    val selectedTimeframe: String = "15m"
)

class SignalsViewModel(
    private val repository: TradingRepository = TradingRepository()
) : ViewModel() {
    private val _uiState = MutableStateFlow(SignalsUiState())
    val uiState: StateFlow<SignalsUiState> = _uiState

    init {
        loadHistory()
    }

    private fun tr(en: String, fa: String): String = if (AppLanguageState.current == "fa") fa else en

    fun selectTimeframe(timeframe: String) {
        _uiState.value = _uiState.value.copy(selectedTimeframe = timeframe)
    }

    fun loadHistory() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, error = null)
            runCatching { repository.getSignalHistory(limit = 30) }
                .onSuccess { response ->
                    _uiState.value = _uiState.value.copy(
                        loading = false,
                        items = response.items.sortedByDescending { it.score },
                        error = null
                    )
                }
                .onFailure { throwable ->
                    _uiState.value = _uiState.value.copy(
                        loading = false,
                        error = throwable.message ?: tr("Failed to load signal history", "بارگذاری تاریخچه سیگنال ناموفق بود")
                    )
                }
        }
    }

    fun scanMarket(symbol: String, market: String, timeframe: String = _uiState.value.selectedTimeframe) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                loading = true,
                error = null,
                scanMessage = tr("Scanning $symbol on $timeframe...", "در حال اسکن $symbol روی $timeframe..."),
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
                    val qualityMessage = when {
                        signal.score >= 80.0 -> tr("Elite setup detected", "ستاپ ممتاز شناسایی شد")
                        signal.score >= 65.0 -> tr("Tradeable setup detected", "ستاپ قابل معامله شناسایی شد")
                        else -> tr("Weak setup - avoid entry", "ستاپ ضعیف است و برای ورود توصیه نمی‌شود")
                    }
                    val grade = signal.setup_grade ?: when {
                        signal.score >= 88.0 -> "A+"
                        signal.score >= 78.0 -> "A"
                        signal.score >= 68.0 -> "B"
                        else -> "C"
                    }
                    _uiState.value = _uiState.value.copy(
                        loading = false,
                        items = (listOf(signal) + _uiState.value.items).sortedByDescending { it.score },
                        notificationSignal = signal,
                        scanMessage = "$qualityMessage • ${signal.symbol} • ${signal.timeframe} • Grade $grade",
                        error = null
                    )
                }
                .onFailure { throwable ->
                    _uiState.value = _uiState.value.copy(
                        loading = false,
                        error = throwable.message ?: tr("Signal scan failed", "اسکن سیگنال ناموفق بود"),
                        scanMessage = ""
                    )
                }
        }
    }

    fun createTradeFromSignal(signal: SignalHistoryItemDto) {
        if (signal.score < 60.0) {
            _uiState.value = _uiState.value.copy(
                journalMessage = tr(
                    "Signal too weak for journal entry",
                    "این سیگنال کیفیت کافی برای ورود به ژورنال معامله را ندارد"
                )
            )
            return
        }
        val entryLow = signal.entry_low
        val entryHigh = signal.entry_high
        val stopLoss = signal.stop_loss
        if (entryLow == null || entryHigh == null || stopLoss == null) {
            _uiState.value = _uiState.value.copy(
                journalMessage = tr("Signal is missing entry/SL data", "اطلاعات ورود یا حد ضرر ناقص است")
            )
            return
        }

        val entry = (entryLow + entryHigh) / 2.0
        val takeProfit = signal.take_profits.firstOrNull()
        val tp2 = signal.take_profits.getOrNull(1)
        val tp3 = signal.take_profits.getOrNull(2)

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
                        notes = "AI signal ${signal.id} • TF=${signal.timeframe} • Score ${signal.score} • TP1=${takeProfit ?: "-"} • TP2=${tp2 ?: "-"} • TP3=${tp3 ?: "-"}"
                    )
                )
            }.onSuccess { trade ->
                _uiState.value = _uiState.value.copy(
                    loading = false,
                    journalMessage = tr("Trade #${trade.id} added to journal", "معامله #${trade.id} به ژورنال اضافه شد")
                )
            }.onFailure { throwable ->
                _uiState.value = _uiState.value.copy(
                    loading = false,
                    journalMessage = throwable.message ?: tr("Failed to add trade", "افزودن معامله ناموفق بود")
                )
            }
        }
    }

    fun consumeNotification() {
        _uiState.value = _uiState.value.copy(notificationSignal = null)
    }
}
