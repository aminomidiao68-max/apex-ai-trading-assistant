package com.arena.smartmoney.data.model
import com.google.gson.annotations.SerializedName

import com.google.gson.JsonObject

data class SessionResponse(
    val session_name: String,
    val market_quality: String,
    val session_score: Double
)

data class MarketOverviewItem(
    val symbol: String,
    val market: String,
    val last_price: Double?,
    val change_pct: Double?,
    val source: String,
    val status: String
)

data class MarketOverviewResponse(
    val items: List<MarketOverviewItem>
)

data class MarketStreamSnapshotDto(
    val symbol: String,
    val market: String,
    val last_price: Double?,
    val change_pct: Double?,
    val source: String,
    val status: String,
    val error: String? = null
)

data class CandleDto(
    val timestamp: String,
    val open: Double,
    val high: Double,
    val low: Double,
    val close: Double,
    val volume: Double
)

data class CandlesResponse(
    val symbol: String,
    val market: String,
    val count: Int,
    val items: List<CandleDto>
)

data class ConnectorStatusDto(
    val connector: String,
    val ready: Boolean,
    val mode: String,
    val notes: List<String>
)

data class ExecutionStatusResponse(
    val live_execution_enabled: Boolean,
    val connectors: List<ConnectorStatusDto>
)

data class ConnectorCapabilityDto(
    val connector: String,
    val market_type: String,
    val maturity: String,
    val supports_live_route: Boolean,
    val status_endpoint: String,
    val execution_endpoint: String?,
    val notes: List<String>
)

data class ExecutionCapabilitiesResponse(
    val items: List<ConnectorCapabilityDto>
)

data class ExecutionPreviewRequestDto(
    val connector: String,
    val symbol: String,
    val side: String,
    val quantity: Double,
    val signal_score: Double,
    val risk_approved: Boolean
)

data class ExecutionPreviewResponseDto(
    val connector: String,
    val eligible: Boolean,
    val normalized_side: String,
    val route: String,
    val mode: String,
    val requires_credentials: Boolean,
    val live_execution_enabled: Boolean,
    val warnings: List<String>,
    val preview_payload: Map<String, Any?>
)

data class BinanceFuturesOrderRequestDto(
    val symbol: String,
    val side: String,
    val quantity: Double,
    val order_type: String = "MARKET",
    val reduce_only: Boolean = false,
    val signal_score: Double,
    val risk_approved: Boolean
)

data class BybitOrderRequestDto(
    val symbol: String,
    val side: String,
    val quantity: Double,
    val category: String = "linear",
    val order_type: String = "Market",
    val reduce_only: Boolean = false,
    val signal_score: Double,
    val risk_approved: Boolean
)

data class OandaOrderRequestDto(
    val instrument: String,
    val units: Int,
    val stop_loss_price: Double? = null,
    val take_profit_price: Double? = null,
    val signal_score: Double,
    val risk_approved: Boolean
)

data class Mt5OrderRequestDto(
    val symbol: String,
    val side: String,
    val volume: Double,
    val signal_score: Double,
    val risk_approved: Boolean
)

data class CTraderOrderRequestDto(
    val symbol: String,
    val side: String,
    val volume: Double,
    val signal_score: Double,
    val risk_approved: Boolean
)

data class ExecutionActionResponseDto(
    val ok: Boolean? = null,
    val mode: String? = null,
    val exchange: String? = null,
    val reason: String? = null,
    val status_code: Int? = null,
    val payload: JsonObject? = null,
    val request: JsonObject? = null
)

data class ReadinessItemDto(
    val category: String,
    val key: String,
    val status: String,
    val message: String
)

data class SystemReadinessDto(
    val overall_status: String,
    val ready_count: Int,
    val warning_count: Int,
    val missing_count: Int,
    val items: List<ReadinessItemDto>
)

data class AuthRegisterRequestDto(
    val name: String,
    val email: String,
    val password: String
)

data class AuthLoginRequestDto(
    val email: String,
    val password: String
)

data class AuthUserDto(
    val id: Int,
    val name: String,
    val email: String,
    val created_at: String
)

data class AuthResponseDto(
    val access_token: String,
    val token_type: String,
    val user: AuthUserDto
)

