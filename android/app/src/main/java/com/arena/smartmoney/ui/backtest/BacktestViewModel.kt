package com.arena.smartmoney.ui.backtest

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.arena.smartmoney.data.model.AnalyticsSummaryDto
import com.arena.smartmoney.data.model.BacktestRunRequestDto
import com.arena.smartmoney.data.model.BacktestSummaryDto
import com.arena.smartmoney.data.model.BacktestSweepRequestDto
import com.arena.smartmoney.data.model.BacktestSweepSummaryDto
import com.arena.smartmoney.data.model.RiskSettingsDto
import com.arena.smartmoney.data.model.TradeStatsDto
import com.arena.smartmoney.data.model.WalkForwardRequestDto
import com.arena.smartmoney.data.model.WalkForwardSummaryDto
import com.arena.smartmoney.data.network.AuthTokenProvider
import com.arena.smartmoney.data.repository.TradingRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import kotlin.math.max
import kotlin.math.min

data class BacktestUiState(
    val loading: Boolean = false,
    val symbol: String = "BTCUSDT",
    val market: String = "crypto",
    val timeframe: String = "15m",
    val scoreThreshold: Double = 65.0,
    val windowSize: Int = 30,
    val lookaheadCandles: Int = 8,
    val maxSignals: Int = 40,
    val takeProfitIndex: Int = 0,
    val trainWindow: Int = 80,
    val testWindow: Int = 30,
    val stepSize: Int = 20,
    val summary: BacktestSummaryDto? = null,
    val sweepSummary: BacktestSweepSummaryDto? = null,
    val walkForwardSummary: WalkForwardSummaryDto? = null,
    val analytics: AnalyticsSummaryDto? = null,
    val error: String? = null
)

