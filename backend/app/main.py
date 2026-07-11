from __future__ import annotations

import time
import os

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


import asyncio as _asyncio, time as _time
_CANDLE_CACHE = {}
_CACHE_TTL = 30  # seconds

def _auto_market(symbol: str, market: str | None) -> str:
    if market: return market.lower()
    u = symbol.upper()
    if u.endswith("USDT") or u.endswith("BTC") or u.endswith("ETH") or u in ("BTC","ETH","SOL","XRP","BNB","DOGE","ADA"):
        return "crypto"
    return "forex"

async def fetch_live_candles(symbol: str, market: str, timeframe: str):
    market = _auto_market(symbol, market)
    cache_key = (symbol.upper(), market, timeframe)
    now = _time.time()
    cached = _CANDLE_CACHE.get(cache_key)
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1]
    last_err = None
    for attempt in range(3):
        try:
            if market == "crypto":
                data = await market_data.fetch_binance_candles(symbol=symbol, interval=timeframe, limit=220)
            elif market == "forex":
                twelve_interval = timeframe.replace("m", "min") if timeframe.endswith("m") else timeframe
                data = await market_data.fetch_twelvedata_candles(symbol=symbol, interval=twelve_interval, outputsize=220)
            else:
                raise HTTPException(status_code=400, detail="market must be crypto or forex")
            _CANDLE_CACHE[cache_key] = (now, data)
            return data
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            if "429" in msg or "too many" in msg:
                await _asyncio.sleep(1.5 * (attempt+1))
                continue
            raise
    raise last_err if last_err else RuntimeError("fetch failed")


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


@app.get("/api/v1/news/health")
def apex_news_health():
    k = os.getenv("FINNHUB_API_KEY", "")
    return {"service": "news", "finnhub_configured": bool(k), "key_length": len(k)}

