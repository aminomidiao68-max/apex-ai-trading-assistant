from __future__ import annotations

import time
import asyncio
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.models import (
    AnalyticsReport,
    AnalyticsSummary,
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthResponse,
    AuthUser,
    BacktestRunRequest,
    BacktestSummary,
    BacktestSweepRequest,
    BacktestSweepSummary,
    WalkForwardRequest,
    WalkForwardSummary,
    BinanceFuturesOrderRequest,
    ConnectorCapability,
    ExecutionPreviewRequest,
    ExecutionPreviewResponse,
    BybitOrderRequest,
    CTraderOrderRequest,
    DeviceTokenRegisterRequest,
    LiveSignalScanRequest,
    MessageResponse,
    Mt5OrderRequest,
    NotificationTestRequest,
    OandaOrderRequest,
    RiskPlan,
    RiskPlanRequest,
    SignalHistoryItem,
    SignalRequest,
    SignalResponse,
    SystemReadinessResponse,
    TradeJournalCloseRequest,
    TradeJournalCreateRequest,
    TradeJournalItem,
    TradeJournalStats,
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

app = FastAPI(title=settings.app_name, version=settings.app_version)


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

# Native Android clients do not require CORS. Browser access is enabled only
# for an explicit environment-specific allowlist (CORS_ALLOWED_ORIGINS).
if settings.cors_allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )


_bearer_scheme = HTTPBearer(auto_error=False)


