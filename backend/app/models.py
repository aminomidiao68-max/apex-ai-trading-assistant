from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator


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


class AIEvidenceItem(BaseModel):
    evidence_id: str = Field(pattern=r"^[A-Z][A-Z0-9_:-]{1,63}$")
    category: Literal[
        "data_quality", "market_regime", "structure", "orderflow",
        "risk", "news", "hard_gate", "invalidation", "other"
    ] = "other"
    statement: str = Field(min_length=3, max_length=500)
    source: str = Field(min_length=2, max_length=100)
    polarity: Literal["positive", "negative", "neutral"] = "neutral"
    value: Optional[str] = Field(default=None, max_length=250)
    is_real: Optional[bool] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class AIExplainRequest(BaseModel):
    symbol: str = Field(min_length=2, max_length=24)
    market: MarketType
    timeframe: str = Field(min_length=1, max_length=12)
    deterministic_status: Literal["actionable", "watch", "reject"]
    deterministic_action_label: Literal[
        "STRONG_LONG", "LONG", "STRONG_SHORT", "SHORT", "WATCH", "NO_TRADE"
    ]
    side: Literal["long", "short", "flat"]
    risk_tier: Literal["normal", "reduced", "blocked"] = "blocked"
    evidence: List[AIEvidenceItem] = Field(default_factory=list, max_length=40)
    negative_evidence: List[AIEvidenceItem] = Field(default_factory=list, max_length=40)
    failed_gates: List[str] = Field(default_factory=list, max_length=30)
    invalidation: Optional[str] = Field(default=None, max_length=300)
    missing_data: List[str] = Field(default_factory=list, max_length=30)
    probability_estimate: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    probability_is_calibrated: bool = False
    probability_label: str = Field(default="model_estimate_not_calibrated", max_length=80)
    calibration_id: Optional[str] = Field(default=None, max_length=120)
    language: Literal["fa", "en"] = "fa"
    provider: Literal["auto", "deterministic", "openai_compatible", "groq", "gemini"] = "auto"

    @model_validator(mode="after")
    def validate_ai_contract(self):
        ids = [item.evidence_id for item in self.evidence + self.negative_evidence]
        if len(ids) != len(set(ids)):
            raise ValueError("evidence_id values must be unique")
        if self.probability_is_calibrated and not self.calibration_id:
            raise ValueError("calibration_id is required for calibrated probability")
        if not self.probability_is_calibrated:
            self.probability_label = "model_estimate_not_calibrated"
            self.calibration_id = None
        return self


class AIExplainResponse(BaseModel):
    provider: str
    provider_attempted: Optional[str] = None
    model: Optional[str] = None
    mode: Literal["generated", "deterministic", "fallback", "refusal"]
    deterministic_status: str
    deterministic_action_label: str
    side: str
    summary: str
    evidence_ids: List[str] = Field(default_factory=list)
    negative_evidence_ids: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    what_would_confirm: List[str] = Field(default_factory=list)
    invalidation: Optional[str] = None
    grounded: bool
    verified: bool
    verifier_status: str
    verifier_issues: List[str] = Field(default_factory=list)
    probability_estimate: Optional[float] = None
    probability_is_calibrated: bool = False
    probability_label: str = "model_estimate_not_calibrated"
    calibration_id: Optional[str] = None
    refusal_reason: Optional[str] = None
    cached: bool = False
    latency_ms: int = 0
    external_ai_used: bool = False
    deterministic_core_preserved: bool = True
    disclaimer: str = "AI explains deterministic evidence and cannot authorize execution."


class QuantDatasetManifest(BaseModel):
    dataset_id: str = Field(min_length=3, max_length=120)
    version: str = Field(min_length=1, max_length=80)
    source: str = Field(min_length=2, max_length=120)
    symbol: str = Field(min_length=2, max_length=24)
    market: MarketType
    timeframe: str = Field(min_length=1, max_length=12)
    start_time: datetime
    end_time: datetime
    sample_count: int = Field(ge=30, le=20_000)
    source_sha256: Optional[str] = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    is_point_in_time: bool = False
    is_survivorship_bias_controlled: bool = False
    is_independent_holdout: bool = False
    data_quality_score: float = Field(default=0.0, ge=0.0, le=100.0)
    notes: List[str] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def validate_dataset_window(self):
        if self.end_time <= self.start_time:
            raise ValueError("dataset end_time must be after start_time")
        return self


class QuantWalkForwardFold(BaseModel):
    fold_id: str = Field(min_length=1, max_length=80)
    train_start_index: int = Field(ge=0)
    train_end_index: int = Field(ge=0)
    test_start_index: int = Field(ge=0)
    test_end_index: int = Field(ge=0)
    embargo_bars: int = Field(default=1, ge=1, le=10_000)
    selected_config_id: str = Field(min_length=1, max_length=120)
    test_returns_rr: List[float] = Field(min_length=1, max_length=5_000)
    test_return_indices: List[int] = Field(default_factory=list, max_length=5_000)

    @model_validator(mode="after")
    def validate_purged_fold(self):
        if self.train_end_index < self.train_start_index:
            raise ValueError("train_end_index must be >= train_start_index")
        if self.test_end_index < self.test_start_index:
            raise ValueError("test_end_index must be >= test_start_index")
        if self.train_end_index + self.embargo_bars >= self.test_start_index:
            raise ValueError("walk-forward fold violates purge/embargo boundary")
        if self.test_return_indices:
            if len(self.test_return_indices) != len(self.test_returns_rr):
                raise ValueError("test_return_indices length must match sparse test returns")
            if any(
                index < self.test_start_index or index > self.test_end_index
                for index in self.test_return_indices
            ):
                raise ValueError("test_return_indices must stay inside the test range")
            if any(
                current <= previous
                for previous, current in zip(
                    self.test_return_indices, self.test_return_indices[1:]
                )
            ):
                raise ValueError("test_return_indices must be strictly increasing")
        else:
            expected = self.test_end_index - self.test_start_index + 1
            if expected != len(self.test_returns_rr):
                raise ValueError("dense test_returns_rr length must match test index range")
        return self


