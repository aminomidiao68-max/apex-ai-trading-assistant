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

data class PaperExecutionControlUpdateDto(
    val paper_trading_enabled: Boolean,
    val kill_switch_engaged: Boolean,
    val automated_feed_enabled: Boolean = false,
    val max_open_orders: Int = 5,
    val max_order_notional: Double = 10000.0,
    val default_fee_bps: Double = 4.0,
    val default_slippage_bps: Double = 1.0,
    val max_daily_drawdown_pct: Double = 3.0,
    val max_tick_age_seconds: Int = 30,
    val max_leverage: Double = 10.0,
    val default_maintenance_margin_rate: Double = 0.005,
    val liquidation_fee_bps: Double = 20.0,
    val max_margin_utilization_pct: Double = 70.0,
    val max_symbol_margin_pct: Double = 30.0,
    val max_risk_group_margin_pct: Double = 50.0,
    val max_directional_notional_multiple: Double = 3.0,
    val acknowledgement: String? = null
)

data class PaperExecutionControlDto(
    val paper_trading_enabled: Boolean = false,
    val kill_switch_engaged: Boolean = true,
    val automated_feed_enabled: Boolean = false,
    val max_open_orders: Int = 5,
    val max_order_notional: Double = 10000.0,
    val default_fee_bps: Double = 4.0,
    val default_slippage_bps: Double = 1.0,
    val max_daily_drawdown_pct: Double = 3.0,
    val max_tick_age_seconds: Int = 30,
    val max_leverage: Double = 10.0,
    val default_maintenance_margin_rate: Double = 0.005,
    val liquidation_fee_bps: Double = 20.0,
    val max_margin_utilization_pct: Double = 70.0,
    val max_symbol_margin_pct: Double = 30.0,
    val max_risk_group_margin_pct: Double = 50.0,
    val max_directional_notional_multiple: Double = 3.0,
    val updated_at: String? = null,
    val live_execution_enabled: Boolean = false
)

data class PaperFeedSubscriptionUpsertDto(
    val symbol: String,
    val market: String = "crypto",
    val poll_interval_seconds: Int = 15,
    val acknowledgement: String = "I_UNDERSTAND_PAPER_ONLY"
)

data class PaperFeedSubscriptionDto(
    val symbol: String,
    val market: String,
    val provider: String,
    val enabled: Boolean,
    val poll_interval_seconds: Int,
    val next_poll_at: String,
    val last_attempt_at: String? = null,
    val last_success_at: String? = null,
    val last_provider_timestamp: String? = null,
    val last_event_id: String? = null,
    val consecutive_failures: Int = 0,
    val last_error_code: String? = null,
    val updated_at: String,
    val is_real_market_quote: Boolean = true,
    val live_routed: Boolean = false
)

data class PaperFeedSubscriptionListDto(
    val items: List<PaperFeedSubscriptionDto> = emptyList(),
    val count: Int = 0
)

data class PaperFeedStatusDto(
    val automated_feed_enabled: Boolean = false,
    val paper_trading_enabled: Boolean = false,
    val kill_switch_engaged: Boolean = true,
    val worker_enabled: Boolean = false,
    val subscription_count: Int = 0,
    val due_subscription_count: Int = 0,
    val latest_success_at: String? = null,
    val latest_error_code: String? = null,
    val supported_markets: List<String> = emptyList(),
    val providers: List<String> = emptyList(),
    val is_real_market_quote: Boolean = true,
    val live_execution_enabled: Boolean = false
)

data class PaperFeedSyncRequestDto(
    val symbols: List<String> = emptyList()
)

data class PaperFeedSyncItemDto(
    val symbol: String,
    val ok: Boolean,
    val provider: String,
    val event_id: String? = null,
    val duplicate_tick: Boolean = false,
    val affected_orders: Int = 0,
    val bid: Double? = null,
    val ask: Double? = null,
    val provider_timestamp: String? = null,
    val error_code: String? = null,
    val is_real_market_quote: Boolean = true,
    val live_routed: Boolean = false
)

