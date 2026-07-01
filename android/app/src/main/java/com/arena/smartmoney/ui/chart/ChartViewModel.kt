package com.arena.smartmoney.ui.chart

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.arena.smartmoney.data.model.CandleDto
import com.arena.smartmoney.data.model.MarketStreamSnapshotDto
import com.arena.smartmoney.data.network.MarketWebSocketClient
import com.arena.smartmoney.data.repository.TradingRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import kotlin.math.max
import kotlin.math.min

data class ChartUiState(
    val loading: Boolean = true,
    val symbol: String = "BTCUSDT",
    val market: String = "crypto",
    val timeframe: String = "15m",
    val candles: List<CandleDto> = emptyList(),
    val visibleCount: Int = 24,
    val startIndex: Int = 0,
    val selectedVisibleIndex: Int = -1,
    val latestSnapshot: MarketStreamSnapshotDto? = null,
    val streamStatus: String = "idle",
    val error: String? = null
)

class ChartViewModel(
    private val repository: TradingRepository = TradingRepository(),
    private val marketStreamClient: MarketWebSocketClient = MarketWebSocketClient()
) : ViewModel() {
    private val _uiState = MutableStateFlow(ChartUiState())
    val uiState: StateFlow<ChartUiState> = _uiState

    init {
        loadChart()
        connectStream()
    }

    fun selectAsset(symbol: String, market: String) {
        _uiState.value = _uiState.value.copy(symbol = symbol, market = market, startIndex = 0)
        loadChart()
        connectStream()
    }

    fun selectTimeframe(timeframe: String) {
        _uiState.value = _uiState.value.copy(timeframe = timeframe, startIndex = 0)
        loadChart()
    }

    fun reconnectStream() {
        connectStream()
    }

    fun zoomIn() {
        val current = _uiState.value
        val newVisible = max(12, current.visibleCount - 6)
        val newSelected = current.selectedVisibleIndex.coerceIn(0, max(newVisible - 1, 0))
        _uiState.value = current.copy(visibleCount = newVisible, selectedVisibleIndex = newSelected)
    }

    fun zoomOut() {
        val current = _uiState.value
        val newVisible = min(current.candles.size.coerceAtLeast(12), current.visibleCount + 6)
        val newSelected = current.selectedVisibleIndex.coerceIn(0, max(newVisible - 1, 0))
        _uiState.value = current.copy(visibleCount = newVisible, selectedVisibleIndex = newSelected)
    }

    fun panLeft() {
        val current = _uiState.value
        _uiState.value = current.copy(startIndex = max(0, current.startIndex - 6))
    }

    fun panRight() {
        val current = _uiState.value
        val maxStart = max(0, current.candles.size - current.visibleCount)
        _uiState.value = current.copy(startIndex = min(maxStart, current.startIndex + 6))
    }

    fun applyGesture(horizontalPan: Float, zoomFactor: Float) {
        val current = _uiState.value
        var visibleCount = current.visibleCount
        var startIndex = current.startIndex

        if (zoomFactor > 1.03f) {
            visibleCount = max(12, visibleCount - 1)
        } else if (zoomFactor < 0.97f) {
            visibleCount = min(current.candles.size.coerceAtLeast(12), visibleCount + 1)
        }

        val panThreshold = 12f
        if (horizontalPan > panThreshold) {
            startIndex = max(0, startIndex - 1)
        } else if (horizontalPan < -panThreshold) {
            val maxStart = max(0, current.candles.size - visibleCount)
            startIndex = min(maxStart, startIndex + 1)
        }

        val selected = current.selectedVisibleIndex.coerceIn(0, max(visibleCount - 1, 0))
        _uiState.value = current.copy(
            visibleCount = visibleCount,
            startIndex = startIndex,
            selectedVisibleIndex = selected
        )
    }

    fun selectVisibleCandleFromTap(tapX: Float, chartWidthPx: Float) {
        val visible = visibleCandles()
        if (visible.isEmpty() || chartWidthPx <= 0f) return
        val slotWidth = chartWidthPx / visible.size
        val idx = (tapX / slotWidth).toInt().coerceIn(0, visible.size - 1)
        _uiState.value = _uiState.value.copy(selectedVisibleIndex = idx)
    }

    fun visibleCandles(): List<CandleDto> {
        val current = _uiState.value
        if (current.candles.isEmpty()) return emptyList()
        val maxStart = max(0, current.candles.size - current.visibleCount)
        val start = min(current.startIndex, maxStart)
        val end = min(current.candles.size, start + current.visibleCount)
        return current.candles.subList(start, end)
    }

    fun selectedVisibleCandle(): CandleDto? {
        val visible = visibleCandles()
        if (visible.isEmpty()) return null
        val index = _uiState.value.selectedVisibleIndex.coerceIn(0, visible.size - 1)
        return visible.getOrNull(index)
    }

    fun loadChart() {
        viewModelScope.launch {
            val current = _uiState.value
            _uiState.value = current.copy(loading = true, error = null)
            runCatching {
                repository.getCandles(
                    symbol = current.symbol,
                    market = current.market,
                    interval = current.timeframe,
                    limit = 80
                )
            }.onSuccess { response ->
                val visible = min(24, response.items.size.coerceAtLeast(12))
                val start = max(0, response.items.size - visible)
                _uiState.value = _uiState.value.copy(
                    loading = false,
                    candles = response.items,
                    visibleCount = visible,
                    startIndex = start,
                    selectedVisibleIndex = max(0, visible - 1),
                    error = null
                )
            }.onFailure { throwable ->
                _uiState.value = _uiState.value.copy(
                    loading = false,
                    error = throwable.message ?: "Failed to load chart data"
                )
            }
        }
    }

    private fun connectStream() {
        val current = _uiState.value
        marketStreamClient.connect(
            symbol = current.symbol,
            market = current.market,
            onStatus = { status ->
                _uiState.value = _uiState.value.copy(streamStatus = status)
            },
            onSnapshot = { snapshot ->
                _uiState.value = _uiState.value.copy(
                    latestSnapshot = snapshot,
                    streamStatus = if (snapshot.error == null) "connected" else "error"
                )
            }
        )
    }

    override fun onCleared() {
        marketStreamClient.disconnect()
        super.onCleared()
    }
}