class QuantValidationRequest(BaseModel):
    strategy_id: str = Field(min_length=3, max_length=120)
    strategy_version: str = Field(min_length=1, max_length=80)
    dataset: QuantDatasetManifest
    returns_rr: List[float] = Field(min_length=30, max_length=20_000)
    timestamps: List[datetime] = Field(default_factory=list, max_length=20_000)
    return_source_indices: List[int] = Field(default_factory=list, max_length=20_000)
    benchmark_returns_rr: List[float] = Field(default_factory=list, max_length=20_000)
    predicted_probabilities: List[float] = Field(default_factory=list, max_length=20_000)
    binary_outcomes: List[int] = Field(default_factory=list, max_length=20_000)
    walk_forward_folds: List[QuantWalkForwardFold] = Field(default_factory=list, max_length=30)
    strategies_tried: int = Field(default=1, ge=1, le=100_000)
    bootstrap_samples: int = Field(default=2_000, ge=500, le=10_000)
    monte_carlo_paths: int = Field(default=2_000, ge=500, le=10_000)
    confidence_level: float = Field(default=0.95, ge=0.80, le=0.999)
    risk_fraction_per_trade: float = Field(default=0.005, gt=0.0, le=0.05)
    ruin_drawdown_threshold: float = Field(default=0.30, gt=0.05, le=0.95)
    max_allowed_drawdown_rr: float = Field(default=12.0, gt=0.0, le=1_000.0)
    max_allowed_ruin_probability: float = Field(default=0.01, ge=0.0, le=0.50)
    random_seed: int = Field(default=73_021, ge=0, le=2_147_483_647)

    @model_validator(mode="after")
    def validate_quant_contract(self):
        import math

        n = len(self.returns_rr)
        if self.dataset.sample_count != n:
            raise ValueError("dataset sample_count must equal returns_rr length")
        for name, values in (
            ("returns_rr", self.returns_rr),
            ("benchmark_returns_rr", self.benchmark_returns_rr),
            ("predicted_probabilities", self.predicted_probabilities),
        ):
            if any(not math.isfinite(float(value)) for value in values):
                raise ValueError(f"{name} must contain only finite values")
        if self.timestamps:
            if len(self.timestamps) != n:
                raise ValueError("timestamps length must equal returns_rr length")
            if any(current <= previous for previous, current in zip(self.timestamps, self.timestamps[1:])):
                raise ValueError("timestamps must be strictly increasing")
        if self.return_source_indices:
            if len(self.return_source_indices) != n:
                raise ValueError("return_source_indices length must equal returns_rr length")
            if any(index < 0 for index in self.return_source_indices):
                raise ValueError("return_source_indices must be non-negative")
            if any(
                current <= previous
                for previous, current in zip(
                    self.return_source_indices, self.return_source_indices[1:]
                )
            ):
                raise ValueError("return_source_indices must be strictly increasing")
        if self.benchmark_returns_rr and len(self.benchmark_returns_rr) != n:
            raise ValueError("benchmark_returns_rr length must equal returns_rr length")
        has_probabilities = bool(self.predicted_probabilities or self.binary_outcomes)
        if has_probabilities:
            if len(self.predicted_probabilities) != n or len(self.binary_outcomes) != n:
                raise ValueError("probabilities and outcomes must both match returns_rr length")
            if any(value < 0.0 or value > 1.0 for value in self.predicted_probabilities):
                raise ValueError("predicted_probabilities must be in [0,1]")
            if any(value not in (0, 1) for value in self.binary_outcomes):
                raise ValueError("binary_outcomes must contain only 0 or 1")
        return self


class HistoricalDataCollectRequest(BaseModel):
    dataset_id: str = Field(min_length=3, max_length=120)
    version: str = Field(min_length=1, max_length=80)
    provider: Literal["auto", "okx", "yahoo", "twelvedata"] = "auto"
    symbol: str = Field(min_length=2, max_length=24)
    market: MarketType
    timeframe: str = Field(min_length=1, max_length=12)
    start_time: datetime
    end_time: datetime
    max_candles: int = Field(default=5_000, ge=30, le=20_000)
    persist: bool = True
    attest_point_in_time: bool = False
    attest_survivorship_controlled: bool = False
    attest_independent_holdout: bool = False
    notes: List[str] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def validate_historical_request(self):
        if self.end_time <= self.start_time:
            raise ValueError("historical end_time must be after start_time")
        if self.start_time.tzinfo is None or self.end_time.tzinfo is None:
            raise ValueError("historical timestamps must be timezone-aware")
        return self


class HistoricalDataCollectResponse(BaseModel):
    dataset_ref: str
    manifest: QuantDatasetManifest
    canonical_sha256: str
    provider: str
    provider_pages: int
    raw_rows: int
    accepted_rows: int
    duplicate_rows: int
    rejected_rows: int
    estimated_missing_bars: int
    gap_ratio: float
    finalized_only: bool
    stored: bool
    storage_backend: str
    issues: List[str] = Field(default_factory=list)
    first_candle: Optional[Candle] = None
    last_candle: Optional[Candle] = None


class HistoricalDatasetRecord(BaseModel):
    dataset_ref: str
    dataset_id: str
    version: str
    source: str
    symbol: str
    market: MarketType
    timeframe: str
    start_time: datetime
    end_time: datetime
    sample_count: int
    source_sha256: str
    canonical_sha256: str
    data_quality_score: float
    created_at: str


class HistoricalDatasetListResponse(BaseModel):
    items: List[HistoricalDatasetRecord] = Field(default_factory=list)
    count: int


class HistoricalDatasetManifestResponse(BaseModel):
    dataset_ref: str
    manifest: QuantDatasetManifest
    canonical_sha256: str
    stored_candle_count: int
    storage_backend: str


class QuantInterval(BaseModel):
    estimate: float
    lower: float
    upper: float
    confidence_level: float
    method: str


