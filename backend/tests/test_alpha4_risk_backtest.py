from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.models import (
    BacktestExecutionSettings,
    BacktestRunRequest,
    Candle,
    MarketType,
    PortfolioPosition,
    RiskPlanRequest,
    RiskSettings,
    SignalDirection,
    TradeStats,
)
from app.services.backtest_service import BacktestService
from app.services.risk_engine import build_risk_plan


def _risk_settings(**overrides) -> RiskSettings:
    values = {
        "account_balance": 10_000,
        "risk_per_trade_pct": 1.0,
        "max_portfolio_heat_pct": 4.0,
        "max_open_risk_pct": 4.0,
        "max_correlated_risk_pct": 2.0,
        "drawdown_reduction_start_pct": 4.0,
        "max_drawdown_pct": 10.0,
        "max_spread_bps": 8.0,
        "max_slippage_bps": 5.0,
        "default_slippage_bps": 1.0,
    }
    values.update(overrides)
    return RiskSettings(**values)


def _risk_request(**overrides) -> RiskPlanRequest:
    values = {
        "symbol": "BTCUSDT",
        "market": MarketType.crypto,
        "direction": SignalDirection.buy,
        "entry_price": 100.0,
        "stop_loss": 98.0,
        "spread_bps": 2.0,
        "estimated_slippage_bps": 1.0,
        "atr_pct": 1.5,
        "risk_settings": _risk_settings(),
        "trade_stats": TradeStats(),
    }
    values.update(overrides)
    return RiskPlanRequest(**values)


def _candles(rows: list[tuple[float, float, float, float]], start_minute: int = 0) -> list[Candle]:
    start = datetime(2026, 7, 13, tzinfo=timezone.utc) + timedelta(minutes=start_minute)
    return [
        Candle(
            timestamp=start + timedelta(minutes=index * 15),
            open=row[0],
            high=row[1],
            low=row[2],
            close=row[3],
            volume=1000,
        )
        for index, row in enumerate(rows)
    ]


def test_alpha4_risk_plan_enforces_drawdown_heat_and_known_execution_costs():
    baseline = build_risk_plan(_risk_request())
    assert baseline.is_trade_allowed is True
    assert baseline.risk_amount == 100.0
    assert baseline.effective_stop_distance > baseline.stop_distance
    assert all(baseline.hard_gates.values())

    reduced = build_risk_plan(
        _risk_request(trade_stats=TradeStats(current_drawdown_pct=7.0))
    )
    assert reduced.is_trade_allowed is True
    assert 0.25 < reduced.drawdown_risk_multiplier < 1.0
    assert reduced.risk_amount < reduced.base_risk_amount

    unknown_spread = build_risk_plan(_risk_request(spread_bps=None))
    assert unknown_spread.is_trade_allowed is False
    assert "execution_spread_known" in unknown_spread.failed_gates

    heat_blocked = build_risk_plan(
        _risk_request(
            risk_settings=_risk_settings(max_correlated_risk_pct=10.0),
            trade_stats=TradeStats(open_risk_amount=350.0, open_positions=1),
        )
    )
    assert heat_blocked.is_trade_allowed is False
    assert "open_risk_budget" in heat_blocked.failed_gates
    assert "portfolio_heat" in heat_blocked.failed_gates
    assert heat_blocked.position_size_units == 0

    drawdown_blocked = build_risk_plan(
        _risk_request(trade_stats=TradeStats(current_drawdown_pct=10.0))
    )
    assert drawdown_blocked.is_trade_allowed is False
    assert "drawdown" in drawdown_blocked.failed_gates
    assert drawdown_blocked.risk_multiplier == 0.0


def test_alpha4_correlation_is_explicit_or_transparently_structural_proxy():
    explicit = PortfolioPosition(
        symbol="ETHUSDT",
        market=MarketType.crypto,
        direction=SignalDirection.buy,
        risk_amount=150.0,
        correlation_to_candidate=0.90,
        correlation_source="explicit",
    )
    blocked = build_risk_plan(_risk_request(open_positions=[explicit]))
    assert blocked.is_trade_allowed is False
    assert blocked.correlated_risk_pct == 2.5
    assert blocked.correlation_source == "explicit"
    assert "correlation_exposure" in blocked.failed_gates

    proxy_position = PortfolioPosition(
        symbol="ETHUSDT",
        market=MarketType.crypto,
        direction=SignalDirection.buy,
        risk_amount=150.0,
    )
    proxied = build_risk_plan(_risk_request(open_positions=[proxy_position]))
    assert proxied.correlation_source == "structural_proxy"
    assert "correlation_exposure" in proxied.failed_gates
    assert any("structural proxy" in warning for warning in proxied.warnings)

    hedge = PortfolioPosition(
        symbol="ETHUSDT",
        market=MarketType.crypto,
        direction=SignalDirection.sell,
        risk_amount=150.0,
        correlation_to_candidate=0.90,
        correlation_source="explicit",
    )
    hedged = build_risk_plan(_risk_request(open_positions=[hedge]))
    assert hedged.correlated_risk_pct == 1.0
    assert "correlation_exposure" not in hedged.failed_gates


