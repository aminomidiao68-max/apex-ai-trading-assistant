package com.arena.smartmoney.ui.setups

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.arena.smartmoney.data.model.TradeSetupDto
import com.arena.smartmoney.data.repository.TradingRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class TradeSetupsUiState(
    val loading: Boolean = true,
    val active: List<TradeSetupDto> = emptyList(),
    val forming: List<TradeSetupDto> = emptyList(),
    val armed: List<TradeSetupDto> = emptyList(),
    val confirmed: List<TradeSetupDto> = emptyList(),
    val triggered: List<TradeSetupDto> = emptyList(),
    val invalidated: List<TradeSetupDto> = emptyList(),
    val expired: List<TradeSetupDto> = emptyList(),
    val selectedStatus: String = "active",
    val selectedSymbol: String = "ALL",
    val selectedTimeframe: String = "ALL",
    val totalScanned: Int = 0,
    val generatedAt: String = "",
    val cached: Boolean = false,
    val error: String? = null,
)

class TradeSetupsViewModel(
    private val repository: TradingRepository = TradingRepository()
) : ViewModel() {
    private val _uiState = MutableStateFlow(TradeSetupsUiState())
    val uiState: StateFlow<TradeSetupsUiState> = _uiState

    init {
        load(force = false)
    }

    fun load(force: Boolean) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, error = null)
            runCatching { repository.scanTradeSetups(force) }
                .onSuccess { response ->
                    _uiState.value = _uiState.value.copy(
                        loading = false,
                        active = response.active,
                        forming = response.forming,
                        armed = response.armed,
                        confirmed = response.confirmed,
                        triggered = response.triggered,
                        invalidated = response.invalidated,
                        expired = response.expired,
                        totalScanned = response.totalScanned,
                        generatedAt = response.generatedAt,
                        cached = response.cached,
                        error = null,
                    )
                }
                .onFailure { throwable ->
                    _uiState.value = _uiState.value.copy(
                        loading = false,
                        error = friendlyNetworkError(throwable.message),
                    )
                }
        }
    }

    fun selectStatus(status: String) {
        _uiState.value = _uiState.value.copy(selectedStatus = status)
    }

    fun selectSymbol(symbol: String) {
        _uiState.value = _uiState.value.copy(selectedSymbol = symbol)
    }

    fun selectTimeframe(timeframe: String) {
        _uiState.value = _uiState.value.copy(selectedTimeframe = timeframe)
    }
}

private fun friendlyNetworkError(raw: String?): String {
    val value = raw.orEmpty().lowercase()
    return when {
        "401" in value -> "نشست ورود معتبر نیست؛ دوباره وارد حساب شوید."
        "connect" in value || "timeout" in value || "onrender" in value ->
            "اتصال به سرور برقرار نشد؛ اینترنت را بررسی و دوباره تلاش کنید."
        else -> "بارگذاری ستاپ‌ها ناموفق بود؛ دوباره تلاش کنید."
    }
}