class QuantCalibrationDiagnostics(BaseModel):
    available: bool
    sample_count: int = 0
    brier_score: Optional[float] = None
    base_rate_brier_score: Optional[float] = None
    brier_skill_score: Optional[float] = None
    expected_calibration_error: Optional[float] = None
    maximum_calibration_error: Optional[float] = None
    log_loss: Optional[float] = None
    reliability_bins: List[dict] = Field(default_factory=list)
    eligible_for_calibration: bool = False
    probability_is_calibrated: bool = False
    calibration_id: Optional[str] = None
    scope: str = "diagnostic_only"
    failed_requirements: List[str] = Field(default_factory=list)


class QuantWalkForwardDiagnostics(BaseModel):
    available: bool
    fold_count: int = 0
    all_boundaries_purged: bool = False
    positive_fold_ratio: float = 0.0
    aggregate_test_net_rr: float = 0.0
    mean_fold_expectancy_rr: float = 0.0
    worst_fold_net_rr: float = 0.0
    selected_config_count: int = 0
    stable: bool = False


class QuantValidationResponse(BaseModel):
    strategy_id: str
    strategy_version: str
    dataset_id: str
    dataset_version: str
    analysis_fingerprint: str
    status: Literal["REJECT", "INSUFFICIENT_EVIDENCE", "WATCH", "RESEARCH_CANDIDATE"]
    sample_count: int
    empirical_win_rate: float
    net_rr: float
    expectancy_rr: float
    median_rr: float
    standard_deviation_rr: float
    profit_factor: float
    max_drawdown_rr: float
    expectancy_interval: QuantInterval
    benchmark_difference_interval: Optional[QuantInterval] = None
    sign_flip_p_value: float
    multiple_testing_alpha: float
    multiple_testing_adjusted_significant: bool
    monte_carlo_drawdown_p50_rr: float
    monte_carlo_drawdown_p95_rr: float
    monte_carlo_drawdown_p99_rr: float
    simulated_risk_of_ruin: float
    walk_forward: QuantWalkForwardDiagnostics
    calibration: QuantCalibrationDiagnostics
    hard_gates: dict[str, bool] = Field(default_factory=dict)
    failed_gates: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    actionable_for_live: bool = False
    deterministic_reproducible: bool = True
    random_seed: int
    disclaimer: str = "Research diagnostics do not prove future profitability or authorize live execution."


class PurgedSplitPlanRequest(BaseModel):
    sample_count: int = Field(ge=100, le=1_000_000)
    train_size: int = Field(ge=50, le=900_000)
    test_size: int = Field(ge=10, le=100_000)
    step_size: int = Field(ge=1, le=100_000)
    embargo_bars: int = Field(ge=1, le=100_000)
    max_folds: int = Field(default=20, ge=1, le=100)


class PurgedSplitPlanResponse(BaseModel):
    sample_count: int
    fold_count: int
    folds: List[dict] = Field(default_factory=list)
    overlap_detected: bool = False
    all_boundaries_purged: bool = True
    plan_fingerprint: str


class StoredBacktestResearchRequest(BaseModel):
    dataset_id: str = Field(min_length=3, max_length=120)
    dataset_version: str = Field(min_length=1, max_length=80)
    configuration_id: str = Field(min_length=3, max_length=120)
    configuration_frozen_at: Optional[datetime] = None
    window_size: int = Field(default=30, ge=20, le=120)
    lookahead_candles: int = Field(default=8, ge=2, le=50)
    score_threshold: float = Field(default=65.0, ge=0.0, le=100.0)
    max_signals: int = Field(default=200, ge=5, le=200)
    take_profit_index: int = Field(default=0, ge=0, le=2)
    risk_settings: RiskSettings = Field(
        default_factory=lambda: RiskSettings(account_balance=5_000, risk_per_trade_pct=1.0)
    )
    trade_stats: TradeStats = Field(default_factory=TradeStats)
    execution: BacktestExecutionSettings = Field(default_factory=BacktestExecutionSettings)


class StoredBacktestResearchResponse(BaseModel):
    dataset_ref: str
    canonical_sha256: str
    configuration_id: str
    configuration_fingerprint: str
    configuration_frozen_before_dataset: bool
    evaluation_scope: Literal["fixed_config_holdout", "retrospective_not_holdout"]
    backtest: BacktestSummary
    limitations: List[str] = Field(default_factory=list)
    actionable_for_live: bool = False


class StoredWalkForwardResearchRequest(BaseModel):
    dataset_id: str = Field(min_length=3, max_length=120)
    dataset_version: str = Field(min_length=1, max_length=80)
    train_size: int = Field(default=500, ge=100, le=15_000)
    test_size: int = Field(default=200, ge=30, le=5_000)
    step_size: int = Field(default=200, ge=30, le=5_000)
    embargo_bars: int = Field(default=10, ge=2, le=1_000)
    max_folds: int = Field(default=10, ge=3, le=30)
    window_sizes: List[int] = Field(default_factory=lambda: [20, 30, 40], min_length=1, max_length=10)
    lookahead_options: List[int] = Field(default_factory=lambda: [6, 8, 10], min_length=1, max_length=10)
    score_thresholds: List[float] = Field(default_factory=lambda: [60.0, 65.0, 70.0], min_length=1, max_length=10)
    take_profit_indices: List[int] = Field(default_factory=lambda: [0, 1, 2], min_length=1, max_length=3)
    max_signals_per_fold: int = Field(default=200, ge=5, le=200)
    minimum_activated_trades: int = Field(default=3, ge=1, le=500)
    bootstrap_samples: int = Field(default=2_000, ge=500, le=10_000)
    monte_carlo_paths: int = Field(default=2_000, ge=500, le=10_000)
    risk_fraction_per_trade: float = Field(default=0.005, gt=0.0, le=0.05)
    ruin_drawdown_threshold: float = Field(default=0.30, gt=0.05, le=0.95)
    max_allowed_drawdown_rr: float = Field(default=12.0, gt=0.0, le=1_000.0)
    max_allowed_ruin_probability: float = Field(default=0.01, ge=0.0, le=0.50)
    random_seed: int = Field(default=73_021, ge=0, le=2_147_483_647)
    risk_settings: RiskSettings = Field(
        default_factory=lambda: RiskSettings(account_balance=5_000, risk_per_trade_pct=1.0)
    )
    trade_stats: TradeStats = Field(default_factory=TradeStats)
    execution: BacktestExecutionSettings = Field(default_factory=BacktestExecutionSettings)

    @model_validator(mode="after")
    def validate_stored_walk_forward(self):
        if self.step_size < self.test_size:
            raise ValueError("step_size must be >= test_size to prevent overlapping OOS windows")
        if self.embargo_bars < max(self.lookahead_options):
            raise ValueError("embargo_bars must be >= maximum lookahead to purge label overlap")
        if min(self.window_sizes) < 20 or max(self.window_sizes) > 120:
            raise ValueError("window_sizes must remain in [20,120]")
        if self.train_size < max(self.window_sizes) + max(self.lookahead_options) + 5:
            raise ValueError("train_size is too small for the largest parameter combination")
        if self.test_size <= max(self.lookahead_options):
            raise ValueError("test_size must exceed maximum lookahead")
        return self