class BacktestViewModel(
    private val repository: TradingRepository = TradingRepository()
) : ViewModel() {
    private val _uiState = MutableStateFlow(BacktestUiState())
    val uiState: StateFlow<BacktestUiState> = _uiState

    init {
        if (AuthTokenProvider.hasServerToken()) {
            loadAnalytics()
        } else {
            _uiState.value = _uiState.value.copy(
                error = "حالت دمو: اجرای بک‌تست و آنالیتیکس نیاز به ورود حساب دارد.",
            )
        }
    }

    fun selectAsset(symbol: String, market: String) {
        _uiState.value = _uiState.value.copy(symbol = symbol, market = market)
    }

    fun selectTimeframe(timeframe: String) {
        _uiState.value = _uiState.value.copy(timeframe = timeframe)
    }

    fun adjustWindowSize(delta: Int) {
        val current = _uiState.value
        _uiState.value = current.copy(windowSize = min(120, max(20, current.windowSize + delta)))
    }

    fun adjustLookahead(delta: Int) {
        val current = _uiState.value
        _uiState.value = current.copy(lookaheadCandles = min(50, max(2, current.lookaheadCandles + delta)))
    }

    fun adjustMaxSignals(delta: Int) {
        val current = _uiState.value
        _uiState.value = current.copy(maxSignals = min(200, max(5, current.maxSignals + delta)))
    }

    fun adjustScoreThreshold(delta: Double) {
        val current = _uiState.value
        _uiState.value = current.copy(scoreThreshold = min(100.0, max(0.0, current.scoreThreshold + delta)))
    }

    fun adjustTrainWindow(delta: Int) {
        val current = _uiState.value
        _uiState.value = current.copy(trainWindow = min(300, max(40, current.trainWindow + delta)))
    }

    fun adjustTestWindow(delta: Int) {
        val current = _uiState.value
        _uiState.value = current.copy(testWindow = min(120, max(10, current.testWindow + delta)))
    }

    fun adjustStepSize(delta: Int) {
        val current = _uiState.value
        _uiState.value = current.copy(stepSize = min(120, max(5, current.stepSize + delta)))
    }

    fun cycleTakeProfit() {
        val current = _uiState.value
        _uiState.value = current.copy(takeProfitIndex = (current.takeProfitIndex + 1) % 3)
    }

    fun runBacktest() {
        if (!ensureAuthenticated()) return
        val current = _uiState.value
        viewModelScope.launch {
            _uiState.value = current.copy(loading = true, error = null)
            runCatching {
                val analyticsDeferred = async { repository.getAnalyticsSummary() }
                val backtest = repository.runBacktest(buildRunRequest(current))
                Pair(backtest, analyticsDeferred.await())
            }.onSuccess { (backtest, analytics) ->
                _uiState.value = _uiState.value.copy(
                    loading = false,
                    summary = backtest,
                    analytics = analytics,
                    error = null
                )
            }.onFailure { throwable ->
                _uiState.value = _uiState.value.copy(
                    loading = false,
                    error = throwable.message ?: "Backtest failed"
                )
            }
        }
    }

    fun runSweep() {
        if (!ensureAuthenticated()) return
        val current = _uiState.value
        viewModelScope.launch {
            _uiState.value = current.copy(loading = true, error = null)
            runCatching {
                val analyticsDeferred = async { repository.getAnalyticsSummary() }
                val sweep = repository.runBacktestSweep(
                    BacktestSweepRequestDto(
                        symbol = current.symbol,
                        market = current.market,
                        timeframe = current.timeframe,
                        window_sizes = listOf(
                            max(20, current.windowSize - 10),
                            current.windowSize,
                            min(120, current.windowSize + 10)
                        ).distinct(),
                        lookahead_options = listOf(
                            max(2, current.lookaheadCandles - 2),
                            current.lookaheadCandles,
                            min(50, current.lookaheadCandles + 2)
                        ).distinct(),
                        score_thresholds = listOf(
                            max(0.0, current.scoreThreshold - 5.0),
                            current.scoreThreshold,
                            min(100.0, current.scoreThreshold + 5.0)
                        ).distinct(),
                        take_profit_indices = listOf(0, 1, 2),
                        max_signals = current.maxSignals,
                        max_results = 10,
                        risk_settings = buildRiskSettings(),
                        trade_stats = buildTradeStats()
                    )
                )
                Pair(sweep, analyticsDeferred.await())
            }.onSuccess { (sweep, analytics) ->
                _uiState.value = _uiState.value.copy(
                    loading = false,
                    sweepSummary = sweep,
                    analytics = analytics,
                    error = null
                )
            }.onFailure { throwable ->
                _uiState.value = _uiState.value.copy(
                    loading = false,
                    error = throwable.message ?: "Backtest sweep failed"
                )
            }
        }
    }

    fun runWalkForward() {
        if (!ensureAuthenticated()) return
        val current = _uiState.value
        viewModelScope.launch {
            _uiState.value = current.copy(loading = true, error = null)
            runCatching {
                val analyticsDeferred = async { repository.getAnalyticsSummary() }
                val walkForward = repository.runWalkForward(
                    WalkForwardRequestDto(
                        symbol = current.symbol,
                        market = current.market,
                        timeframe = current.timeframe,
                        train_window = current.trainWindow,
                        test_window = current.testWindow,
                        step_size = current.stepSize,
                        lookahead_options = listOf(
                            max(2, current.lookaheadCandles - 2),
                            current.lookaheadCandles,
                            min(50, current.lookaheadCandles + 2)
                        ).distinct(),
                        window_sizes = listOf(
                            max(20, current.windowSize - 10),
                            current.windowSize,
                            min(120, current.windowSize + 10)
                        ).distinct(),
                        score_thresholds = listOf(
                            max(0.0, current.scoreThreshold - 5.0),
                            current.scoreThreshold,
                            min(100.0, current.scoreThreshold + 5.0)
                        ).distinct(),
                        take_profit_indices = listOf(0, 1, 2),
                        max_signals = current.maxSignals,
                        max_steps = 6,
                        risk_settings = buildRiskSettings(),
                        trade_stats = buildTradeStats()
                    )
                )
                Pair(walkForward, analyticsDeferred.await())
            }.onSuccess { (walkForward, analytics) ->
                _uiState.value = _uiState.value.copy(
                    loading = false,
                    walkForwardSummary = walkForward,
                    analytics = analytics,
                    error = null
                )
            }.onFailure { throwable ->
                _uiState.value = _uiState.value.copy(
                    loading = false,
                    error = throwable.message ?: "Walk-forward failed / اجرای واک‌فوروارد ناموفق بود"
                )
            }
        }
    }

    fun loadAnalytics() {
        if (!ensureAuthenticated()) return
        viewModelScope.launch {
            runCatching { repository.getAnalyticsSummary() }
                .onSuccess { analytics ->
                    _uiState.value = _uiState.value.copy(analytics = analytics)
                }
        }
    }

    private fun ensureAuthenticated(): Boolean {
        if (AuthTokenProvider.hasServerToken()) return true
        _uiState.value = _uiState.value.copy(
            loading = false,
            error = "حالت دمو: برای اجرای بک‌تست وارد حساب شوید.",
        )
        return false
    }

    private fun buildRunRequest(state: BacktestUiState) = BacktestRunRequestDto(
        symbol = state.symbol,
        market = state.market,
        timeframe = state.timeframe,
        window_size = state.windowSize,
        lookahead_candles = state.lookaheadCandles,
        score_threshold = state.scoreThreshold,
        max_signals = state.maxSignals,
        take_profit_index = state.takeProfitIndex,
        risk_settings = buildRiskSettings(),
        trade_stats = buildTradeStats()
    )

    private fun buildRiskSettings() = RiskSettingsDto(
        account_balance = 5000.0,
        risk_per_trade_pct = 1.0,
        max_daily_loss_pct = 3.0,
        max_trades_per_day = 4,
        max_consecutive_losses = 3,
        max_open_positions = 2,
        value_per_point = 1.0,
        breakeven_rr = 1.0,
        partial_tp_rr = listOf(1.0, 2.0, 3.0)
    )

    private fun buildTradeStats() = TradeStatsDto(
        trades_today = 1,
        consecutive_losses = 0,
        daily_loss_pct = 0.5,
        open_positions = 0
    )
}
