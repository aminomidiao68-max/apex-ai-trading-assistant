from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import (
    AuthLoginRequest,
    AuthRegisterRequest,
    BacktestRunRequest,
    BacktestSweepRequest,
    WalkForwardRequest,
    BinanceFuturesOrderRequest,
    ConnectorCapability,
    ExecutionPreviewRequest,
    BybitOrderRequest,
    CTraderOrderRequest,
    DeviceTokenRegisterRequest,
    LiveSignalScanRequest,
    MessageResponse,
    Mt5OrderRequest,
    NotificationTestRequest,
    OandaOrderRequest,
    RiskPlanRequest,
    SignalRequest,
    TradeJournalCloseRequest,
    TradeJournalCreateRequest,
)
from app.services.auth_service import AuthService
from app.services.backtest_service import BacktestService
from app.services.binance_connector import BinanceFuturesConnector
from app.services.bybit_connector import BybitConnector
from app.services.ctrader_connector import CTraderConnector
from app.services.execution_engine import ExecutionEngine
from app.services.market_data_service import MarketDataService
from app.services.news_engine import mock_news
from app.services.notification_service import NotificationService
from app.services.readiness_service import ReadinessService
from app.services.mt5_connector import Mt5Connector
from app.services.oanda_connector import OandaConnector
from app.services.risk_engine import build_risk_plan
from app.services.session_engine import evaluate_session
from app.services.signal_engine import SignalEngine
from app.services.storage_service import StorageService

app = FastAPI(title=settings.app_name, version="0.9.0")
engine = SignalEngine()
backtest_service = BacktestService(engine)
market_data = MarketDataService()
execution_guard = ExecutionEngine()
binance_connector = BinanceFuturesConnector()
bybit_connector = BybitConnector()
oanda_connector = OandaConnector()
mt5_connector = Mt5Connector()
ctrader_connector = CTraderConnector()
auth_service = AuthService()
storage = StorageService()
notification_service = NotificationService(storage)
readiness_service = ReadinessService()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authorization must be Bearer token")
    return authorization.split(" ", 1)[1].strip()


async def fetch_live_candles(symbol: str, market: str, timeframe: str):
    market = market.lower()
    if market == "crypto":
        return await market_data.fetch_binance_candles(symbol=symbol, interval=timeframe, limit=220)
    if market == "forex":
        twelve_interval = timeframe.replace("m", "min") if timeframe.endswith("m") else timeframe
        return await market_data.fetch_twelvedata_candles(symbol=symbol, interval=twelve_interval, outputsize=220)
    raise HTTPException(status_code=400, detail="market must be crypto or forex")


async def fetch_live_snapshot(symbol: str, market: str):
    market = market.lower()
    if market == "crypto":
        return await market_data.fetch_binance_ticker(symbol=symbol)
    if market == "forex":
        return await market_data.fetch_twelvedata_quote(symbol=symbol)
    raise HTTPException(status_code=400, detail="market must be crypto or forex")


def resolve_timeframe_context(timeframe: str) -> tuple[str | None, str | None]:
    timeframe = timeframe.lower()
    mapping = {
        "1m": ("5m", None),
        "5m": ("15m", "1m"),
        "15m": ("1h", "5m"),
        "1h": ("4h", "15m"),
    }
    return mapping.get(timeframe, (None, None))


async def build_multi_timeframe_context(symbol: str, market: str, timeframe: str) -> dict:
    higher_tf, lower_tf = resolve_timeframe_context(timeframe)
    higher_candles = []
    lower_candles = []

    if higher_tf:
        try:
            higher_candles = await fetch_live_candles(symbol=symbol, market=market, timeframe=higher_tf)
        except Exception:
            higher_candles = []

    if lower_tf:
        try:
            lower_candles = await fetch_live_candles(symbol=symbol, market=market, timeframe=lower_tf)
        except Exception:
            lower_candles = []

    return {
        "higher_timeframe": higher_tf,
        "higher_timeframe_candles": higher_candles,
        "lower_timeframe": lower_tf,
        "lower_timeframe_candles": lower_candles,
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}


@app.get("/api/v1/system/readiness")
def system_readiness():
    return readiness_service.build()


@app.post("/api/v1/auth/register")
def register(request: AuthRegisterRequest):
    return auth_service.register(request)


@app.post("/api/v1/auth/login")
def login(request: AuthLoginRequest):
    return auth_service.login(request)


@app.get("/api/v1/auth/me")
def me(authorization: str | None = Header(default=None)):
    token = extract_bearer_token(authorization)
    return auth_service.get_user_by_token(token)


@app.post("/api/v1/auth/logout", response_model=MessageResponse)
def logout(authorization: str | None = Header(default=None)):
    token = extract_bearer_token(authorization)
    auth_service.logout(token)
    return MessageResponse(message="Logged out successfully")