data class PaperFeedSyncResponseDto(
    val items: List<PaperFeedSyncItemDto> = emptyList(),
    val count: Int = 0,
    val success_count: Int = 0,
    val failure_count: Int = 0,
    val live_execution_enabled: Boolean = false
)

data class PaperConnectorProbeRequestDto(
    val force: Boolean = false
)

data class PaperConnectorCheckpointDto(
    val connector: String,
    val state: String,
    val public_connectivity_only: Boolean = true,
    val authenticated: Boolean = false,
    val order_routing_enabled: Boolean = false,
    val consecutive_failures: Int = 0,
    val backoff_until: String? = null,
    val latency_ms: Int? = null,
    val server_time_offset_ms: Int? = null,
    val last_probe_at: String? = null,
    val last_success_at: String? = null,
    val last_error_code: String? = null,
    val live_execution_enabled: Boolean = false
)

data class PaperConnectorCheckpointListDto(
    val items: List<PaperConnectorCheckpointDto> = emptyList(),
    val count: Int = 0,
    val live_execution_enabled: Boolean = false
)

data class PaperLedgerAuditDto(
    val consistent: Boolean,
    val order_count: Int,
    val fill_count: Int,
    val event_count: Int,
    val position_count: Int,
    val margin_event_count: Int,
    val issues: List<String> = emptyList(),
    val repair_performed: Boolean = false,
    val actionable_for_live: Boolean = false,
    val live_execution_enabled: Boolean = false,
    val audited_at: String
)

data class PaperOrderCreateRequestDto(
    val idempotency_key: String,
    val symbol: String,
    val market: String,
    val side: String,
    val order_type: String,
    val quantity: Double,
    val reference_bid: Double,
    val reference_ask: Double,
    val available_quantity: Double? = null,
    val limit_price: Double? = null,
    val time_in_force: String = "GTC",
    val max_slippage_bps: Double = 5.0,
    val fee_bps: Double? = null,
    val leverage: Double = 1.0,
    val margin_mode: String = "isolated",
    val correlation_snapshot_id: String? = null,
    val signal_score: Double = 85.0,
    val risk_approved: Boolean = true,
    val strategy_id: String? = null,
    val setup_id: String? = null
)

data class PaperFillDto(
    val fill_id: String,
    val order_id: String,
    val quantity: Double,
    val price: Double,
    val fee_amount: Double,
    val liquidity: String,
    val source: String,
    val created_at: String
)

data class PaperOrderEventDto(
    val event_id: String,
    val order_id: String,
    val sequence: Int,
    val event_type: String,
    val from_status: String? = null,
    val to_status: String,
    val reason: String,
    val payload_hash: String,
    val created_at: String
)

data class PaperOrderDto(
    val order_id: String,
    val idempotency_key: String,
    val symbol: String,
    val market: String,
    val side: String,
    val order_type: String,
    val quantity: Double,
    val limit_price: Double? = null,
    val time_in_force: String,
    val status: String,
    val filled_quantity: Double,
    val remaining_quantity: Double,
    val average_fill_price: Double? = null,
    val total_fees: Double = 0.0,
    val reference_bid: Double,
    val reference_ask: Double,
    val max_slippage_bps: Double,
    val leverage: Double = 1.0,
    val margin_mode: String = "isolated",
    val maintenance_margin_rate: Double = 0.005,
    val risk_group: String = "unclassified",
    val correlation_source: String = "structural_proxy",
    val correlation_snapshot_id: String? = null,
    val signal_score: Double,
    val risk_approved: Boolean,
    val strategy_id: String? = null,
    val setup_id: String? = null,
    val created_at: String,
    val updated_at: String,
    val terminal_at: String? = null,
    val live_routed: Boolean = false,
    val fills: List<PaperFillDto> = emptyList(),
    val events: List<PaperOrderEventDto> = emptyList()
)

data class PaperOrderListResponseDto(
    val items: List<PaperOrderDto> = emptyList(),
    val count: Int = 0
)

