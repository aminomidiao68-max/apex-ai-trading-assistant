package com.arena.smartmoney.ui.analytics

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.arena.smartmoney.data.model.AnalyticsReportDto
import com.arena.smartmoney.data.network.AuthTokenProvider
import com.arena.smartmoney.data.repository.TradingRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class AnalyticsUiState(
    val loading: Boolean = false,
    val report: AnalyticsReportDto? = null,
    val error: String? = null
)

class AnalyticsViewModel(
    private val repository: TradingRepository = TradingRepository()
) : ViewModel() {
    private val _uiState = MutableStateFlow(AnalyticsUiState())
    val uiState: StateFlow<AnalyticsUiState> = _uiState

    init {
        load()
    }

    fun load() {
        if (!AuthTokenProvider.hasServerToken()) {
            _uiState.value = AnalyticsUiState(
                loading = false,
                error = "حالت دمو: آنالیتیکس شخصی نیاز به ورود حساب دارد.",
            )
            return
        }
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, error = null)
            runCatching { repository.getAnalyticsReport() }
                .onSuccess { report ->
                    _uiState.value = AnalyticsUiState(loading = false, report = report)
                }
                .onFailure { throwable ->
                    _uiState.value = AnalyticsUiState(
                        loading = false,
                        error = throwable.message ?: "Failed to load analytics / خطا در بارگذاری آنالیتیکس"
                    )
                }
        }
    }
}