def test_conservative_intrabar_requires_entry_and_chooses_stop_first():
    service = BacktestService()
    execution = BacktestExecutionSettings(
        fee_bps_per_side=4.0,
        spread_bps=2.0,
        slippage_bps=1.0,
        entry_expiry_bars=2,
    )

    no_entry = service._evaluate_trade(
        SignalDirection.buy,
        _candles([(103.0, 104.0, 102.0, 103.5), (104.0, 105.0, 103.0, 104.5)]),
        entry=100.0,
        stop=99.0,
        take_profit=102.0,
        market=MarketType.crypto,
        timeframe="15m",
        execution=execution,
    )
    assert no_entry["outcome"] == "no_entry"
    assert no_entry["activated"] is False
    assert no_entry["rr_realized"] == 0.0

    ambiguous = service._evaluate_trade(
        SignalDirection.buy,
        _candles([(100.0, 103.0, 98.0, 102.0)]),
        entry=100.0,
        stop=99.0,
        take_profit=102.0,
        market=MarketType.crypto,
        timeframe="15m",
        execution=execution,
    )
    assert ambiguous["outcome"] == "loss"
    assert ambiguous["exit_reason"] == "ambiguous_bar_stop_first"
    assert ambiguous["gross_rr"] == -1.0
    assert ambiguous["rr_realized"] < -1.0
    assert ambiguous["costs_rr"] > 0


def test_backtest_charges_fees_slippage_funding_and_marks_unclosed():
    service = BacktestService()
    result = service._evaluate_trade(
        SignalDirection.buy,
        _candles([(100.0, 100.5, 99.8, 100.2), (100.2, 101.2, 100.0, 101.0)]),
        entry=100.0,
        stop=98.0,
        take_profit=105.0,
        market=MarketType.crypto,
        timeframe="4h",
        execution=BacktestExecutionSettings(
            fee_bps_per_side=5.0,
            spread_bps=2.0,
            slippage_bps=1.0,
            funding_bps_per_8h=3.0,
            entry_expiry_bars=1,
            mark_unclosed_to_market=True,
        ),
    )
    assert result["outcome"] == "unclosed"
    assert result["exit_reason"] == "marked_to_market"
    assert result["gross_rr"] == 0.5
    assert result["fee_rr"] > 0
    assert result["funding_rr"] > 0
    assert result["rr_realized"] < result["gross_rr"]


class _AlwaysLongEngine:
    def __init__(self) -> None:
        self.seen_windows: list[list[datetime]] = []

    def analyze(self, request):
        self.seen_windows.append([candle.timestamp for candle in request.candles])
        return SimpleNamespace(
            direction=SignalDirection.buy,
            score=90.0,
            entry_low=100.0,
            entry_high=100.0,
            stop_loss=99.0,
            take_profits=[101.0, 102.0, 103.0],
        )


def test_anti_lookahead_uses_only_closed_window_and_prevents_overlap():
    history = _candles([(100.0, 100.2, 99.8, 100.0)] * 20)
    future = _candles(
        [
            (100.0, 100.4, 99.8, 100.1),
            (100.1, 100.5, 99.9, 100.2),
            (100.2, 100.6, 100.0, 100.3),
            (100.3, 101.2, 100.1, 101.0),
            (100.0, 100.4, 99.8, 100.1),
            (100.1, 100.5, 99.9, 100.2),
        ],
        start_minute=20 * 15,
    )
    candles = history + future
    engine = _AlwaysLongEngine()
    service = BacktestService(engine)
    request = BacktestRunRequest(
        symbol="BTCUSDT",
        market=MarketType.crypto,
        timeframe="15m",
        window_size=20,
        lookahead_candles=3,
        score_threshold=65,
        max_signals=5,
        execution=BacktestExecutionSettings(
            fee_bps_per_side=0,
            spread_bps=0,
            slippage_bps=0,
            entry_expiry_bars=1,
            prevent_overlapping_trades=True,
        ),
    )

    one = service._generate_results(request, candles, start_index=20, end_index=21)
    assert len(one) == 1
    assert engine.seen_windows[0] == [candle.timestamp for candle in candles[:20]]
    assert candles[20].timestamp not in engine.seen_windows[0]
    assert one[0].signal_time == candles[19].timestamp.isoformat()

    engine.seen_windows.clear()
    all_results = service._generate_results(request, candles)
    signal_positions = [
        next(i for i, candle in enumerate(candles) if candle.timestamp.isoformat() == item.signal_time)
        for item in all_results
    ]
    assert all(b - a >= 3 for a, b in zip(signal_positions, signal_positions[1:]))

    summary = service._summarize_results(request, len(candles), all_results)
    assert summary.anti_lookahead_enforced is True
    assert summary.execution_model == "conservative_ohlc_v2"
    assert "signals_use_closed_candles_only" in summary.assumptions


def test_backtest_rejects_non_monotonic_timestamps():
    service = BacktestService(_AlwaysLongEngine())
    items = _candles([(100.0, 101.0, 99.0, 100.0)] * 25)
    items[5] = items[4]
    request = BacktestRunRequest(symbol="BTCUSDT", market=MarketType.crypto)
    with pytest.raises(ValueError, match="strictly increasing"):
        service.run(request, items)
