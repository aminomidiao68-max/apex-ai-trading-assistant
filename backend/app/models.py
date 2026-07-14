from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class MarketType(str, Enum):
    forex = "forex"
    crypto = "crypto"


class SignalDirection(str, Enum):
    buy = "buy"
    sell = "sell"
    neutral = "neutral"


class ImpactLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Candle(BaseModel):
    timestamp: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(default=0.0, ge=0)

    @model_validator(mode="after")
    def validate_ohlc(self):
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high must be greater than or equal to open, close and low")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low must be less than or equal to open, close and high")
        return self


class OrderFlowData(BaseModel):
    delta_volume: Optional[float] = None
    open_interest_change_pct: Optional[float] = None
    funding_rate: Optional[float] = None
    aggressive_buy_ratio: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    aggressive_sell_ratio: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class NewsEvent(BaseModel):
    title: str
    currency: Optional[str] = None
    impact: ImpactLevel = ImpactLevel.medium
    event_time: datetime
    minutes_buffer_before: int = 30
    minutes_buffer_after: int = 30


class TradeStats(BaseModel):
    trades_today: int = Field(default=0, ge=0)
    consecutive_losses: int = Field(default=0, ge=0)
    daily_loss_pct: float = Field(default=0.0, ge=0.0)
    open_positions: int = Field(default=0, ge=0)
    current_drawdown_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    open_risk_amount: float = Field(default=0.0, ge=0.0)
    portfolio_heat_pct: float = Field(default=0.0, ge=0.0, le=100.0)


class RiskSettings(BaseModel):
    account_balance: float = Field(gt=0)
    risk_per_trade_pct: float = Field(default=0.5, gt=0, le=5)
    max_daily_loss_pct: float = Field(default=3.0, gt=0, le=20)
    max_trades_per_day: int = Field(default=4, ge=1, le=30)
    max_consecutive_losses: int = Field(default=3, ge=1, le=20)
    max_open_positions: int = Field(default=2, ge=1, le=20)
    value_per_point: float = Field(default=1.0, gt=0)
    breakeven_rr: float = Field(default=1.0, ge=0.5, le=5)
    partial_tp_rr: List[float] = Field(default_factory=lambda: [1.0, 2.0, 3.0])
    max_portfolio_heat_pct: float = Field(default=4.0, gt=0.0, le=25.0)
    max_open_risk_pct: float = Field(default=4.0, gt=0.0, le=25.0)
    max_correlated_risk_pct: float = Field(default=2.0, gt=0.0, le=15.0)
    drawdown_reduction_start_pct: float = Field(default=4.0, ge=0.0, le=50.0)
    max_drawdown_pct: float = Field(default=10.0, gt=0.0, le=80.0)
    min_drawdown_risk_multiplier: float = Field(default=0.25, ge=0.0, le=1.0)
    max_spread_bps: float = Field(default=8.0, gt=0.0, le=200.0)
    default_slippage_bps: float = Field(default=1.0, ge=0.0, le=100.0)
    max_slippage_bps: float = Field(default=5.0, gt=0.0, le=100.0)

    @model_validator(mode="after")
    def validate_drawdown_policy(self):
        if self.drawdown_reduction_start_pct >= self.max_drawdown_pct:
            raise ValueError("drawdown_reduction_start_pct must be below max_drawdown_pct")
        return self


class SignalRequest(BaseModel):
    symbol: str
    market: MarketType
    timeframe: str
    candles: List[Candle] = Field(min_length=20)
    higher_timeframe: Optional[str] = None
    higher_timeframe_candles: List[Candle] = Field(default_factory=list)
    lower_timeframe: Optional[str] = None
    lower_timeframe_candles: List[Candle] = Field(default_factory=list)
    order_flow: Optional[OrderFlowData] = None
    news: List[NewsEvent] = Field(default_factory=list)
    risk_settings: Optional[RiskSettings] = None
    trade_stats: Optional[TradeStats] = None
    now_utc: Optional[datetime] = None
    client_timezone: str = "UTC"


class LiveSignalScanRequest(BaseModel):
    symbol: str
    market: MarketType
    timeframe: str = "15m"
    risk_settings: RiskSettings = Field(
        default_factory=lambda: RiskSettings(account_balance=5000, risk_per_trade_pct=1.0)
    )
    trade_stats: TradeStats = Field(default_factory=TradeStats)
    client_timezone: str = "UTC"


