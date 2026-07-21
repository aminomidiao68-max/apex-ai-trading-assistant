from __future__ import annotations

import os
import time
import asyncio
import hmac
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.models import (
    AIExplainRequest,
    AIExplainResponse,
    AutomatedPanelResearchRequest,
    AutomatedPanelResearchResponse,
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
    HistoricalDataCollectRequest,
    HistoricalDataCollectResponse,
    HistoricalDatasetListResponse,
    HistoricalDatasetManifestResponse,
    DeviceTokenRegisterRequest,
    LiveSignalScanRequest,
    MessageResponse,
    Mt5OrderRequest,
    NotificationTestRequest,
    OandaOrderRequest,
    OperationalDriftRequest,
    OperationalDriftResponse,
    OperationalPromotionPanelRequest,
    OperationalPromotionPanelResponse,
    OperationalSloRequest,
    OperationalSloResponse,
    PaperExecutionControl,
    PaperExecutionControlUpdateRequest,
    PaperFeedStatus,
    PaperFeedSubscription,
    PaperFeedSubscriptionListResponse,
    PaperFeedSubscriptionUpsertRequest,
    PaperFeedSyncRequest,
    PaperFeedSyncResponse,
    PaperFundingSettlementRequest,
    PaperFundingSettlementResponse,
    PaperLedgerAuditResponse,
    PaperConnectorCheckpoint,
    PaperConnectorCheckpointListResponse,
    PaperConnectorProbeRequest,
    PaperCorrelationSnapshotRequest,
    PaperCorrelationSnapshotResponse,
    PaperChaosDrillRunRequest,
    PaperChaosDrillRunResponse,
    PaperRecoverySnapshotRequest,
    PaperRecoverySnapshotResponse,
    PaperTestnetExecutionControl,
    PaperTestnetExecutionControlUpdate,
    PaperTestnetOrder,
    PaperTestnetOrderListResponse,
    PaperTestnetOrderRequest,
    PaperMarginEventListResponse,
    PaperPrivateTestnetReconciliationResponse,
    PaperPrivateTestnetSyncRequest,
    PaperRecoveryDrillRequest,
    PaperRecoveryDrillResponse,
    PaperShadowReconciliationRequest,
    PaperShadowReconciliationResponse,
    PaperMarketTickRequest,
    PaperOrder,
    PaperOrderCreateRequest,
    PaperOrderListResponse,
    PaperPortfolio,
    PaperReconciliationResponse,
    ProviderConnectionTestResponse,
    ProviderSecretStatus,
    ProviderSecretStatusResponse,
    ProviderSecretUpsertRequest,
    PurgedSplitPlanRequest,
    PurgedSplitPlanResponse,
    QuantValidationRequest,
    QuantValidationResponse,
    RiskPlan,
    RiskPlanRequest,
    SignalHistoryItem,
    SignalShadowCaptureResponse,
    SignalShadowDiagnosticsResponse,
    SignalShadowPanelResponse,
    SignalShadowResearchPanelResponse,
    SignalShadowResearchSnapshotResponse,
    SignalShadowResolutionResponse,
    SignalRequest,
    SignalResponse,
    StrategyPanelValidationRequest,
    StrategyPanelValidationResponse,
    StoredBacktestResearchRequest,
    StoredBacktestResearchResponse,
    StoredWalkForwardResearchRequest,
    StoredWalkForwardResearchResponse,
    SystemReadinessResponse,
    TradeJournalCloseRequest,
    TradeJournalCreateRequest,
    TradeJournalItem,
    TradeJournalStats,
)
from app.services.ai_explainability_service import OpenAICompatibleProvider, ai_explainability_service
from app.services.auth_service import AuthService
from app.services.automated_panel_service import AutomatedPanelError, AutomatedPanelResearchService
from app.services.backtest_service import BacktestService
from app.services.binance_connector import BinanceFuturesConnector
from app.services.bybit_connector import BybitConnector
from app.services.ctrader_connector import CTraderConnector
from app.services.deflated_performance_service import deflated_performance_service
from app.services.execution_engine import ExecutionEngine
from app.services.historical_data_service import HistoricalDataError, HistoricalDataService
from app.services.intraday_fusion_service import IntradayFusionService
from app.services.market_data_service import MarketDataService
from app.services.news_engine import mock_news
from app.services.notification_service import NotificationService
from app.services.orderflow_service import OrderFlowService
from app.services.operational_validation_service import OperationalValidationError, OperationalValidationService
from app.services.paper_correlation_service import PaperCorrelationError, PaperCorrelationService
from app.services.paper_chaos_service import PaperChaosError, PaperChaosService
from app.services.paper_market_feed_service import PaperFeedError, PaperMarketFeedService
from app.services.paper_oms_service import PaperOmsError, PaperOmsService
from app.services.paper_private_testnet_service import PaperPrivateTestnetError, PaperPrivateTestnetService
from app.services.paper_testnet_execution_service import PaperTestnetExecutionError, PaperTestnetExecutionService
from app.services.paper_recovery_service import PaperRecoveryError, PaperRecoveryService
from app.services.provider_secret_service import ProviderSecretService, ProviderVaultError
from app.services.production_guard_service import (
    client_identity,
    http_logger,
    monitoring_service,
    rate_limiter,
    request_id,
    structured_http_log,
)
from app.services.quant_validation_service import quant_validation_service
from app.services.readiness_service import ReadinessService
from app.services.mt5_connector import Mt5Connector
from app.services.oanda_connector import OandaConnector
from app.services.risk_engine import build_risk_plan
from app.services.session_engine import evaluate_session
from app.services.setup_state_engine import SetupStateEngine
from app.services.signal_engine import SignalEngine
from app.services.signal_shadow_service import SignalShadowError, SignalShadowService
from app.services.strict_decision_engine import apply_strict_decision
from app.services.storage_service import StorageService
from app.services.stored_research_service import StoredResearchError, StoredResearchService
from app.services.strategy_panel_service import strategy_panel_validation_service
from app.services.user_news_service import user_news_service