class StoredWalkForwardFoldResult(BaseModel):
    fold_id: str
    train_start_index: int
    train_end_index: int
    test_start_index: int
    test_end_index: int
    embargo_bars: int
    selected_config_id: str
    selected_window_size: int
    selected_lookahead_candles: int
    selected_score_threshold: float
    selected_take_profit_index: int
    training_net_rr: float
    training_win_rate: float
    test_summary: BacktestSummary
    oos_return_count: int
    fold_fingerprint: str


class StoredWalkForwardResearchResponse(BaseModel):
    dataset_ref: str
    canonical_sha256: str
    status: Literal["REJECT", "INSUFFICIENT_EVIDENCE", "WATCH", "RESEARCH_CANDIDATE"]
    fold_count: int
    combinations_per_fold: int
    total_oos_activated_trades: int
    aggregate_oos_net_rr: float
    folds: List[StoredWalkForwardFoldResult] = Field(default_factory=list)
    quant_validation: Optional[QuantValidationResponse] = None
    limitations: List[str] = Field(default_factory=list)
    actionable_for_live: bool = False


class StrategyReturnSeries(BaseModel):
    strategy_id: str = Field(min_length=2, max_length=120)
    strategy_version: str = Field(min_length=1, max_length=80)
    returns_rr: List[float] = Field(min_length=100, max_length=20_000)


class StrategyPanelValidationRequest(BaseModel):
    panel_id: str = Field(min_length=3, max_length=120)
    panel_version: str = Field(min_length=1, max_length=80)
    dataset: QuantDatasetManifest
    strategies: List[StrategyReturnSeries] = Field(min_length=3, max_length=100)
    timestamps: List[datetime] = Field(default_factory=list, max_length=20_000)
    block_count: int = Field(default=8, ge=4, le=12)
    selection_metric: Literal["expectancy", "sharpe_like"] = "sharpe_like"

    @model_validator(mode="after")
    def validate_strategy_panel(self):
        import math

        if self.block_count % 2 != 0:
            raise ValueError("block_count must be even for CSCV")
        ids = [item.strategy_id for item in self.strategies]
        if len(ids) != len(set(ids)):
            raise ValueError("strategy_id values must be unique")
        n = self.dataset.sample_count
        if n < self.block_count * 10:
            raise ValueError("dataset is too small for requested CSCV blocks")
        for item in self.strategies:
            if len(item.returns_rr) != n:
                raise ValueError("every strategy return series must match dataset sample_count")
            if any(not math.isfinite(float(value)) for value in item.returns_rr):
                raise ValueError("strategy return series must contain only finite values")
        if self.timestamps:
            if len(self.timestamps) != n:
                raise ValueError("timestamps length must match strategy observations")
            if any(current <= previous for previous, current in zip(self.timestamps, self.timestamps[1:])):
                raise ValueError("strategy panel timestamps must be strictly increasing")
        return self


class StrategyPanelValidationResponse(BaseModel):
    panel_id: str
    panel_version: str
    dataset_id: str
    analysis_fingerprint: str
    status: Literal["REJECT", "INCONCLUSIVE", "HIGH_OVERFIT_RISK", "ROBUSTNESS_CANDIDATE"]
    strategy_count: int
    observation_count: int
    block_count: int
    cscv_combinations: int
    selection_metric: str
    probability_of_backtest_overfitting: float
    median_selected_oos_rank_percentile: float
    mean_is_oos_degradation: float
    selected_strategy_frequency: dict[str, int] = Field(default_factory=dict)
    most_selected_strategy_id: Optional[str] = None
    most_selected_strategy_mean_oos_metric: Optional[float] = None
    hard_gates: dict[str, bool] = Field(default_factory=dict)
    failed_gates: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    actionable_for_live: bool = False
    deterministic_reproducible: bool = True
    disclaimer: str = "CSCV/PBO measures selection overfitting risk on this panel; it does not prove future profitability."


class DeflatedPerformanceDiagnostics(BaseModel):
    available: bool
    sample_count: int = 0
    active_return_count: int = 0
    mean_rr: float = 0.0
    standard_deviation_rr: float = 0.0
    sharpe_like_per_observation: float = 0.0
    skewness: float = 0.0
    kurtosis: float = 0.0
    probabilistic_sharpe_vs_zero: float = 0.0
    expected_max_sharpe_threshold: float = 0.0
    deflated_sharpe_probability: float = 0.0
    strategy_trials: int = 1
    eligible: bool = False
    failed_requirements: List[str] = Field(default_factory=list)
    scope: str = "per_observation_non_annualized"