def require_credentials(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> HTTPAuthorizationCredentials:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing or invalid Bearer token")
    return credentials


def current_user(
    credentials: HTTPAuthorizationCredentials = Depends(require_credentials),
):
    return auth_service.get_user_by_token(credentials.credentials)


import asyncio as _asyncio, time as _time

_CANDLE_CACHE: dict[tuple[str, str, str], tuple[float, list]] = {}
_CANDLE_LOCKS: dict[tuple[str, str, str], _asyncio.Lock] = {}
_MAX_STALE_CACHE_SECONDS = 24 * 60 * 60


def _canonical_timeframe(timeframe: str) -> str:
    value = (timeframe or "15m").lower().strip()
    if value.endswith("min"):
        value = value[:-3] + "m"
    return {"60m": "1h", "240m": "4h", "1day": "1d"}.get(value, value)


def _cache_ttl(timeframe: str) -> int:
    return {
        "1m": 45,
        "3m": 60,
        "5m": 90,
        "15m": 180,
        "30m": 300,
        "1h": 600,
        "2h": 900,
        "4h": 1800,
        "1d": 3600,
    }.get(_canonical_timeframe(timeframe), 180)


def _auto_market(symbol: str, market: str | None) -> str:
    if market:
        return market.lower()
    upper = symbol.upper()
    if upper.endswith("USDT") or upper.endswith("BTC") or upper.endswith("ETH") or upper in (
        "BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "ADA"
    ):
        return "crypto"
    return "forex"


async def fetch_live_candles(symbol: str, market: str, timeframe: str):
    market = _auto_market(symbol, market)
    canonical_tf = _canonical_timeframe(timeframe)
    cache_key = (symbol.upper(), market, canonical_tf)
    now = _time.time()
    cached = _CANDLE_CACHE.get(cache_key)
    if cached and now - cached[0] < _cache_ttl(canonical_tf):
        return cached[1]

    lock = _CANDLE_LOCKS.setdefault(cache_key, _asyncio.Lock())
    async with lock:
        now = _time.time()
        cached = _CANDLE_CACHE.get(cache_key)
        if cached and now - cached[0] < _cache_ttl(canonical_tf):
            return cached[1]
        try:
            if market == "crypto":
                data = await market_data.fetch_binance_candles(
                    symbol=symbol, interval=canonical_tf, limit=260
                )
            elif market == "forex":
                data = await market_data.fetch_forex_candles(
                    symbol=symbol, interval=canonical_tf, outputsize=260
                )
            else:
                raise HTTPException(status_code=400, detail="market must be crypto or forex")
            if len(data) < 30:
                raise RuntimeError("insufficient provider data")
            _CANDLE_CACHE[cache_key] = (now, data)
            return data
        except HTTPException:
            raise
        except Exception as exc:
            # A stale chart is safer and more useful than an empty chart during
            # a temporary provider outage. The response never exposes provider
            # URLs, API keys or raw exception strings.
            if cached and now - cached[0] <= _MAX_STALE_CACHE_SECONDS:
                return cached[1]
            raise HTTPException(
                status_code=502,
                detail=(
                    f"Market data is temporarily unavailable for "
                    f"{symbol.upper()} ({market}/{canonical_tf})"
                ),
            ) from exc


async def fetch_live_snapshot(symbol: str, market: str):
    market = market.lower()
    if market == "crypto":
        return await market_data.fetch_binance_ticker(symbol=symbol)
    if market == "forex":
        return await market_data.fetch_forex_quote(symbol=symbol)
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


@app.get("/api/v1/system/readiness", response_model=SystemReadinessResponse)
def system_readiness():
    return readiness_service.build()


@app.post("/api/v1/auth/register", response_model=AuthResponse)
def register(request: AuthRegisterRequest):
    return auth_service.register(request)


@app.post("/api/v1/auth/login", response_model=AuthResponse)
def login(request: AuthLoginRequest):
    return auth_service.login(request)


@app.get("/api/v1/auth/me", response_model=AuthUser)
def me(user=Depends(current_user)):
    return user


@app.post("/api/v1/auth/logout", response_model=MessageResponse)
def logout(credentials: HTTPAuthorizationCredentials = Depends(require_credentials)):
    auth_service.logout(credentials.credentials)
    return MessageResponse(message="Logged out successfully")


@app.post("/api/v1/notifications/register-device")
def register_device(request: DeviceTokenRegisterRequest, user=Depends(current_user)):
    return storage.register_device_token(user.id, request)


@app.get("/api/v1/notifications/devices")
def list_devices(user=Depends(current_user)):
    return {"items": [item.model_dump() for item in storage.list_device_tokens(user.id)]}


@app.post("/api/v1/notifications/test")
def send_test_notification(request: NotificationTestRequest, user=Depends(current_user)):
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
    return {"service": "news", "finnhub_configured": bool(settings.finnhub_api_key)}

@app.get("/api/v1/news/brief")
async def apex_news_brief():
    """Real news brief from Finnhub via news_engine_v2, with graceful fallback."""
    import logging
    logger = logging.getLogger("apex.api.news")
    k = settings.finnhub_api_key
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


@app.get("/api/v1/analytics/summary", response_model=AnalyticsSummary)
def analytics_summary(user=Depends(current_user)):
    return storage.get_analytics_summary(user_id=user.id)


@app.get("/api/v1/analytics/report", response_model=AnalyticsReport)
def analytics_report(user=Depends(current_user)):
    return storage.get_analytics_report(user_id=user.id)


@app.get("/api/v1/market/overview")
async def get_market_overview(
    symbols: str = Query(default="BTCUSDT,ETHUSDT,EURUSD,GBPUSD,XAUUSD")
) -> dict:
    symbol_list = [item.strip().upper() for item in symbols.split(",") if item.strip()]
    items = await market_data.market_overview(symbol_list)
    return {"items": [item.model_dump() for item in items]}


@app.get("/api/v1/market/candles")
async def get_market_candles(
    symbol: str = Query(min_length=2, max_length=24),
    market: str = Query(pattern="^(crypto|forex)$"),
    interval: str = Query(default="15m", pattern="^(1m|3m|5m|15m|30m|1h|2h|4h|6h|12h|1d|1min|3min|5min|15min|30min)$"),
    limit: int = Query(default=200, ge=20, le=500),
) -> dict:
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
        # Provider-specific mappings are handled by MarketDataService.
        return _canonical_timeframe(tf)

    int_fetch = _tf_fetch(market_eff, interval)
    try:
        raw = await fetch_live_candles(symbol=symbol, market=market_eff, timeframe=int_fetch)
    except Exception:
        logger.exception("SMC candles fetch failed")
        return _smc_err(
            symbol,
            interval,
            0,
            "داده بازار موقتاً در دسترس نیست؛ چند لحظه دیگر دوباره تلاش کنید.",
            code="provider_unavailable",
        )

    items = _norm_candles(raw[-limit:])
    if len(items) < 30:
        return _smc_err(symbol, interval, items[-1]["c"] if items else 0, "حداقل ۳۰ کندل لازم است.", code="insufficient_data")

    # Build HTF candles locally from the selected data. This removes a second
    # provider request for every tap and prevents TwelveData quota bursts.
    htf_bias = None
    htf_used = None
    try:
        key = _canonical_timeframe(interval)
        htf = {
            "1m": "5m",
            "3m": "15m",
            "5m": "15m",
            "15m": "1h",
            "30m": "4h",
            "1h": "4h",
            "2h": "4h",
            "4h": "1d",
        }.get(key)
        if htf:
            htf_used = htf
            hraw = _resample_candles(raw, htf)
            hitems = _norm_candles(hraw)
            if len(hitems) >= 30:
                from app.services.smc_engine import analyze as _an

                hrep = _an(hitems, symbol=symbol, timeframe=htf)
                htf_bias = hrep.get("bias")
    except Exception:
        logger.warning("HTF bias calculation failed", exc_info=True)

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
        report = analyze(
            items,
            symbol=symbol,
            timeframe=_canonical_timeframe(interval),
            htf_bias=htf_bias,
            news_blocked=_news_blocked,
        )
        report["market"] = market_eff
        report["htf"] = {"timeframe": htf_used, "bias": htf_bias}
        report["status"] = "ok"
        return _prepare_chart_report(report, items, max_candles=160)
    except Exception:
        logger.exception("SMC analysis failed")
        return _smc_err(
            symbol,
            interval,
            items[-1]["c"] if items else 0,
            "تحلیل نمودار موقتاً ناموفق بود؛ دوباره تلاش کنید.",
            code="analysis_failed",
            candles=items[-160:],
            count=len(items),
        )


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

def _resample_candles(raw, target_timeframe: str):
    seconds = {
        "5m": 5 * 60,
        "15m": 15 * 60,
        "30m": 30 * 60,
        "1h": 60 * 60,
        "2h": 2 * 60 * 60,
        "4h": 4 * 60 * 60,
        "1d": 24 * 60 * 60,
    }.get(_canonical_timeframe(target_timeframe))
    if not seconds:
        return []
    try:
        return market_data.aggregate_candles(list(raw), seconds)
    except Exception:
        return []


def _rebase_items(items, offset: int, total: int, keep_extended: bool = False):
    rebased = []
    for original in items or []:
        item = dict(original)
        try:
            index = int(item.get("index", 0))
        except (TypeError, ValueError):
            continue
        if index >= total:
            continue
        if index < offset:
            if not keep_extended:
                continue
            index = offset
        item["index"] = index - offset
        rebased.append(item)
    return rebased


def _rebase_price_zones(items, offset: int, total: int):
    rebased = []
    for original in items or []:
        item = dict(original)
        try:
            start = int(item.get("index", 0))
            end = int(item.get("end_idx", total - 1))
        except (TypeError, ValueError):
            continue
        if start >= total or end < offset:
            continue
        visible_start = max(start, offset)
        visible_end = min(max(end, visible_start), total - 1)
        item["index"] = visible_start - offset
        item["end_idx"] = visible_end - offset
        rebased.append(item)
    return rebased


def _rebase_killzones(items, offset: int, total: int):
    rebased = []
    for original in items or []:
        item = dict(original)
        try:
            start = int(item.get("start_idx", item.get("index", 0)))
            end = int(item.get("end_idx", start))
        except (TypeError, ValueError):
            continue
        if end < offset or start >= total:
            continue
        start = max(start, offset)
        end = min(end, total - 1)
        item["start_idx"] = start - offset
        item["end_idx"] = end - offset
        item["index"] = start - offset
        rebased.append(item)
    return rebased


def _prepare_chart_report(report: dict, items: list[dict], max_candles: int = 160) -> dict:
    """Trim candles and rebase every overlay index to the returned chart window."""
    total = len(items)
    offset = max(0, total - max_candles)
    display = items[offset:]
    report["candles"] = display
    report["candles_count"] = total
    if display:
        report["visible_range"] = {
            "low": min(item["l"] for item in display),
            "high": max(item["h"] for item in display),
        }

    report["events"] = _rebase_items(report.get("events"), offset, total)[-6:]
    report["order_blocks"] = _rebase_items(
        report.get("order_blocks"), offset, total, keep_extended=True
    )[-5:]
    report["fvg"] = _rebase_items(report.get("fvg"), offset, total)[-5:]
    report["breakers"] = _rebase_items(
        report.get("breakers"), offset, total, keep_extended=True
    )[-4:]
    all_liquidity = _rebase_items(report.get("inducements"), offset, total)
    selected_liquidity = []
    for kind in ("buyside_liq", "sellside_liq", "eqh", "eql"):
        matches = [item for item in all_liquidity if item.get("kind") == kind]
        if matches:
            selected_liquidity.append(matches[-1])
    # Preserve up to two additional recent sweep points for IDM dots.
    for item in reversed(all_liquidity):
        if item not in selected_liquidity and "liq" in str(item.get("kind", "")):
            selected_liquidity.append(item)
        if len(selected_liquidity) >= 6:
            break
    report["inducements"] = sorted(
        selected_liquidity, key=lambda item: int(item.get("index", 0))
    )

    all_killzones = _rebase_killzones(report.get("killzones"), offset, total)
    simple_killzones = [
        item for item in all_killzones
        if "همپوشانی" not in str(item.get("name", ""))
        and "overlap" not in str(item.get("name", "")).lower()
    ][-2:]
    if not simple_killzones and all_killzones:
        simple_killzones = all_killzones[-1:]
    report["killzones"] = simple_killzones

    overlay = dict(report.get("overlay") or {})
    overlay["labels"] = _rebase_items(overlay.get("labels"), offset, total)[-8:]
    raw_by_kind: dict[str, list[dict]] = {"OB": [], "FVG": [], "iFVG": [], "BRK": []}
    for zone in overlay.get("zones") or []:
        kind = str(zone.get("kind", ""))
        if kind in raw_by_kind:
            raw_by_kind[kind].append(zone)

    rebased_by_kind = {
        kind: _rebase_price_zones(zones, offset, total)
        for kind, zones in raw_by_kind.items()
    }
    current_price = float(report.get("price") or 0)
    atr = max(float(report.get("atr") or 0), 1e-9)

    def importance(item: dict) -> tuple[float, int]:
        midpoint = (float(item.get("top", 0)) + float(item.get("bottom", 0))) / 2
        distance_penalty = min(abs(midpoint - current_price) / atr, 30.0) if current_price else 0
        score = (
            int(item.get("quality", 0)) * 100
            + (25 if item.get("fresh", False) else 0)
            + int(item.get("index", 0)) * 0.2
            - distance_penalty
        )
        return score, int(item.get("index", 0))

    def strongest_per_side(items: list[dict]) -> list[dict]:
        selected = []
        for side in ("bullish", "bearish"):
            candidates = [item for item in items if item.get("side") == side]
            if candidates:
                selected.append(max(candidates, key=importance))
        return sorted(selected, key=lambda item: int(item.get("index", 0)))

    selected_obs = strongest_per_side(rebased_by_kind["OB"])
    selected_fvgs = strongest_per_side(
        rebased_by_kind["FVG"] + rebased_by_kind["iFVG"]
    )
    selected_breakers = sorted(
        rebased_by_kind["BRK"], key=importance, reverse=True
    )[:1]

    # At most 2 OBs + 2 FVGs + 1 faint breaker, all with a finite extension
    # ending on the first price revisit. This keeps only institutional zones.
    overlay["zones"] = (
        simple_killzones + selected_obs + selected_fvgs + selected_breakers
    )
    report["overlay"] = overlay
    return report


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
async def scan_signals(min_confluence: int = Query(default=40, ge=0, le=100)):
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
                    hraw = _resample_candles(raw, hm)
                    hi = _norm_candles(hraw)
                    if len(hi) >= 30:
                        hrep = analyze(hi, symbol=sym, timeframe=hm)
                        htf_bias = hrep.get("bias")
            except Exception: pass
            r = analyze(items, symbol=sym, timeframe=tf, htf_bias=htf_bias, news_blocked=_news_blocked)
            return {"symbol":sym,"market":mkt_eff,"timeframe":tf,
                    "bias":r["bias"],"direction":r["direction"],"confluence":r["confluence"],
                    "rr":r.get("rr",0),"price":r["price"],"note":r["note"],
                    "probability":r.get("probability",0),
                    "setup_type":r.get("setup_type","-"),"setupType":r.get("setup_type","-"),
                    "grade":r.get("grade","-"),
                    "omega_compliant":r.get("omega_compliant",False),
                    "omega_reasons":r.get("omega_reasons",[]),
                    "action_label":r.get("action_label","WAIT"),
                    "levels":r["levels"],"tp1":r.get("tp1"),"tp2":r.get("tp2"),"tp3":r.get("tp3"),
                    "ai":r["ai"],"status":"ok","total_scanned":0}
        except Exception as e:
            log.warning("scan %s@%s failed: %s", sym, tf, e)
            return None
    jobs = [_job(s,m,t) for s,m,t in _SCAN_WATCHLIST]
    out = await asyncio.gather(*jobs)
    candidates = [
        x for x in out
        if x and x["confluence"] >= min_confluence and x["direction"] in ("long", "short")
    ]
    actionable = [
        x for x in candidates
        if x.get("omega_compliant") and x.get("grade") not in ("D", "F")
    ]
    watching = [x for x in candidates if x not in actionable]
    actionable.sort(key=lambda x: (-x["confluence"], -x["rr"]))
    watching.sort(key=lambda x: (-x["confluence"], -x["rr"]))
    return {
        "signals": actionable,
        "watching": watching,
        "total_scanned": len(_SCAN_WATCHLIST),
        "count": len(actionable),
        "watching_count": len(watching),
        "created_by": "Amin Omidi",
    }


_SETUP_SYMBOLS = [
    ("XAUUSD", "forex"), ("EURUSD", "forex"), ("GBPUSD", "forex"),
    ("USDJPY", "forex"), ("AUDUSD", "forex"), ("US30", "forex"),
    ("NAS100", "forex"), ("BTCUSDT", "crypto"), ("ETHUSDT", "crypto"),
    ("SOLUSDT", "crypto"),
]
_SETUP_TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
_SETUP_SCAN_CACHE: dict = {"timestamp": 0.0, "payload": None}
_SETUP_SCAN_LOCK = _asyncio.Lock()
_SETUP_CACHE_TTL = 300


def _setup_payload(report: dict, symbol: str, market: str, timeframe: str, status: str) -> dict:
    watching = sorted(
        report.get("watching") or [], key=lambda item: float(item.get("distance", 1e18))
    )
    watch = watching[0] if watching else None
    direction = report.get("direction", "neutral")
    entry = (report.get("levels") or {}).get("entry")
    stop_loss = (report.get("levels") or {}).get("sl")
    tp1 = report.get("tp1")
    tp2 = report.get("tp2")
    tp3 = report.get("tp3")
    if status == "forming" and direction not in ("long", "short") and watch:
        direction = watch.get("direction", "neutral")
        entry = watch.get("entry")
        stop_loss = watch.get("sl")
        tp1 = watch.get("tp")
        tp2 = None
        tp3 = None

    reasons = [str(item) for item in report.get("omega_reasons") or []]
    if direction in ("long", "short") and report.get("htf_bias"):
        expected = "bullish" if direction == "long" else "bearish"
        if report.get("htf_bias") != expected:
            reasons.append("HTF conflict")
    if status == "forming" and not reasons:
        reasons.append("Waiting for structure/entry confirmation")

    setup_type = report.get("setup_type") or "-"
    return {
        "id": f"{symbol}:{timeframe}:{direction}:{setup_type}",
        "symbol": symbol,
        "market": market,
        "timeframe": timeframe,
        "status": status,
        "setup_type": setup_type,
        "setup_family": "SMC/ICT",
        "direction": direction,
        "bias": report.get("bias", "neutral"),
        "grade": report.get("grade", "-"),
        "confluence": report.get("confluence", 0),
        "probability": report.get("probability", 0),
        "rr": round(float(report.get("rr") or 0), 2),
        "price": report.get("price", 0),
        "entry": entry,
        "stop_loss": stop_loss,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "invalidation": report.get("invalidation"),
        "omega_compliant": bool(report.get("omega_compliant")),
        "action_label": report.get("action_label", "WAIT"),
        "mtf_aligned": bool(report.get("mtf_aligned")),
        "htf_bias": report.get("htf_bias"),
        "note": report.get("note", ""),
        "missing_confirmations": reasons[:4],
        "factors": [
            item.get("name", "") for item in (report.get("confluence_factors") or [])[:5]
            if item.get("name")
        ],
    }


@app.get("/api/v1/setups/scan")
async def scan_trade_setups(force: bool = Query(default=False)):
    """Scan 10 symbols × 7 timeframes and return confirmed/forming setups.

    Results are cached for five minutes. Only actual detected setup types are
    returned; an empty result is a valid market state, not a synthetic signal.
    """
    now = _time.time()
    cached = _SETUP_SCAN_CACHE.get("payload")
    age = now - float(_SETUP_SCAN_CACHE.get("timestamp") or 0)
    if cached and not force and age < _SETUP_CACHE_TTL:
        return {**cached, "cached": True, "cache_age_seconds": round(age, 1)}

    async with _SETUP_SCAN_LOCK:
        now = _time.time()
        cached = _SETUP_SCAN_CACHE.get("payload")
        age = now - float(_SETUP_SCAN_CACHE.get("timestamp") or 0)
        if cached and not force and age < _SETUP_CACHE_TTL:
            return {**cached, "cached": True, "cache_age_seconds": round(age, 1)}

        from app.services.smc_engine import analyze

        news_blocked = False
        try:
            from app.news_engine_v2 import build_news_brief

            brief = await build_news_brief()
            news_blocked = bool((brief.get("block") or {}).get("blocked"))
        except Exception:
            pass

        semaphore = _asyncio.Semaphore(6)

        async def job(symbol: str, market: str, timeframe: str):
            async with semaphore:
                try:
                    raw = await fetch_live_candles(symbol, market, timeframe)
                    items = _norm_candles(raw)
                    if len(items) < 30:
                        return None
                    htf = {
                        "1m": "5m", "5m": "15m", "15m": "1h", "30m": "4h",
                        "1h": "4h", "4h": "1d",
                    }.get(timeframe)
                    htf_bias = None
                    if htf:
                        higher = _norm_candles(_resample_candles(raw, htf))
                        if len(higher) >= 30:
                            htf_bias = analyze(higher, symbol=symbol, timeframe=htf).get("bias")
                    report = analyze(
                        items,
                        symbol=symbol,
                        timeframe=timeframe,
                        htf_bias=htf_bias,
                        news_blocked=news_blocked,
                    )
                    report["htf_bias"] = htf_bias
                    confirmed = (
                        report.get("omega_compliant")
                        and report.get("grade") in ("A+", "A", "B")
                        and report.get("direction") in ("long", "short")
                        and bool(report.get("plan_lines"))
                    )
                    has_forming_setup = (
                        report.get("setup_type") not in (None, "", "-")
                        and (
                            report.get("direction") in ("long", "short")
                            or bool(report.get("watching"))
                        )
                        and int(report.get("confluence") or 0) >= 15
                    )
                    if confirmed:
                        return _setup_payload(report, symbol, market, timeframe, "confirmed")
                    if has_forming_setup:
                        return _setup_payload(report, symbol, market, timeframe, "forming")
                    return None
                except Exception:
                    return None

        matrix = [
            (symbol, market, timeframe)
            for symbol, market in _SETUP_SYMBOLS
            for timeframe in _SETUP_TIMEFRAMES
        ]
        results = await _asyncio.gather(*(job(*item) for item in matrix))
        setups = [item for item in results if item]
        confirmed = sorted(
            (item for item in setups if item["status"] == "confirmed"),
            key=lambda item: (item["grade"] == "A+", item["confluence"], item["probability"], item["rr"]),
            reverse=True,
        )[:20]
        forming = sorted(
            (item for item in setups if item["status"] == "forming"),
            key=lambda item: (item["confluence"], item["probability"], item["rr"]),
            reverse=True,
        )[:20]
        generated_at = datetime.now(timezone.utc).isoformat()
        payload = {
            "confirmed": confirmed,
            "forming": forming,
            "invalidated": [],
            "confirmed_count": len(confirmed),
            "forming_count": len(forming),
            "invalidated_count": 0,
            "total_scanned": len(matrix),
            "generated_at": generated_at,
            "cached": False,
            "cache_age_seconds": 0,
        }
        _SETUP_SCAN_CACHE["timestamp"] = _time.time()
        _SETUP_SCAN_CACHE["payload"] = payload
        return payload


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


@app.post("/api/v1/execution/preview", response_model=ExecutionPreviewResponse)
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


@app.post("/api/v1/risk/plan", response_model=RiskPlan)
def risk_plan(request: RiskPlanRequest):
    return build_risk_plan(request)


@app.post("/api/v1/signals/analyze", response_model=SignalResponse)
def analyze_signal(request: SignalRequest, user=Depends(current_user)):
    return engine.analyze(request)


@app.post("/api/v1/signals/analyze-and-save", response_model=SignalHistoryItem)
def analyze_and_save_signal(request: SignalRequest, user=Depends(current_user)):
    signal = engine.analyze(request)
    saved_signal = storage.save_signal(signal, user_id=user.id)
    try:
        notification_service.try_send_fresh_signal_alert(saved_signal, user_id=user.id)
    except Exception:
        pass
    return saved_signal


@app.post("/api/v1/signals/live-scan", response_model=SignalHistoryItem)
async def live_scan_signal(request: LiveSignalScanRequest, user=Depends(current_user)):
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
    saved_signal = storage.save_signal(signal, user_id=user.id)
    try:
        notification_service.try_send_fresh_signal_alert(saved_signal, user_id=user.id)
    except Exception:
        pass
    return saved_signal


@app.get("/api/v1/signals/history")
def signal_history(
    limit: int = Query(default=30, ge=1, le=200),
    user=Depends(current_user),
):
    return {
        "items": [
            item.model_dump() for item in storage.list_signals(limit=limit, user_id=user.id)
        ]
    }


@app.post("/api/v1/backtest/run", response_model=BacktestSummary)
async def run_backtest(request: BacktestRunRequest, user=Depends(current_user)):
    candles = await fetch_live_candles(
        symbol=request.symbol,
        market=request.market.value,
        timeframe=request.timeframe,
    )
    if len(candles) < request.window_size + request.lookahead_candles + 5:
        raise HTTPException(status_code=400, detail="Not enough candles to run backtest")
    return backtest_service.run(request, candles)


@app.post("/api/v1/backtest/sweep", response_model=BacktestSweepSummary)
async def run_backtest_sweep(request: BacktestSweepRequest, user=Depends(current_user)):
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


@app.post("/api/v1/backtest/walk-forward", response_model=WalkForwardSummary)
async def run_walk_forward(request: WalkForwardRequest, user=Depends(current_user)):
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


@app.post("/api/v1/trades", response_model=TradeJournalItem)
def create_trade(request: TradeJournalCreateRequest, user=Depends(current_user)):
    return storage.create_trade(request, user_id=user.id)


@app.get("/api/v1/trades")
def list_trades(
    limit: int = Query(default=50, ge=1, le=200),
    user=Depends(current_user),
):
    return {
        "items": [
            item.model_dump() for item in storage.list_trades(limit=limit, user_id=user.id)
        ]
    }


@app.get("/api/v1/trades/stats", response_model=TradeJournalStats)
def trade_stats(user=Depends(current_user)):
    return storage.get_trade_stats(user_id=user.id)


@app.post("/api/v1/trades/{trade_id}/close", response_model=TradeJournalItem)
def close_trade(
    trade_id: int,
    request: TradeJournalCloseRequest,
    user=Depends(current_user),
):
    try:
        return storage.close_trade(trade_id, request, user_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/api/v1/trades/{trade_id}", response_model=MessageResponse)
def delete_trade(trade_id: int, user=Depends(current_user)):
    try:
        storage.delete_trade(trade_id, user_id=user.id)
        return MessageResponse(message=f"Trade {trade_id} deleted")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/v1/execution/binance/order")
async def place_binance_order(request: BinanceFuturesOrderRequest, user=Depends(current_user)):
    guard = execution_guard.validate_pre_trade(
        signal_score=request.signal_score,
        trade_allowed=request.risk_approved,
    )
    if not guard["ok"]:
        raise HTTPException(status_code=400, detail=guard)
    return await binance_connector.place_order(request)


@app.post("/api/v1/execution/bybit/order")
async def place_bybit_order(request: BybitOrderRequest, user=Depends(current_user)):
    guard = execution_guard.validate_pre_trade(
        signal_score=request.signal_score,
        trade_allowed=request.risk_approved,
    )
    if not guard["ok"]:
        raise HTTPException(status_code=400, detail=guard)
    return await bybit_connector.place_order(request)


@app.post("/api/v1/execution/mt5/order")
async def place_mt5_order(request: Mt5OrderRequest, user=Depends(current_user)):
    guard = execution_guard.validate_pre_trade(
        signal_score=request.signal_score,
        trade_allowed=request.risk_approved,
    )
    if not guard["ok"]:
        raise HTTPException(status_code=400, detail=guard)
    return await mt5_connector.place_order(request)


@app.post("/api/v1/execution/ctrader/order")
async def place_ctrader_order(request: CTraderOrderRequest, user=Depends(current_user)):
    guard = execution_guard.validate_pre_trade(
        signal_score=request.signal_score,
        trade_allowed=request.risk_approved,
    )
    if not guard["ok"]:
        raise HTTPException(status_code=400, detail=guard)
    return await ctrader_connector.place_order(request)


@app.post("/api/v1/execution/oanda/order")
async def place_oanda_order(request: OandaOrderRequest, user=Depends(current_user)):
    guard = execution_guard.validate_pre_trade(
        signal_score=request.signal_score,
        trade_allowed=request.risk_approved,
    )
    if not guard["ok"]:
        raise HTTPException(status_code=400, detail=guard)
    return await oanda_connector.place_order(request)