@asynccontextmanager
async def lifespan(_: FastAPI):
    global paper_feed_worker_task, signal_shadow_worker_task, signal_shadow_wake_task
    if settings.paper_feed_worker_enabled and paper_feed_worker_task is None:
        paper_feed_worker_task = asyncio.create_task(
            paper_market_feed_service.run_forever(),
            name="paper-market-feed-worker",
        )
    if settings.signal_shadow_worker_enabled and signal_shadow_worker_task is None:
        signal_shadow_worker_task = asyncio.create_task(
            signal_shadow_worker_loop(),
            name="signal-shadow-worker",
        )
    try:
        yield
    finally:
        if paper_feed_worker_task is not None:
            paper_feed_worker_task.cancel()
            try:
                await paper_feed_worker_task
            except asyncio.CancelledError:
                pass
            paper_feed_worker_task = None
        if signal_shadow_worker_task is not None:
            signal_shadow_worker_task.cancel()
            try:
                await signal_shadow_worker_task
            except asyncio.CancelledError:
                pass
            signal_shadow_worker_task = None
        if signal_shadow_wake_task is not None and not signal_shadow_wake_task.done():
            signal_shadow_wake_task.cancel()
            try:
                await signal_shadow_wake_task
            except asyncio.CancelledError:
                pass
            signal_shadow_wake_task = None


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url=None,
)
_STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.get("/docs", include_in_schema=False)
def self_hosted_swagger_docs():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{settings.app_name} - API Docs",
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
    )


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
provider_secret_service = ProviderSecretService(storage.database)
paper_oms_service = PaperOmsService(storage.database)
paper_chaos_service = PaperChaosService(storage.database)
paper_recovery_service = PaperRecoveryService(storage.database)
paper_private_testnet_service = PaperPrivateTestnetService(
    storage.database,
    provider_secret_service,
)
paper_testnet_execution_service = PaperTestnetExecutionService(
    storage.database,
    provider_secret_service,
)
paper_market_feed_service = PaperMarketFeedService(storage.database, paper_oms_service)
paper_feed_worker_task: asyncio.Task | None = None
signal_shadow_worker_task: asyncio.Task | None = None
signal_shadow_wake_task: asyncio.Task | None = None
signal_shadow_cycle_lock = asyncio.Lock()
signal_shadow_last_attempt_monotonic: dict[str, float] = {}
historical_data_service = HistoricalDataService(storage.database)
paper_correlation_service = PaperCorrelationService(
    storage.database,
    historical_data_service.store,
)
operational_validation_service = OperationalValidationService(
    storage.database,
    historical_data_service.store,
)
stored_research_service = StoredResearchService(
    historical_data_service.store,
    backtest_service,
    quant_validation_service,
)
automated_panel_service = AutomatedPanelResearchService(
    storage.database,
    historical_data_service.store,
    backtest_service,
    strategy_panel_validation_service,
    quant_validation_service,
    deflated_performance_service,
)
notification_service = NotificationService(storage)
readiness_service = ReadinessService(storage.database)
orderflow_service = OrderFlowService(ttl_seconds=20)
intraday_fusion_service = IntradayFusionService()
signal_shadow_service = SignalShadowService(storage.database)
setup_state_engine = SetupStateEngine()


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


@app.middleware("http")
async def production_guard(request: Request, call_next):
    started = time.monotonic()
    req_id = request_id(request.headers.get("X-Request-ID"))
    identity = client_identity(
        request.client.host if request.client else None,
        request.headers.get("X-Forwarded-For"),
    )
    path = request.url.path
    error_type = None

    try:
        content_length = int(request.headers.get("Content-Length") or 0)
    except ValueError:
        content_length = 0
    body_too_large = content_length > settings.max_request_body_bytes
    if not content_length and request.method in {"POST", "PUT", "PATCH"}:
        body_too_large = len(await request.body()) > settings.max_request_body_bytes

    rate_decision = None
    if body_too_large:
        response = JSONResponse(
            status_code=413,
            content={"detail": "Request body is too large", "request_id": req_id},
        )
    elif (
        settings.rate_limit_enabled
        and os.getenv("APP_ENV", settings.app_env).lower() != "test"
        and path not in {"/health", "/ready"}
    ):
        rate_decision = rate_limiter.check(identity, path)
        if not rate_decision.allowed:
            monitoring_service.record_rate_limited()
            response = JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after_seconds": rate_decision.retry_after_seconds,
                    "request_id": req_id,
                },
                headers={"Retry-After": str(rate_decision.retry_after_seconds)},
            )
        else:
            try:
                response = await call_next(request)
            except Exception as exc:
                response = JSONResponse(
                    status_code=500,
                    content={"detail": "Internal server error", "request_id": req_id},
                )
                error_type = type(exc).__name__[:60]
    else:
        try:
            response = await call_next(request)
        except Exception as exc:
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "request_id": req_id},
            )
            error_type = type(exc).__name__[:60]

    route_object = request.scope.get("route")
    route = getattr(route_object, "path", None) or "__unmatched__"
    latency_ms = max(0, int((time.monotonic() - started) * 1000))
    monitoring_service.record(route, response.status_code, latency_ms)
    structured_http_log(
        http_logger,
        req_id=req_id,
        method=request.method,
        route=route,
        status_code=response.status_code,
        latency_ms=latency_ms,
        identity=identity,
        error_type=error_type,
    )

    response.headers["X-Request-ID"] = req_id
    response.headers["X-Response-Time-Ms"] = str(latency_ms)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if path.startswith(("/docs", "/redoc")):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://fastapi.tiangolo.com; frame-ancestors 'none'"
        )
    else:
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    if settings.app_env.lower() == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if path.startswith(("/api/v1/auth", "/api/v1/ai")):
        response.headers["Cache-Control"] = "no-store"
    if rate_decision is not None:
        response.headers["X-RateLimit-Limit"] = str(rate_decision.limit)
        response.headers["X-RateLimit-Remaining"] = str(rate_decision.remaining)
    return response


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


def optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
):
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None
    return auth_service.get_user_by_token(credentials.credentials)


def _runtime_ai_provider_for_user(user_id: int, requested: str = "auto"):
    selected = requested
    if selected == "auto":
        selected = (
            "groq"
            if provider_secret_service.get_material(user_id, "groq")
            else "openai_compatible"
        )
    if selected == "groq":
        material = provider_secret_service.get_material(user_id, "groq")
        if material:
            return OpenAICompatibleProvider(
                base_url="https://api.groq.com/openai/v1",
                api_key=material.api_key,
                model=material.model or "llama-3.3-70b-versatile",
                provider_name="groq",
            )
    if selected == "openai_compatible":
        material = provider_secret_service.get_material(user_id, "openai")
        if material:
            return OpenAICompatibleProvider(
                base_url="https://api.openai.com/v1",
                api_key=material.api_key,
                model=material.model or "gpt-4.1-mini",
                provider_name="openai_compatible",
            )
    return None


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


async def enrich_orderflow(report: dict, symbol: str, market: str, items: list[dict]) -> dict:
    snapshot = await orderflow_service.get_snapshot(symbol, market, items)
    candle_proxy = dict(report.get("orderflow") or {})
    merged = {"candle_proxy": candle_proxy, **snapshot}
    report["orderflow"] = merged
    return snapshot


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "env": settings.app_env,
    }


@app.get("/ready")
def ready():
    database = storage.database.health()
    production_database_ready = (
        settings.app_env.lower() != "production"
        or (database["backend"] == "postgresql" and database["persistent"])
    )
    ready_now = bool(
        database["connected"]
        and database["migration_current"]
        and production_database_ready
    )
    return JSONResponse(
        status_code=200 if ready_now else 503,
        content={
            "status": "ready" if ready_now else "not_ready",
            "database": {
                "connected": database["connected"],
                "backend": database["backend"],
                "persistent": database["persistent"],
                "migration_current": database["migration_current"],
                "production_database_ready": production_database_ready,
            },
            "live_execution_enabled": settings.enable_live_execution,
        },
    )


@app.get("/api/v1/system/health/deep")
def deep_health(user=Depends(current_user)) -> dict:
    return {
        "status": "ok",
        "version": settings.app_version,
        "database": storage.database.health(),
        "ai": ai_explainability_service.status(),
        "monitoring": monitoring_service.snapshot(),
        "rate_limiting": {
            "enabled": settings.rate_limit_enabled,
            "mode": "in_process_sliding_window",
        },
        "live_execution_enabled": settings.enable_live_execution,
    }


@app.get("/api/v1/system/metrics")
def production_metrics(user=Depends(current_user)) -> dict:
    return monitoring_service.snapshot()


@app.post("/api/v1/operations/drift", response_model=OperationalDriftResponse)
def run_operational_drift(request: OperationalDriftRequest, user=Depends(current_user)):
    try:
        return operational_validation_service.run_drift(user.id, request)
    except OperationalValidationError as exc:
        _raise_operational_validation_error(exc)