class AutomatedPanelResearchRequest(BaseModel):
    experiment_id: str = Field(min_length=3, max_length=120)
    experiment_version: str = Field(min_length=1, max_length=80)
    dataset_id: str = Field(min_length=3, max_length=120)
    dataset_version: str = Field(min_length=1, max_length=80)
    holdout_fraction: float = Field(default=0.20, ge=0.10, le=0.40)
    holdout_embargo_bars: int = Field(default=10, ge=2, le=1_000)
    window_sizes: List[int] = Field(default_factory=lambda: [20, 30, 40], min_length=1, max_length=10)
    lookahead_options: List[int] = Field(default_factory=lambda: [6, 8, 10], min_length=1, max_length=10)
    score_thresholds: List[float] = Field(default_factory=lambda: [60.0, 65.0, 70.0], min_length=1, max_length=10)
    take_profit_indices: List[int] = Field(default_factory=lambda: [0, 1, 2], min_length=1, max_length=3)
    pbo_block_count: int = Field(default=8, ge=4, le=12)
    selection_metric: Literal["expectancy", "sharpe_like"] = "sharpe_like"
    max_signals_per_strategy: int = Field(default=200, ge=5, le=200)
    minimum_development_trades: int = Field(default=30, ge=10, le=200)
    minimum_holdout_trades: int = Field(default=50, ge=20, le=200)
    bootstrap_samples: int = Field(default=2_000, ge=500, le=10_000)
    monte_carlo_paths: int = Field(default=2_000, ge=500, le=10_000)
    random_seed: int = Field(default=73_021, ge=0, le=2_147_483_647)
    risk_settings: RiskSettings = Field(
        default_factory=lambda: RiskSettings(account_balance=5_000, risk_per_trade_pct=1.0)
    )
    trade_stats: TradeStats = Field(default_factory=TradeStats)
    execution: BacktestExecutionSettings = Field(default_factory=BacktestExecutionSettings)

    @model_validator(mode="after")
    def validate_automated_panel(self):
        if self.pbo_block_count % 2:
            raise ValueError("pbo_block_count must be even")
        if self.holdout_embargo_bars < max(self.lookahead_options):
            raise ValueError("holdout embargo must be >= maximum lookahead")
        if min(self.window_sizes) < 20 or max(self.window_sizes) > 120:
            raise ValueError("window_sizes must remain in [20,120]")
        combinations = (
            len(set(self.window_sizes))
            * len(set(self.lookahead_options))
            * len(set(self.score_thresholds))
            * len(set(self.take_profit_indices))
        )
        if combinations < 3:
            raise ValueError("automated panel requires at least three parameter combinations")
        if combinations > 100:
            raise ValueError("automated panel is capped at 100 parameter combinations")
        return self


class AutomatedSelectedConfiguration(BaseModel):
    strategy_id: str
    window_size: int
    lookahead_candles: int
    score_threshold: float
    take_profit_index: int
    development_activated_trades: int
    development_net_rr: float
    development_expectancy_rr: float


class AutomatedPanelResearchResponse(BaseModel):
    experiment_ref: str
    experiment_fingerprint: str
    dataset_ref: str
    canonical_sha256: str
    status: Literal[
        "REJECT", "INCONCLUSIVE", "HIGH_OVERFIT_RISK",
        "HOLDOUT_FAILED", "FINAL_HOLDOUT_CANDIDATE"
    ]
    development_start_index: int
    development_end_index: int
    holdout_start_index: int
    holdout_end_index: int
    holdout_embargo_bars: int
    parameter_combinations: int
    eligible_panel_strategies: int
    panel_validation: Optional[StrategyPanelValidationResponse] = None
    selected_configuration: Optional[AutomatedSelectedConfiguration] = None
    holdout_backtest: Optional[BacktestSummary] = None
    holdout_quant_validation: Optional[QuantValidationResponse] = None
    deflated_performance: Optional[DeflatedPerformanceDiagnostics] = None
    hard_gates: dict[str, bool] = Field(default_factory=dict)
    failed_gates: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    experiment_reused: bool = False
    actionable_for_live: bool = False


class ProviderSecretUpsertRequest(BaseModel):
    api_key: SecretStr = Field(min_length=8, max_length=500)
    api_secret: Optional[SecretStr] = Field(default=None, min_length=8, max_length=500)
    account_id: Optional[SecretStr] = Field(default=None, max_length=200)
    model: Optional[str] = Field(default=None, max_length=120)
    enabled: bool = True


class ProviderSecretStatus(BaseModel):
    provider: Literal[
        "groq", "openai", "twelvedata", "finnhub", "newsapi", "oanda",
        "binance_testnet", "bybit_testnet",
    ]
    configured: bool
    enabled: bool
    has_account_id: bool = False
    has_api_secret: bool = False
    model: Optional[str] = None
    last_test_status: Optional[str] = None
    last_tested_at: Optional[str] = None
    updated_at: Optional[str] = None


class ProviderSecretStatusResponse(BaseModel):
    vault_configured: bool
    providers: List[ProviderSecretStatus] = Field(default_factory=list)
    raw_secrets_returned: bool = False


class ProviderConnectionTestResponse(BaseModel):
    provider: str
    status: Literal["connected", "auth_failed", "unavailable", "not_configured", "vault_unavailable"]
    tested_at: str
    live_execution_enabled: bool = False
    details_exposed: bool = False