data class PaperPositionDto(
    val symbol: String,
    val market: String,
    val quantity: Double,
    val average_entry_price: Double? = null,
    val mark_price: Double? = null,
    val leverage: Double = 1.0,
    val margin_mode: String = "isolated",
    val risk_group: String = "unclassified",
    val correlation_source: String = "structural_proxy",
    val correlation_snapshot_id: String? = null,
    val initial_margin: Double = 0.0,
    val maintenance_margin: Double = 0.0,
    val maintenance_margin_rate: Double = 0.005,
    val margin_ratio_pct: Double? = null,
    val liquidation_price: Double? = null,
    val accumulated_funding: Double = 0.0,
    val position_status: String = "flat",
    val liquidated_at: String? = null,
    val realized_pnl: Double = 0.0,
    val unrealized_pnl: Double = 0.0,
    val total_fees: Double = 0.0,
    val notional: Double = 0.0,
    val updated_at: String
)

data class PaperPortfolioDto(
    val initial_cash: Double,
    val cash_balance: Double,
    val equity: Double,
    val peak_equity: Double,
    val realized_pnl: Double,
    val unrealized_pnl: Double,
    val total_fees: Double,
    val total_funding: Double = 0.0,
    val used_margin: Double = 0.0,
    val maintenance_margin: Double = 0.0,
    val free_margin: Double = 0.0,
    val margin_utilization_pct: Double = 0.0,
    val margin_level_pct: Double? = null,
    val liquidation_count: Int = 0,
    val daily_drawdown_pct: Double,
    val kill_switch_engaged: Boolean,
    val live_execution_enabled: Boolean = false,
    val positions: List<PaperPositionDto> = emptyList(),
    val updated_at: String
)