@app.get("/api/v1/news/brief")
async def apex_news_brief():
    """Real news brief from Finnhub via news_engine_v2, with graceful fallback."""
    import logging
    logger = logging.getLogger("apex.api.news")
    k = os.getenv("FINNHUB_API_KEY", "")
    try:
        from app.news_engine_v2 import build_news_brief
        data = await build_news_brief()
        data.setdefault("finnhub_configured", bool(k))
        data.setdefault("server_time_unix", int(time.time()))
        data.setdefault("server_time_iso", "")
        data.setdefault("block", {"blocked": False, "reasons": [], "block_until": 0, "active_events": []})
        default_note = "اخبار واقعی Finnhub در حال پردازش است." if k else "کلید Finnhub (FINNHUB_API_KEY) روی Render ست نشده است."
        adj = data.get("adjustment") or {}
        adj.setdefault("bias", "neutral"); adj.setdefault("score_penalty", 0); adj.setdefault("note", default_note)
        data["adjustment"] = adj
        data.setdefault("events", {"upcoming": [], "live": [], "past": []})
        data.setdefault("headlines", [])
        return data
    except Exception as e:
        logger.exception("news brief failed, returning stub")
        return {
            "finnhub_configured": bool(k),
            "server_time_unix": int(time.time()),
            "server_time_iso": "",
            "block": {"blocked": False, "reasons": [], "block_until": 0, "active_events": []},
            "adjustment": {"bias": "neutral", "score_penalty": 0, "note": f"خطا در دریافت اخبار: {e}"},
            "events": {"upcoming": [], "live": [], "past": []},
            "headlines": []
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




@app.get("/api/v1/analysis/smc")
async def get_smc_analysis(
    symbol: str = Query("XAUUSD", description="Trading symbol"),
    market: str = Query("", description="forex, crypto, or auto"),
    interval: str = Query("15min", description="Candle interval"),
    limit: int = Query(220, ge=50, le=500),
):
    """Pro SMC analysis with multi-timeframe bias, killzones, liquidity pools, order flow."""
    import logging
    logger = logging.getLogger("apex.api.smc")
    symbol = symbol.upper()
    market_eff = _auto_market(symbol, market or None)

    def _tf_fetch(mk: str, tf: str) -> str:
        if mk == "crypto":
            return tf.replace("min", "m")  # binance wants "15m" not "15min"
        # forex -> twelvedata: "15min", "1h", "4h", "1d"
        if tf in ("1m","5m","15m","30m"):
            return tf + "in"  # -> "1min"
        return tf

    int_fetch = _tf_fetch(market_eff, interval)
    try:
        raw = await fetch_live_candles(symbol=symbol, market=market_eff, timeframe=int_fetch)
    except Exception as e:
        logger.exception("SMC candles fetch failed")
        return _smc_err(symbol, interval, 0, f"خطا در دریافت داده‌های بازار: {e}")

    items = _norm_candles(raw[-limit:])
    if len(items) < 30:
        return _smc_err(symbol, interval, items[-1]["c"] if items else 0, "حداقل ۳۰ کندل لازم است.", code="insufficient_data")

    # Determine HTF bias (1h for 15m, 4h for 1h etc)
    htf_bias = None; htf_used = None
    try:
        # Normalize interval key: strip "in" suffix if present so map keys match both "15m"/"15min"
        key = interval.replace("min", "m")
        htf_map = {"1m":"5m","5m":"15m","15m":"1h","30m":"4h","1h":"4h","4h":"1d","1d":"1d"}
        htf = htf_map.get(key)
        if htf:
            htf_used = htf
            htf_fetch = _tf_fetch(market_eff, htf)
            hraw = await fetch_live_candles(symbol=symbol, market=market_eff, timeframe=htf_fetch)
            hitems = _norm_candles(hraw)
            if len(hitems) >= 30:
                from app.services.smc_engine import analyze as _an
                hrep = _an(hitems, symbol=symbol, timeframe=htf)
                htf_bias = hrep.get("bias")
    except Exception as e:
        logger.warning("HTF bias fetch failed: %s", e)

    try:
        from app.services.smc_engine import analyze
        # Fetch news block status (light call; cached internally)
        _news_blocked = False
        try:
            from app.news_engine_v2 import build_news_brief as _nb
            _nbrief = await _nb()
            _news_blocked = bool((_nbrief.get("block") or {}).get("blocked"))
        except Exception:
            pass
        report = analyze(items, symbol=symbol, timeframe=interval, htf_bias=htf_bias, news_blocked=_news_blocked)
        report["market"] = market_eff
        report["htf"] = {"timeframe": htf_used, "bias": htf_bias}
        # visible chart candles (trim to last 120)
        report["candles"] = items[-120:]
        report["candles_count"] = len(items)
        report["status"] = "ok"
        return report
    except Exception as e:
        logger.exception("SMC analysis failed")
        return _smc_err(symbol, interval, items[-1]["c"] if items else 0, f"خطا در تحلیل SMC: {e}", code="analysis_failed", candles=items[-120:], count=len(items))


def _norm_candles(raw):
    items = []
    for c in raw:
        d = c.model_dump() if hasattr(c,"model_dump") else (dict(c) if isinstance(c,dict) else {})
        t_raw = d.get("t", d.get("time", d.get("datetime", d.get("timestamp", 0))))
        # Convert datetime objects to unix seconds
        if hasattr(t_raw, "timestamp"):
            t = t_raw.timestamp()
        else:
            try:
                t = float(t_raw)
                if t > 1e12: t = t/1000.0  # ms -> s
                elif t > 1e10: pass  # seconds in ms-range? unlikely but ok
            except Exception:
                continue
        o = d.get("o", d.get("open",0)); h = d.get("h", d.get("high",0))
        l = d.get("l", d.get("low",0)); cl = d.get("c", d.get("close",0))
        v = d.get("v", d.get("volume",0))
        try: items.append({"t":float(t),"o":float(o),"h":float(h),"l":float(l),"c":float(cl),"v":float(v)})
        except Exception: continue
    return items

def _smc_err(symbol, tf, price, note, code="fetch_failed", candles=None, count=0):
    return {"symbol":symbol,"timeframe":tf,"price":price or 0,
            "bias":"neutral","direction":"neutral","confluence":0,"probability":0,"setup_type":"-",
            "rr":0,"atr":0,"note":note,"status":code,
            "levels":{"entry":None,"sl":None,"tp":None},"tp1":None,"tp2":None,"tp3":None,
            "invalidation":None,"entry_zone":None,"plan_lines":[],
            "premium_zone":"eq","mtf_aligned":False,"htf_bias":None,
            "news_blocked":False,"volume_spike":False,
            "events":[],"order_blocks":[],"fvg":[],"breakers":[],"inducements":[],
            "sessions":[],"killzones":[],
            "orderflow":{"delta":0,"pressure":"neutral","cvd_curve":[],"volume_spike":False},
            "ai":{"side":"انتظار","trend":"خنثی","summary":note,"recommendation":"-","confluence":0,
                  "probability":0,"rr":0,"verdict":"-","setup_type":"-"},
            "visible_range":{"low":0,"high":0},"atr":0,"market":"",
            "htf":{"timeframe":None,"bias":None},"candles":candles or [],"candles_count":count,
            "overlay":{"lines":[],"zones":[],"labels":[]},"created_by":"Amin Omidi"}


_SCAN_WATCHLIST = [
    # Forex majors
    ("XAUUSD","forex","5min"),
    ("XAUUSD","forex","15min"),
    ("XAUUSD","forex","1h"),
    ("EURUSD","forex","15min"),
    ("GBPUSD","forex","15min"),
    ("USDJPY","forex","15min"),
    ("AUDUSD","forex","15min"),
    ("USDCAD","forex","15min"),
    ("EURJPY","forex","15min"),
    ("GBPJPY","forex","15min"),
    # Crypto
    ("BTCUSDT","crypto","5min"),
    ("BTCUSDT","crypto","15min"),
    ("BTCUSDT","crypto","1h"),
    ("ETHUSDT","crypto","5min"),
    ("ETHUSDT","crypto","15min"),
    ("SOLUSDT","crypto","15min"),
    ("BNBUSDT","crypto","15min"),
    ("XRPUSDT","crypto","15min"),
    ("DOGEUSDT","crypto","5min"),
    ("ADAUSDT","crypto","15min"),
]

@app.get("/api/v1/signals/scan")
async def scan_signals(min_confluence: int = 2):
    """Multi-symbol multi-tf professional SMC scan."""
    from app.services.smc_engine import analyze
    import asyncio, logging
    log = logging.getLogger("apex.api.signals")
    results = []
    _news_blocked = False
    try:
        from app.news_engine_v2 import build_news_brief as _nb
        _nbrief = await _nb()
        _news_blocked = bool((_nbrief.get("block") or {}).get("blocked"))
    except Exception: pass

    async def _job(sym, mkt, tf):
        try:
            mkt_eff = _auto_market(sym, mkt)
            if mkt_eff == "crypto":
                tf_fetch = tf.replace("min","m")
            elif mkt_eff == "forex" and tf in ("1m","5m","15m","30m"):
                tf_fetch = tf + "in"
            else:
                tf_fetch = tf
            raw = await fetch_live_candles(sym, mkt_eff, tf_fetch)
            items = _norm_candles(raw)
            if len(items) < 30: return None
            # HTF for scan
            htf_bias=None
            try:
                key=tf.replace("min","m"); hm={"1m":"5m","5m":"15m","15m":"1h","30m":"4h","1h":"4h"}.get(key)
                if hm:
                    if mkt_eff == "crypto":
                        hf = hm.replace("min","m")
                    elif mkt_eff == "forex" and hm in ("1m","5m","15m","30m"):
                        hf = hm + "in"
                    else:
                        hf = hm
                    hraw = await fetch_live_candles(sym, mkt_eff, hf)
                    hi=_norm_candles(hraw)
                    if len(hi)>=30:
                        hrep=analyze(hi,symbol=sym,timeframe=hm)
                        htf_bias=hrep.get("bias")
            except Exception: pass
            r = analyze(items, symbol=sym, timeframe=tf, htf_bias=htf_bias, news_blocked=_news_blocked)
            return {"symbol":sym,"market":mkt_eff,"timeframe":tf,
                    "bias":r["bias"],"direction":r["direction"],"confluence":r["confluence"],
                    "rr":r.get("rr",0),"price":r["price"],"note":r["note"],
                    "probability":r.get("probability",0),
                    "setup_type":r.get("setup_type","-"),"setupType":r.get("setup_type","-"),
                    "grade":r.get("grade","-"),
                    "levels":r["levels"],"tp1":r.get("tp1"),"tp2":r.get("tp2"),"tp3":r.get("tp3"),
                    "ai":r["ai"],"status":"ok","total_scanned":0}
        except Exception as e:
            log.warning("scan %s@%s failed: %s", sym, tf, e)
            return None
    jobs = [_job(s,m,t) for s,m,t in _SCAN_WATCHLIST]
    out = await asyncio.gather(*jobs)
    sigs = [x for x in out if x and x["confluence"] >= min_confluence and x["direction"] in ("long","short")]
    sigs.sort(key=lambda x: (-x["confluence"], -x["rr"]))
    return {"signals": sigs, "total_scanned": len(_SCAN_WATCHLIST), "count": len(sigs), "created_by": "Amin Omidi"}


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
    saved_signal = storage.save_signal(signal)
    try:
        notification_service.try_send_fresh_signal_alert(saved_signal)
    except Exception:
        pass
    return saved_signal


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
    saved_signal = storage.save_signal(signal)
    try:
        notification_service.try_send_fresh_signal_alert(saved_signal)
    except Exception:
        pass
    return saved_signal


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