class PaperExecutionControlUpdateRequest(BaseModel):
    paper_trading_enabled: bool
    kill_switch_engaged: bool = True
    automated_feed_enabled: bool = False
    max_open_orders: int = Field(default=5, ge=1, le=50)
    max_order_notional: float = Field(default=10_000.0, gt=0.0, le=100_000_000.0)
    default_fee_bps: float = Field(default=4.0, ge=0.0, le=100.0)
    default_slippage_bps: float = Field(default=1.0, ge=0.0, le=100.0)
    max_daily_drawdown_pct: float = Field(default=3.0, gt=0.0, le=20.0)
    max_tick_age_seconds: int = Field(default=30, ge=5, le=300)
    max_leverage: float = Field(default=10.0, ge=1.0, le=50.0)
    default_maintenance_margin_rate: float = Field(default=0.005, gt=0.0, le=0.20)
    liquidation_fee_bps: float = Field(default=20.0, ge=0.0, le=200.0)
    max_margin_utilization_pct: float = Field(default=70.0, gt=0.0, le=95.0)
    max_symbol_margin_pct: float = Field(default=30.0, gt=0.0, le=100.0)
    max_risk_group_margin_pct: float = Field(default=50.0, gt=0.0, le=100.0)
    max_directional_notional_multiple: float = Field(default=3.0, gt=0.0, le=20.0)
    acknowledgement: Optional[str] = Field(default=None, max_length=80)

    @model_validator(mode="after")
    def validate_paper_control(self):
        if self.paper_trading_enabled and self.acknowledgement != "I_UNDERSTAND_PAPER_ONLY":
            raise ValueError("paper mode requires I_UNDERSTAND_PAPER_ONLY acknowledgement")
        return self


class PaperExecutionControl(BaseModel):
    paper_trading_enabled: bool = False
    kill_switch_engaged: bool = True
    automated_feed_enabled: bool = False
    max_open_orders: int = 5
    max_order_notional: float = 10_000.0
    default_fee_bps: float = 4.0
    default_slippage_bps: float = 1.0
    max_daily_drawdown_pct: float = 3.0
    max_tick_age_seconds: int = 30
    max_leverage: float = 10.0
    default_maintenance_margin_rate: float = 0.005
    liquidation_fee_bps: float = 20.0
    max_margin_utilization_pct: float = 70.0
    max_symbol_margin_pct: float = 30.0
    max_risk_group_margin_pct: float = 50.0
    max_directional_notional_multiple: float = 3.0
    updated_at: Optional[str] = None
    live_execution_enabled: bool = False


class PaperOrderCreateRequest(BaseModel):
    idempotency_key: str = Field(pattern=r"^[A-Za-z0-9_-]{12,100}$")
    symbol: str = Field(min_length=2, max_length=24)
    market: MarketType
    side: Literal["buy", "sell"]
    order_type: Literal["market", "limit"] = "market"
    quantity: float = Field(gt=0.0, le=1_000_000_000.0)
    reference_bid: float = Field(gt=0.0)
    reference_ask: float = Field(gt=0.0)
    available_quantity: Optional[float] = Field(default=None, gt=0.0)
    limit_price: Optional[float] = Field(default=None, gt=0.0)
    time_in_force: Literal["GTC", "IOC", "FOK"] = "GTC"
    max_slippage_bps: float = Field(default=5.0, ge=0.0, le=100.0)
    fee_bps: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    leverage: float = Field(default=1.0, ge=1.0, le=50.0)
    margin_mode: Literal["isolated", "cross"] = "isolated"
    correlation_snapshot_id: Optional[str] = Field(
        default=None,
        pattern=r"^[A-Za-z0-9_-]{12,100}$",
    )
    signal_score: float = Field(default=0.0, ge=0.0, le=100.0)
    risk_approved: bool = False
    strategy_id: Optional[str] = Field(default=None, max_length=120)
    setup_id: Optional[str] = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def validate_paper_order(self):
        if self.reference_ask < self.reference_bid:
            raise ValueError("reference_ask must be >= reference_bid")
        if self.order_type == "limit" and self.limit_price is None:
            raise ValueError("limit_price is required for limit orders")
        return self


class PaperMarketTickRequest(BaseModel):
    symbol: str = Field(min_length=2, max_length=24)
    bid: float = Field(gt=0.0)
    ask: float = Field(gt=0.0)
    available_quantity: float = Field(gt=0.0)
    timestamp: datetime
    source: str = Field(default="user_supplied_paper_tick", min_length=2, max_length=100)
    event_id: Optional[str] = Field(default=None, pattern=r"^[A-Za-z0-9_-]{12,100}$")

    @model_validator(mode="after")
    def validate_tick(self):
        if self.ask < self.bid:
            raise ValueError("ask must be >= bid")
        if self.timestamp.tzinfo is None:
            raise ValueError("paper tick timestamp must be timezone-aware")
        return self


class PaperFill(BaseModel):
    fill_id: str
    order_id: str
    quantity: float
    price: float
    fee_amount: float
    liquidity: str
    source: str
    created_at: str


class PaperOrderEvent(BaseModel):
    event_id: str
    order_id: str
    sequence: int
    event_type: str
    from_status: Optional[str] = None
    to_status: str
    reason: str
    payload_hash: str
    created_at: str


class PaperOrder(BaseModel):
    order_id: str
    idempotency_key: str
    symbol: str
    market: MarketType
    side: str
    order_type: str
    quantity: float
    limit_price: Optional[float] = None
    time_in_force: str
    status: str
    filled_quantity: float
    remaining_quantity: float
    average_fill_price: Optional[float] = None
    total_fees: float = 0.0
    reference_bid: float
    reference_ask: float
    max_slippage_bps: float
    leverage: float = 1.0
    margin_mode: Literal["isolated", "cross"] = "isolated"
    maintenance_margin_rate: float = 0.005
    risk_group: str = "unclassified"
    correlation_source: Literal["structural_proxy", "stored_dataset_statistical"] = "structural_proxy"
    correlation_snapshot_id: Optional[str] = None
    signal_score: float
    risk_approved: bool
    strategy_id: Optional[str] = None
    setup_id: Optional[str] = None
    created_at: str
    updated_at: str
    terminal_at: Optional[str] = None
    live_routed: bool = False
    fills: List[PaperFill] = Field(default_factory=list)
    events: List[PaperOrderEvent] = Field(default_factory=list)


class PaperOrderListResponse(BaseModel):
    items: List[PaperOrder] = Field(default_factory=list)
    count: int
    tick_event_id: Optional[str] = None
    duplicate_tick: bool = False