data class MessageResponseDto(
    val message: String
)

data class DeviceTokenItemDto(
    val id: Int,
    val user_id: Int,
    val token: String,
    val platform: String,
    val device_name: String?,
    val created_at: String
)

data class DeviceTokenRegisterRequestDto(
    val token: String,
    val platform: String = "android",
    val device_name: String? = null
)

data class NotificationTestRequestDto(
    val title: String,
    val body: String
)

data class NotificationDispatchResultDto(
    val success: Boolean,
    val mode: String,
    val registered_devices: Int,
    val sent_count: Int,
    val message: String
)

data class RiskSettingsDto(
    val account_balance: Double,
    val risk_per_trade_pct: Double,
    val max_daily_loss_pct: Double,
    val max_trades_per_day: Int,
    val max_consecutive_losses: Int,
    val max_open_positions: Int,
    val value_per_point: Double,
    val breakeven_rr: Double,
    val partial_tp_rr: List<Double>
)

data class TradeStatsDto(
    val trades_today: Int,
    val consecutive_losses: Int,
    val daily_loss_pct: Double,
    val open_positions: Int
)

data class RiskPlanRequestDto(
    val entry_price: Double,
    val stop_loss: Double,
    val direction: String,
    val risk_settings: RiskSettingsDto,
    val trade_stats: TradeStatsDto
)

data class RiskPlanResponse(
    val is_trade_allowed: Boolean,
    val risk_amount: Double,
    val position_size_units: Double,
    val stop_distance: Double,
    val max_loss_amount: Double,
    val breakeven_rr: Double,
    val partial_take_profit_rr: List<Double>,
    val warnings: List<String>
)

data class LiveSignalScanRequestDto(
    val symbol: String,
    val market: String,
    val timeframe: String,
    val risk_settings: RiskSettingsDto,
    val trade_stats: TradeStatsDto,
    val client_timezone: String = "Asia/Tehran"
)

data class ScoreBreakdownDto(
    val structure: Double,
    val smc: Double,
    val order_flow: Double,
    val session: Double,
    val news: Double,
    val indicators: Double,
    val total: Double
)

data class SignalHistoryItemDto(
    val id: Int,
    val symbol: String,
    val market: String,
    val timeframe: String,
    val direction: String,
    val score: Double,
    val confidence: String,
    val session_name: String,
    val news_blocked: Boolean,
    val entry_low: Double?,
    val entry_high: Double?,
    val stop_loss: Double?,
    val take_profits: List<Double>,
    val risk_to_reward: Double?,
    val score_breakdown: ScoreBreakdownDto? = null,
    val setup_grade: String? = null,
    val execution_label: String? = null,
    val entry_model: String? = null,
    val ai_summary: String? = null,
    val confluence_tags: List<String>? = null,
    val risk_flags: List<String>? = null,
    val reasons: List<String>,
    val created_at: String
)

data class SignalHistoryResponse(
    val items: List<SignalHistoryItemDto>
)

data class TradeJournalCreateRequestDto(
    val symbol: String,
    val market: String,
    val direction: String,
    val entry_price: Double,
    val stop_loss: Double,
    val take_profit: Double?,
    val size: Double,
    val notes: String
)

data class TradeJournalCloseRequestDto(
    val exit_price: Double,
    val pnl_amount: Double?,
    val notes: String
)

data class TradeJournalItemDto(
    val id: Int,
    val symbol: String,
    val market: String,
    val direction: String,
    val entry_price: Double,
    val stop_loss: Double,
    val take_profit: Double?,
    val exit_price: Double?,
    val size: Double,
    val pnl_amount: Double?,
    val status: String,
    val notes: String,
    val created_at: String,
    val closed_at: String?
)

data class TradesResponse(
    val items: List<TradeJournalItemDto>
)

data class TradeJournalStatsDto(
    val total_trades: Int,
    val open_trades: Int,
    val closed_trades: Int,
    val wins: Int,
    val losses: Int,
    val win_rate: Double,
    val net_pnl: Double
)

data class AnalyticsSymbolCountDto(
    val symbol: String,
    val count: Int
)