@app.post("/api/v1/operations/slo", response_model=OperationalSloResponse)
def evaluate_operational_slo(request: OperationalSloRequest, user=Depends(current_user)):
    return operational_validation_service.evaluate_slo(monitoring_service.snapshot(), request)


@app.post("/api/v1/operations/promotion-panel", response_model=OperationalPromotionPanelResponse)
def evaluate_operational_promotion_panel(
    request: OperationalPromotionPanelRequest,
    user=Depends(current_user),
):
    try:
        return operational_validation_service.evaluate_promotion_panel(
            user.id, request, monitoring_service.snapshot()
        )
    except OperationalValidationError as exc:
        _raise_operational_validation_error(exc)


@app.get("/api/v1/ai/status")
def ai_status() -> dict:
    """Return provider readiness without exposing keys, endpoints or secrets."""
    return ai_explainability_service.status()


@app.post("/api/v1/ai/explain", response_model=AIExplainResponse)
async def explain_ai_decision(request: AIExplainRequest, user=Depends(current_user)):
    """Explain an immutable deterministic decision using cited evidence only."""
    runtime_provider = _runtime_ai_provider_for_user(user.id, request.provider)
    return await ai_explainability_service.explain(
        request,
        runtime_provider=runtime_provider,
        cache_namespace=f"user-{user.id}",
    )


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


def _raise_provider_vault_error(exc: ProviderVaultError):
    status = 503 if exc.code == "provider_vault_not_configured" else 400
    raise HTTPException(status_code=status, detail={"code": exc.code}) from exc


@app.get("/api/v1/settings/providers", response_model=ProviderSecretStatusResponse)
def provider_secret_status(user=Depends(current_user)):
    return provider_secret_service.list_status(user.id)


@app.post(
    "/api/v1/settings/providers/{provider}",
    response_model=ProviderSecretStatus,
)
def save_provider_secret(
    provider: str,
    request: ProviderSecretUpsertRequest,
    user=Depends(current_user),
):
    try:
        return provider_secret_service.upsert(user.id, provider, request)
    except ProviderVaultError as exc:
        _raise_provider_vault_error(exc)


@app.post(
    "/api/v1/settings/providers/{provider}/test",
    response_model=ProviderConnectionTestResponse,
)
async def test_provider_secret(provider: str, user=Depends(current_user)):
    try:
        return await provider_secret_service.test_connection(user.id, provider)
    except ProviderVaultError as exc:
        _raise_provider_vault_error(exc)


@app.delete(
    "/api/v1/settings/providers/{provider}",
    response_model=MessageResponse,
)
def delete_provider_secret(provider: str, user=Depends(current_user)):
    try:
        provider_secret_service.delete(user.id, provider)
        return MessageResponse(message=f"Provider {provider} configuration deleted")
    except ProviderVaultError as exc:
        _raise_provider_vault_error(exc)


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
    except Exception:
        logger.error("news brief failed; returning sanitized fallback")
        return {
            "finnhub_configured": bool(k),
            "server_time_unix": int(time.time()),
            "server_time_iso": "",
            "block": {"blocked": False, "reasons": [], "block_until": 0, "active_events": []},
            "adjustment": {"bias": "neutral", "score_penalty": 0, "note": "اخبار موقتاً در دسترس نیست؛ بعداً دوباره تلاش کنید."},
            "events": {"upcoming": [], "live": [], "past": []},
            "headlines": []
        }


@app.get("/api/v1/news/personalized")
async def personalized_news(user=Depends(current_user)) -> dict:
    return await user_news_service.build(user.id, provider_secret_service)


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
    user=Depends(optional_current_user),
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
        logger.error("SMC candles fetch failed; details suppressed")
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
        logger.warning("HTF bias calculation failed; details suppressed")

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
        flow = await enrich_orderflow(report, symbol, market_eff, items)
        report = apply_strict_decision(
            report,
            items,
            market=market_eff,
            timeframe=_canonical_timeframe(interval),
            orderflow_source=str(flow.get("source") or "unknown"),
            orderflow_confidence=float(flow.get("confidence") or 0),
            orderflow_snapshot=flow,
        )
        try:
            report = await ai_explainability_service.enrich_report(
                report,
                market=market_eff,
                timeframe=_canonical_timeframe(interval),
                language="fa",
                runtime_provider=(
                    _runtime_ai_provider_for_user(user.id, "auto") if user else None
                ),
                cache_namespace=(f"user-{user.id}" if user else "public"),
            )
        except Exception:
            # The strict deterministic decision remains available even if the
            # optional explanation layer is unavailable.
            pass
        report["status"] = "ok"
        return _prepare_chart_report(report, items, max_candles=160)
    except Exception:
        logger.error("SMC analysis failed; details suppressed")
        return _smc_err(
            symbol,
            interval,
            items[-1]["c"] if items else 0,
            "تحلیل نمودار موقتاً ناموفق بود؛ دوباره تلاش کنید.",
            code="analysis_failed",
            candles=items[-160:],
            count=len(items),
        )



@app.get("/api/v1/analysis/intraday-fusion")
async def get_intraday_fusion(
    symbol: str = Query("BTCUSDT", min_length=2, max_length=24),
    market: str = Query("", pattern="^(|crypto|forex)$"),
    user=Depends(optional_current_user),
):
    """Precision-first causal fusion of completed 5m/15m/1h/4h evidence."""
    from app.services.smc_engine import analyze

    symbol = symbol.upper()
    market_eff = _auto_market(symbol, market or None)
    timeframes = ("5m", "15m", "1h", "4h")
    try:
        raw_frames = await asyncio.gather(
            *(fetch_live_candles(symbol=symbol, market=market_eff, timeframe=tf) for tf in timeframes)
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"code": "fusion_market_data_unavailable"}) from exc
    items_by_tf = {
        tf: _completed_candles(_norm_candles(raw[-260:]), tf)[-260:]
        for tf, raw in zip(timeframes, raw_frames)
    }
    if any(len(items_by_tf[tf]) < 50 for tf in timeframes):
        raise HTTPException(status_code=422, detail={"code": "fusion_insufficient_frame_data"})
    initial = {tf: analyze(items_by_tf[tf], symbol=symbol, timeframe=tf) for tf in timeframes}
    higher = {"5m": "15m", "15m": "1h", "1h": "4h", "4h": None}
    reports = []
    for tf in timeframes:
        htf = higher[tf]
        htf_bias = initial[htf].get("bias") if htf else initial[tf].get("bias")
        report = analyze(items_by_tf[tf], symbol=symbol, timeframe=tf, htf_bias=htf_bias)
        report["market"] = market_eff
        report["frame_freshness"] = _frame_freshness(items_by_tf[tf], tf)
        flow = await enrich_orderflow(report, symbol, market_eff, items_by_tf[tf])
        report = apply_strict_decision(
            report,
            items_by_tf[tf],
            market=market_eff,
            timeframe=tf,
            orderflow_source=str(flow.get("source") or "unknown"),
            orderflow_confidence=float(flow.get("confidence") or 0),
            orderflow_snapshot=flow,
        )
        reports.append({"timeframe": tf, "report": report})
    result = intraday_fusion_service.fuse(symbol, market_eff, reports)
    result["frame_source"] = "server_generated_completed_candles"
    result["completed_candle_enforced"] = True
    result["user_scoped_ai_used"] = False
    return result


def _all_fusion_frames_stale(result: dict) -> bool:
    frames = [item for item in (result.get("frames") or []) if isinstance(item, dict)]
    return bool(frames) and all(item.get("fresh") is False for item in frames)


