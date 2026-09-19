package com.arena.smartmoney.ui.readiness

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.arena.smartmoney.data.model.ShadowPanelDto
import com.arena.smartmoney.data.model.SystemReadinessDto
import com.arena.smartmoney.data.repository.TradingRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class ReadinessUiState(
    val loading: Boolean = false,
    val readiness: SystemReadinessDto? = null,
    val panel: ShadowPanelDto? = null,
    val error: String? = null
)

class ReadinessViewModel(
    private val repository: TradingRepository = TradingRepository()
) : ViewModel() {
    private val _uiState = MutableStateFlow(ReadinessUiState())
    val uiState: StateFlow<ReadinessUiState> = _uiState

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, error = null)
            val readinessResult = runCatching { repository.getSystemReadiness() }
            val panelResult = runCatching { repository.getShadowPanel() }
            val readinessError = readinessResult.exceptionOrNull()?.message
            _uiState.value = ReadinessUiState(
                loading = false,
                readiness = readinessResult.getOrNull(),
                panel = panelResult.getOrNull(),
                error = if (readinessResult.isFailure && panelResult.isFailure) {
                    readinessError ?: "Failed to load readiness / خطا در بارگذاری"
                } else {
                    null
                }
            )
        }
    }
}
