from __future__ import annotations

from app.models import (
    RiskPlanRequest,
    ScoreBreakdown,
    SignalDirection,
    SignalRequest,
    SignalResponse,
    TradeStats,
)
from app.services.indicators import atr, ema, momentum_histogram, rsi
from app.services.news_engine import evaluate_news_risk
from app.services.risk_engine import build_risk_plan
from app.services.session_engine import evaluate_session
from app.services.smc_engine import detect_smc_features


class SignalEngine:
    def analyze(self, request: SignalRequest) -> SignalResponse:
        closes = [c.close for c in request.candles]
        highs = [c.high for c in request.candles]
        lows = [c.low for c in request.candles]
        last_price = closes[-1]

        ema20 = ema(closes, 20)
        ema50 = ema(closes, 50)
        current_rsi = rsi(closes, 14)
        current_atr = atr(highs, lows, closes, 14)
        momentum = momentum_histogram(closes)

        structure_score = 0.0
        indicator_score = 0.0
        bull_bias = 0.0
        bear_bias = 0.0
        reasons: list[str] = []

        if ema20 > ema50 and last_price > ema20:
            structure_score += 16
            indicator_score += 5
            bull_bias += 1.5
            reasons.append("Price above EMA20/EMA50 with bullish structure")
        elif ema20 < ema50 and last_price < ema20:
            structure_score += 16
            indicator_score += 5
            bear_bias += 1.5
            reasons.append("Price below EMA20/EMA50 with bearish structure")
        else:
            structure_score += 8
            reasons.append("Mixed structure, no clear trend dominance")

        if 45 <= current_rsi <= 65:
            indicator_score += 3
        elif current_rsi > 65:
            bull_bias += 0.8
            indicator_score += 4
            reasons.append("RSI supports bullish momentum")
        elif current_rsi < 35:
            bear_bias += 0.8
            indicator_score += 4
            reasons.append("RSI supports bearish momentum")

        if momentum > 0:
            bull_bias += 0.6
            indicator_score += 2
        elif momentum < 0:
            bear_bias += 0.6
            indicator_score += 2

        structure_score = min(structure_score, 25.0)
        indicator_score = min(indicator_score, 10.0)

        smc = detect_smc_features(request.candles)
        smc_score = smc["score"]
        reasons.extend(smc["reasons"])
        if smc["direction"] == SignalDirection.buy:
            bull_bias += 1.6
        elif smc["direction"] == SignalDirection.sell:
            bear_bias += 1.6

        order_flow_score = 8.0
        if request.order_flow:
            of = request.order_flow
            if (of.delta_volume or 0) > 0:
                bull_bias += 0.6
                order_flow_score += 3
            elif (of.delta_volume or 0) < 0:
                bear_bias += 0.6
                order_flow_score += 3

            if request.market.value == "crypto":
                if (of.open_interest_change_pct or 0) > 0:
                    order_flow_score += 2
                if (of.funding_rate or 0) > 0.02:
                    bear_bias += 0.3
                elif (of.funding_rate or 0) < -0.02:
                    bull_bias += 0.3
                if (of.aggressive_buy_ratio or 0) > 0.55:
                    bull_bias += 0.6
                    order_flow_score += 3
                if (of.aggressive_sell_ratio or 0) > 0.55:
                    bear_bias += 0.6
                    order_flow_score += 3
        order_flow_score = min(order_flow_score, 20.0)

        session = evaluate_session(request.now_utc)
        session_score = session["score"]
        if session["quality"] == "high":
            reasons.append(f"Active trading session: {session['session_name']}")
        else:
            reasons.append("Off-session conditions reduce setup quality")

        news = evaluate_news_risk(request.news, request.now_utc)
        news_score = news["score"]
        reasons.extend(news["warnings"])

        if news["blocked"]:
            direction = SignalDirection.neutral
        else:
            if bull_bias > bear_bias + 0.4:
                direction = SignalDirection.buy
            elif bear_bias > bull_bias + 0.4:
                direction = SignalDirection.sell
            else:
                direction = SignalDirection.neutral

        if direction == SignalDirection.buy and ema20 > ema50 and smc["direction"] == SignalDirection.buy:
            structure_score = min(structure_score + 4, 25.0)
            indicator_score = min(indicator_score + 1.5, 10.0)
            reasons.append("Bullish multi-layer confluence confirmed")
        elif direction == SignalDirection.sell and ema20 < ema50 and smc["direction"] == SignalDirection.sell:
            structure_score = min(structure_score + 4, 25.0)
            indicator_score = min(indicator_score + 1.5, 10.0)
            reasons.append("Bearish multi-layer confluence confirmed")

        if current_atr > 0 and session["quality"] == "high" and not news["blocked"]:
            indicator_score = min(indicator_score + 1.0, 10.0)
            reasons.append("Volatility and session conditions support execution")

        entry_low = None
        entry_high = None
        stop_loss = None
        take_profits: list[float] = []
        rr = None

        if direction == SignalDirection.buy:
            zone = smc.get("bullish_ob") or smc.get("fvg")
            entry_low = (zone or {}).get("low", last_price - current_atr * 0.2)
            entry_high = (zone or {}).get("high", last_price)
            stop_loss = min(smc.get("recent_low", last_price - current_atr), entry_low - current_atr * 0.2)
            risk = max(((entry_low + entry_high) / 2) - stop_loss, current_atr * 0.5)
            mid_entry = (entry_low + entry_high) / 2
            take_profits = [round(mid_entry + risk * n, 6) for n in (1, 2, 3)]
            rr = 3.0
        elif direction == SignalDirection.sell:
            zone = smc.get("bearish_ob") or smc.get("fvg")
            entry_low = (zone or {}).get("low", last_price)
            entry_high = (zone or {}).get("high", last_price + current_atr * 0.2)
            stop_loss = max(smc.get("recent_high", last_price + current_atr), entry_high + current_atr * 0.2)
            risk = max(stop_loss - ((entry_low + entry_high) / 2), current_atr * 0.5)
            mid_entry = (entry_low + entry_high) / 2
            take_profits = [round(mid_entry - risk * n, 6) for n in (1, 2, 3)]
            rr = 3.0

        total_score = round(structure_score + smc_score + order_flow_score + session_score + news_score + indicator_score, 2)
        total_score = min(total_score, 100.0)

        confidence = "low"
        if total_score >= 80:
            confidence = "high"
        elif total_score >= 65:
            confidence = "medium"

        risk_plan = None
        if request.risk_settings and direction != SignalDirection.neutral and stop_loss is not None:
            risk_plan = build_risk_plan(
                RiskPlanRequest(
                    entry_price=round((entry_low + entry_high) / 2, 6),
                    stop_loss=round(stop_loss, 6),
                    direction=direction,
                    risk_settings=request.risk_settings,
                    trade_stats=request.trade_stats or TradeStats(),
                )
            )
            if not risk_plan.is_trade_allowed:
                reasons.extend(risk_plan.warnings)

        breakdown = ScoreBreakdown(
            structure=round(structure_score, 2),
            smc=round(smc_score, 2),
            order_flow=round(order_flow_score, 2),
            session=round(session_score, 2),
            news=round(news_score, 2),
            indicators=round(indicator_score, 2),
            total=total_score,
        )

        return SignalResponse(
            symbol=request.symbol,
            market=request.market,
            timeframe=request.timeframe,
            direction=direction,
            score=total_score,
            confidence=confidence,
            session_name=session["session_name"],
            session_quality=session["quality"],
            news_blocked=news["blocked"],
            entry_low=round(entry_low, 6) if entry_low is not None else None,
            entry_high=round(entry_high, 6) if entry_high is not None else None,
            stop_loss=round(stop_loss, 6) if stop_loss is not None else None,
            take_profits=take_profits,
            risk_to_reward=rr,
            score_breakdown=breakdown,
            reasons=reasons,
            risk_plan=risk_plan,
        )
