package com.arena.smartmoney.ui.readiness

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.arena.smartmoney.data.model.ShadowPanelDto
import com.arena.smartmoney.data.model.ShadowTimelineDto
import com.arena.smartmoney.data.model.ShadowTimelineItemDto
import com.arena.smartmoney.data.model.SystemReadinessDto
import com.arena.smartmoney.data.repository.TradingRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class ReadinessUiState(
    val loading: Boolean = false,
    val readiness: SystemReadinessDto? = null,
    val panel: ShadowPanelDto? = null,
    val timelineItems: List<ShadowTimelineItemDto> = emptyList(),
    val timelineTotal: Int? = null,
    val timelineOverallTotal: Int? = null,
    val timelineHasMore: Boolean = false,
    val timelineLoading: Boolean = false,
    val timelineLoadingMore: Boolean = false,
    val timelineError: String? = null,
    val timelineExpanded: Boolean = false,
    val timelineFilter: String = "ALL", // ALL, CANDIDATE, RESOLVED, WINLOSS
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
            if (existing.timelineExpanded && existing.timelineItems.isNotEmpty()) {
                // keep timeline; user can manually refresh
            }
        }
    }

    fun toggleTimeline() {
        val expanded = !_uiState.value.timelineExpanded
        _uiState.value = _uiState.value.copy(timelineExpanded = expanded)
        if (expanded && _uiState.value.timelineItems.isEmpty()) {
            refreshTimeline()
        }
    }

    fun setTimelineFilter(filter: String) {
        if (_uiState.value.timelineFilter == filter) return
        _uiState.value = _uiState.value.copy(timelineFilter = filter)
        refreshTimeline()
    }

    fun refreshTimeline() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(timelineLoading = true, timelineError = null, timelineHasMore = false)
            val filter = _uiState.value.timelineFilter
            val fusionStatus = when (filter) {
                "CANDIDATE", "RESOLVED", "WINLOSS" -> "ACTIONABLE_CANDIDATE"
                else -> null
            }
            // For WINLOSS we still fetch candidates then client-filter; no outcome filter needed server-side
            val result = runCatching {
                repository.getShadowTimeline(limit = 50, offset = 0, fusionStatus = fusionStatus)
            }
            val dto = result.getOrNull()
            _uiState.value = _uiState.value.copy(
                timelineLoading = false,
                timelineItems = dto?.items ?: emptyList(),
                timelineTotal = dto?.total,
                timelineOverallTotal = dto?.overallTotal,
                timelineHasMore = (dto != null && (dto.items.size < dto.total) && dto.total > 50),
                timelineError = result.exceptionOrNull()?.message
            )
        }
    }

    fun loadMoreTimeline() {
        if (_uiState.value.timelineLoading || _uiState.value.timelineLoadingMore) return
        if (!_uiState.value.timelineHasMore) return
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(timelineLoadingMore = true)
            val filter = _uiState.value.timelineFilter
            val fusionStatus = when (filter) {
                "CANDIDATE", "RESOLVED", "WINLOSS" -> "ACTIONABLE_CANDIDATE"
                else -> null
            }
            val offset = _uiState.value.timelineItems.size
            val result = runCatching {
                repository.getShadowTimeline(limit = 50, offset = offset, fusionStatus = fusionStatus)
            }
            val dto = result.getOrNull()
            if (dto != null) {
                val combined = _uiState.value.timelineItems + dto.items
                _uiState.value = _uiState.value.copy(
                    timelineLoadingMore = false,
                    timelineItems = combined,
                    timelineHasMore = combined.size < dto.total,
                    timelineError = null
                )
            } else {
                _uiState.value = _uiState.value.copy(
                    timelineLoadingMore = false,
                    timelineError = result.exceptionOrNull()?.message
                )
            }
        }
    }
}
