package com.arena.smartmoney.ui.readiness

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.arena.smartmoney.data.model.ShadowPanelDto
import com.arena.smartmoney.data.model.ShadowTimelineDto
import com.arena.smartmoney.data.model.SystemReadinessDto
import com.arena.smartmoney.data.repository.TradingRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class ReadinessUiState(
    val loading: Boolean = false,
    val readiness: SystemReadinessDto? = null,
    val panel: ShadowPanelDto? = null,
    val timeline: ShadowTimelineDto? = null,
    val timelineLoading: Boolean = false,
    val timelineError: String? = null,
    val timelineExpanded: Boolean = false,
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
            // keep timeline as-is on refresh; reload only if already expanded
            val existing = _uiState.value
            val readinessError = readinessResult.exceptionOrNull()?.message
            _uiState.value = existing.copy(
                loading = false,
                readiness = readinessResult.getOrNull(),
                panel = panelResult.getOrNull(),
                error = if (readinessResult.isFailure && panelResult.isFailure) {
                    readinessError ?: "Failed to load readiness / خطا در بارگذاری"
                } else {
                    null
                }
            )
            if (existing.timelineExpanded && existing.timeline != null) {
                refreshTimeline()
            }
        }
    }

    fun toggleTimeline() {
        val expanded = !_uiState.value.timelineExpanded
        _uiState.value = _uiState.value.copy(timelineExpanded = expanded)
        if (expanded && _uiState.value.timeline == null) {
            refreshTimeline()
        }
    }

    fun refreshTimeline() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(timelineLoading = true, timelineError = null)
            val result = runCatching { repository.getShadowTimeline(limit = 50) }
            _uiState.value = _uiState.value.copy(
                timelineLoading = false,
                timeline = result.getOrNull(),
                timelineError = result.exceptionOrNull()?.message
            )
        }
    }
}
