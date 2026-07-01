package com.arena.smartmoney.ui.risk

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.arena.smartmoney.data.model.RiskPlanRequestDto
import com.arena.smartmoney.data.model.RiskPlanResponse
import com.arena.smartmoney.data.model.RiskSettingsDto
import com.arena.smartmoney.data.model.TradeStatsDto
import com.arena.smartmoney.data.repository.TradingRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class RiskUiState(
    val entry: String = "100.0",
    val stop: String = "98.5",
    val balance: String = "5000",
    val riskPct: String = "1.0",
    val result: RiskPlanResponse? = null,
    val loading: Boolean = false,
    val error: String? = null
)

class RiskCalculatorViewModel(
    private val repository: TradingRepository = TradingRepository()
) : ViewModel() {
    private val _uiState = MutableStateFlow(RiskUiState())
    val uiState: StateFlow<RiskUiState> = _uiState

    fun onEntryChange(value: String) { _uiState.value = _uiState.value.copy(entry = value) }
    fun onStopChange(value: String) { _uiState.value = _uiState.value.copy(stop = value) }
    fun onBalanceChange(value: String) { _uiState.value = _uiState.value.copy(balance = value) }
    fun onRiskPctChange(value: String) { _uiState.value = _uiState.value.copy(riskPct = value) }

    fun calculate() {
        val entry = _uiState.value.entry.toDoubleOrNull()
        val stop = _uiState.value.stop.toDoubleOrNull()
        val balance = _uiState.value.balance.toDoubleOrNull()
        val riskPct = _uiState.value.riskPct.toDoubleOrNull()

        if (entry == null || stop == null || balance == null || riskPct == null) {
            _uiState.value = _uiState.value.copy(error = "Please enter valid numeric values")
            return
        }

        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, error = null)
            val request = RiskPlanRequestDto(
                entry_price = entry,
                stop_loss = stop,
                direction = if (entry > stop) "buy" else "sell",
                risk_settings = RiskSettingsDto(
                    account_balance = balance,
                    risk_per_trade_pct = riskPct,
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

            runCatching { repository.calculateRisk(request) }
                .onSuccess { plan ->
                    _uiState.value = _uiState.value.copy(loading = false, result = plan, error = null)
                }
                .onFailure { e ->
                    _uiState.value = _uiState.value.copy(loading = false, error = e.message)
                }
        }
    }
}