data class PaperReconciliationResponseDto(
    val order_id: String,
    val consistent: Boolean,
    val filled_quantity_matches: Boolean,
    val average_price_matches: Boolean,
    val fees_match: Boolean,
    val event_sequence_valid: Boolean,
    val terminal_state_valid: Boolean,
    val issues: List<String> = emptyList(),
    val live_execution_enabled: Boolean = false
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

data class ProviderSecretUpsertRequestDto(
    val api_key: String,
    val api_secret: String? = null,
    val account_id: String? = null,
    val model: String? = null,
    val enabled: Boolean = true
)

data class ProviderSecretStatusDto(
    val provider: String,
    val configured: Boolean,
    val enabled: Boolean,
    val has_account_id: Boolean = false,
    val has_api_secret: Boolean = false,
    val model: String? = null,
    val last_test_status: String? = null,
    val last_tested_at: String? = null,
    val updated_at: String? = null
)

data class ProviderSecretStatusResponseDto(
    val vault_configured: Boolean,
    val providers: List<ProviderSecretStatusDto> = emptyList(),
    val raw_secrets_returned: Boolean = false
)

data class ProviderConnectionTestResponseDto(
    val provider: String,
    val status: String,
    val tested_at: String,
    val live_execution_enabled: Boolean = false,
    val details_exposed: Boolean = false
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
    val partial_tp_rr: List<Double>,
    val max_portfolio_heat_pct: Double = 4.0,
    val max_open_risk_pct: Double = 4.0,
    val max_correlated_risk_pct: Double = 2.0,
    val drawdown_reduction_start_pct: Double = 4.0,
    val max_drawdown_pct: Double = 10.0,
    val min_drawdown_risk_multiplier: Double = 0.25,
    val max_spread_bps: Double = 8.0,
    val default_slippage_bps: Double = 1.0,
    val max_slippage_bps: Double = 5.0
)

data class TradeStatsDto(
    val trades_today: Int,
    val consecutive_losses: Int,
    val daily_loss_pct: Double,
    val open_positions: Int,
    val current_drawdown_pct: Double = 0.0,
    val open_risk_amount: Double = 0.0,
    val portfolio_heat_pct: Double = 0.0
)

data class PortfolioPositionDto(
    val symbol: String,
    val market: String,
    val direction: String,
    val risk_amount: Double,
    val correlation_to_candidate: Double? = null,
    val correlation_source: String = "unknown"
)

data class RiskPlanRequestDto(
    val entry_price: Double,
    val stop_loss: Double,
    val direction: String,
    val risk_settings: RiskSettingsDto,
    val trade_stats: TradeStatsDto,
    val symbol: String = "BTCUSDT",
    val market: String = "crypto",
    val spread_bps: Double? = 2.0,
    val estimated_slippage_bps: Double? = 1.0,
    val atr_pct: Double? = 1.0,
    val open_positions: List<PortfolioPositionDto> = emptyList()
)

data class RiskPlanResponse(
    val is_trade_allowed: Boolean,
    val risk_amount: Double,
    val position_size_units: Double,
    val stop_distance: Double,
    val max_loss_amount: Double,
    val breakeven_rr: Double,
    val partial_take_profit_rr: List<Double>,
    val base_risk_amount: Double = 0.0,
    val adjusted_risk_pct: Double = 0.0,
    val risk_multiplier: Double = 0.0,
    val effective_stop_distance: Double = 0.0,
    val execution_cost_per_unit: Double = 0.0,
    val portfolio_heat_pct: Double = 0.0,
    val open_risk_pct: Double = 0.0,
    val correlated_risk_pct: Double = 0.0,
    val risk_budget_remaining: Double = 0.0,
    val drawdown_risk_multiplier: Double = 1.0,
    val volatility_risk_multiplier: Double = 1.0,
    val correlation_source: String = "none",
    val hard_gates: Map<String, Boolean> = emptyMap(),
    val failed_gates: List<String> = emptyList(),
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

data class BacktestExecutionSettingsDto(
    val fee_bps_per_side: Double? = null,
    val spread_bps: Double? = null,
    val slippage_bps: Double? = null,
    val funding_bps_per_8h: Double = 0.0,
    val entry_expiry_bars: Int = 3,
    val intrabar_policy: String = "stop_first",
    val mark_unclosed_to_market: Boolean = true,
    val prevent_overlapping_trades: Boolean = true
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
    val trade_stats: TradeStatsDto,
    val execution: BacktestExecutionSettingsDto = BacktestExecutionSettingsDto()
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
    val bars_held: Int,
    val activated: Boolean = false,
    val activation_time: String? = null,
    val bars_to_entry: Int = 0,
    val exit_price: Double? = null,
    val exit_reason: String = "",
    val gross_rr: Double = 0.0,
    val costs_rr: Double = 0.0,
    val fee_rr: Double = 0.0,
    val funding_rr: Double = 0.0
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
    val activated_signals: Int = 0,
    val no_entry: Int = 0,
    val closed_trades: Int = 0,
    val gross_rr: Double = 0.0,
    val total_costs_rr: Double = 0.0,
    val total_fee_rr: Double = 0.0,
    val total_funding_rr: Double = 0.0,
    val max_drawdown_rr: Double = 0.0,
    val execution_model: String = "conservative_ohlc_v2",
    val intrabar_policy: String = "stop_first",
    val anti_lookahead_enforced: Boolean = true,
    val assumptions: List<String> = emptyList(),
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
    val trade_stats: TradeStatsDto,
    val minimum_activated_trades: Int = 3,
    val execution: BacktestExecutionSettingsDto = BacktestExecutionSettingsDto()
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
    val longest_loss_streak: Int,
    val activated_signals: Int = 0,
    val no_entry: Int = 0,
    val total_costs_rr: Double = 0.0,
    val max_drawdown_rr: Double = 0.0
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
    val trade_stats: TradeStatsDto,
    val minimum_activated_trades: Int = 3,
    val execution: BacktestExecutionSettingsDto = BacktestExecutionSettingsDto()
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
    @SerializedName("time_tehran") val timeTehran: String = "",
    val volatility: Double = 0.0,
    val phase: String = "upcoming",
    val source: String = "finnhub",
    val minutes_until: Int = 0
)
data class NewsHeadline(
    val id: String = "", val title: String = "", val summary: String = "",
    val source: String = "", val category: String = "general", val url: String = "",
    val image: String = "", val time_unix: Long = 0L,
    @SerializedName("published_at") val publishedAt: String = "",
    val impact: String = "low",
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

// ---- Phase C: SMC / Smart Money Concepts v2 ----
data class SmcLevel(val entry: Float? = null, val sl: Float? = null, val tp: Float? = null)
data class SmcEvent(val kind: String = "", val dir: String = "", val index: Int = 0, val price: Float = 0f, val time: Long? = null)
data class SmcCandle(
    val t: Long = 0L, val o: Float = 0f, val h: Float = 0f,
    val l: Float = 0f, val c: Float = 0f, val v: Float = 0f
)
data class SmcZone(
    val kind: String = "", val side: String = "", val index: Int = 0,
    val top: Float = 0f, val bottom: Float = 0f, val mitigated: Boolean = false,
    @SerializedName("start_idx") val startIdx: Int = -1,
    @SerializedName("end_idx") val endIdx: Int = -1,
    val name: String = "",
    val inverse: Boolean = false,
    @SerializedName("size_pct") val sizePct: Float = 0f,
    @SerializedName("full_height") val fullHeight: Boolean = false,
    val quality: Int = 5,
    val fresh: Boolean = true,
    val vol: Float = 0f,
    val color: String = ""
)
data class SmcLabel(val kind: String = "", val dir: String = "", val index: Int = 0, val price: Float = 0f)
data class SmcLine(val kind: String = "", val price: Float = 0f)
data class SmcOverlay(
    val lines: List<SmcLine> = emptyList(),
    val zones: List<SmcZone> = emptyList(),
    val labels: List<SmcLabel> = emptyList()
)
data class SmcOrderFlow(
    val source: String = "unknown",
    @SerializedName("is_real") val isReal: Boolean = false,
    val confidence: Float = 0f,
    val delta: Float = 0f,
    val pressure: String = "neutral",
    val cvd: Float = 0f,
    val cvd_curve: List<Map<String, Double>> = emptyList(),
    @SerializedName("volume_spike") val volumeSpike: Boolean = false,
    @SerializedName("cvd_divergence") val cvdDivergence: String? = null,
    val absorption: Boolean = false,
    val climax: Boolean = false,
    @SerializedName("avg_volume") val avgVolume: Float = 0f,
    @SerializedName("aggressive_buy_ratio") val aggressiveBuyRatio: Float? = null,
    @SerializedName("aggressive_sell_ratio") val aggressiveSellRatio: Float? = null,
    @SerializedName("large_trade_imbalance") val largeTradeImbalance: Float? = null,
    @SerializedName("depth_imbalance") val depthImbalance: Float? = null,
    @SerializedName("spread_bps") val spreadBps: Float? = null,
    @SerializedName("open_interest_usd") val openInterestUsd: Double? = null,
    @SerializedName("open_interest_change_pct") val openInterestChangePct: Float? = null,
    @SerializedName("funding_rate") val fundingRate: Float? = null,
    val disclaimer: String = ""
)
data class SmcVisibleRange(
    val low: Float = 0f,
    val high: Float = 0f
)
data class SmcHtf(
    val timeframe: String? = null,
    val bias: String? = null
)
data class SmcConfluenceFactor(
    val name: String = "",
    val points: Int = 0,
    val why: String = ""
)
data class SmcWatching(
    val direction: String = "neutral",
    val entry: Float = 0f,
    val sl: Float = 0f,
    val tp: Float = 0f,
    val distance: Float = 0f,
    val atr: Float = 0f,
    val reasons: List<String> = emptyList(),
    val status: String = ""
)
data class SmcAiEvidence(
    @SerializedName("evidence_id") val evidenceId: String = "",
    val category: String = "other",
    val statement: String = "",
    val source: String = "",
    val polarity: String = "neutral",
    val value: String? = null,
    @SerializedName("is_real") val isReal: Boolean? = null,
    val confidence: Float? = null
)

data class SmcAiNarrative(
    val side: String = "انتظار",
    val trend: String = "خنثی",
    val summary: String = "",
    val recommendation: String = "",
    val confluence: Int = 0,
    val rr: Float = 0f,
    val probability: Int = 0,
    val verdict: String = "",
    @SerializedName("setup_type") val setupType: String = "-",
    val grade: String = "-",
    val factors: List<SmcConfluenceFactor> = emptyList(),
    val provider: String = "deterministic",
    @SerializedName("provider_attempted") val providerAttempted: String? = null,
    val mode: String = "deterministic",
    @SerializedName("deterministic_status") val deterministicStatus: String = "reject",
    @SerializedName("deterministic_action_label") val deterministicActionLabel: String = "NO_TRADE",
    val grounded: Boolean = false,
    val verified: Boolean = false,
    @SerializedName("verifier_status") val verifierStatus: String = "",
    @SerializedName("verifier_issues") val verifierIssues: List<String> = emptyList(),
    @SerializedName("evidence_ids") val evidenceIds: List<String> = emptyList(),
    @SerializedName("negative_evidence_ids") val negativeEvidenceIds: List<String> = emptyList(),
    @SerializedName("evidence_items") val evidenceItems: List<SmcAiEvidence> = emptyList(),
    @SerializedName("negative_evidence") val negativeEvidence: List<SmcAiEvidence> = emptyList(),
    val risks: List<String> = emptyList(),
    @SerializedName("what_would_confirm") val whatWouldConfirm: List<String> = emptyList(),
    val invalidation: String? = null,
    @SerializedName("refusal_reason") val refusalReason: String? = null,
    @SerializedName("external_ai_used") val externalAiUsed: Boolean = false,
    @SerializedName("probability_is_calibrated") val probabilityIsCalibrated: Boolean = false,
    @SerializedName("probability_label") val probabilityLabel: String = "model_estimate_not_calibrated",
    @SerializedName("deterministic_core_preserved") val deterministicCorePreserved: Boolean = true
)
data class SmcSignal(
    val symbol: String = "",
    val market: String = "forex",
    val timeframe: String = "",
    val bias: String = "neutral",
    val direction: String = "neutral",
    val confluence: Int = 0,
    val rr: Float = 0f,
    val price: Float = 0f,
    val note: String = "",
    val levels: SmcLevel = SmcLevel(),
    val tp1: Float? = null,
    val tp2: Float? = null,
    val tp3: Float? = null,
    val probability: Int = 0,
    val grade: String = "-",
    @SerializedName("setup_type") val setupType: String = "-",
    @SerializedName("omega_compliant") val omegaCompliant: Boolean = false,
    @SerializedName("omega_reasons") val omegaReasons: List<String> = emptyList(),
    @SerializedName("action_label") val actionLabel: String = "WAIT",
    val ai: SmcAiNarrative = SmcAiNarrative(),
    val status: String = "ok"
)
data class SmcScanResponse(
    val signals: List<SmcSignal> = emptyList(),
    val watching: List<SmcSignal> = emptyList(),
    @SerializedName("total_scanned") val totalScanned: Int = 0,
    val count: Int = 0,
    @SerializedName("watching_count") val watchingCount: Int = 0,
    @SerializedName("created_by") val createdBy: String = "Amin Omidi"
)

data class TradeSetupDto(
    val id: String = "",
    val symbol: String = "",
    val market: String = "",
    val timeframe: String = "",
    val status: String = "forming",
    @SerializedName("setup_type") val setupType: String = "-",
    @SerializedName("setup_family") val setupFamily: String = "SMC/ICT",
    val direction: String = "neutral",
    val bias: String = "neutral",
    val grade: String = "-",
    val confluence: Int = 0,
    val probability: Int = 0,
    val rr: Float = 0f,
    val price: Float = 0f,
    val atr: Float = 0f,
    val entry: Float? = null,
    @SerializedName("entry_low") val entryLow: Float? = null,
    @SerializedName("entry_high") val entryHigh: Float? = null,
    @SerializedName("stop_loss") val stopLoss: Float? = null,
    val tp1: Float? = null,
    val tp2: Float? = null,
    val tp3: Float? = null,
    val invalidation: Float? = null,
    @SerializedName("omega_compliant") val omegaCompliant: Boolean = false,
    @SerializedName("action_label") val actionLabel: String = "WAIT",
    @SerializedName("mtf_aligned") val mtfAligned: Boolean = false,
    @SerializedName("htf_bias") val htfBias: String? = null,
    val note: String = "",
    @SerializedName("missing_confirmations") val missingConfirmations: List<String> = emptyList(),
    val factors: List<String> = emptyList(),
    val decision: SmcStrictDecision = SmcStrictDecision(),
    @SerializedName("data_quality") val dataQuality: SmcDataQuality = SmcDataQuality(),
    @SerializedName("market_regime") val marketRegime: SmcMarketRegime = SmcMarketRegime(),
    @SerializedName("lifecycle_state") val lifecycleState: String = status,
    @SerializedName("first_seen_at") val firstSeenAt: String? = null,
    @SerializedName("last_seen_at") val lastSeenAt: String? = null,
    @SerializedName("armed_at") val armedAt: String? = null,
    @SerializedName("confirmed_at") val confirmedAt: String? = null,
    @SerializedName("triggered_at") val triggeredAt: String? = null,
    @SerializedName("terminated_at") val terminatedAt: String? = null,
    @SerializedName("expires_at") val expiresAt: String? = null,
    @SerializedName("cooldown_until") val cooldownUntil: String? = null,
    @SerializedName("transition_reason") val transitionReason: String = "",
    @SerializedName("scan_count") val scanCount: Int = 0,
    @SerializedName("missing_scans") val missingScans: Int = 0
)

data class TradeSetupsResponseDto(
    val active: List<TradeSetupDto> = emptyList(),
    val forming: List<TradeSetupDto> = emptyList(),
    val armed: List<TradeSetupDto> = emptyList(),
    val confirmed: List<TradeSetupDto> = emptyList(),
    val triggered: List<TradeSetupDto> = emptyList(),
    val invalidated: List<TradeSetupDto> = emptyList(),
    val expired: List<TradeSetupDto> = emptyList(),
    @SerializedName("active_count") val activeCount: Int = 0,
    @SerializedName("forming_count") val formingCount: Int = 0,
    @SerializedName("armed_count") val armedCount: Int = 0,
    @SerializedName("confirmed_count") val confirmedCount: Int = 0,
    @SerializedName("triggered_count") val triggeredCount: Int = 0,
    @SerializedName("invalidated_count") val invalidatedCount: Int = 0,
    @SerializedName("expired_count") val expiredCount: Int = 0,
    @SerializedName("total_scanned") val totalScanned: Int = 0,
    @SerializedName("generated_at") val generatedAt: String = "",
    val cached: Boolean = false,
    @SerializedName("cache_age_seconds") val cacheAgeSeconds: Float = 0f
)

data class SmcEntryZone(
    val high: Float = 0f,
    val low: Float = 0f
)

data class SmcDataQuality(
    val score: Float = 0f,
    val tradable: Boolean = false,
    val issues: List<String> = emptyList(),
    val warnings: List<String> = emptyList()
)

data class SmcMarketRegime(
    val name: String = "unknown",
    val direction: String = "neutral",
    @SerializedName("efficiency_ratio") val efficiencyRatio: Float = 0f,
    @SerializedName("volatility_ratio") val volatilityRatio: Float = 0f,
    @SerializedName("risk_multiplier") val riskMultiplier: Float = 0f
)

data class SmcDecisionOrderFlow(
    val source: String = "unknown",
    @SerializedName("is_real") val isReal: Boolean = false,
    val confidence: Float = 0f,
    val pressure: String = "neutral",
    val aligned: Boolean = false,
    @SerializedName("spread_bps") val spreadBps: Float? = null,
    @SerializedName("depth_imbalance") val depthImbalance: Float? = null,
    @SerializedName("funding_rate") val fundingRate: Float? = null,
    @SerializedName("open_interest_change_pct") val openInterestChangePct: Float? = null
)

data class SmcStrictDecision(
    val status: String = "reject",
    val side: String = "flat",
    @SerializedName("action_label") val actionLabel: String = "NO_TRADE",
    @SerializedName("strict_omega_compliant") val strictOmegaCompliant: Boolean = false,
    @SerializedName("risk_tier") val riskTier: String = "blocked",
    @SerializedName("risk_multiplier") val riskMultiplier: Float = 0f,
    @SerializedName("hard_gates_total") val hardGatesTotal: Int = 0,
    @SerializedName("hard_gates_passed") val hardGatesPassed: Int = 0,
    @SerializedName("failed_gates") val failedGates: List<String> = emptyList(),
    @SerializedName("no_trade_reason") val noTradeReason: String? = null,
    @SerializedName("expires_after_bars") val expiresAfterBars: Int = 0,
    val orderflow: SmcDecisionOrderFlow = SmcDecisionOrderFlow()
)

data class SmcReport(
    val symbol: String = "",
    val timeframe: String = "",
    val market: String = "forex",
    val price: Float = 0f,
    val bias: String = "neutral",
    val direction: String = "neutral",
    val confluence: Int = 0,
    val probability: Int = 0,
    @SerializedName("setup_type") val setupType: String = "-",
    val rr: Float = 0f,
    val atr: Float = 0f,
    val note: String = "",
    val status: String = "",
    val grade: String = "-",
    @SerializedName("trend_strength") val trendStrength: Int = 0,
    val vwap: Float = 0f,
    val levels: SmcLevel = SmcLevel(),
    val tp1: Float? = null,
    val tp2: Float? = null,
    val tp3: Float? = null,
    val invalidation: Float? = null,
    @SerializedName("entry_zone") val entryZone: SmcEntryZone? = null,
    @SerializedName("plan_lines") val planLines: List<SmcLine> = emptyList(),
    @SerializedName("premium_zone") val premiumZone: String = "eq",
    @SerializedName("mtf_aligned") val mtfAligned: Boolean = false,
    @SerializedName("htf_bias") val htfBias: String? = null,
    @SerializedName("news_blocked") val newsBlocked: Boolean = false,
    @SerializedName("volume_spike") val volumeSpike: Boolean = false,
    @SerializedName("session_active") val sessionActive: String = "-",
    @SerializedName("session_weight") val sessionWeight: Float = 0f,
    @SerializedName("session_color") val sessionColor: String = "#f59e0b",
    val events: List<SmcEvent> = emptyList(),
    @SerializedName("order_blocks") val orderBlocks: List<SmcZone> = emptyList(),
    val fvg: List<SmcZone> = emptyList(),
    val breakers: List<SmcZone> = emptyList(),
    val inducements: List<SmcLabel> = emptyList(),
    val sessions: List<String> = emptyList(),
    val killzones: List<SmcZone> = emptyList(),
    val orderflow: SmcOrderFlow = SmcOrderFlow(),
    val ai: SmcAiNarrative = SmcAiNarrative(),
    val htf: SmcHtf = SmcHtf(),
    @SerializedName("visible_range") val visibleRange: SmcVisibleRange = SmcVisibleRange(),
    val candles: List<SmcCandle> = emptyList(),
    val overlay: SmcOverlay = SmcOverlay(),
    val watching: List<SmcWatching> = emptyList(),
    @SerializedName("confluence_factors") val confluenceFactors: List<SmcConfluenceFactor> = emptyList(),
    val candlesCount: Int = 0,
    @SerializedName("created_by") val createdBy: String = "Amin Omidi",
    @SerializedName("omega_compliant") val omegaCompliant: Boolean = false,
    @SerializedName("strict_omega_compliant") val strictOmegaCompliant: Boolean = false,
    @SerializedName("omega_reasons") val omegaReasons: List<String> = emptyList(),
    @SerializedName("action_label") val actionLabel: String = "WAIT",
    val decision: SmcStrictDecision = SmcStrictDecision(),
    @SerializedName("data_quality") val dataQuality: SmcDataQuality = SmcDataQuality(),
    @SerializedName("market_regime") val marketRegime: SmcMarketRegime = SmcMarketRegime()
)