class PortfolioPosition(BaseModel):
    symbol: str = Field(min_length=2, max_length=24)
    market: MarketType
    direction: SignalDirection
    risk_amount: float = Field(ge=0.0)
    correlation_to_candidate: Optional[float] = Field(default=None, ge=-1.0, le=1.0)
    correlation_source: Literal["explicit", "structural_proxy", "unknown"] = "unknown"


class RiskPlanRequest(BaseModel):
    entry_price: float = Field(gt=0)
    stop_loss: float = Field(gt=0)
    direction: SignalDirection
    risk_settings: RiskSettings
    trade_stats: TradeStats = Field(default_factory=TradeStats)
    symbol: str = Field(default="UNKNOWN", min_length=2, max_length=24)
    market: Optional[MarketType] = None
    spread_bps: Optional[float] = Field(default=None, ge=0.0, le=500.0)
    estimated_slippage_bps: Optional[float] = Field(default=None, ge=0.0, le=500.0)
    atr_pct: Optional[float] = Field(default=None, gt=0.0, le=100.0)
    open_positions: List[PortfolioPosition] = Field(default_factory=list, max_length=100)


class ScoreBreakdown(BaseModel):
    structure: float
    smc: float
    order_flow: float
    session: float
    news: float
    indicators: float
    total: float


class RiskPlan(BaseModel):
    is_trade_allowed: bool
    risk_amount: float
    position_size_units: float
    stop_distance: float
    max_loss_amount: float
    breakeven_rr: float
    partial_take_profit_rr: List[float]
    base_risk_amount: float = 0.0
    adjusted_risk_pct: float = 0.0
    risk_multiplier: float = 0.0
    effective_stop_distance: float = 0.0
    execution_cost_per_unit: float = 0.0
    portfolio_heat_pct: float = 0.0
    open_risk_pct: float = 0.0
    correlated_risk_pct: float = 0.0
    risk_budget_remaining: float = 0.0
    drawdown_risk_multiplier: float = 1.0
    volatility_risk_multiplier: float = 1.0
    correlation_source: str = "none"
    hard_gates: dict[str, bool] = Field(default_factory=dict)
    failed_gates: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class SignalResponse(BaseModel):
    symbol: str
    market: MarketType
    timeframe: str
    direction: SignalDirection
    score: float
    confidence: str
    session_name: str
    session_quality: str
    news_blocked: bool
    entry_low: Optional[float] = None
    entry_high: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profits: List[float] = Field(default_factory=list)
    risk_to_reward: Optional[float] = None
    score_breakdown: ScoreBreakdown
    setup_grade: str = "C"
    execution_label: str = "observe"
    entry_model: str = "No Trade"
    ai_summary: str = ""
    confluence_tags: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
    risk_plan: Optional[RiskPlan] = None


class SignalHistoryItem(BaseModel):
    id: int
    symbol: str
    market: MarketType
    timeframe: str
    direction: SignalDirection
    score: float
    confidence: str
    session_name: str
    news_blocked: bool
    entry_low: Optional[float] = None
    entry_high: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profits: List[float] = Field(default_factory=list)
    risk_to_reward: Optional[float] = None
    score_breakdown: Optional[ScoreBreakdown] = None
    setup_grade: str = "C"
    execution_label: str = "observe"
    entry_model: str = "No Trade"
    ai_summary: str = ""
    confluence_tags: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
    created_at: str


class TradeJournalCreateRequest(BaseModel):
    symbol: str = Field(min_length=2, max_length=24)
    market: MarketType
    direction: SignalDirection
    entry_price: float = Field(gt=0)
    stop_loss: float = Field(gt=0)
    take_profit: Optional[float] = Field(default=None, gt=0)
    size: float = Field(gt=0)
    notes: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def validate_trade_levels(self):
        if self.direction == SignalDirection.neutral:
            raise ValueError("neutral direction cannot be journaled as an open trade")
        if self.direction == SignalDirection.buy:
            if self.stop_loss >= self.entry_price:
                raise ValueError("buy stop_loss must be below entry_price")
            if self.take_profit is not None and self.take_profit <= self.entry_price:
                raise ValueError("buy take_profit must be above entry_price")
        if self.direction == SignalDirection.sell:
            if self.stop_loss <= self.entry_price:
                raise ValueError("sell stop_loss must be above entry_price")
            if self.take_profit is not None and self.take_profit >= self.entry_price:
                raise ValueError("sell take_profit must be below entry_price")
        return self