@app.post("/api/v1/notifications/register-device")
def register_device(request: DeviceTokenRegisterRequest, authorization: str | None = Header(default=None)):
    token = extract_bearer_token(authorization)
    user = auth_service.get_user_by_token(token)
    return storage.register_device_token(user.id, request)


@app.get("/api/v1/notifications/devices")
def list_devices(authorization: str | None = Header(default=None)):
    token = extract_bearer_token(authorization)
    user = auth_service.get_user_by_token(token)
    return {"items": [item.model_dump() for item in storage.list_device_tokens(user.id)]}


@app.post("/api/v1/notifications/test")
def send_test_notification(request: NotificationTestRequest, authorization: str | None = Header(default=None)):
    token = extract_bearer_token(authorization)
    user = auth_service.get_user_by_token(token)
    return notification_service.send_test_notification(user.id, request.title, request.body)


@app.get("/api/v1/sessions/current")
def current_session() -> dict:
    data = evaluate_session(datetime.now(timezone.utc))
    return {
        "session_name": data["session_name"],
        "market_quality": data["quality"],
        "session_score": data["score"],
    }


@app.get("/api/v1/news/mock")
def get_mock_news(market: str = "forex") -> dict:
    return {"items": mock_news(market)}


@app.get("/api/v1/analytics/summary")
def analytics_summary():
    return storage.get_analytics_summary()


@app.get("/api/v1/analytics/report")
def analytics_report():
    return storage.get_analytics_report()


@app.get("/api/v1/market/overview")
async def get_market_overview(
    symbols: str = Query(default="BTCUSDT,ETHUSDT,EURUSD,GBPUSD,XAUUSD")
) -> dict:
    symbol_list = [item.strip().upper() for item in symbols.split(",") if item.strip()]
    items = await market_data.market_overview(symbol_list)
    return {"items": [item.model_dump() for item in items]}


@app.get("/api/v1/market/candles")
async def get_market_candles(symbol: str, market: str, interval: str = "15m", limit: int = 200) -> dict:
    candles = await fetch_live_candles(symbol=symbol, market=market, timeframe=interval)
    return {
        "symbol": symbol.upper(),
        "market": market,
        "count": min(len(candles), limit),
        "items": [c.model_dump() for c in candles[-limit:]],
    }


@app.websocket("/ws/market")
async def market_websocket(websocket: WebSocket, symbol: str = "BTCUSDT", market: str = "crypto"):
    await websocket.accept()
    try:
        while True:
            snapshot = await fetch_live_snapshot(symbol=symbol.upper(), market=market)
            await websocket.send_json(snapshot.model_dump())
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        return
    except Exception as exc:
        await websocket.send_json({"error": str(exc)})
        await websocket.close()


@app.get("/api/v1/execution/capabilities")
def execution_capabilities():
    return {"items": [item.model_dump() for item in execution_guard.capabilities()]}


@app.post("/api/v1/execution/preview")
def execution_preview(request: ExecutionPreviewRequest):
    return execution_guard.preview_order(request)


@app.get("/api/v1/execution/status")
def execution_status() -> dict:
    return {
        "live_execution_enabled": settings.enable_live_execution,
        "connectors": [
            binance_connector.status().model_dump(),
            bybit_connector.status().model_dump(),
            oanda_connector.status().model_dump(),
            mt5_connector.status().model_dump(),
            ctrader_connector.status().model_dump(),
        ],
    }


@app.post("/api/v1/risk/plan")
def risk_plan(request: RiskPlanRequest):
    return build_risk_plan(request)


@app.post("/api/v1/signals/analyze")
def analyze_signal(request: SignalRequest):
    return engine.analyze(request)


@app.post("/api/v1/signals/analyze-and-save")
def analyze_and_save_signal(request: SignalRequest):
    signal = engine.analyze(request)
    return storage.save_signal(signal)


@app.post("/api/v1/signals/live-scan")
async def live_scan_signal(request: LiveSignalScanRequest):
    candles = await fetch_live_candles(
        symbol=request.symbol,
        market=request.market.value,
        timeframe=request.timeframe,
    )
    if len(candles) < 20:
        raise HTTPException(status_code=400, detail="Not enough candles available for live scan")

    mtf_context = await build_multi_timeframe_context(
        symbol=request.symbol,
        market=request.market.value,
        timeframe=request.timeframe,
    )

    signal = engine.analyze(
        SignalRequest(
            symbol=request.symbol.upper(),
            market=request.market,
            timeframe=request.timeframe,
            candles=candles,
            higher_timeframe=mtf_context["higher_timeframe"],
            higher_timeframe_candles=mtf_context["higher_timeframe_candles"],
            lower_timeframe=mtf_context["lower_timeframe"],
            lower_timeframe_candles=mtf_context["lower_timeframe_candles"],
            risk_settings=request.risk_settings,
            trade_stats=request.trade_stats,
            now_utc=datetime.now(timezone.utc),
            client_timezone=request.client_timezone,
        )
    )
    return storage.save_signal(signal)