async def run_signal_shadow_cycle() -> dict:
    if signal_shadow_cycle_lock.locked():
        return {
            "status": "skipped_locked",
            "captured": 0,
            "resolved": 0,
            "skipped_all_frames_stale": 0,
            "errors": 0,
            "attempted_symbols": 0,
            "not_due_symbols": 0,
            "collector_max_concurrency": max(
                1,
                min(settings.signal_shadow_max_concurrency, 8),
            ),
        }
    captured = resolved = skipped_all_frames_stale = errors = 0
    interval = max(300, settings.signal_shadow_interval_seconds)
    async with signal_shadow_cycle_lock:
        for context in signal_shadow_service.pending_contexts(0, limit=50):
            try:
                if not context.get("resolution_timeframe"):
                    continue
                raw = await fetch_live_candles(
                    symbol=context["symbol"], market=context["market"],
                    timeframe=context["resolution_timeframe"],
                )
                outcome = signal_shadow_service.resolve(
                    0, context["observation_id"], _norm_candles(raw)
                )
                if outcome.outcome_status != "PENDING":
                    resolved += 1
            except Exception:
                errors += 1
        maximum_concurrency = max(1, min(settings.signal_shadow_max_concurrency, 8))
        semaphore = asyncio.Semaphore(maximum_concurrency)

        async def collect_symbol(symbol: str) -> str:
            now_monotonic = time.monotonic()
            last_attempt = signal_shadow_last_attempt_monotonic.get(symbol)
            if last_attempt is not None and now_monotonic - last_attempt < interval:
                return "not_due"
            if not signal_shadow_service.should_capture(0, symbol, interval):
                return "not_due"
            # Record attempts even when providers fail or all frames are stale;
            # otherwise a five-minute wake would repeatedly hit closed markets.
            signal_shadow_last_attempt_monotonic[symbol] = now_monotonic
            async with semaphore:
                try:
                    market = _auto_market(symbol, None)
                    result = await get_intraday_fusion(symbol=symbol, market=market, user=None)
                    # A fully stale frame set represents a closed/unavailable market,
                    # not a new OOS observation. Do not inflate NO_TRADE counts.
                    if _all_fusion_frames_stale(result):
                        return "stale"
                    signal_shadow_service.capture(0, result)
                    return "captured"
                except Exception:
                    return "error"

        symbols = list(dict.fromkeys(item.upper() for item in settings.signal_shadow_symbols))
        collection_results = await asyncio.gather(*(collect_symbol(symbol) for symbol in symbols))
        captured += collection_results.count("captured")
        skipped_all_frames_stale += collection_results.count("stale")
        errors += collection_results.count("error")
        attempted_symbols = sum(result != "not_due" for result in collection_results)
        not_due_symbols = collection_results.count("not_due")
    panel = signal_shadow_service.panel(0, minimum_required_resolved=30)
    research = signal_shadow_service.research_panel(
        0,
        minimum_terminal_outcomes=30,
        minimum_activated_outcomes=30,
        breakdown_minimum_activated=10,
    )
    diagnostics = signal_shadow_service.diagnostics(0)
    return {
        "status": "completed",
        "captured": captured,
        "resolved": resolved,
        "skipped_all_frames_stale": skipped_all_frames_stale,
        "errors": errors,
        "attempted_symbols": attempted_symbols,
        "not_due_symbols": not_due_symbols,
        "collector_max_concurrency": maximum_concurrency,
        "total_observations": panel.total_observations,
        "candidate_count": panel.candidate_count,
        "pending_outcomes": panel.pending_outcomes,
        "resolved_outcomes": panel.resolved_outcomes,
        "activated_resolved_outcomes": panel.activated_resolved_outcomes,
        "research_status": research.status,
        "research_ready": research.research_ready,
        "valid_non_all_stale_observations": diagnostics.valid_non_all_stale_observations,
        "observation_span_days": diagnostics.observation_span_days,
        "scarcity_review_status": diagnostics.scarcity_review_status,
        "feasibility_audit_authorized": diagnostics.feasibility_audit_authorized,
        "precision_claimed": research.precision_claimed,
        "actionable_for_live": False,
    }


async def signal_shadow_worker_loop() -> None:
    await asyncio.sleep(20)
    interval = max(300, settings.signal_shadow_interval_seconds)
    while True:
        try:
            await run_signal_shadow_cycle()
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        await asyncio.sleep(interval)


@app.post("/internal/signal-shadow-cycle", include_in_schema=False)
async def trigger_signal_shadow_cycle(
    x_shadow_cron_token: str | None = Header(default=None, alias="X-Shadow-Cron-Token"),
):
    expected = settings.signal_shadow_cron_token
    if settings.app_env != "staging" or not expected:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    if not x_shadow_cron_token or not hmac.compare_digest(x_shadow_cron_token, expected):
        raise HTTPException(status_code=401, detail={"code": "invalid_shadow_cron_token"})
    return await run_signal_shadow_cycle()


def _consume_signal_shadow_wake(task: asyncio.Task) -> None:
    try:
        task.result()
    except (asyncio.CancelledError, Exception):
        # The next wake remains available; details must never leak into logs.
        pass


@app.post("/internal/signal-shadow-wake", include_in_schema=False, status_code=202)
async def trigger_external_signal_shadow_wake(
    x_shadow_external_token: str | None = Header(
        default=None,
        alias="X-Shadow-External-Token",
    ),
):
    global signal_shadow_wake_task
    expected = settings.signal_shadow_external_cron_token
    if settings.app_env != "staging" or not expected:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    if not x_shadow_external_token or not hmac.compare_digest(
        x_shadow_external_token,
        expected,
    ):
        raise HTTPException(status_code=401, detail={"code": "invalid_external_cron_token"})
    if signal_shadow_cycle_lock.locked() or (
        signal_shadow_wake_task is not None and not signal_shadow_wake_task.done()
    ):
        return {
            "status": "already_running",
            "background_started": False,
            "actionable_for_live": False,
        }
    signal_shadow_wake_task = asyncio.create_task(
        run_signal_shadow_cycle(),
        name="signal-shadow-external-wake",
    )
    signal_shadow_wake_task.add_done_callback(_consume_signal_shadow_wake)
    return {
        "status": "accepted",
        "background_started": True,
        "actionable_for_live": False,
    }


@app.post("/api/v1/analysis/intraday-fusion/shadow", response_model=SignalShadowCaptureResponse)
async def capture_intraday_fusion_shadow(
    symbol: str = Query("BTCUSDT", min_length=2, max_length=24),
    market: str = Query("", pattern="^(|crypto|forex)$"),
    user=Depends(current_user),
):
    result = await get_intraday_fusion(symbol=symbol, market=market, user=user)
    return signal_shadow_service.capture(user.id, result)


@app.post("/api/v1/analysis/intraday-fusion/shadow/{observation_id}/resolve", response_model=SignalShadowResolutionResponse)
async def resolve_intraday_fusion_shadow(observation_id: str, user=Depends(current_user)):
    try:
        context = signal_shadow_service.resolution_context(user.id, observation_id)
        if not context.get("resolution_timeframe"):
            raise SignalShadowError("shadow_resolution_timeframe_missing")
        raw = await fetch_live_candles(
            symbol=context["symbol"], market=context["market"],
            timeframe=context["resolution_timeframe"],
        )
        return signal_shadow_service.resolve(user.id, observation_id, _norm_candles(raw))
    except SignalShadowError as exc:
        status = 404 if "not_found" in exc.code else 400
        raise HTTPException(status_code=status, detail={"code": exc.code}) from exc


