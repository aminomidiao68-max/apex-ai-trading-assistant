package com.arena.smartmoney.ui.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.arena.smartmoney.data.model.MarketOverviewItem
import com.arena.smartmoney.data.model.MarketStreamSnapshotDto
import com.arena.smartmoney.data.model.TradeJournalStatsDto
import com.arena.smartmoney.data.network.AuthTokenProvider
import com.arena.smartmoney.data.network.MarketWebSocketClient
import com.arena.smartmoney.data.repository.TradingRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class DashboardUiState(
    val loading: Boolean = true,
    val sessionName: String = "Loading...",
    val marketQuality: String = "-",
    val sessionScore: Double = 0.0,
    val watchlistSymbols: List<String> = listOf("BTCUSDT", "ETHUSDT", "EURUSD", "GBPUSD", "XAUUSD"),
    val watchlist: List<MarketOverviewItem> = emptyList(),
    val tradeStats: TradeJournalStatsDto? = null,
    val streamSymbol: String = "BTCUSDT",
    val streamMarket: String = "crypto",
    val liveSnapshot: MarketStreamSnapshotDto? = null,
    val streamStatus: String = "idle",
    val error: String? = null
)

class DashboardViewModel(
    private val repository: TradingRepository = TradingRepository(),
    private val marketStreamClient: MarketWebSocketClient = MarketWebSocketClient()
) : ViewModel() {
    private val _uiState = MutableStateFlow(DashboardUiState())
    val uiState: StateFlow<DashboardUiState> = _uiState

    init {
        refreshAll()
        connectStream()
    }

    fun refreshAll() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, error = null)
            val sessionDeferred = async { runCatching { repository.getCurrentSession() } }
            val overviewDeferred = async {
                runCatching {
                    repository.getMarketOverview(_uiState.value.watchlistSymbols.joinToString(","))
                }
            }
            val statsDeferred = if (AuthTokenProvider.hasServerToken()) {
                async { runCatching { repository.getTradeStats() } }
            } else null

            val session = sessionDeferred.await().getOrNull()
            val overview = overviewDeferred.await().getOrNull()
            val stats = statsDeferred?.await()?.getOrNull()
            val publicDataAvailable = session != null || overview != null
            _uiState.value = _uiState.value.copy(
                loading = false,
                sessionName = session?.session_name ?: if (publicDataAvailable) "Public / Demo" else "Offline",
                marketQuality = session?.market_quality ?: "-",
                sessionScore = session?.session_score ?: 0.0,
                watchlist = overview?.items ?: _uiState.value.watchlist,
                tradeStats = stats,
                error = if (publicDataAvailable) null else "اتصال بازار موقتاً برقرار نیست؛ دوباره تلاش کنید.",
            )
        }
    }

    fun selectStreamSymbol(symbol: String) {
        val market = if (symbol.endsWith("USDT")) "crypto" else "forex"
        _uiState.value = _uiState.value.copy(streamSymbol = symbol, streamMarket = market)
        connectStream()
    }

    fun reconnectStream() {
        connectStream()
    }

    private fun connectStream() {
        val current = _uiState.value
        marketStreamClient.connect(
            symbol = current.streamSymbol,
            market = current.streamMarket,
            onStatus = { status ->
                _uiState.value = _uiState.value.copy(streamStatus = status)
            },
            onSnapshot = { snapshot ->
                _uiState.value = _uiState.value.copy(
                    liveSnapshot = snapshot,
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