@app.get("/api/v1/signals/history")
def signal_history(limit: int = 30):
    return {"items": [item.model_dump() for item in storage.list_signals(limit=limit)]}


@app.post("/api/v1/backtest/run")
async def run_backtest(request: BacktestRunRequest):
    candles = await fetch_live_candles(
        symbol=request.symbol,
        market=request.market.value,
        timeframe=request.timeframe,
    )
    if len(candles) < request.window_size + request.lookahead_candles + 5:
        raise HTTPException(status_code=400, detail="Not enough candles to run backtest")
    return backtest_service.run(request, candles)


@app.post("/api/v1/backtest/sweep")
async def run_backtest_sweep(request: BacktestSweepRequest):
    candles = await fetch_live_candles(
        symbol=request.symbol,
        market=request.market.value,
        timeframe=request.timeframe,
    )
    min_window = min(request.window_sizes) if request.window_sizes else 20
    min_lookahead = min(request.lookahead_options) if request.lookahead_options else 2
    if len(candles) < min_window + min_lookahead + 5:
        raise HTTPException(status_code=400, detail="Not enough candles to run backtest sweep")
    return backtest_service.run_sweep(request, candles)


@app.post("/api/v1/backtest/walk-forward")
async def run_walk_forward(request: WalkForwardRequest):
    candles = await fetch_live_candles(
        symbol=request.symbol,
        market=request.market.value,
        timeframe=request.timeframe,
    )
    min_window = min(request.window_sizes) if request.window_sizes else 20
    min_lookahead = min(request.lookahead_options) if request.lookahead_options else 2
    if len(candles) < request.train_window + request.test_window + min_window + min_lookahead:
        raise HTTPException(status_code=400, detail="Not enough candles to run walk-forward")
    return backtest_service.run_walk_forward(request, candles)


@app.post("/api/v1/trades")
def create_trade(request: TradeJournalCreateRequest):
    return storage.create_trade(request)


@app.get("/api/v1/trades")
def list_trades(limit: int = 50):
    return {"items": [item.model_dump() for item in storage.list_trades(limit=limit)]}


@app.get("/api/v1/trades/stats")
def trade_stats():
    return storage.get_trade_stats()


@app.post("/api/v1/trades/{trade_id}/close")
def close_trade(trade_id: int, request: TradeJournalCloseRequest):
    try:
        return storage.close_trade(trade_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/api/v1/trades/{trade_id}", response_model=MessageResponse)
def delete_trade(trade_id: int):
    try:
        storage.delete_trade(trade_id)
        return MessageResponse(message=f"Trade {trade_id} deleted")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/v1/execution/binance/order")
async def place_binance_order(request: BinanceFuturesOrderRequest):
    guard = execution_guard.validate_pre_trade(
        signal_score=request.signal_score,
        trade_allowed=request.risk_approved,
    )
    if not guard["ok"]:
        raise HTTPException(status_code=400, detail=guard)
    return await binance_connector.place_order(request)


@app.post("/api/v1/execution/bybit/order")
async def place_bybit_order(request: BybitOrderRequest):
    guard = execution_guard.validate_pre_trade(
        signal_score=request.signal_score,
        trade_allowed=request.risk_approved,
    )
    if not guard["ok"]:
        raise HTTPException(status_code=400, detail=guard)
    return await bybit_connector.place_order(request)


@app.post("/api/v1/execution/mt5/order")
async def place_mt5_order(request: Mt5OrderRequest):
    guard = execution_guard.validate_pre_trade(
        signal_score=request.signal_score,
        trade_allowed=request.risk_approved,
    )
    if not guard["ok"]:
        raise HTTPException(status_code=400, detail=guard)
    return await mt5_connector.place_order(request)


@app.post("/api/v1/execution/ctrader/order")
async def place_ctrader_order(request: CTraderOrderRequest):
    guard = execution_guard.validate_pre_trade(
        signal_score=request.signal_score,
        trade_allowed=request.risk_approved,
    )
    if not guard["ok"]:
        raise HTTPException(status_code=400, detail=guard)
    return await ctrader_connector.place_order(request)


@app.post("/api/v1/execution/oanda/order")
async def place_oanda_order(request: OandaOrderRequest):
    guard = execution_guard.validate_pre_trade(
        signal_score=request.signal_score,
        trade_allowed=request.risk_approved,
    )
    if not guard["ok"]:
        raise HTTPException(status_code=400, detail=guard)
    return await oanda_connector.place_order(request)