@app.get("/api/v1/analysis/intraday-fusion/shadow/system-panel", response_model=SignalShadowPanelResponse)
def get_system_intraday_fusion_shadow_panel(
    minimum_required_resolved: int = Query(default=30, ge=10, le=1000),
    user=Depends(current_user),
):
    return signal_shadow_service.panel(0, minimum_required_resolved)


@app.get("/api/v1/analysis/intraday-fusion/shadow/panel", response_model=SignalShadowPanelResponse)
def get_intraday_fusion_shadow_panel(
    minimum_required_resolved: int = Query(default=30, ge=10, le=1000),
    user=Depends(current_user),
):
    return signal_shadow_service.panel(user.id, minimum_required_resolved)


@app.get(
    "/api/v1/analysis/intraday-fusion/shadow/system-diagnostics",
    response_model=SignalShadowDiagnosticsResponse,
)
def get_system_intraday_fusion_shadow_diagnostics(user=Depends(current_user)):
    return signal_shadow_service.diagnostics(0)


@app.get(
    "/api/v1/analysis/intraday-fusion/shadow/diagnostics",
    response_model=SignalShadowDiagnosticsResponse,
)
def get_intraday_fusion_shadow_diagnostics(user=Depends(current_user)):
    return signal_shadow_service.diagnostics(user.id)


@app.get(
    "/api/v1/analysis/intraday-fusion/shadow/system-research-panel",
    response_model=SignalShadowResearchPanelResponse,
)
def get_system_intraday_fusion_shadow_research_panel(
    minimum_terminal_outcomes: int = Query(default=30, ge=30, le=1000),
    minimum_activated_outcomes: int = Query(default=30, ge=30, le=1000),
    breakdown_minimum_activated: int = Query(default=10, ge=10, le=1000),
    user=Depends(current_user),
):
    return signal_shadow_service.research_panel(
        0,
        minimum_terminal_outcomes=minimum_terminal_outcomes,
        minimum_activated_outcomes=minimum_activated_outcomes,
        breakdown_minimum_activated=breakdown_minimum_activated,
    )


@app.get(
    "/api/v1/analysis/intraday-fusion/shadow/research-panel",
    response_model=SignalShadowResearchPanelResponse,
)
def get_intraday_fusion_shadow_research_panel(
    minimum_terminal_outcomes: int = Query(default=30, ge=30, le=1000),
    minimum_activated_outcomes: int = Query(default=30, ge=30, le=1000),
    breakdown_minimum_activated: int = Query(default=10, ge=10, le=1000),
    user=Depends(current_user),
):
    return signal_shadow_service.research_panel(
        user.id,
        minimum_terminal_outcomes=minimum_terminal_outcomes,
        minimum_activated_outcomes=minimum_activated_outcomes,
        breakdown_minimum_activated=breakdown_minimum_activated,
    )


@app.post(
    "/api/v1/analysis/intraday-fusion/shadow/system-research-snapshot",
    response_model=SignalShadowResearchSnapshotResponse,
)
def lock_system_intraday_fusion_shadow_research_snapshot(
    minimum_terminal_outcomes: int = Query(default=30, ge=30, le=1000),
    minimum_activated_outcomes: int = Query(default=30, ge=30, le=1000),
    breakdown_minimum_activated: int = Query(default=10, ge=10, le=1000),
    user=Depends(current_user),
):
    try:
        return signal_shadow_service.lock_research_snapshot(
            0,
            minimum_terminal_outcomes=minimum_terminal_outcomes,
            minimum_activated_outcomes=minimum_activated_outcomes,
            breakdown_minimum_activated=breakdown_minimum_activated,
        )
    except SignalShadowError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code}) from exc


@app.post(
    "/api/v1/analysis/intraday-fusion/shadow/research-snapshot",
    response_model=SignalShadowResearchSnapshotResponse,
)
def lock_intraday_fusion_shadow_research_snapshot(
    minimum_terminal_outcomes: int = Query(default=30, ge=30, le=1000),
    minimum_activated_outcomes: int = Query(default=30, ge=30, le=1000),
    breakdown_minimum_activated: int = Query(default=10, ge=10, le=1000),
    user=Depends(current_user),
):
    try:
        return signal_shadow_service.lock_research_snapshot(
            user.id,
            minimum_terminal_outcomes=minimum_terminal_outcomes,
            minimum_activated_outcomes=minimum_activated_outcomes,
            breakdown_minimum_activated=breakdown_minimum_activated,
        )
    except SignalShadowError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code}) from exc


@app.get(
    "/api/v1/analysis/intraday-fusion/shadow/system-research-snapshot/{snapshot_id}",
    response_model=SignalShadowResearchSnapshotResponse,
)
def get_system_intraday_fusion_shadow_research_snapshot(
    snapshot_id: str,
    user=Depends(current_user),
):
    try:
        return signal_shadow_service.get_research_snapshot(0, snapshot_id)
    except SignalShadowError as exc:
        status_code = 404 if exc.code.endswith("not_found") else 400
        raise HTTPException(status_code=status_code, detail={"code": exc.code}) from exc


@app.get(
    "/api/v1/analysis/intraday-fusion/shadow/research-snapshot/{snapshot_id}",
    response_model=SignalShadowResearchSnapshotResponse,
)
def get_intraday_fusion_shadow_research_snapshot(
    snapshot_id: str,
    user=Depends(current_user),
):
    try:
        return signal_shadow_service.get_research_snapshot(user.id, snapshot_id)
    except SignalShadowError as exc:
        status_code = 404 if exc.code.endswith("not_found") else 400
        raise HTTPException(status_code=status_code, detail={"code": exc.code}) from exc


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


def _completed_candles(items: list[dict], timeframe: str, now_timestamp: float | None = None):
    """Drop malformed, duplicate and still-open bars before causal analysis."""
    seconds = {
        "1m": 60,
        "3m": 3 * 60,
        "5m": 5 * 60,
        "15m": 15 * 60,
        "30m": 30 * 60,
        "1h": 60 * 60,
        "2h": 2 * 60 * 60,
        "4h": 4 * 60 * 60,
        "1d": 24 * 60 * 60,
    }.get(_canonical_timeframe(timeframe))
    if not seconds:
        return []
    cutoff = float(now_timestamp if now_timestamp is not None else time.time())
    unique = {}
    for item in items:
        try:
            timestamp = float(item["t"])
            open_price = float(item["o"])
            high = float(item["h"])
            low = float(item["l"])
            close = float(item["c"])
        except (KeyError, TypeError, ValueError):
            continue
        if timestamp + seconds > cutoff:
            continue
        if timestamp <= 0 or min(open_price, high, low, close) <= 0:
            continue
        if low > high or not (low <= open_price <= high and low <= close <= high):
            continue
        unique[timestamp] = dict(item)
    return [unique[key] for key in sorted(unique)]