class TradeJournalCloseRequest(BaseModel):
    exit_price: float = Field(gt=0)
    pnl_amount: Optional[float] = None
    notes: str = ""


class TradeJournalItem(BaseModel):
    id: int
    symbol: str
    market: MarketType
    direction: SignalDirection
    entry_price: float
    stop_loss: float
    take_profit: Optional[float] = None
    exit_price: Optional[float] = None
    size: float
    pnl_amount: Optional[float] = None
    status: str
    notes: str = ""
    created_at: str
    closed_at: Optional[str] = None


class TradeJournalStats(BaseModel):
    total_trades: int
    open_trades: int
    closed_trades: int
    wins: int
    losses: int
    win_rate: float
    net_pnl: float


class AnalyticsSymbolCount(BaseModel):
    symbol: str
    count: int


class SignalSymbolStats(BaseModel):
    symbol: str
    count: int
    average_score: float


class TradePerformanceBySymbol(BaseModel):
    symbol: str
    trade_count: int
    wins: int
    losses: int
    win_rate: float
    net_pnl: float


class AnalyticsSummary(BaseModel):
    total_saved_signals: int
    buy_signals: int
    sell_signals: int
    neutral_signals: int
    average_signal_score: float
    recent_signals_24h: int
    top_signal_symbols: List[AnalyticsSymbolCount] = Field(default_factory=list)
    trade_stats: TradeJournalStats


class AnalyticsReport(BaseModel):
    summary: AnalyticsSummary
    signal_stats_by_symbol: List[SignalSymbolStats] = Field(default_factory=list)
    trade_performance_by_symbol: List[TradePerformanceBySymbol] = Field(default_factory=list)
    recent_notification_events_7d: int


class BacktestExecutionSettings(BaseModel):
    fee_bps_per_side: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    spread_bps: Optional[float] = Field(default=None, ge=0.0, le=200.0)
    slippage_bps: Optional[float] = Field(default=None, ge=0.0, le=200.0)
    funding_bps_per_8h: float = Field(default=0.0, ge=0.0, le=100.0)
    entry_expiry_bars: int = Field(default=3, ge=1, le=50)
    intrabar_policy: Literal["stop_first"] = "stop_first"
    mark_unclosed_to_market: bool = True
    prevent_overlapping_trades: bool = True


class BacktestRunRequest(BaseModel):
    symbol: str
    market: MarketType
    timeframe: str = "15m"
    window_size: int = Field(default=30, ge=20, le=120)
    lookahead_candles: int = Field(default=8, ge=2, le=50)
    score_threshold: float = Field(default=65.0, ge=0.0, le=100.0)
    max_signals: int = Field(default=40, ge=5, le=200)
    take_profit_index: int = Field(default=0, ge=0, le=2)
    client_timezone: str = "UTC"
    risk_settings: RiskSettings = Field(
        default_factory=lambda: RiskSettings(account_balance=5000, risk_per_trade_pct=1.0)
    )
    trade_stats: TradeStats = Field(default_factory=TradeStats)
    execution: BacktestExecutionSettings = Field(default_factory=BacktestExecutionSettings)


class BacktestTradeResult(BaseModel):
    signal_time: str
    direction: SignalDirection
    score: float
    entry_price: float
    stop_loss: float
    take_profit: float
    outcome: str
    rr_realized: float
    bars_held: int
    activated: bool = False
    activation_time: Optional[str] = None
    bars_to_entry: int = 0
    exit_price: Optional[float] = None
    exit_reason: str = ""
    gross_rr: float = 0.0
    costs_rr: float = 0.0
    fee_rr: float = 0.0
    funding_rr: float = 0.0


class BacktestSummary(BaseModel):
    symbol: str
    market: MarketType
    timeframe: str
    tested_candles: int
    evaluated_signals: int
    wins: int
    losses: int
    unclosed: int
    win_rate: float
    average_score: float
    net_rr: float
    average_win_rr: float
    average_loss_rr: float
    expectancy_rr: float
    profit_factor: float
    longest_win_streak: int
    longest_loss_streak: int
    activated_signals: int = 0
    no_entry: int = 0
    closed_trades: int = 0
    gross_rr: float = 0.0
    total_costs_rr: float = 0.0
    total_fee_rr: float = 0.0
    total_funding_rr: float = 0.0
    max_drawdown_rr: float = 0.0
    execution_model: str = "conservative_ohlc_v2"
    intrabar_policy: str = "stop_first"
    anti_lookahead_enforced: bool = True
    assumptions: List[str] = Field(default_factory=list)
    items: List[BacktestTradeResult] = Field(default_factory=list)