data class AnalyticsSummaryDto(
    val total_saved_signals: Int,
    val buy_signals: Int,
    val sell_signals: Int,
    val neutral_signals: Int,
    val average_signal_score: Double,
    val recent_signals_24h: Int,
    val top_signal_symbols: List<AnalyticsSymbolCountDto>,
    val trade_stats: TradeJournalStatsDto
)

data class TradePerformanceBySymbolDto(
    val symbol: String,
    val trade_count: Int,
    val wins: Int,
    val losses: Int,
    val win_rate: Double,
    val net_pnl: Double
)

data class SignalSymbolStatsDto(
    val symbol: String,
    val count: Int,
    val average_score: Double
)

data class AnalyticsReportDto(
    val summary: AnalyticsSummaryDto,
    val signal_stats_by_symbol: List<SignalSymbolStatsDto>,
    val trade_performance_by_symbol: List<TradePerformanceBySymbolDto>,
    val recent_notification_events_7d: Int
)

data class BacktestRunRequestDto(
    val symbol: String,
    val market: String,
    val timeframe: String,
    val window_size: Int,
    val lookahead_candles: Int,
    val score_threshold: Double,
    val max_signals: Int,
    val take_profit_index: Int,
    val client_timezone: String = "Asia/Tehran",
    val risk_settings: RiskSettingsDto,
    val trade_stats: TradeStatsDto
)

data class BacktestTradeResultDto(
    val signal_time: String,
    val direction: String,
    val score: Double,
    val entry_price: Double,
    val stop_loss: Double,
    val take_profit: Double,
    val outcome: String,
    val rr_realized: Double,
    val bars_held: Int
)

data class BacktestSummaryDto(
    val symbol: String,
    val market: String,
    val timeframe: String,
    val tested_candles: Int,
    val evaluated_signals: Int,
    val wins: Int,
    val losses: Int,
    val unclosed: Int,
    val win_rate: Double,
    val average_score: Double,
    val net_rr: Double,
    val average_win_rr: Double,
    val average_loss_rr: Double,
    val expectancy_rr: Double,
    val profit_factor: Double,
    val longest_win_streak: Int,
    val longest_loss_streak: Int,
    val items: List<BacktestTradeResultDto>
)

data class BacktestSweepRequestDto(
    val symbol: String,
    val market: String,
    val timeframe: String,
    val window_sizes: List<Int>,
    val lookahead_options: List<Int>,
    val score_thresholds: List<Double>,
    val take_profit_indices: List<Int>,
    val max_signals: Int,
    val max_results: Int,
    val client_timezone: String = "Asia/Tehran",
    val risk_settings: RiskSettingsDto,
    val trade_stats: TradeStatsDto
)

data class BacktestSweepCandidateDto(
    val window_size: Int,
    val lookahead_candles: Int,
    val score_threshold: Double,
    val take_profit_index: Int,
    val evaluated_signals: Int,
    val wins: Int,
    val losses: Int,
    val unclosed: Int,
    val win_rate: Double,
    val net_rr: Double,
    val expectancy_rr: Double,
    val profit_factor: Double,
    val longest_win_streak: Int,
    val longest_loss_streak: Int
)

data class BacktestSweepSummaryDto(
    val symbol: String,
    val market: String,
    val timeframe: String,
    val combinations_tested: Int,
    val best_by_net_rr: BacktestSweepCandidateDto?,
    val best_by_win_rate: BacktestSweepCandidateDto?,
    val items: List<BacktestSweepCandidateDto>
)

data class WalkForwardRequestDto(
    val symbol: String,
    val market: String,
    val timeframe: String,
    val train_window: Int,
    val test_window: Int,
    val step_size: Int,
    val lookahead_options: List<Int>,
    val window_sizes: List<Int>,
    val score_thresholds: List<Double>,
    val take_profit_indices: List<Int>,
    val max_signals: Int,
    val max_steps: Int,
    val client_timezone: String = "Asia/Tehran",
    val risk_settings: RiskSettingsDto,
    val trade_stats: TradeStatsDto
)