def _frame_freshness(items: list[dict], timeframe: str, now_timestamp: float | None = None):
    """Fail closed when the latest completed bar is too old for its frame."""
    seconds = {
        "1m": 60,
        "3m": 3 * 60,
        "5m": 5 * 60,
        "15m": 15 * 60,
        "30m": 30 * 60,
        "1h": 60 * 60,
        "2h": 2 * 60 * 60,
        "4h": 4 * 60 * 60,
        "1d": 24 * 60 * 60,
    }.get(_canonical_timeframe(timeframe))
    if not seconds or not items:
        return {"fresh": False, "age_seconds": None, "maximum_age_seconds": None}
    cutoff = float(now_timestamp if now_timestamp is not None else time.time())
    latest_close = float(items[-1]["t"]) + seconds
    age = max(0.0, cutoff - latest_close)
    maximum_age = seconds * 2.5
    return {
        "fresh": age <= maximum_age,
        "age_seconds": round(age, 3),
        "maximum_age_seconds": round(maximum_age, 3),
    }


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
            flow = await enrich_orderflow(r, sym, mkt_eff, items)
            r = apply_strict_decision(
                r,
                items,
                market=mkt_eff,
                timeframe=_canonical_timeframe(tf),
                orderflow_source=str(flow.get("source") or "unknown"),
                orderflow_confidence=float(flow.get("confidence") or 0),
                orderflow_snapshot=flow,
            )
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
        except Exception:
            log.warning("scan failed for %s@%s; details suppressed", sym, tf)
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
    entry_zone = report.get("entry_zone") or {}
    entry_low = entry_zone.get("low")
    entry_high = entry_zone.get("high")
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
        "atr": report.get("atr", 0),
        "entry": entry,
        "entry_low": entry_low,
        "entry_high": entry_high,
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
        "decision": report.get("decision") or {},
        "data_quality": report.get("data_quality") or {},
        "market_regime": report.get("market_regime") or {},
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
    if cached and age < _SETUP_CACHE_TTL and (not force or age < 60):
        return {
            **cached,
            "cached": True,
            "cache_age_seconds": round(age, 1),
            "refresh_cooldown": bool(force and age < 60),
        }

    async with _SETUP_SCAN_LOCK:
        now = _time.time()
        cached = _SETUP_SCAN_CACHE.get("payload")
        age = now - float(_SETUP_SCAN_CACHE.get("timestamp") or 0)
        if cached and age < _SETUP_CACHE_TTL and (not force or age < 60):
            return {
                **cached,
                "cached": True,
                "cache_age_seconds": round(age, 1),
                "refresh_cooldown": bool(force and age < 60),
            }

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
                    flow = await enrich_orderflow(report, symbol, market, items)
                    report = apply_strict_decision(
                        report,
                        items,
                        market=market,
                        timeframe=timeframe,
                        orderflow_source=str(flow.get("source") or "unknown"),
                        orderflow_confidence=float(flow.get("confidence") or 0),
                        orderflow_snapshot=flow,
                    )
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
                    candidate = None
                    if confirmed:
                        candidate = _setup_payload(report, symbol, market, timeframe, "confirmed")
                    elif has_forming_setup:
                        candidate = _setup_payload(report, symbol, market, timeframe, "forming")
                    return {
                        "candidate": candidate,
                        "market_key": f"{symbol}:{timeframe}",
                        "price": float(report.get("price") or 0),
                    }
                except Exception:
                    return None

        matrix = [
            (symbol, market, timeframe)
            for symbol, market in _SETUP_SYMBOLS
            for timeframe in _SETUP_TIMEFRAMES
        ]
        results = await _asyncio.gather(*(job(*item) for item in matrix))
        successful = [item for item in results if item]
        candidates = [item["candidate"] for item in successful if item.get("candidate")]
        market_prices = {
            item["market_key"]: float(item.get("price") or 0) for item in successful
        }
        lifecycle = setup_state_engine.update(
            candidates,
            market_prices,
            now=datetime.now(timezone.utc),
        )
        forming = lifecycle["forming"][:20]
        armed = lifecycle["armed"][:20]
        confirmed = lifecycle["confirmed"][:20]
        triggered = lifecycle["triggered"][:20]
        invalidated = lifecycle["invalidated"][:20]
        expired = lifecycle["expired"][:20]
        generated_at = datetime.now(timezone.utc).isoformat()
        payload = {
            "active": confirmed + triggered,
            "forming": forming,
            "armed": armed,
            "confirmed": confirmed,
            "triggered": triggered,
            "invalidated": invalidated,
            "expired": expired,
            "active_count": len(confirmed) + len(triggered),
            "forming_count": len(forming),
            "armed_count": len(armed),
            "confirmed_count": len(confirmed),
            "triggered_count": len(triggered),
            "invalidated_count": len(invalidated),
            "expired_count": len(expired),
            "total_scanned": len(matrix),
            "generated_at": generated_at,
            "cached": False,
            "cache_age_seconds": 0,
            "state_machine": "v1",
        }
        _SETUP_SCAN_CACHE["timestamp"] = _time.time()
        _SETUP_SCAN_CACHE["payload"] = payload
        return payload