class BacktestSweepRequest(BaseModel):
    symbol: str
    market: MarketType
    timeframe: str = "15m"
    window_sizes: List[int] = Field(default_factory=lambda: [20, 30, 40], min_length=1, max_length=10)
    lookahead_options: List[int] = Field(default_factory=lambda: [6, 8, 10], min_length=1, max_length=10)
    score_thresholds: List[float] = Field(default_factory=lambda: [60.0, 65.0, 70.0], min_length=1, max_length=10)
    take_profit_indices: List[int] = Field(default_factory=lambda: [0, 1, 2], min_length=1, max_length=3)
    max_signals: int = Field(default=40, ge=5, le=200)
    max_results: int = Field(default=12, ge=3, le=50)
    minimum_activated_trades: int = Field(default=3, ge=1, le=100)
    client_timezone: str = "UTC"
    risk_settings: RiskSettings = Field(
        default_factory=lambda: RiskSettings(account_balance=5000, risk_per_trade_pct=1.0)
    )
    trade_stats: TradeStats = Field(default_factory=TradeStats)
    execution: BacktestExecutionSettings = Field(default_factory=BacktestExecutionSettings)


class BacktestSweepCandidate(BaseModel):
    window_size: int
    lookahead_candles: int
    score_threshold: float
    take_profit_index: int
    evaluated_signals: int
    wins: int
    losses: int
    unclosed: int
    win_rate: float
    net_rr: float
    expectancy_rr: float
    profit_factor: float
    longest_win_streak: int
    longest_loss_streak: int
    activated_signals: int = 0
    no_entry: int = 0
    total_costs_rr: float = 0.0
    max_drawdown_rr: float = 0.0


class BacktestSweepSummary(BaseModel):
    symbol: str
    market: MarketType
    timeframe: str
    combinations_tested: int
    best_by_net_rr: Optional[BacktestSweepCandidate] = None
    best_by_win_rate: Optional[BacktestSweepCandidate] = None
    items: List[BacktestSweepCandidate] = Field(default_factory=list)


class WalkForwardRequest(BaseModel):
    symbol: str
    market: MarketType
    timeframe: str = "15m"
    train_window: int = Field(default=80, ge=40, le=300)
    test_window: int = Field(default=30, ge=10, le=120)
    step_size: int = Field(default=20, ge=5, le=120)
    lookahead_options: List[int] = Field(default_factory=lambda: [6, 8, 10], min_length=1, max_length=10)
    window_sizes: List[int] = Field(default_factory=lambda: [20, 30, 40], min_length=1, max_length=10)
    score_thresholds: List[float] = Field(default_factory=lambda: [60.0, 65.0, 70.0], min_length=1, max_length=10)
    take_profit_indices: List[int] = Field(default_factory=lambda: [0, 1, 2], min_length=1, max_length=3)
    max_signals: int = Field(default=30, ge=5, le=200)
    max_steps: int = Field(default=8, ge=1, le=30)
    minimum_activated_trades: int = Field(default=3, ge=1, le=100)
    client_timezone: str = "UTC"
    risk_settings: RiskSettings = Field(
        default_factory=lambda: RiskSettings(account_balance=5000, risk_per_trade_pct=1.0)
    )
    trade_stats: TradeStats = Field(default_factory=TradeStats)
    execution: BacktestExecutionSettings = Field(default_factory=BacktestExecutionSettings)


class WalkForwardStepResult(BaseModel):
    step_index: int
    train_start_time: str
    train_end_time: str
    test_start_time: str
    test_end_time: str
    selected_window_size: int
    selected_lookahead_candles: int
    selected_score_threshold: float
    selected_take_profit_index: int
    training_net_rr: float
    training_win_rate: float
    test_evaluated_signals: int
    test_wins: int
    test_losses: int
    test_unclosed: int
    test_win_rate: float
    test_net_rr: float
    test_expectancy_rr: float