class PaperFeedSubscriptionUpsertRequest(BaseModel):
    symbol: str = Field(min_length=2, max_length=24, pattern=r"^[A-Za-z0-9_-]+$")
    market: MarketType = MarketType.crypto
    poll_interval_seconds: int = Field(default=15, ge=5, le=300)
    acknowledgement: str = Field(pattern=r"^I_UNDERSTAND_PAPER_ONLY$")

    @model_validator(mode="after")
    def validate_supported_feed_market(self):
        if self.market != MarketType.crypto:
            raise ValueError("automated paper feed currently supports crypto only")
        return self


class PaperFeedSyncRequest(BaseModel):
    symbols: List[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def normalize_symbols(self):
        normalized = []
        for symbol in self.symbols:
            value = symbol.strip().upper()
            if not value or len(value) > 24 or not value.replace("-", "").replace("_", "").isalnum():
                raise ValueError("invalid paper feed symbol")
            if value not in normalized:
                normalized.append(value)
        self.symbols = normalized
        return self


class PaperFeedSubscription(BaseModel):
    symbol: str
    market: MarketType
    provider: str
    enabled: bool
    poll_interval_seconds: int
    next_poll_at: str
    last_attempt_at: Optional[str] = None
    last_success_at: Optional[str] = None
    last_provider_timestamp: Optional[str] = None
    last_event_id: Optional[str] = None
    consecutive_failures: int = 0
    last_error_code: Optional[str] = None
    updated_at: str
    is_real_market_quote: bool = True
    live_routed: bool = False


class PaperFeedSubscriptionListResponse(BaseModel):
    items: List[PaperFeedSubscription] = Field(default_factory=list)
    count: int


class PaperFeedSyncItem(BaseModel):
    symbol: str
    ok: bool
    provider: str
    event_id: Optional[str] = None
    duplicate_tick: bool = False
    affected_orders: int = 0
    bid: Optional[float] = None
    ask: Optional[float] = None
    provider_timestamp: Optional[str] = None
    error_code: Optional[str] = None
    is_real_market_quote: bool = True
    live_routed: bool = False


class PaperFeedSyncResponse(BaseModel):
    items: List[PaperFeedSyncItem] = Field(default_factory=list)
    count: int
    success_count: int
    failure_count: int
    live_execution_enabled: bool = False


class PaperFeedStatus(BaseModel):
    automated_feed_enabled: bool
    paper_trading_enabled: bool
    kill_switch_engaged: bool
    worker_enabled: bool
    subscription_count: int
    due_subscription_count: int
    latest_success_at: Optional[str] = None
    latest_error_code: Optional[str] = None
    supported_markets: List[str] = Field(default_factory=lambda: ["crypto"])
    providers: List[str] = Field(default_factory=lambda: ["okx_public"])
    is_real_market_quote: bool = True
    live_execution_enabled: bool = False


class PaperPosition(BaseModel):
    symbol: str
    market: MarketType
    quantity: float
    average_entry_price: Optional[float] = None
    mark_price: Optional[float] = None
    leverage: float = 1.0
    margin_mode: Literal["isolated", "cross"] = "isolated"
    risk_group: str = "unclassified"
    correlation_source: Literal["structural_proxy", "stored_dataset_statistical"] = "structural_proxy"
    correlation_snapshot_id: Optional[str] = None
    initial_margin: float = 0.0
    maintenance_margin: float = 0.0
    maintenance_margin_rate: float = 0.005
    margin_ratio_pct: Optional[float] = None
    liquidation_price: Optional[float] = None
    accumulated_funding: float = 0.0
    position_status: Literal["open", "flat", "liquidated"] = "flat"
    liquidated_at: Optional[str] = None
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    total_fees: float = 0.0
    notional: float = 0.0
    updated_at: str


class PaperPortfolio(BaseModel):
    initial_cash: float
    cash_balance: float
    equity: float
    peak_equity: float
    realized_pnl: float
    unrealized_pnl: float
    total_fees: float
    total_funding: float = 0.0
    used_margin: float = 0.0
    maintenance_margin: float = 0.0
    free_margin: float = 0.0
    margin_utilization_pct: float = 0.0
    margin_level_pct: Optional[float] = None
    liquidation_count: int = 0
    daily_drawdown_pct: float
    kill_switch_engaged: bool
    live_execution_enabled: bool = False
    positions: List[PaperPosition] = Field(default_factory=list)
    updated_at: str


class PaperFundingSettlementRequest(BaseModel):
    event_id: str = Field(pattern=r"^[A-Za-z0-9_-]{12,100}$")
    symbol: str = Field(min_length=2, max_length=24, pattern=r"^[A-Za-z0-9_-]+$")
    funding_rate: float = Field(ge=-0.05, le=0.05)
    timestamp: datetime
    source: str = Field(default="user_supplied_paper_funding", min_length=2, max_length=100)

    @model_validator(mode="after")
    def validate_funding_timestamp(self):
        if self.timestamp.tzinfo is None:
            raise ValueError("funding timestamp must be timezone-aware")
        return self


class PaperMarginEvent(BaseModel):
    event_id: str
    event_type: Literal["funding", "liquidation"]
    symbol: str
    amount: float
    funding_rate: Optional[float] = None
    mark_price: Optional[float] = None
    realized_pnl: float = 0.0
    source: str
    is_real_rate: bool = False
    payload_hash: str
    created_at: str
    live_routed: bool = False


class PaperFundingSettlementResponse(BaseModel):
    event: PaperMarginEvent
    duplicate: bool = False
    cash_balance: float
    total_funding: float
    live_execution_enabled: bool = False


class PaperMarginEventListResponse(BaseModel):
    items: List[PaperMarginEvent] = Field(default_factory=list)
    count: int
    live_execution_enabled: bool = False


class PaperReconciliationResponse(BaseModel):
    order_id: str
    consistent: bool
    filled_quantity_matches: bool
    average_price_matches: bool
    fees_match: bool
    event_sequence_valid: bool
    terminal_state_valid: bool
    issues: List[str] = Field(default_factory=list)
    live_execution_enabled: bool = False


PaperTestnetConnector = Literal["binance_futures_testnet", "bybit_testnet"]


class PaperConnectorProbeRequest(BaseModel):
    force: bool = False


class PaperConnectorCheckpoint(BaseModel):
    connector: PaperTestnetConnector
    state: Literal["unknown", "connected", "backoff", "disconnected"]
    public_connectivity_only: bool = True
    authenticated: bool = False
    order_routing_enabled: bool = False
    consecutive_failures: int = 0
    backoff_until: Optional[str] = None
    latency_ms: Optional[int] = None
    server_time_offset_ms: Optional[int] = None
    last_probe_at: Optional[str] = None
    last_success_at: Optional[str] = None
    last_error_code: Optional[str] = None
    live_execution_enabled: bool = False


class PaperConnectorCheckpointListResponse(BaseModel):
    items: List[PaperConnectorCheckpoint] = Field(default_factory=list)
    count: int
    live_execution_enabled: bool = False


class PaperShadowOrderSnapshot(BaseModel):
    order_id: str = Field(min_length=8, max_length=100)
    status: Literal["accepted", "working", "partially_filled", "filled", "canceled", "rejected", "expired"]
    filled_quantity: float = Field(ge=0.0)
    average_fill_price: Optional[float] = Field(default=None, gt=0.0)
    total_fees: float = Field(default=0.0, ge=0.0)


class PaperShadowReconciliationRequest(BaseModel):
    run_id: str = Field(pattern=r"^[A-Za-z0-9_-]{12,100}$")
    connector: PaperTestnetConnector
    snapshot_id: str = Field(pattern=r"^[A-Za-z0-9_-]{8,100}$")
    snapshot_timestamp: datetime
    orders: List[PaperShadowOrderSnapshot] = Field(default_factory=list, max_length=200)
    source: str = Field(default="user_supplied_shadow_snapshot", min_length=2, max_length=100)

    @model_validator(mode="after")
    def validate_shadow_snapshot(self):
        if self.snapshot_timestamp.tzinfo is None:
            raise ValueError("shadow snapshot timestamp must be timezone-aware")
        ids = [item.order_id for item in self.orders]
        if len(ids) != len(set(ids)):
            raise ValueError("shadow snapshot order_id values must be unique")
        return self


class PaperShadowReconciliationResponse(BaseModel):
    run_id: str
    connector: PaperTestnetConnector
    snapshot_id: str
    status: Literal["CONSISTENT", "MISMATCH", "EMPTY"]
    matched_orders: int = 0
    mismatched_orders: int = 0
    missing_local_orders: int = 0
    missing_external_orders: int = 0
    issues: List[str] = Field(default_factory=list)
    duplicate: bool = False
    snapshot_verified_by_provider: bool = False
    public_connectivity_only: bool = True
    actionable_for_live: bool = False
    live_execution_enabled: bool = False
    created_at: str


class PaperPrivateTestnetSyncRequest(BaseModel):
    force: bool = False


class PaperPrivateTestnetReconciliationResponse(BaseModel):
    reconciliation_id: str
    connector: PaperTestnetConnector
    status: Literal["CONSISTENT", "MISMATCH", "EMPTY", "UNAVAILABLE"]
    external_order_count: int = 0
    external_fill_count: int = 0
    matched_orders: int = 0
    mismatched_orders: int = 0
    issues: List[str] = Field(default_factory=list)
    provider_authenticated: bool = True
    provider_snapshot_verified: bool = True
    read_only: bool = True
    order_routing_enabled: bool = False
    actionable_for_live: bool = False
    live_execution_enabled: bool = False
    created_at: str


class PaperRecoveryDrillRequest(BaseModel):
    connector: PaperTestnetConnector
    outcomes: List[bool] = Field(min_length=1, max_length=50)


class PaperRecoveryDrillResponse(BaseModel):
    connector: PaperTestnetConnector
    transitions: List[str]
    final_state: Literal["connected", "backoff"]
    consecutive_failures: int
    final_backoff_seconds: int
    deterministic: bool = True
    network_called: bool = False
    order_routing_enabled: bool = False
    live_execution_enabled: bool = False


class PaperLedgerAuditResponse(BaseModel):
    consistent: bool
    order_count: int
    fill_count: int
    event_count: int
    position_count: int
    margin_event_count: int
    issues: List[str] = Field(default_factory=list)
    repair_performed: bool = False
    actionable_for_live: bool = False
    live_execution_enabled: bool = False
    audited_at: str


class PaperCorrelationDatasetRef(BaseModel):
    dataset_id: str = Field(min_length=3, max_length=120)
    version: str = Field(min_length=1, max_length=80)


class PaperCorrelationSnapshotRequest(BaseModel):
    snapshot_id: str = Field(pattern=r"^[A-Za-z0-9_-]{12,100}$")
    datasets: List[PaperCorrelationDatasetRef] = Field(min_length=2, max_length=12)
    minimum_observations: int = Field(default=60, ge=30, le=100_000)
    cluster_threshold: float = Field(default=0.70, ge=0.30, le=0.99)

    @model_validator(mode="after")
    def validate_unique_correlation_datasets(self):
        refs = [(item.dataset_id, item.version) for item in self.datasets]
        if len(refs) != len(set(refs)):
            raise ValueError("correlation dataset references must be unique")
        return self


class PaperCorrelationSnapshotResponse(BaseModel):
    snapshot_id: str
    symbols: List[str]
    dataset_refs: List[str]
    observations: int
    matrix: dict[str, dict[str, float]]
    clusters: List[List[str]]
    cluster_threshold: float
    shrinkage_weight: float
    canonical_sha256: str
    duplicate: bool = False
    correlation_source: Literal["stored_dataset_statistical"] = "stored_dataset_statistical"
    actionable_for_live: bool = False
    live_execution_enabled: bool = False
    created_at: str


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
