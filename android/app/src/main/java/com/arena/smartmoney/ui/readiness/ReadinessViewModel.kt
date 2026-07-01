package com.arena.smartmoney.ui.readiness

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.arena.smartmoney.data.model.SystemReadinessDto
import com.arena.smartmoney.data.repository.TradingRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class ReadinessUiState(
    val loading: Boolean = false,
    val readiness: SystemReadinessDto? = null,
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
            runCatching { repository.getSystemReadiness() }
                .onSuccess { readiness ->
                    _uiState.value = ReadinessUiState(loading = false, readiness = readiness)
                }
                .onFailure { throwable ->
                    _uiState.value = ReadinessUiState(
                        loading = false,
                        error = throwable.message ?: "Failed to load system readiness"
                    )
                }
        }
    }
}