class WalkForwardSummary(BaseModel):
    symbol: str
    market: MarketType
    timeframe: str
    steps_executed: int
    total_test_signals: int
    total_wins: int
    total_losses: int
    total_unclosed: int
    aggregate_win_rate: float
    aggregate_net_rr: float
    average_step_expectancy_rr: float
    best_step_index: Optional[int] = None
    worst_step_index: Optional[int] = None
    items: List[WalkForwardStepResult] = Field(default_factory=list)


class ConnectorCapability(BaseModel):
    connector: str
    market_type: str
    maturity: str
    supports_live_route: bool
    status_endpoint: str
    execution_endpoint: Optional[str] = None
    notes: List[str] = Field(default_factory=list)


class ExecutionPreviewRequest(BaseModel):
    connector: Literal["binance_futures", "bybit", "oanda", "mt5", "ctrader"]
    symbol: str
    side: Literal["buy", "sell"]
    quantity: float = Field(gt=0)
    signal_score: float = Field(default=0.0, ge=0.0, le=100.0)
    risk_approved: bool = False


class ExecutionPreviewResponse(BaseModel):
    connector: str
    eligible: bool
    normalized_side: str
    route: str
    mode: str
    requires_credentials: bool
    live_execution_enabled: bool
    warnings: List[str] = Field(default_factory=list)
    preview_payload: dict = Field(default_factory=dict)


class ReadinessItem(BaseModel):
    category: str
    key: str
    status: Literal["ready", "missing", "warning"]
    message: str


class SystemReadinessResponse(BaseModel):
    overall_status: Literal["ready", "partial", "blocked"]
    ready_count: int
    warning_count: int
    missing_count: int
    items: List[ReadinessItem] = Field(default_factory=list)


class DeviceTokenRegisterRequest(BaseModel):
    token: str = Field(min_length=20)
    platform: str = Field(default="android", min_length=2, max_length=30)
    device_name: Optional[str] = None


class NotificationTestRequest(BaseModel):
    title: str = Field(default="APEX AI Test")
    body: str = Field(default="Test push from backend")


class DeviceTokenItem(BaseModel):
    id: int
    user_id: int
    token: str
    platform: str
    device_name: Optional[str] = None
    created_at: str


class NotificationDispatchResult(BaseModel):
    success: bool
    mode: str
    registered_devices: int
    sent_count: int
    message: str


class MarketSnapshot(BaseModel):
    symbol: str
    market: MarketType
    last_price: Optional[float] = None
    change_pct: Optional[float] = None
    source: str
    status: str


class ConnectorStatus(BaseModel):
    connector: str
    ready: bool
    mode: str
    notes: List[str] = Field(default_factory=list)


class BinanceFuturesOrderRequest(BaseModel):
    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: float = Field(gt=0)
    order_type: Literal["MARKET"] = "MARKET"
    reduce_only: bool = False
    signal_score: float = Field(default=0.0, ge=0.0, le=100.0)
    risk_approved: bool = False


class BybitOrderRequest(BaseModel):
    symbol: str
    side: Literal["Buy", "Sell"]
    quantity: float = Field(gt=0)
    category: Literal["linear", "inverse", "spot"] = "linear"
    order_type: Literal["Market"] = "Market"
    reduce_only: bool = False
    signal_score: float = Field(default=0.0, ge=0.0, le=100.0)
    risk_approved: bool = False


class Mt5OrderRequest(BaseModel):
    symbol: str
    side: Literal["buy", "sell"]
    volume: float = Field(gt=0)
    signal_score: float = Field(default=0.0, ge=0.0, le=100.0)
    risk_approved: bool = False


class CTraderOrderRequest(BaseModel):
    symbol: str
    side: Literal["buy", "sell"]
    volume: float = Field(gt=0)
    signal_score: float = Field(default=0.0, ge=0.0, le=100.0)
    risk_approved: bool = False


class OandaOrderRequest(BaseModel):
    instrument: str
    units: int
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    signal_score: float = Field(default=0.0, ge=0.0, le=100.0)
    risk_approved: bool = False


class AuthRegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=5, max_length=120)
    password: str = Field(min_length=8, max_length=120)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("name must contain at least two non-space characters")
        return normalized

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        local, separator, domain = normalized.partition("@")
        if not separator or not local or "." not in domain:
            raise ValueError("invalid email address")
        return normalized


class AuthLoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=120)
    password: str = Field(min_length=6, max_length=120)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class AuthUser(BaseModel):
    id: int
    name: str
    email: str
    created_at: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUser


class MessageResponse(BaseModel):
    message: str