data class WalkForwardStepResultDto(
    val step_index: Int,
    val train_start_time: String,
    val train_end_time: String,
    val test_start_time: String,
    val test_end_time: String,
    val selected_window_size: Int,
    val selected_lookahead_candles: Int,
    val selected_score_threshold: Double,
    val selected_take_profit_index: Int,
    val training_net_rr: Double,
    val training_win_rate: Double,
    val test_evaluated_signals: Int,
    val test_wins: Int,
    val test_losses: Int,
    val test_unclosed: Int,
    val test_win_rate: Double,
    val test_net_rr: Double,
    val test_expectancy_rr: Double
)

data class WalkForwardSummaryDto(
    val symbol: String,
    val market: String,
    val timeframe: String,
    val steps_executed: Int,
    val total_test_signals: Int,
    val total_wins: Int,
    val total_losses: Int,
    val total_unclosed: Int,
    val aggregate_win_rate: Double,
    val aggregate_net_rr: Double,
    val average_step_expectancy_rr: Double,
    val best_step_index: Int?,
    val worst_step_index: Int?,
    val items: List<WalkForwardStepResultDto>
)

data class NewsEvent(
    val id: String = "",
    val title: String = "",
    val country: String = "",
    val currency: String = "",
    val impact: String = "low",
    val actual: String? = null,
    val forecast: String? = null,
    val previous: String? = null,
    val unit: String = "",
    val time_unix: Long = 0L,
    val time_iso: String = "",
    val source: String = "finnhub",
    val minutes_until: Int = 0
)
data class NewsHeadline(
    val id: String = "", val title: String = "", val summary: String = "",
    val source: String = "", val category: String = "general", val url: String = "",
    val image: String = "", val time_unix: Long = 0L, val impact: String = "low",
    val country: String = "GLOBAL", val currency: String = ""
)
data class NewsBlockStatus(
    val blocked: Boolean = false, val reasons: List<String> = emptyList(),
    val block_until: Long = 0L, val active_events: List<NewsEvent> = emptyList()
)
data class NewsAdjustment(
    val bias: String = "neutral", val score_penalty: Int = 0, val note: String = ""
)
data class NewsBrief(
    val finnhub_configured: Boolean = false, val server_time_unix: Long = 0L,
    val server_time_iso: String = "", val block: NewsBlockStatus = NewsBlockStatus(),
    val adjustment: NewsAdjustment = NewsAdjustment(),
    val events: NewsEventGroups = NewsEventGroups(),
    val headlines: List<NewsHeadline> = emptyList()
)
data class NewsEventGroups(
    val upcoming: List<NewsEvent> = emptyList(),
    val live: List<NewsEvent> = emptyList(),
    val past: List<NewsEvent> = emptyList()
)

// ---- Phase C: SMC / Smart Money Concepts ----
data class SmcLevel(val entry: Float? = null, val sl: Float? = null, val tp: Float? = null)
data class SmcEvent(val kind: String = "", val dir: String = "", val index: Int = 0, val price: Float = 0f, val time: Long? = null)
data class SmcZone(val kind: String = "", val side: String = "", val index: Int = 0, val top: Float = 0f, val bottom: Float = 0f, val mitigated: Boolean = false)
data class SmcLabel(val kind: String = "", val dir: String = "", val index: Int = 0, val price: Float = 0f)
data class SmcLine(val kind: String = "", val price: Float = 0f)
data class SmcOverlay(
    val lines: List<SmcLine> = emptyList(),
    val zones: List<SmcZone> = emptyList(),
    val labels: List<SmcLabel> = emptyList()
)
data class SmcReport(
    val symbol: String = "",
    val timeframe: String = "",
    val price: Float = 0f,
    val bias: String = "neutral",
    val direction: String = "neutral",
    val confluence: Int = 0,
    val note: String = "",
    val status: String = "",
    val levels: SmcLevel = SmcLevel(),
    val events: List<SmcEvent> = emptyList(),
    @SerializedName("order_blocks") val orderBlocks: List<SmcZone> = emptyList(),
    val fvg: List<SmcZone> = emptyList(),
    val breakers: List<SmcZone> = emptyList(),
    val inducements: List<SmcLabel> = emptyList(),
    val overlay: SmcOverlay = SmcOverlay(),
    @SerializedName("candles_count") val candlesCount: Int = 0,
    @SerializedName("created_by") val createdBy: String = "Amin Omidi"
)