@app.get("/api/v1/orderflow/{symbol}")
async def get_orderflow_snapshot(
    symbol: str,
    market: str = Query(default="crypto", pattern="^(crypto|forex)$"),
    timeframe: str = Query(default="5m", pattern="^(1m|5m|15m|30m|1h|4h|1d)$"),
):
    candles = await fetch_live_candles(symbol, market, timeframe)
    items = _norm_candles(candles)
    snapshot = await orderflow_service.get_snapshot(symbol.upper(), market, items)
    return {
        "symbol": symbol.upper(),
        "market": market,
        "timeframe": timeframe,
        "snapshot": snapshot,
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
    except Exception:
        await websocket.send_json(
            {"error": "market_stream_unavailable", "request_id": request_id(None)}
        )
        await websocket.close()


def _raise_paper_oms_error(exc: PaperOmsError):
    status = 400
    if exc.code == "paper_order_not_found":
        status = 404
    elif exc.code in {
        "idempotency_key_payload_conflict",
        "tick_event_id_payload_conflict",
        "funding_event_id_payload_conflict",
    }:
        status = 409
    raise HTTPException(status_code=status, detail={"code": exc.code}) from exc


def _raise_paper_feed_error(exc: PaperFeedError):
    status = 404 if exc.code == "paper_feed_subscription_not_found" else 400
    raise HTTPException(status_code=status, detail={"code": exc.code}) from exc


def _raise_paper_recovery_error(exc: PaperRecoveryError):
    status = 409 if "payload_conflict" in exc.code else 400
    raise HTTPException(status_code=status, detail={"code": exc.code}) from exc


def _raise_operational_validation_error(exc: OperationalValidationError):
    status = 409 if "conflict" in exc.code else 404 if exc.code == "historical_dataset_not_found" else 400
    raise HTTPException(status_code=status, detail={"code": exc.code}) from exc


def _raise_paper_correlation_error(exc: PaperCorrelationError):
    status = 409 if "payload_conflict" in exc.code else 400
    if exc.code == "historical_dataset_not_found":
        status = 404
    raise HTTPException(status_code=status, detail={"code": exc.code}) from exc


def _raise_private_testnet_error(exc: PaperPrivateTestnetError):
    raise HTTPException(status_code=400, detail={"code": exc.code}) from exc


def _raise_paper_chaos_error(exc: PaperChaosError):
    status = 409 if "conflict" in exc.code else 404 if "not_found" in exc.code else 400
    raise HTTPException(status_code=status, detail={"code": exc.code}) from exc


def _raise_testnet_execution_error(exc: PaperTestnetExecutionError):
    status = 409 if "conflict" in exc.code else 400
    raise HTTPException(status_code=status, detail={"code": exc.code}) from exc


@app.get("/api/v1/paper/control", response_model=PaperExecutionControl)
def get_paper_control(user=Depends(current_user)):
    return paper_oms_service.get_control(user.id)


@app.post("/api/v1/paper/control", response_model=PaperExecutionControl)
def update_paper_control(
    request: PaperExecutionControlUpdateRequest,
    user=Depends(current_user),
):
    try:
        return paper_oms_service.update_control(user.id, request)
    except PaperOmsError as exc:
        _raise_paper_oms_error(exc)


@app.get("/api/v1/paper/feed/status", response_model=PaperFeedStatus)
def get_paper_feed_status(user=Depends(current_user)):
    return paper_market_feed_service.status(user.id)


@app.get(
    "/api/v1/paper/feed/subscriptions",
    response_model=PaperFeedSubscriptionListResponse,
)
def list_paper_feed_subscriptions(user=Depends(current_user)):
    return paper_market_feed_service.list_subscriptions(user.id)


@app.post(
    "/api/v1/paper/feed/subscriptions",
    response_model=PaperFeedSubscription,
)
def upsert_paper_feed_subscription(
    request: PaperFeedSubscriptionUpsertRequest,
    user=Depends(current_user),
):
    try:
        return paper_market_feed_service.upsert_subscription(user.id, request)
    except PaperFeedError as exc:
        _raise_paper_feed_error(exc)


@app.delete(
    "/api/v1/paper/feed/subscriptions/{symbol}",
    response_model=PaperFeedSubscription,
)
def disable_paper_feed_subscription(symbol: str, user=Depends(current_user)):
    try:
        return paper_market_feed_service.disable_subscription(user.id, symbol)
    except PaperFeedError as exc:
        _raise_paper_feed_error(exc)


@app.post("/api/v1/paper/feed/sync", response_model=PaperFeedSyncResponse)
async def sync_paper_market_feed(
    request: PaperFeedSyncRequest,
    user=Depends(current_user),
):
    return await paper_market_feed_service.sync_user(user.id, request)


@app.get("/api/v1/paper/testnet/execution/control", response_model=PaperTestnetExecutionControl)
def get_testnet_execution_control(user=Depends(current_user)):
    return paper_testnet_execution_service.get_control(user.id)


@app.post("/api/v1/paper/testnet/execution/control", response_model=PaperTestnetExecutionControl)
def update_testnet_execution_control(request: PaperTestnetExecutionControlUpdate, user=Depends(current_user)):
    try:
        return paper_testnet_execution_service.update_control(user.id, request)
    except PaperTestnetExecutionError as exc:
        _raise_testnet_execution_error(exc)


@app.post("/api/v1/paper/testnet/execution/orders", response_model=PaperTestnetOrder)
async def place_testnet_order(request: PaperTestnetOrderRequest, user=Depends(current_user)):
    try:
        return await paper_testnet_execution_service.place(user.id, request)
    except PaperTestnetExecutionError as exc:
        _raise_testnet_execution_error(exc)


@app.get("/api/v1/paper/testnet/execution/orders", response_model=PaperTestnetOrderListResponse)
def list_testnet_orders(user=Depends(current_user)):
    return paper_testnet_execution_service.list(user.id)


@app.post("/api/v1/paper/testnet/execution/orders/{order_id}/cancel", response_model=PaperTestnetOrder)
async def cancel_testnet_order(order_id: str, user=Depends(current_user)):
    try:
        return await paper_testnet_execution_service.cancel(user.id, order_id)
    except PaperTestnetExecutionError as exc:
        _raise_testnet_execution_error(exc)


@app.get(
    "/api/v1/paper/testnet/checkpoints",
    response_model=PaperConnectorCheckpointListResponse,
)
def list_paper_testnet_checkpoints(user=Depends(current_user)):
    return paper_recovery_service.list_checkpoints(user.id)


@app.post(
    "/api/v1/paper/testnet/connectors/{connector}/probe",
    response_model=PaperConnectorCheckpoint,
)
async def probe_paper_testnet_connector(
    connector: str,
    request: PaperConnectorProbeRequest,
    user=Depends(current_user),
):
    try:
        return await paper_recovery_service.probe_connector(user.id, connector, request.force)
    except PaperRecoveryError as exc:
        _raise_paper_recovery_error(exc)


@app.post(
    "/api/v1/paper/testnet/connectors/{connector}/private-reconcile",
    response_model=PaperPrivateTestnetReconciliationResponse,
)
async def reconcile_private_paper_testnet(
    connector: str,
    request: PaperPrivateTestnetSyncRequest,
    user=Depends(current_user),
):
    try:
        return await paper_private_testnet_service.reconcile(user.id, connector)
    except PaperPrivateTestnetError as exc:
        _raise_private_testnet_error(exc)


@app.post(
    "/api/v1/paper/testnet/recovery-drill",
    response_model=PaperRecoveryDrillResponse,
)
def run_paper_recovery_drill(
    request: PaperRecoveryDrillRequest,
    user=Depends(current_user),
):
    return paper_private_testnet_service.recovery_drill(request)


@app.post(
    "/api/v1/paper/testnet/shadow-reconcile",
    response_model=PaperShadowReconciliationResponse,
)
def reconcile_paper_testnet_shadow(
    request: PaperShadowReconciliationRequest,
    user=Depends(current_user),
):
    try:
        return paper_recovery_service.reconcile_shadow_snapshot(user.id, request)
    except PaperRecoveryError as exc:
        _raise_paper_recovery_error(exc)


@app.get("/api/v1/paper/audit", response_model=PaperLedgerAuditResponse)
def audit_paper_ledger(user=Depends(current_user)):
    return paper_recovery_service.audit_ledger(user.id)


@app.post("/api/v1/paper/recovery/snapshots", response_model=PaperRecoverySnapshotResponse)
def create_paper_recovery_snapshot(request: PaperRecoverySnapshotRequest, user=Depends(current_user)):
    try:
        return paper_chaos_service.create_snapshot(user.id, request.snapshot_id)
    except PaperChaosError as exc:
        _raise_paper_chaos_error(exc)


@app.get("/api/v1/paper/recovery/snapshots/{snapshot_id}/verify", response_model=PaperRecoverySnapshotResponse)
def verify_paper_recovery_snapshot(snapshot_id: str, user=Depends(current_user)):
    try:
        return paper_chaos_service.verify_snapshot(user.id, snapshot_id)
    except PaperChaosError as exc:
        _raise_paper_chaos_error(exc)


@app.post("/api/v1/paper/chaos/run", response_model=PaperChaosDrillRunResponse)
def run_paper_chaos_drill(request: PaperChaosDrillRunRequest, user=Depends(current_user)):
    if not settings.paper_chaos_enabled:
        raise HTTPException(status_code=403, detail={"code": "paper_chaos_disabled"})
    try:
        return paper_chaos_service.run(user.id, request)
    except PaperChaosError as exc:
        _raise_paper_chaos_error(exc)


@app.post(
    "/api/v1/paper/risk/correlation/snapshots",
    response_model=PaperCorrelationSnapshotResponse,
)
def build_paper_correlation_snapshot(
    request: PaperCorrelationSnapshotRequest,
    user=Depends(current_user),
):
    try:
        return paper_correlation_service.build_snapshot(user.id, request)
    except PaperCorrelationError as exc:
        _raise_paper_correlation_error(exc)


@app.post("/api/v1/paper/orders", response_model=PaperOrder)
def submit_paper_order(
    request: PaperOrderCreateRequest,
    user=Depends(current_user),
):
    try:
        return paper_oms_service.submit(user.id, request)
    except PaperOmsError as exc:
        _raise_paper_oms_error(exc)


@app.get("/api/v1/paper/orders", response_model=PaperOrderListResponse)
def list_paper_orders(
    limit: int = Query(default=100, ge=1, le=500),
    user=Depends(current_user),
):
    return paper_oms_service.list(user.id, limit)


@app.get("/api/v1/paper/orders/{order_id}", response_model=PaperOrder)
def get_paper_order(order_id: str, user=Depends(current_user)):
    try:
        return paper_oms_service.get(user.id, order_id)
    except PaperOmsError as exc:
        _raise_paper_oms_error(exc)


@app.post("/api/v1/paper/orders/{order_id}/cancel", response_model=PaperOrder)
def cancel_paper_order(order_id: str, user=Depends(current_user)):
    try:
        return paper_oms_service.cancel(user.id, order_id)
    except PaperOmsError as exc:
        _raise_paper_oms_error(exc)


@app.get("/api/v1/paper/portfolio", response_model=PaperPortfolio)
def get_paper_portfolio(user=Depends(current_user)):
    return paper_oms_service.get_portfolio(user.id)


@app.post("/api/v1/paper/mark", response_model=PaperPortfolio)
def mark_paper_portfolio(
    request: PaperMarketTickRequest,
    user=Depends(current_user),
):
    try:
        return paper_oms_service.mark_portfolio(user.id, request)
    except PaperOmsError as exc:
        _raise_paper_oms_error(exc)


@app.post(
    "/api/v1/paper/funding/settle",
    response_model=PaperFundingSettlementResponse,
)
def settle_paper_funding(
    request: PaperFundingSettlementRequest,
    user=Depends(current_user),
):
    try:
        return paper_oms_service.settle_funding(user.id, request)
    except PaperOmsError as exc:
        _raise_paper_oms_error(exc)


@app.get(
    "/api/v1/paper/margin/events",
    response_model=PaperMarginEventListResponse,
)
def list_paper_margin_events(
    limit: int = Query(default=100, ge=1, le=500),
    user=Depends(current_user),
):
    return paper_oms_service.list_margin_events(user.id, limit)


@app.post("/api/v1/paper/ticks", response_model=PaperOrderListResponse)
def process_paper_tick(
    request: PaperMarketTickRequest,
    user=Depends(current_user),
):
    try:
        return paper_oms_service.process_tick(user.id, request)
    except PaperOmsError as exc:
        _raise_paper_oms_error(exc)


@app.get(
    "/api/v1/paper/orders/{order_id}/reconcile",
    response_model=PaperReconciliationResponse,
)
def reconcile_paper_order(order_id: str, user=Depends(current_user)):
    try:
        return paper_oms_service.reconcile(user.id, order_id)
    except PaperOmsError as exc:
        _raise_paper_oms_error(exc)


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


@app.post("/api/v1/research/quant-validate", response_model=QuantValidationResponse)
def quant_validate(request: QuantValidationRequest, user=Depends(current_user)):
    """Run reproducible research diagnostics without authorizing live execution."""
    return quant_validation_service.validate(request)


@app.post("/api/v1/research/purged-split-plan", response_model=PurgedSplitPlanResponse)
def purged_split_plan(request: PurgedSplitPlanRequest, user=Depends(current_user)):
    """Build a deterministic purged walk-forward index plan."""
    return quant_validation_service.build_split_plan(request)


def _raise_historical_http_error(exc: HistoricalDataError):
    status = 400
    if exc.code == "historical_dataset_not_found":
        status = 404
    elif exc.code == "immutable_dataset_version_conflict":
        status = 409
    elif "unavailable" in exc.code or "provider_error" in exc.code:
        status = 502
    raise HTTPException(status_code=status, detail={"code": exc.code}) from exc


@app.post("/api/v1/research/historical/collect", response_model=HistoricalDataCollectResponse)
async def collect_historical_dataset(
    request: HistoricalDataCollectRequest,
    user=Depends(current_user),
):
    """Collect, validate, fingerprint and optionally persist finalized historical candles."""
    try:
        twelve_material = provider_secret_service.get_material(user.id, "twelvedata")
        return await historical_data_service.collect(
            request,
            user_id=user.id,
            runtime_twelvedata_key=(twelve_material.api_key if twelve_material else None),
        )
    except HistoricalDataError as exc:
        _raise_historical_http_error(exc)


@app.get("/api/v1/research/datasets", response_model=HistoricalDatasetListResponse)
def list_historical_datasets(
    limit: int = Query(default=100, ge=1, le=500),
    user=Depends(current_user),
):
    return historical_data_service.store.list(user_id=user.id, limit=limit)


@app.get(
    "/api/v1/research/datasets/{dataset_id}/{version}",
    response_model=HistoricalDatasetManifestResponse,
)
def get_historical_dataset_manifest(
    dataset_id: str,
    version: str,
    user=Depends(current_user),
):
    try:
        return historical_data_service.store.get_manifest(user.id, dataset_id, version)
    except HistoricalDataError as exc:
        _raise_historical_http_error(exc)


def _raise_stored_research_http_error(exc: StoredResearchError):
    status = 404 if exc.code == "historical_dataset_not_found" else 400
    raise HTTPException(status_code=status, detail={"code": exc.code}) from exc


@app.post(
    "/api/v1/research/stored-backtest",
    response_model=StoredBacktestResearchResponse,
)
def run_stored_backtest(
    request: StoredBacktestResearchRequest,
    user=Depends(current_user),
):
    try:
        return stored_research_service.run_fixed_backtest(user.id, request)
    except StoredResearchError as exc:
        _raise_stored_research_http_error(exc)


@app.post(
    "/api/v1/research/stored-walk-forward",
    response_model=StoredWalkForwardResearchResponse,
)
def run_stored_walk_forward(
    request: StoredWalkForwardResearchRequest,
    user=Depends(current_user),
):
    try:
        return stored_research_service.run_purged_walk_forward(user.id, request)
    except StoredResearchError as exc:
        _raise_stored_research_http_error(exc)


@app.post(
    "/api/v1/research/strategy-panel/validate",
    response_model=StrategyPanelValidationResponse,
)
def validate_strategy_panel(
    request: StrategyPanelValidationRequest,
    user=Depends(current_user),
):
    """Estimate CSCV probability of backtest overfitting for a strategy panel."""
    return strategy_panel_validation_service.validate(request)


@app.post(
    "/api/v1/research/automated-panel/final-holdout",
    response_model=AutomatedPanelResearchResponse,
)
def run_automated_panel_final_holdout(
    request: AutomatedPanelResearchRequest,
    user=Depends(current_user),
):
    """Lock a final holdout, build the panel on development data, and evaluate once."""
    try:
        return automated_panel_service.run(user.id, request)
    except AutomatedPanelError as exc:
        status = 409 if exc.code == "immutable_experiment_version_conflict" else 400
        if exc.code == "historical_dataset_not_found":
            status = 404
        raise HTTPException(status_code=status, detail={"code": exc.code}) from exc


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
        raise HTTPException(
            status_code=404, detail="Trade was not found or is not in a valid state"
        ) from exc


@app.delete("/api/v1/trades/{trade_id}", response_model=MessageResponse)
def delete_trade(trade_id: int, user=Depends(current_user)):
    try:
        storage.delete_trade(trade_id, user_id=user.id)
        return MessageResponse(message=f"Trade {trade_id} deleted")
    except ValueError as exc:
        raise HTTPException(
            status_code=404, detail="Trade was not found or is not in a valid state"
        ) from exc


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
