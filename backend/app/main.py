from __future__ import annotations

import os
import re
import time
import asyncio
import hmac
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Form, Header, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, File, UploadFile
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
    SignalShadowFeasibilityPanelResponse,
    SignalShadowForwardHoldoutPlanResponse,
    SignalShadowHoldoutConsumeRequest,
    SignalShadowHoldoutConsumptionResponse,
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
from app.services.strategy_grounded_helper import StrategyGroundedHelper
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
from app.services.microstructure_service import (
    MicrostructureService,
    build_ai_context_text,
    build_compact_context_text,
    detect_symbol_from_text,
    norm_timeframe,
)
from app.services import indicator_pack_v2
from app.services import strategy_pack_v2
from app.services.news_engine import mock_news
from app.services import advanced_indicators
from app.services import ict_engine
from app.services import rtm_engine
from app.services import smt_engine
from app.services import proximity_alert_service
from app.services import prime_backtest_service
from app.services import strategy_backtest_service
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
from app.services.provider_secret_service import (
    OPENAI_COMPATIBLE_BASE_URLS,
    ProviderSecretService,
    ProviderVaultError,
)
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
microstructure_service = MicrostructureService(ttl_seconds=45)
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


# Vault provider id -> (explain-layer provider name, preferred default model).
# All of these are OpenAI-compatible, so one provider class serves every one of
# them; base URLs come from provider_secret_service.OPENAI_COMPATIBLE_BASE_URLS
# so the probe, the explain layer and the chat/vision chains can never drift.
_USER_AI_PROVIDERS = (
    ("groq", "groq", "openai/gpt-oss-120b"),
    ("openrouter", "openrouter", "openai/gpt-4o-mini"),
    ("cerebras", "cerebras", "llama3.1-8b"),
    ("openai", "openai_compatible", "gpt-4.1-mini"),
)


def _runtime_ai_provider_for_user(user_id: int, requested: str = "auto"):
    """Build the user's own (BYOK) explainer provider — never a system key.

    "auto" walks the user's saved providers in latency order and returns the
    first enabled one; an explicit id pins that provider only.
    """
    candidates = _USER_AI_PROVIDERS
    if requested and requested != "auto":
        wanted = "openai" if requested == "openai_compatible" else requested
        candidates = tuple(c for c in _USER_AI_PROVIDERS if c[0] == wanted)
        if not candidates:
            return None
    for vault_id, provider_name, default_model in candidates:
        try:
            material = provider_secret_service.get_material(user_id, vault_id)
        except Exception:
            material = None
        if material and material.api_key:
            return OpenAICompatibleProvider(
                base_url=OPENAI_COMPATIBLE_BASE_URLS[vault_id],
                api_key=material.api_key,
                model=material.model or default_model,
                provider_name=provider_name,
            )
    return None


_BYOK_CHAT_MODELS = {
    "cerebras": "llama3.1-8b",
    "groq": "openai/gpt-oss-120b",
    "openrouter": "openai/gpt-4o-mini",
    "openai": "gpt-4.1-mini",
}
# Vision needs a multimodal model; Cerebras has none, so it is excluded there.
_BYOK_VISION_MODELS = {
    "groq": "qwen/qwen3.6-27b",
    "openrouter": "openai/gpt-4o-mini",
    "openai": "gpt-4o-mini",
}


def _byok_candidates(user, kind: str = "chat") -> list[dict]:
    """OpenAI-compatible candidates from the user's own saved keys (BYOK).

    User keys always come before system keys: the user pays for them, and it
    keeps system quota for anonymous sessions. Identical ordering in chat,
    vision and deep-analysis so the three can never disagree.
    """
    models = _BYOK_VISION_MODELS if kind == "vision" else _BYOK_CHAT_MODELS
    out: list[dict] = []
    if not user:
        return out
    for vault_id, default_model in models.items():
        try:
            material = provider_secret_service.get_material(user.id, vault_id)
        except Exception:
            material = None
        if not (material and material.api_key):
            continue
        out.append({
            "provider": f"{vault_id.title()} (User BYOK)",
            "base_url": OPENAI_COMPATIBLE_BASE_URLS[vault_id],
            "api_key": material.api_key.strip(),
            "model": (material.model or default_model).strip(),
            # "is_groq" means "OpenAI-compatible with live model discovery"
            "is_groq": vault_id in ("groq", "openrouter", "cerebras"),
        })
    return out


def _openai_compat_headers(api_key: str, base_url: str) -> dict:
    """Headers for an OpenAI-compatible request.

    OpenRouter routes via HTTP-Referer / X-Title; harmless on other providers.
    """
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if "openrouter" in str(base_url or "").lower():
        headers["HTTP-Referer"] = "https://github.com/aminomidiao68-max/apex-ai-trading-assistant"
        headers["X-Title"] = "APEX AI Trading Assistant"
    return headers


def _system_ai_candidates(kind: str = "chat") -> list[dict]:
    """System (env) candidates: Groq → OpenRouter → Cerebras → OpenAI.

    Cerebras is last among the configured keys: its free tier became a
    card-gated $5 trial (2026-07-21), so key holders without billing get 402s.
    Keeping it registered costs nothing and revives it automatically once
    billing exists.
    """
    models = _BYOK_VISION_MODELS if kind == "vision" else _BYOK_CHAT_MODELS
    out: list[dict] = []
    env_map = {
        "groq": ("AI_GROQ_API_KEY", "AI_GROQ_BASE_URL", "AI_GROQ_MODEL"),
        "openrouter": ("AI_OPENROUTER_API_KEY", "AI_OPENROUTER_BASE_URL", "AI_OPENROUTER_MODEL"),
        "cerebras": ("AI_CEREBRAS_API_KEY", "AI_CEREBRAS_BASE_URL", "AI_CEREBRAS_MODEL"),
    }
    for vault_id, (key_env, base_env, model_env) in env_map.items():
        if vault_id not in models:
            continue
        key = os.getenv(key_env, "").strip()
        if not key:
            continue
        out.append({
            "provider": f"{vault_id.title()} (System)",
            "base_url": os.getenv(base_env, OPENAI_COMPATIBLE_BASE_URLS[vault_id]),
            "api_key": key,
            "model": os.getenv(model_env, models[vault_id]),
            "is_groq": True,
        })
    sys_openai_key = (settings.ai_openai_api_key or "").strip()
    if sys_openai_key and "openai" in models:
        sys_base = settings.ai_openai_base_url or OPENAI_COMPATIBLE_BASE_URLS["openai"]
        out.append({
            "provider": "OpenAI (System)",
            "base_url": sys_base,
            "api_key": sys_openai_key,
            "model": models["openai"],
            "is_groq": "groq" in sys_base.lower(),
        })
    return out


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


def _strip_reasoning_blocks(text: str | None) -> str:
    """Remove <think>...</think> reasoning chains leaked by thinking models."""
    if not text:
        return ""
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<\|?channel\|?>\s*analysis\s*<\|message\|>", "", cleaned, flags=re.IGNORECASE)
    unterminated = re.search(r"<think>", cleaned, flags=re.IGNORECASE)
    if unterminated:
        cleaned = cleaned[:unterminated.start()]
    return cleaned.strip()


def _ai_payload_extra(model: str) -> dict:
    """Groq reasoning models (qwen/gpt-oss) must not leak their thinking."""
    lowered = (model or "").lower()
    if "qwen" in lowered or "gpt-oss" in lowered:
        return {"reasoning_format": "hidden"}
    return {}


_GPT_OSS_MIN_COMPLETION_TOKENS = 2500


def _adapt_payload_for_model(payload: dict, model: str, is_groq: bool) -> dict:
    """Groq's gpt-oss endpoints reject any temperature other than the default
    and require max_completion_tokens instead of max_tokens (HTTP 400 otherwise).
    Their reasoning tokens also count against that budget, so a small limit
    yields an empty answer — floor it and ask for the lowest reasoning effort."""
    if is_groq and "gpt-oss" in (model or "").lower():
        payload = {k: v for k, v in payload.items() if k != "temperature"}
        budget = payload.pop("max_tokens", None)
        if budget is not None:
            payload["max_completion_tokens"] = max(int(budget), _GPT_OSS_MIN_COMPLETION_TOKENS)
        payload["reasoning_effort"] = "low"
    return payload


# Groq rotates/deprecates models frequently; pick from the LIVE model list
# instead of hardcoding IDs so deprecations never break the service.
_GROQ_VISION_PREFERENCE = ("qwen3.8", "qwen3.6", "vision", "scout", "maverick")
_GROQ_CHAT_PREFERENCE = ("gpt-oss-120b", "gpt-oss-20b", "qwen3.8", "qwen3.6", "70b", "8b")
_GROQ_VISION_FALLBACK = ["qwen/qwen3.8-27b", "qwen/qwen3.6-27b"]
_GROQ_CHAT_FALLBACK = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.6-27b",
    "llama-3.1-8b-instant",
]
_GROQ_MODELS_CACHE: dict[str, tuple[float, list[str]]] = {}


async def _groq_available_models(api_key: str, base_url: str) -> list[str]:
    cache_key = f"{base_url}|{api_key[:12]}"
    now = time.monotonic()
    cached = _GROQ_MODELS_CACHE.get(cache_key)
    if cached and now - cached[0] < 600:
        return cached[1]
    try:
        async with httpx.AsyncClient(timeout=8.0, headers={"Authorization": f"Bearer {api_key}"}) as client:
            response = await client.get(f"{base_url}/models")
            response.raise_for_status()
            ids = [m.get("id") for m in response.json().get("data", []) if m.get("id")]
        _GROQ_MODELS_CACHE[cache_key] = (now, ids)
        return ids
    except Exception:
        return []


# Per-base model preferences. OpenRouter and Cerebras have their own catalogues,
# so a Groq-shaped preference list would silently pick wrong (or no) models there.
_OPENROUTER_CHAT_PREFERENCE = (
    "gpt-4o-mini", "gpt-4.1-mini", "llama-3.3-70b", "claude-3.5-haiku", "deepseek-chat",
)
_OPENROUTER_VISION_PREFERENCE = ("gpt-4o-mini", "gpt-4.1-mini", "llama-3.2-11b-vision", "qwen-vl")
_CEREBRAS_CHAT_PREFERENCE = ("llama3.1-8b", "gpt-oss-120b", "qwen-3-32b", "llama-3.3-70b")


def _preference_for(cand: dict, kind: str) -> tuple:
    base = str(cand.get("base_url") or "").lower()
    if "openrouter" in base:
        return _OPENROUTER_VISION_PREFERENCE if kind == "vision" else _OPENROUTER_CHAT_PREFERENCE
    if "cerebras" in base:
        # Cerebras has no multimodal model; if a vision request ever lands here the
        # caller fails over to the next candidate rather than sending a bad model id.
        return _CEREBRAS_CHAT_PREFERENCE
    return _GROQ_VISION_PREFERENCE if kind == "vision" else _GROQ_CHAT_PREFERENCE


def _fallback_for(cand: dict, kind: str) -> list[str]:
    base = str(cand.get("base_url") or "").lower()
    if "openrouter" in base:
        return ["openai/gpt-4o-mini", "anthropic/claude-3.5-haiku", "meta-llama/llama-3.3-70b-instruct"]
    if "cerebras" in base:
        return ["llama3.1-8b", "gpt-oss-120b"]
    return list(_GROQ_VISION_FALLBACK if kind == "vision" else _GROQ_CHAT_FALLBACK)


def _groq_kind_compatible(model_lower: str, kind: str) -> bool:
    if kind != "vision":
        return True
    return any(tag in model_lower for tag in
               ("qwen3", "vision", "scout", "maverick", "gpt-4o", "gpt-4.1", "vl"))


async def _model_options_for(cand: dict, kind: str) -> list[str]:
    configured = (cand.get("model") or "").strip()
    if not cand.get("is_groq"):
        return [configured or "gpt-4o-mini"]
    options: list[str] = [configured] if configured else []
    live = await _groq_available_models(cand["api_key"], cand["base_url"])
    lowered_live = {m.lower(): m for m in live}
    for pref in _preference_for(cand, kind):
        for model_lower, model_id in lowered_live.items():
            if pref in model_lower and model_id not in options and _groq_kind_compatible(model_lower, kind):
                options.append(model_id)
        if len(options) >= 3:
            break
    if not live:
        # Discovery failed (network/invalid key): configured default first, then
        # known-good fallbacks so one dead model never kills the request.
        for fb in _fallback_for(cand, kind):
            if fb not in options:
                options.append(fb)
            if len(options) >= 3:
                break
    return options[:3]


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


async def get_micro_summary(
    symbol: str,
    market: str,
    timeframe: str | None,
    timeout_s: float = 6.0,
    compact: bool = True,
) -> dict | None:
    """Best-effort real microstructure snapshot (L2/footprint/VP/flow); None on failure."""
    try:
        return await asyncio.wait_for(
            microstructure_service.get_microstructure(
                symbol, market, timeframe or "15m", compact=compact
            ),
            timeout=timeout_s,
        )
    except Exception:
        return None


def _oscillator_snapshot(items: list[dict]) -> dict:
    """Deterministic indicator snapshot (RSI / EMA stack / ATR / momentum / BB width)."""
    try:
        from app.services.indicators import atr as _atr, ema as _ema, momentum_histogram as _mom, rsi as _rsi
        closes = [float(c["c"]) for c in items if c.get("c")]
        highs = [float(c["h"]) for c in items if c.get("h")]
        lows = [float(c["l"]) for c in items if c.get("l")]
        if len(closes) < 30:
            return {}
        rsi_v = round(_rsi(closes), 1)
        ema20 = _ema(closes, 20)
        ema50 = _ema(closes, 50) if len(closes) >= 50 else None
        ema200 = _ema(closes, 200) if len(closes) >= 200 else None
        atr_v = _atr(highs, lows, closes)
        mom = round(_mom(closes), 4)
        price = closes[-1]
        stack = "bullish" if price > ema20 and (ema50 is None or ema20 >= ema50) else "bearish" if price < ema20 and (ema50 is None or ema20 <= ema50) else "mixed"
        # Bollinger bandwidth proxy (20, 2)
        window = closes[-20:]
        mean = sum(window) / len(window)
        var = sum((x - mean) ** 2 for x in window) / len(window)
        sd = var ** 0.5
        bb_width_pct = round((4 * sd) / mean * 100, 2) if mean else None
        return {
            "rsi14": rsi_v,
            "price": price,
            "ema20": round(ema20, 6),
            "ema50": round(ema50, 6) if ema50 else None,
            "ema200": round(ema200, 6) if ema200 else None,
            "ema_stack": stack,
            "atr14": round(atr_v, 6),
            "momentum_histogram": mom,
            "bb_width_pct": bb_width_pct,
            "rsi_zone": "overbought" if rsi_v >= 70 else "oversold" if rsi_v <= 30 else "neutral",
        }
    except Exception:
        return {}


def _buyer_seller_force(report: dict, micro: dict | None) -> dict:
    """Deterministic buyers-vs-sellers gauge (0-100) from REAL tape/book only."""
    buyers = 50.0
    flow = (micro or {}).get("flow") or {}
    filters = (micro or {}).get("filters") or {}
    fp = (micro or {}).get("footprint") or {}
    l2 = (micro or {}).get("l2") or {}
    delta = float(flow.get("delta") or 0.0)
    buyers += max(-1.0, min(1.0, delta)) * 25
    imb = float((l2.get("imbalance_top25") if isinstance(l2.get("imbalance_top25"), (int, float)) else 0.0) or 0.0)
    buyers += max(-1.0, min(1.0, imb)) * 15
    stacked_buy = int(fp.get("stacked_buy") or 0)
    stacked_sell = int(fp.get("stacked_sell") or 0)
    buyers += min(6, (stacked_buy - stacked_sell) * 2)
    divergence = flow.get("cvd_divergence")
    if divergence == "bullish":
        buyers += 4
    elif divergence == "bearish":
        buyers -= 4
    if flow.get("absorption"):
        buyers = 50 + (buyers - 50) * 0.85
    bias = str(filters.get("net_bias") or "neutral")
    if bias == "bullish":
        buyers += 3
    elif bias == "bearish":
        buyers -= 3
    buyers = max(5.0, min(95.0, buyers))
    label = "buyers_dominant" if buyers >= 58 else "sellers_dominant" if buyers <= 42 else "balanced"
    return {
        "buyers_pct": round(buyers, 1),
        "sellers_pct": round(100.0 - buyers, 1),
        "label": label,
        "basis": "real_delta_depth_stacked_cvd",
    }


def _numbered_liquidity(report: dict) -> list[dict]:
    pools = []
    for item in (report.get("inducements") or [])[:8]:
        price = item.get("price")
        try:
            price = float(price)
        except (TypeError, ValueError):
            continue
        if price <= 0:
            continue
        pools.append({
            "kind": str(item.get("kind") or "liq"),
            "price": price,
            "side": str(item.get("dir") or item.get("side") or ""),
        })
    return pools


def _gap_list(report: dict) -> list[dict]:
    gaps = []
    for zone in (report.get("fvg") or [])[:8]:
        try:
            top = float(zone.get("top"))
            bottom = float(zone.get("bottom"))
        except (TypeError, ValueError):
            continue
        if top <= 0 or bottom <= 0:
            continue
        gaps.append({
            "top": top,
            "bottom": bottom,
            "side": str(zone.get("side") or zone.get("kind") or ""),
            "fresh": bool(zone.get("fresh", False)),
        })
    return gaps


def _top_order_blocks(report: dict) -> list[dict]:
    obs = []
    for zone in (report.get("order_blocks") or [])[:4]:
        try:
            top = float(zone.get("top"))
            bottom = float(zone.get("bottom"))
        except (TypeError, ValueError):
            continue
        if top <= 0 or bottom <= 0:
            continue
        obs.append({
            "top": top,
            "bottom": bottom,
            "side": str(zone.get("side") or zone.get("kind") or ""),
            "quality": int(zone.get("quality") or 0),
        })
    return obs


def build_market_dossier(report: dict, micro: dict | None, items: list[dict]) -> str:
    """Dense Persian dossier of ALL real, deterministic market facts for AI prompts."""
    osc = _oscillator_snapshot(items)
    force = report.get("force") or _buyer_seller_force(report, micro)
    liq = _numbered_liquidity(report)
    gaps = _gap_list(report)
    obs = _top_order_blocks(report)
    events = (report.get("events") or [])[-4:]
    if micro and micro.get("is_real"):
        # compact payloads carry "flow"/"vp"/"l2" keys; full payloads carry "order_flow"/...
        is_compact = "order_flow" not in micro and "flow" in micro
        micro_line = build_compact_context_text(micro) if is_compact else build_ai_context_text(micro)
    else:
        micro_line = "⚠️ داده خردساختار واقعی (L2/فوت‌پرینت) در دسترس نیست؛ نباید عددی از خودت بسازی."

    def fmt(v) -> str:
        return f"{v:g}" if isinstance(v, (int, float)) else str(v)

    lines: list[str] = ["📁 پرونده کامل بازار (فقط اعداد واقعی سیستم؛ ساخت عدد ممنوع):"]

    lines.append("1) ساختار: bias=" + fmt(report.get("bias")) +
                 " | HTF=" + fmt((report.get("htf") or {}).get("bias")) +
                 " | premium_zone=" + fmt(report.get("premium_zone")) +
                 " | price=" + fmt(report.get("price")))
    if events:
        ev_txt = "؛ ".join(f"{e.get('kind')}@{fmt(e.get('price'))}" for e in events if e.get("price"))
        if ev_txt:
            lines.append("2) رویدادهای ساختاری: " + ev_txt)
    if liq:
        lines.append("3) نقدینگی‌های شماره‌دار: " + "؛ ".join(
            f"{i+1}) {item['kind']} در قیمت {item['price']:g}" for i, item in enumerate(liq)
        ))
    if gaps:
        lines.append("4) گپ‌ها/نواحی ناهم‌قیمت (FVG): " + "؛ ".join(
            f"{i+1}) {g['side']} از {g['bottom']:g} تا {g['top']:g}" + (" (تازه)" if g["fresh"] else "")
            for i, g in enumerate(gaps)
        ))
    if obs:
        lines.append("5) بلوک‌های سفارش (OB): " + "؛ ".join(
            f"{o['side']} از {o['bottom']:g} تا {o['top']:g} (کیفیت {o['quality']})" for o in obs
        ))
    if not osc:
        lines.append("6) اندیکاتورها: داده کافی نیست")
    if osc:
        lines.append(
            "6) اندیکاتورها: RSI14=" + fmt(osc.get("rsi14")) + " (" + fmt(osc.get("rsi_zone")) + ")"
            + " | EMA stack=" + fmt(osc.get("ema_stack"))
            + " | EMA20=" + fmt(osc.get("ema20"))
            + " | EMA50=" + fmt(osc.get("ema50"))
            + " | EMA200=" + fmt(osc.get("ema200"))
            + " | ATR14=" + fmt(osc.get("atr14"))
            + " | MACD-hist=" + fmt(osc.get("momentum_histogram"))
            + " | BB-width%=" + fmt(osc.get("bb_width_pct"))
        )
    lines.append("7) نیروی واقعی خریدار/فروشنده: خریدار=" + fmt(force.get("buyers_pct")) + "%"
                 + " | فروشنده=" + fmt(force.get("sellers_pct")) + "% (" + fmt(force.get("label")) + ")")
    ict = report.get("ict")
    if ict:
        sweeps_txt = "؛ ".join(f"{e['kind']}@{e['price']:g}" for e in (ict.get("events") or []) if e.get("kind") not in ("displacement", "BOS", "CHoCH"))
        disp = ict.get("displacement") or {}
        pd_info = ict.get("premium_discount") or {}
        eq = ict.get("equal_highs_lows") or {}
        fvg_states = ict.get("fvg_states") or []
        sb = ict.get("silver_bullet") or {}
        ms = ict.get("market_structure") or {}
        ote = ict.get("ote") or {}
        kz = ict.get("killzone") or {}
        inv = ict.get("inversion_fvg") or []
        brk = ict.get("breakers") or []
        struct_txt = ""
        if ms.get("state"):
            ev_txt2 = "؛ ".join(f"{e.get('kind')} {e.get('dir')}@{e.get('price'):g}" for e in (ms.get("events") or [])[-3:] if e.get("price"))
            struct_txt = f"ساختار={ms.get('state')} ({ms.get('pattern')})" + (f" | رویدادها: {ev_txt2}" if ev_txt2 else "") + " | "
        ote_txt = ""
        if ote.get("available"):
            ote_txt = (f"OTE({ote.get('direction')}): ناحیه {ote.get('ote_bottom'):g}–{ote.get('ote_top'):g}"
                       + (" ← قیمت داخل ناحیه OTE است" if ote.get("price_in_zone") else "") + " | ")
        kz_txt = ""
        kz_active = kz.get("active") or {}
        if kz_active:
            kz_txt = f"کیلزون فعال={kz_active.get('name')} ({kz_active.get('minutes_left')} دقیقه مانده، کیفیت {kz.get('quality')}) | "
        elif kz:
            kz_txt = f"کیلزون فعال نیست (کیفیت {kz.get('quality')}) | "
        brk_txt = ""
        if brk:
            brk_txt = "بریکرها: " + "؛ ".join(f"{b.get('kind')} {b.get('bottom'):g}–{b.get('top'):g}" for b in brk[-2:]) + " | "
        inv_txt = ""
        if inv:
            inv_txt = "FVG وارونه: " + "؛ ".join(f"{g.get('original_side')} پر شده → نقش {g.get('inverted_role')} ({g.get('bottom'):g}–{g.get('top'):g})" for g in inv[:2]) + " | "
        ict_line = (
            "11) ICT پیشرفته (لایو): "
            + struct_txt
            + (f"سوییپ‌ها: {sweeps_txt} | " if sweeps_txt else "")
            + f"Displacement={disp.get('direction')} (قدرت {disp.get('strength')}%) | "
            + f"موقعیت در رنج={pd_info.get('position_pct')}% ({pd_info.get('zone')}) | "
            + ote_txt
            + kz_txt
            + f"EQH={len(eq.get('eqh') or [])} EQL={len(eq.get('eql') or [])} | "
            + f"SilverBullet={'فعال' if sb.get('active') else 'غیرفعال'} | "
            + brk_txt
            + inv_txt
            + f"وضعیت FVG: " + ("؛ ".join(f"{g['side']} {g['state']} {g['filled_pct']}% CE={g['ce']}" for g in fvg_states) or "بدون گپ باز")
        )
        lines.append(ict_line)
    else:
        lines.append("11) ICT پیشرفته: داده کافی نیست")
    ind = report.get("indicator_confluence")
    if ind and ind.get("available"):
        values = ind.get("values") or {}
        lines.append(
            "12) هم‌گرایی کل اندیکاتورها/اوسیلاتورها: امتیاز=" + fmt(ind.get("score"))
            + " (" + fmt(ind.get("stance")) + ")"
            + " | صعودی=" + fmt(ind.get("bull_count")) + " نزولی=" + fmt(ind.get("bear_count")) + " خنثی=" + fmt(ind.get("neutral_count"))
            + " | RSI=" + fmt(values.get("rsi14"))
            + " | StochK/D=" + fmt(values.get("stoch_k")) + "/" + fmt(values.get("stoch_d"))
            + " | StochRSI=" + fmt(values.get("stoch_rsi_k"))
            + " | CCI=" + fmt(values.get("cci20"))
            + " | Williams%R=" + fmt(values.get("williams_r"))
            + " | MFI=" + fmt(values.get("mfi14"))
            + " | OBV-slope=" + fmt((values.get("obv") or {}).get("slope"))
            + " | ADX=" + fmt((values.get("adx") or {}).get("adx"))
            + " | +DI=" + fmt((values.get("adx") or {}).get("plus_di"))
            + " | -DI=" + fmt((values.get("adx") or {}).get("minus_di"))
            + " | VWAP-dist%=" + fmt((values.get("vwap") or {}).get("distance_pct"))
            + " | SuperTrend=" + fmt((values.get("supertrend") or {}).get("direction"))
            + " | Ichimoku=" + fmt((values.get("ichimoku") or {}).get("position"))
            + " | %B=" + fmt((values.get("bollinger") or {}).get("percent_b"))
        )
    else:
        lines.append("12) هم‌گرایی اندیکاتورها: داده کافی نیست")
    smt = report.get("smt")
    if smt and smt.get("available"):
        divs = smt.get("divergences") or []
        div_txt = "؛ ".join(
            f"{d.get('kind')} — قوی: {d.get('strong')}، ضعیف: {d.get('weak')}"
            for d in divs[-2:]
        ) or "بدون واگرایی اخیر"
        lines.append(
            "13) واگرایی SMT (لایو، قطعی): جفت=" + fmt(smt.get("primary")) + "/" + fmt(smt.get("correlated"))
            + " | همبستگی=" + fmt(smt.get("correlation"))
            + (" (قابل اتکا)" if smt.get("correlation_reliable") else " (زیر آستانه اتکا)")
            + " | امتیاز SMT=" + fmt(smt.get("score"))
            + " | " + div_txt
        )
    else:
        lines.append("13) واگرایی SMT: داده جفت همبسته در دسترس نیست")
    ind2 = report.get("indicators_v2") or {}
    ind2_sum = ind2.get("summary") or {}
    if ind2_sum.get("available"):
        pack = ind2.get("pack") or {}
        lines.append("14) پک اندیکاتورهای پیشرفته v2: " + indicator_pack_v2.build_context_text(pack, ind2_sum).replace("\n", " | "))
    else:
        lines.append("14) پک اندیکاتورهای پیشرفته v2: داده کافی نیست")
    strat2 = report.get("strategies_v2") or {}
    if strat2.get("available"):
        lines.append("15) پک استراتژی‌های کلاسیک v2:\n" + strategy_pack_v2.build_context_text(strat2))
    else:
        lines.append("15) پک استراتژی‌های کلاسیک v2: داده کافی نیست")
    lines.append("8) خردساختار زنده: " + micro_line.replace("\n", " | "))
    lines.append("9) حکم قطعی سیستم: action_label=" + fmt(report.get("action_label"))
                 + " | grade=" + fmt(report.get("grade"))
                 + " | direction=" + fmt(report.get("direction"))
                 + " | confluence=" + fmt(report.get("confluence"))
                 + " | probability=" + fmt(report.get("probability"))
                 + " | RR=" + fmt(report.get("rr")))
    levels = report.get("levels") or {}
    if report.get("action_label") not in (None, "NO_TRADE", "WAIT", "WATCH") and levels.get("entry"):
        lines.append("10) سطوح قطعی سیستم: Entry=" + fmt(levels.get("entry"))
                     + " | SafeSL=" + fmt(levels.get("sl"))
                     + " | TP1=" + fmt(report.get("tp1"))
                     + " | TP2=" + fmt(report.get("tp2"))
                     + " | TP3=" + fmt(report.get("tp3")))
    else:
        lines.append("10) سطوح ورود: سیستم اجازه ورود نداده (NO_TRADE/WAIT)؛ نباید برنامه ورود جعل شود.")
    return "\n".join(lines)


def _micro_confluence_points(micro: dict | None, direction: str) -> int:
    """Deterministic additive confluence (0..15) from REAL microstructure.

    Read-only: it never mutates the strict engine's gates or verdicts; it only
    quantifies how aligned the live tape/book is with the setup direction.
    """
    if not micro or not micro.get("is_real"):
        return 0
    filters = micro.get("filters") or {}
    bias = str(filters.get("net_bias") or "neutral")
    score = float(filters.get("score") or 0.0)
    flow = micro.get("flow") or {}
    fp = micro.get("footprint") or {}
    points = 0
    if direction == "long":
        if bias == "bullish":
            points += 6
        elif bias == "bearish":
            points -= 5
        if int(fp.get("stacked_buy") or 0) >= 3:
            points += 3
        if flow.get("cvd_divergence") == "bearish":
            points -= 2
        elif flow.get("cvd_divergence") == "bullish":
            points += 1
        if score > 0:
            points += int(min(3, round(abs(score) * 3)))
    elif direction == "short":
        if bias == "bearish":
            points += 6
        elif bias == "bullish":
            points -= 5
        if int(fp.get("stacked_sell") or 0) >= 3:
            points += 3
        if flow.get("cvd_divergence") == "bullish":
            points -= 2
        elif flow.get("cvd_divergence") == "bearish":
            points += 1
        if score < 0:
            points += int(min(3, round(abs(score) * 3)))
    if micro.get("full_coverage") is False:
        points = min(points, 10)
    return max(0, min(15, points))


def _micro_level_lines(micro: dict | None) -> list[dict]:
    """Real micro levels (POC/VAH/VAL/walls) as chart line descriptors."""
    if not micro or not micro.get("is_real"):
        return []
    vp = micro.get("vp") or {}
    l2 = micro.get("l2") or {}
    levels: list[dict] = []
    for kind, value, label in (
        ("POC", vp.get("poc"), "POC"),
        ("VAH", vp.get("vah"), "VAH"),
        ("VAL", vp.get("val"), "VAL"),
        ("BIDWALL", (l2.get("bid_wall") or {}).get("price"), "Bid Wall"),
        ("ASKWALL", (l2.get("ask_wall") or {}).get("price"), "Ask Wall"),
    ):
        try:
            price = float(value) if value is not None else 0.0
        except (TypeError, ValueError):
            price = 0.0
        if price > 0:
            levels.append({"kind": kind, "price": price, "label": label})
    return levels


_SMT_PAIRS = {
    "BTCUSDT": ("ETHUSDT", "crypto"),
    "ETHUSDT": ("BTCUSDT", "crypto"),
    "SOLUSDT": ("ETHUSDT", "crypto"),
    "XAUUSD": ("XAGUSD", "forex"),
    "EURUSD": ("GBPUSD", "forex"),
    "GBPUSD": ("EURUSD", "forex"),
    "AUDUSD": ("NZDUSD", "forex"),
}


async def _smt_for_symbol(symbol: str, market: str, timeframe: str | None, items: list[dict]) -> dict | None:
    """Deterministic SMT divergence vs the canonical correlated leg (real candles only)."""
    pair = _SMT_PAIRS.get(str(symbol).upper())
    if not pair or not items or not timeframe:
        return None
    corr_symbol, corr_market = pair
    raw = await fetch_live_candles(corr_symbol, corr_market, _canonical_timeframe(timeframe))
    corr_items = _norm_candles(raw)[-len(items):]
    return smt_engine.detect_smt(items, corr_items, str(symbol).upper(), corr_symbol)


async def enrich_orderflow(
    report: dict,
    symbol: str,
    market: str,
    items: list[dict],
    timeframe: str | None = None,
    with_smt: bool = True,
) -> dict:
    snapshot = await orderflow_service.get_snapshot(symbol, market, items)
    candle_proxy = dict(report.get("orderflow") or {})
    merged = {"candle_proxy": candle_proxy, **snapshot}
    micro = await get_micro_summary(symbol, market, timeframe, compact=True)
    if micro is not None:
        merged["micro"] = micro
        report["microstructure"] = micro
        report["micro_levels"] = _micro_level_lines(micro)
    try:
        report["ict"] = ict_engine.summarize(items, report)
    except Exception:
        report["ict"] = None
    if with_smt:
        try:
            report["smt"] = await _smt_for_symbol(symbol, market, timeframe, items)
        except Exception:
            report["smt"] = None
    try:
        report["indicator_confluence"] = advanced_indicators.confluence_snapshot(items)
    except Exception:
        report["indicator_confluence"] = None
    # v3.12: professional indicator pack v2 + classic strategy pack v2 (deterministic)
    try:
        _pack = indicator_pack_v2.compute_all(items)
        report["indicators_v2"] = {"pack": _pack, "summary": indicator_pack_v2.summarize(_pack)}
    except Exception:
        report["indicators_v2"] = None
    try:
        report["strategies_v2"] = strategy_pack_v2.scan_all(items, timeframe or "15m")
    except Exception:
        report["strategies_v2"] = None
    # v3.19: RTM (Quasimodo / FTR / flag-MPL / compression) + supply-demand zones
    # + liquidity map with draw-on-liquidity. Deterministic, real candles only;
    # advisory evidence for the AI layer and chart overlay — never a hard gate.
    try:
        rtm = rtm_engine.summarize(items, report)
        report["rtm"] = rtm
        overlay = dict(report.get("overlay") or {})
        extra = rtm_engine.overlay_items(rtm)
        overlay["lines"] = list(overlay.get("lines") or []) + extra["lines"]
        overlay["zones"] = list(overlay.get("zones") or []) + extra["zones"]
        overlay["labels"] = list(overlay.get("labels") or []) + extra["labels"]
        report["overlay"] = overlay
    except Exception:
        report["rtm"] = None
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
    # Serve traffic as long as the active backend is connected and migrated.
    # A production SQLite fallback is reported as "degraded" instead of failing
    # the Render health check (which would keep the whole service down).
    ready_now = bool(database["connected"] and database["migration_current"])
    degraded = bool(
        settings.app_env.lower() == "production"
        and database["backend"] != "postgresql"
    )
    return JSONResponse(
        status_code=200 if ready_now else 503,
        content={
            "status": "ready" if ready_now else "not_ready",
            "degraded": degraded,
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
        flow = await enrich_orderflow(report, symbol, market_eff, items, timeframe=_canonical_timeframe(interval))
        report = apply_strict_decision(
            report,
            items,
            market=market_eff,
            timeframe=_canonical_timeframe(interval),
            orderflow_source=str(flow.get("source") or "unknown"),
            orderflow_confidence=float(flow.get("confidence") or 0),
            orderflow_snapshot=flow,
        )
        report["force"] = _buyer_seller_force(report, report.get("microstructure"))
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
        flow = await enrich_orderflow(report, symbol, market_eff, items_by_tf[tf], timeframe=tf, with_smt=False)
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


@app.post("/api/v1/analysis/vision")
async def analyze_chart_vision(
    file: UploadFile = File(...),
    symbol: str = Form(default=""),
    timeframe: str = Form(default="15m"),
    user=Depends(optional_current_user),
):
    import base64
    import httpx
    import logging
    logger = logging.getLogger("apex.api.vision")

    if not settings.ai_external_enabled and not _byok_candidates(user, "vision"):
        return {
            "success": True,
            "analysis": "⚠️ هوش مصنوعی سیستمی غیرفعال است و کلید شخصی (BYOK) هم ذخیره نشده. "
                        "برای تحلیل تصویر، کلید Cerebras/Groq/OpenRouter/OpenAI خود را در تنظیمات ذخیره کنید."
        }

    content = await file.read()
    base64_image = base64.b64encode(content).decode("utf-8")

    # Vision: user BYOK first (multimodal only — Cerebras has no vision model),
    # then system keys. Groq/OpenRouter/OpenAI are all OpenAI-compatible.
    candidates = _byok_candidates(user, "vision") + _system_ai_candidates("vision")

    if not candidates:
        return {
            "success": True,
            "analysis": "⚠️ هیچ کلید AI تنظیم نشده است. در تنظیمات، یکی از کلیدهای Cerebras، Groq، OpenRouter یا OpenAI را ذخیره کنید."
        }

    errors = []
    # Execute with fallback logic
    for cand in candidates:
        api_key = cand["api_key"]
        if api_key.startswith("b'") and api_key.endswith("'"):
            api_key = api_key[2:-1]
        elif api_key.startswith('b"') and api_key.endswith('"'):
            api_key = api_key[2:-1]
        api_key = api_key.strip("'\"")

        headers = _openai_compat_headers(api_key, cand.get("base_url", ""))

        # Self-adaptive model selection (live Groq list, deprecation-proof)
        model_options = await _model_options_for(cand, kind="vision")

        prompt_text = (
            "به عنوان یک مدیر ریسک سخت‌گیر و تحلیل‌گر ارشد نهادی (SMC/ICT/کوانت)، این چارت را با بالاترین دقت و سخت‌گیری تحلیل کن. "
            "پاسخ باید مهندسی، بدون توهم و کاملاً ساختاریافته به فارسی باشد و دقیقاً این بخش‌ها را داشته باشد:\n\n"
            "⚠️ قوانین صریح خروجی: کل پاسخ فقط و فقط فارسی باشد. هیچ بخش انگلیسی، هیچ تگ <think>، هیچ زنجیره فکر منتشر نکن. "
            "هر عددی که در «پرونده کامل بازار» داده شده معتبر است؛ مطلقاً عددی از خودت نساز و اگر عددی نداری صریح بگو «داده کافی نیست».\n\n"
            "ساختار اجباری پاسخ:\n"
            "🏆 حکم نهایی مسیر بازار: صعودی / نزولی / رنج + درصد اطمینان (بر اساس نیروی خریدار/فروشنده و هم‌راستایی ساختار و حکم سیستم)\n"
            "⚖️ ترازوی قدرت: زور خریدار X٪ مقابل فروشنده Y٪ (با ذکر دلیل از دلتا/عمق/فوت‌پرینت)\n"
            "💧 نقدینگی‌ها: دقیقاً همان نقدینگی‌های شماره‌دار پرونده را با قیمت اعلام کن و بگو قیمت به کدام‌ها نزدیک است و چه ریسکی می‌سازند\n"
            "🩹 گپ‌ها (FVG): محدوده عددی هر گپ، تازه یا پرشده، و نقش آن (مگنت/حمایت/مقاومت)\n"
            "🧱 سفارشات: دیوارهای L2 و بلوک‌های سفارش با قیمت + تفسیر جذب/شکست\n"
            "🕯️ فوت‌پرینت و والوم پروفایل: POC/VAH/VAL با عدد + موقعیت قیمت نسبت به آن‌ها\n"
            "📰 فیلتر خبری و زمانی: اگر سیستم خبر را بلاک کرده یا جلسه ضعیف است صریحاً بگو\n"
            "📊 هم‌گرایی کل اندیکاتورها و اوسیلاتورها: RSI/EMA/MACD/BB و تلاقی‌شان با ساختار\n"
            "🔬 پک اندیکاتور پیشرفته v2: رأی ۱۶ اندیکاتور حرفه‌ای (TRIX/KST/Aroon/TTM Squeeze/Choppiness/VWAP-z و...) از پرونده — هم‌راستا یا مخالف ساختار؟\n"
            "🧰 استراتژی‌های کلاسیک v2: سیگنال‌های فعال پک ۲۲تایی (وایکاف، سر و شانه، ORB، پرچم، جوداس، Power of 3 و...) با کیفیت هرکدام؛ تضادها را صریح بگو\n"
            "🏛️ ICT ساختاری: وضعیت BOS/CHoCH + ناحیه OTE (قیمت داخلش هست؟) + کیلزون فعال + بریکرها/FVG وارونه\n"
            "🧾 برنامه معاملاتی: فقط اگر حکم قطعی سیستم قابل‌معامله بود (نه NO_TRADE/WAIT) سه سناریوی ورود با اعداد Entry/SL/TP1/TP2/TP3 سیستم را اعلام کن؛ در غیر این صورت بنویس «بدون ورود» و دلیل دقیق سخت‌گیری را بیاور\n"
            "❌ رد شرایط: صادقانه بگو چه شرایطی کم است تا ستاپ درجه-A شود\n\n"
            "۱. 🌀 تشخیص ساختار و رژیم بازار (Market Structure & Regime Detection):\n"
            "   - روند کلی بازار (نزولی، صعودی، رنج تعادلی، یا تراکم شدید Bollinger Bands).\n"
            "   - نواحی شکست معتبر (BoS/CHoCH با بدنه کندل پر).\n\n"
            "۲. 💧 ردیابی نقدینگی و سوییپ‌ها (Liquidity pools & Sweeps):\n"
            "   - شناسایی استخرهای نقدینگی بالا و پایین چارت (PDH/PDL) یا قیمت‌های برابر (EQH/EQL).\n"
            "   - بررسی وقوع سوییپ نقدینگی (Liquidity Sweep) همراه با ریجکشن.\n\n"
            "۳. 📊 آنالیز پروفایل حجم (Volume Profile Shape & Levels):\n"
            "   - موقعیت قیمت نسبت به مرزهای ارزش (VAH/VAL) و نقطه کنترل (POC) و بزرگترین گره پرحجم (HVN).\n"
            "   - تحلیل شکل پروفایل (D-Shape, P-Shape, b-Shape) و اعمال قانون ۸۰٪ ولوم پروفایل.\n\n"
            "۴. 🕯️ سیلان سفارشات و سنجه‌های مشتقات (Order Flow & Derivatives):\n"
            "   - تحلیل مارکت اوردرها، دلتا و بررسی احتمال وقوع واگرایی مخفی یا معمولی CVD.\n"
            "   - وضعیت بهره باز (Open Interest) و نرخ فاندینگ (Funding Rate) در صورت وجود شواهد مشتقات.\n\n"
            "۵. 📖 تطبیق با استراتژی مرجع (۲۰ کتابچه + پک پیشرفته ICT/Wyckoff ۲۱-۳۰):\n"
            "   - ستاپ شناسایی‌شده را دقیقاً با شماره استراتژی مرجع تطبیق بده؛ اگر سوییپ/گپ/Displacement/پنجره Silver Bullet در پرونده هست، حتماً از پک ICT (۲۱-۳۰) استفاده کن و وین‌ریت و RR آماری آن را ذکر کن.\n\n"
            "۶. 🛡️ مدیریت سرمایه و برنامه خروج (Risk Plan & Grade):\n"
            "   - محدوده ورود پیشنهادی (Entry Zone)، حد ضرر امن (Safe SL) و اهداف سه گانه سود (TP1, TP2, TP3).\n"
            "   - تعیین رتبه نهایی معامله (Grade A+, A, B, C, D) بر اساس سیستم امتیازدهی وزن‌دار کوانت.\n\n"
            "قوانین طلایی برای اعمال:\n" + StrategyGroundedHelper.get_grounding_system_prompt_addon()
        )

        # Ground the vision analysis in REAL data: deterministic SMC report + microstructure.
        micro_block = ""
        vision_symbol = (symbol or "").strip().upper() or detect_symbol_from_text(file.filename or "")
        if vision_symbol:
            micro = await get_micro_summary(
                vision_symbol, "auto", timeframe, timeout_s=8.0, compact=False
            )
            vision_report = None
            try:
                v_market = _auto_market(vision_symbol, None)
                v_tf = _canonical_timeframe(timeframe)
                v_raw = await fetch_live_candles(symbol=vision_symbol, market=v_market, timeframe=v_tf)
                v_items = _norm_candles(v_raw[-150:])
                if len(v_items) >= 30:
                    from app.services.smc_engine import analyze as _v_analyze
                    vision_report = _v_analyze(v_items, symbol=vision_symbol, timeframe=v_tf)
                    vision_report["market"] = v_market
                    v_flow = await orderflow_service.get_snapshot(vision_symbol, v_market, v_items)
                    vision_report["microstructure"] = micro
                    vision_report["force"] = _buyer_seller_force(vision_report, micro)
                    # v3.11: deterministic ICT + SMT so the vision dossier is complete
                    try:
                        vision_report["ict"] = ict_engine.summarize(v_items, vision_report)
                    except Exception:
                        vision_report["ict"] = None
                    try:
                        vision_report["smt"] = await _smt_for_symbol(vision_symbol, v_market, v_tf, v_items)
                    except Exception:
                        vision_report["smt"] = None
                    # v3.12: indicator + strategy packs for the vision dossier
                    try:
                        _v_pack = indicator_pack_v2.compute_all(v_items)
                        vision_report["indicators_v2"] = {"pack": _v_pack, "summary": indicator_pack_v2.summarize(_v_pack)}
                    except Exception:
                        vision_report["indicators_v2"] = None
                    try:
                        vision_report["strategies_v2"] = strategy_pack_v2.scan_all(v_items, v_tf)
                    except Exception:
                        vision_report["strategies_v2"] = None
                    apply_strict_decision(
                        vision_report,
                        v_items,
                        market=v_market,
                        timeframe=v_tf,
                        orderflow_source=str(v_flow.get("source") or "unknown"),
                        orderflow_confidence=float(v_flow.get("confidence") or 0),
                        orderflow_snapshot=v_flow,
                    )
            except Exception as _ve:
                import logging as _log
                _log.getLogger("apex.api.vision").warning(f"vision grounding report failed: {_ve}")
            if vision_report is not None:
                micro_block = "\n\n" + build_market_dossier(vision_report, micro, [])
            elif micro:
                micro_block = (
                    f"\n\n📡 داده‌های زنده و واقعی خردساختار بازار برای {vision_symbol} "
                    f"(سیستم به‌صورت قطعی از صرافی محاسبه کرده؛ این اعداد را مبنا قرار بده، "
                    "در تحلیل به همین سطوح ارجاع بده و هیچ عددی از خودت نساز):\n"
                    + build_ai_context_text(micro)
                )

        base_payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt_text + micro_block
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 2048,
        }
        token_budgets = [2048] if not cand["is_groq"] else [900, 600]
        for model in model_options:
            for budget in token_budgets:
                payload = _adapt_payload_for_model(
                    {**base_payload, "model": model, "max_tokens": budget, **_ai_payload_extra(model)},
                    model, cand["is_groq"],
                )
                try:
                    url = f"{cand['base_url']}/chat/completions"
                    logger.info(f"Trying vision analysis with {cand['provider']} ({model}, max_tokens={budget})")
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(url, headers=headers, json=payload)
                        response.raise_for_status()
                        data = response.json()
                        analysis_text = _strip_reasoning_blocks(data["choices"][0]["message"]["content"])
                        if not analysis_text:
                            raise RuntimeError("empty analysis after stripping reasoning chain")
                        return {
                            "success": True,
                            "analysis": analysis_text,
                            "provider_used": cand["provider"],
                            "model": model,
                            "errors_overcome": errors
                        }
                except Exception as exc:
                    err_msg = str(exc)
                    if hasattr(exc, "response") and exc.response is not None:
                        try:
                            err_msg = exc.response.json().get("error", {}).get("message", exc.response.text)
                        except Exception:
                            err_msg = exc.response.text or str(exc)
                    lowered = err_msg.lower()
                    rate_limited = "otpm" in lowered or "tokens per minute" in lowered or "request too large" in lowered
                    if rate_limited and budget != token_budgets[-1]:
                        logger.warning(f"Vision {cand['provider']} ({model}) rate-limited; retrying with lower budget")
                        continue
                    logger.warning(f"Vision provider {cand['provider']} ({model}) failed: {err_msg}")
                    errors.append(f"{cand['provider']} [{model}]: {err_msg}")
                    break

    return {
        "success": False,
        "analysis": f"❌ خطا در تمام تلاش‌های هوش مصنوعی:\n" + "\n".join(errors)
    }


from pydantic import BaseModel

class ChatTurn(BaseModel):
    role: str = "user"
    content: str = ""


class AIChatRequest(BaseModel):
    message: str
    symbol: str = ""
    timeframe: str = "15m"
    history: list[ChatTurn] = []


def _chat_history_messages(history: list[ChatTurn] | None) -> list[dict]:
    """Sanitize conversation history: last 8 turns, max 2000 chars each."""
    messages: list[dict] = []
    for turn in (history or [])[-8:]:
        role = "assistant" if str(turn.role or "").lower().startswith("a") else "user"
        content = str(turn.content or "").strip()[:2000]
        if content:
            messages.append({"role": role, "content": content})
    return messages


@app.post("/api/v1/aichat")
async def execute_ai_chat_assistant(
    request: AIChatRequest,
    user=Depends(optional_current_user),
):
    import httpx
    import logging
    logger = logging.getLogger("apex.api.chat")

    if not settings.ai_external_enabled and not _byok_candidates(user, "chat"):
        return {
            "success": True,
            "reply": "⚠️ هوش مصنوعی سیستمی غیرفعال است و کلید شخصی (BYOK) هم ذخیره نشده. "
                     "برای چت زنده، کلید Cerebras/Groq/OpenRouter/OpenAI خود را در تنظیمات ذخیره کنید."
        }

    # Chat: user BYOK first (Cerebras for latency, then Groq/OpenRouter/OpenAI),
    # then system keys. All OpenAI-compatible, so one request path serves them.
    candidates = _byok_candidates(user, "chat") + _system_ai_candidates("chat")

    if not candidates:
        return {
            "success": True,
            "reply": "⚠️ هیچ کلید AI تنظیم نشده است. در تنظیمات، یکی از کلیدهای Cerebras، Groq، OpenRouter یا OpenAI را ذخیره کنید."
        }

    errors = []
    # Execute with fallback logic
    for cand in candidates:
        api_key = cand["api_key"]
        if api_key.startswith("b'") and api_key.endswith("'"):
            api_key = api_key[2:-1]
        elif api_key.startswith('b"') and api_key.endswith('"'):
            api_key = api_key[2:-1]
        api_key = api_key.strip("'\"")

        headers = _openai_compat_headers(api_key, cand.get("base_url", ""))

        # Self-adaptive model selection (live Groq list, deprecation-proof)
        model_options = await _model_options_for(cand, kind="chat")

        system_prompt = (
            "شما دستیار ارشد، زبده و ریاضیدان ترید اسمارت مانی (SMC)، آی‌سی‌تی (ICT) و جریان سفارشات (Order Flow) پلتفرم APEX PRO v3.12 هستید. "
            "وظیفه شما راهنمایی معامله‌گران بر اساس اصول علمی، سیستم امتیازدهی کمّی کوانت، ۶ ستون اصلی استراتژی و دانشنامه جامع ۲۰ استراتژی معاملاتی است.\n\n"
            "📁 اگر «پرونده قطعی بازار» در پیام هست: تمام اعداد آن واقعی و محاسبه‌شده سیستم است (ساختار ICT شامل BOS/CHoCH و OTE و کیلزون، "
            "فوت‌پرینت و CVD، پک ۲۲ اندیکاتور پیشرفته با رأی‌گیری، پک ۳۴ استراتژی کلاسیک/ICT/اسمارت‌مانی فعال، SMT). "
            "پاسخ را دقیقاً بر پایه همان اعداد بساز؛ اگر بخشی «داده کافی نیست» بود صریح بگو و حدس نزن. "
            "تضاد بین استراتژی‌ها/اندیکاتورها را پنهان نکن — سخت‌گیرانه وزن‌دهی کن و بگو کدام شواهد قوی‌ترند.\n\n"
            "دستورالعمل‌های رفتاری شما:\n"
            "۱. همیشه پاسخ‌ها را به زبان فارسی روان، علمی، صمیمانه، بسیار متمرکز بر مدیریت ریسک و بدون ادعاهای تضمین سود کاذب صادر کنید.\n"
            "۲. اصطلاحات فنی بازار را به درستی به کار ببرید و ترجیحاً پاسخ‌ها را با بخش‌بندی‌های منظم مجهز به ایموجی‌های تخصصی ارسال کنید.\n"
            "۳. هر زمان کاربر درباره ستاپ‌ها، جهت بازار، یا اصول ولوم پروفایل سوال کرد، پاسخ را مستقیماً به فریمورک ۶ ستون اصلی پیوند دهید.\n"
            "۴. از قوانین و جزئیات ۳۰ استراتژی مرجع (۲۰ استراتژی کتابچه + ۱۰ استراتژی پک پیشرفته ICT/Wyckoff) برای تحلیل سناریوهای کاربر استفاده کنید و شماره استراتژی متناظر را ذکر کنید.\n"
            "۵. پاسخ نهایی فقط و فقط فارسی باشد؛ هیچ تگ <think>، هیچ زنجیره فکر و هیچ متن انگلیسی خام در خروجی منتشر نکن.\n"
            "۶. سخت‌گیری حداکثری: هر عددی که در دیتای زنده داده شده معتبر است و مطلقاً نباید عددی از خودت بسازی؛ اگر دیتایی موجود نیست صریح بگو «داده کافی نیست».\n"
            "۷. وقتی درباره مسیر بازار می‌پرسند، همیشه حکم صریح بده: صعودی/نزولی/رنج + درصد اطمینان + ترازوی زور خریدار مقابل فروشنده (از دلتا/عمق/فوت‌پرینت واقعی)\n"
            "۸. نقدینگی‌ها و گپ‌ها (FVG) و دیوارهای سفارش را همیشه با عدد اعلام کن و فقط اگر شرایط معاملاتی واقعاً مناسب بود Entry/SL/TP با اعداد سیستم بده؛ در غیر این صورت «بدون ورود» + دلیل سخت‌گیری.\n\n"
            "ماتریس طلایی ۶ ستون و ۲۰ استراتژی مبنای شما:\n" + StrategyGroundedHelper.get_grounding_system_prompt_addon()
        )

        # Ground the chat in REAL microstructure when a symbol is present.
        live_context = ""
        chat_symbol = (request.symbol or "").strip().upper() or detect_symbol_from_text(request.message)
        if chat_symbol:
            micro = await get_micro_summary(
                chat_symbol, "auto", request.timeframe or "15m", timeout_s=8.0, compact=False
            )
            if micro:
                live_context = (
                    f"📊 داده‌های زنده و واقعی بازار برای {chat_symbol} (سیستم به‌صورت قطعی از صرافی محاسبه کرده؛ "
                    "این اعداد را معتبر فرض کن، در پاسخ به همین سطوح ارجاع بده و هیچ عددی از خودت نساز):\n"
                    + build_ai_context_text(micro)
                    + "\n\n"
                )
            # v3.12: full deterministic dossier (SMC + ICT v2 + packs + SMT) for chat grounding
            try:
                c_tf = _canonical_timeframe(request.timeframe or "15m")
                c_market = _auto_market(chat_symbol, None)
                c_raw = await fetch_live_candles(symbol=chat_symbol, market=c_market, timeframe=c_tf)
                c_items = _norm_candles(c_raw[-220:])
                if len(c_items) >= 30:
                    from app.services.smc_engine import analyze as _c_an
                    c_report = _c_an(c_items, symbol=chat_symbol, timeframe=c_tf)
                    c_report["market"] = c_market
                    try:
                        c_report["ict"] = ict_engine.summarize(c_items, c_report)
                    except Exception:
                        c_report["ict"] = None
                    try:
                        c_report["smt"] = await _smt_for_symbol(chat_symbol, c_market, c_tf, c_items)
                    except Exception:
                        c_report["smt"] = None
                    try:
                        _c_pack = indicator_pack_v2.compute_all(c_items)
                        c_report["indicators_v2"] = {"pack": _c_pack, "summary": indicator_pack_v2.summarize(_c_pack)}
                    except Exception:
                        c_report["indicators_v2"] = None
                    try:
                        c_report["strategies_v2"] = strategy_pack_v2.scan_all(c_items, c_tf)
                    except Exception:
                        c_report["strategies_v2"] = None
                    c_report["force"] = _buyer_seller_force(c_report, micro)
                    live_context += "📁 پرونده قطعی بازار (تحلیل سیستم، نه حدس):\n" + build_market_dossier(c_report, micro, c_items) + "\n\n"
            except Exception:
                pass

        history_messages = _chat_history_messages(request.history)
        base_payload = {
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                }
            ]
            + history_messages
            + [
                {
                    "role": "user",
                    "content": live_context + request.message
                }
            ],
            "temperature": 0.7,
            "max_tokens": 1600,
        }
        token_budgets = [1600] if not cand["is_groq"] else [1200, 700]
        for model in model_options:
            for budget in token_budgets:
                payload = _adapt_payload_for_model(
                    {**base_payload, "model": model, "max_tokens": budget, **_ai_payload_extra(model)},
                    model, cand["is_groq"],
                )
                try:
                    url = f"{cand['base_url']}/chat/completions"
                    logger.info(f"Trying AI chat with {cand['provider']} ({model}, max_tokens={budget})")
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(url, headers=headers, json=payload)
                        response.raise_for_status()
                        data = response.json()
                        reply = _strip_reasoning_blocks(data["choices"][0]["message"]["content"])
                        if not reply:
                            raise RuntimeError("empty reply after stripping reasoning chain")
                        return {
                            "success": True,
                            "reply": reply,
                            "provider_used": cand["provider"],
                            "model": model,
                            "errors_overcome": errors
                        }
                except Exception as exc:
                    err_msg = str(exc)
                    if hasattr(exc, "response") and exc.response is not None:
                        try:
                            err_msg = exc.response.json().get("error", {}).get("message", exc.response.text)
                        except Exception:
                            err_msg = exc.response.text or str(exc)
                    lowered = err_msg.lower()
                    rate_limited = "otpm" in lowered or "tokens per minute" in lowered or "request too large" in lowered
                    if rate_limited and budget != token_budgets[-1]:
                        logger.warning(f"Chat {cand['provider']} ({model}) rate-limited; retrying with lower budget")
                        continue
                    logger.warning(f"Chat provider {cand['provider']} ({model}) failed: {err_msg}")
                    errors.append(f"{cand['provider']} [{model}]: {err_msg}")
                    break

    return {
        "success": False,
        "reply": f"❌ خطا در تمام تلاش‌های هوش مصنوعی:\n" + "\n".join(errors)
    }


_DEEP_CACHE: dict[str, tuple[float, dict]] = {}


@app.get("/api/v1/analysis/deep")
async def deep_institutional_analysis(
    symbol: str = Query(..., min_length=2, max_length=24),
    timeframe: str = Query("15m"),
    market: str = Query("", pattern="^(|crypto|forex|auto)$"),
    user=Depends(optional_current_user),
):
    """Institutional deep analysis: deterministic core verdict + advisory AI narrative.

    The strict engine's verdict is the single source of truth; the AI narrative
    is advisory-only and must explicitly flag any disagreement with the core.
    """
    import json as _json
    import logging
    logger = logging.getLogger("apex.api.deep")
    symbol = symbol.upper()
    tf = _canonical_timeframe(timeframe)
    cache_key = f"{symbol}|{tf}"
    now = _time.time()
    cached = _DEEP_CACHE.get(cache_key)
    if cached and now - cached[0] < 90:
        return {**cached[1], "cached": True, "cache_age_seconds": round(now - cached[0], 1)}

    if not settings.ai_external_enabled and not _byok_candidates(user, "chat"):
        return {
            "success": False,
            "detail": "هوش مصنوعی سیستمی غیرفعال است و کلید شخصی (BYOK) هم ذخیره نشده است.",
            "cached": False,
        }

    market_eff = _auto_market(symbol, market or None)
    from app.services.smc_engine import analyze
    try:
        raw = await fetch_live_candles(symbol=symbol, market=market_eff, timeframe=tf)
    except Exception:
        return {"success": False, "detail": "داده بازار موقتاً در دسترس نیست.", "cached": False}
    items = _norm_candles(raw[-220:])
    if len(items) < 30:
        return {"success": False, "detail": "داده کافی نیست.", "cached": False}

    htf_bias = None
    try:
        hm = {"1m": "5m", "5m": "15m", "15m": "1h", "30m": "4h", "1h": "4h"}.get(tf)
        if hm:
            hitems = _norm_candles(_resample_candles(raw, hm))
            if len(hitems) >= 30:
                hrep = analyze(hitems, symbol=symbol, timeframe=hm)
                htf_bias = hrep.get("bias")
    except Exception:
        htf_bias = None

    _news_blocked = False
    try:
        from app.news_engine_v2 import build_news_brief as _nb
        _nbrief = await _nb()
        _news_blocked = bool((_nbrief.get("block") or {}).get("blocked"))
    except Exception:
        pass

    report = analyze(items, symbol=symbol, timeframe=tf, htf_bias=htf_bias, news_blocked=_news_blocked)
    report["market"] = market_eff
    flow = await enrich_orderflow(report, symbol, market_eff, items, timeframe=tf)
    report = apply_strict_decision(
        report,
        items,
        market=market_eff,
        timeframe=tf,
        orderflow_source=str(flow.get("source") or "unknown"),
        orderflow_confidence=float(flow.get("confidence") or 0),
        orderflow_snapshot=flow,
    )

    report["force"] = _buyer_seller_force(report, report.get("microstructure"))
    micro_obj = report.get("microstructure") or {}
    direction = report.get("direction", "neutral")
    setup_type = report.get("setup_type") or "-"
    handbook = StrategyGroundedHelper.map_setup_to_handbook(setup_type, direction)
    decision = report.get("decision") or {}
    deterministic = {
        "symbol": symbol,
        "timeframe": tf,
        "market": market_eff,
        "bias": report.get("bias"),
        "direction": direction,
        "grade": report.get("grade"),
        "action_label": report.get("action_label"),
        "setup_type": setup_type,
        "confluence": report.get("confluence"),
        "probability": report.get("probability"),
        "rr": report.get("rr"),
        "price": report.get("price"),
        "levels": report.get("levels"),
        "entry_zone": report.get("entry_zone"),
        "htf": report.get("htf"),
        "micro_net": (micro_obj.get("filters") or {}).get("net_bias") or "neutral",
        "micro_confluence": _micro_confluence_points(micro_obj, direction),
        "force": report.get("force"),
        "liquidity_pools": _numbered_liquidity(report),
        "gaps_fvg": _gap_list(report),
        "order_blocks": _top_order_blocks(report),
        "oscillators": _oscillator_snapshot(items),
        "ict": report.get("ict"),
        "smt": report.get("smt"),
        "indicator_confluence": report.get("indicator_confluence"),
        "indicators_v2": (report.get("indicators_v2") or {}).get("summary"),
        "strategies_v2": {
            "counts": (report.get("strategies_v2") or {}).get("counts"),
            "net_direction": (report.get("strategies_v2") or {}).get("net_direction"),
            "agreement_pct": (report.get("strategies_v2") or {}).get("agreement_pct"),
            "active": [
                {"name_fa": s.get("name_fa"), "direction": s.get("direction"), "quality": s.get("quality"), "reason_fa": s.get("reason_fa")}
                for s in ((report.get("strategies_v2") or {}).get("active") or [])[:8]
            ],
            "forming": [
                {"name_fa": s.get("name_fa"), "reason_fa": s.get("reason_fa")}
                for s in ((report.get("strategies_v2") or {}).get("forming") or [])[:4]
            ],
        } if (report.get("strategies_v2") or {}).get("available") else None,
        "no_trade_reason": decision.get("no_trade_reason"),
        "handbook": handbook,
    }

    micro_block = build_market_dossier(report, micro_obj, items)

    deep_system_prompt = (
        "شما مدیر تحلیل ارشد میز معاملات نهادی (Institutional Desk) در پلتفرم APEX PRO v3.1 هستید؛ سخت‌گیرترین عضو میز. "
        "یک یادداشت تحلیلی عمیق، مهندسی، بدون توهم و کاملاً فارسی ارائه کنید.\n\n"
        "⚠️ قواعد الزامی:\n"
        "۱. خروجی قطعی سیستم (action_label و grade) مرجع نهایی و غیرقابل تغییر است؛ اگر تحلیل کارشناسی شما با آن متفاوت است، فقط در بخش «⚖️ تعارض با سیستم» صریحاً بنویسید و دلیل بیاورید.\n"
        "۲. فقط از اعداد پرونده کامل بازار استفاده کنید؛ هیچ عددی از خودتان نسازید و اگر داده‌ای نیست صریح بگویید.\n"
        "۳. کل پاسخ فقط فارسی باشد؛ بدون هیچ تگ <think> و بدون زنجیره فکر.\n"
        "۴. سخت‌گیری حداکثری: تا وقتی حکم سیستم NO_TRADE/WAIT است، هیچ برنامه ورودی ارائه ندهید؛ فقط مسیر بازار، نیروها و شروط فعال‌سازی را بگویید.\n\n"
        "ساختار الزامی پاسخ:\n"
        "🧭 خلاصه اجرایی (حداکثر ۳ خط)\n"
        "🏆 حکم مسیر بازار: صعودی/نزولی/رنج + درصد اطمینان + دلیل (ساختار+حجم+جریان)\n"
        "⚖️ ترازوی نیرو: زور خریدار X٪ مقابل فروشنده Y٪ با استناد به دلتا/عمق/فوت‌پرینت\n"
        "💧 نقدینگی‌های شماره‌دار با قیمت + نزدیک‌ترین تله نقدینگی به قیمت فعلی\n"
        "🩹 گپ‌ها (FVG) با محدوده عددی + نقش هر گپ\n"
        "🧱 سفارشات: دیوارهای L2 و OBها با قیمت + جذب یا شکست\n"
        "📊 پروفایل حجم: POC/VAH/VAL با عدد + موقعیت قیمت + سناریوی ۸۰٪ Value Area\n"
        "🕯️ فوت‌پرینت: دلتای کندل‌ها، Imbalanceهای روی‌هم، اتمام‌نیافته‌ها + جمع‌بندی (مهاجرت POC، واگرایی دلتا/قیمت)\n"
        "📈 اندیکاتورها و اوسیلاتورها: RSI/EMA/MACD/BB هم‌گرا یا واگرا با ساختار؟\n"
        "🔬 پک اندیکاتور پیشرفته v2: رأی‌ها (صعودی/نزولی/خنثی)، وضعیت TTM Squeeze، Choppiness (رژیم روند/رنج)، z-score نسبت به VWAP — هم‌راستا با ساختار یا نه؟\n"
        "🧰 استراتژی‌های کلاسیک v2: سیگنال‌های فعال/در حال شکل‌گیری با کیفیت هرکدام (وایکاف، ORB، سر و شانه، پرچم، جوداس، Power of 3 و...) — اگر با هم تضاد دارند بگو کدام با ساختار/جریان هم‌راستاست\n"
        "🏛️ ICT ساختاری: وضعیت BOS/CHoCH و الگوی HH/HL یا LH/LL + آیا قیمت داخل ناحیه OTE است؟ + کیلزون فعال و کیفیت زمانی + بریکرها و FVGهای وارونه\n"
        "📰 فیلتر خبری و زمانی: وضعیت بلاک خبر و کیفیت جلسه\n"
        "🛰️ هم‌راستایی خردساختار (µ) با ستاپ\n"
        "🔗 واگرایی SMT با جفت همبسته: اگر در پرونده هست با عدد گزارش بده؛ اگر نیست صریح بگو داده نیست\n"
        "📖 تطبیق با استراتژی مرجع (کتابچه ۲۰تایی + پک ICT ۲۱-۳۰ با ذکر شماره)\n"
        "🎯 سناریو اصلی و سناریوی جایگزین (فقط محرک/شرط، بدون ورود در حالت NO_TRADE)\n"
        "🛡️ برنامه ریسک: فقط اگر سیستم actionable بود: Entry/SL/TP1-TP3 با اعداد سیستم\n"
        "❌ چک‌لیست سخت‌گیری: چه چیزی کم است تا Grade-A شود\n"
        "⚖️ تعارض یا تأیید تصمیم قطعی سیستم\n\n"
        + StrategyGroundedHelper.get_grounding_system_prompt_addon()
    )
    user_block = (
        f"خروجی قطعی سیستم (مرجع نهایی):\n"
        f"{_json.dumps(deterministic, ensure_ascii=False, default=str)}\n\n"
        f"دیتای زنده خردساختار بازار:\n{micro_block}\n\n"
        f"حالا یادداشت تحلیل عمیق نهادی برای {symbol} در تایم‌فریم {tf} را طبق ساختار الزامی بنویس."
    )

    # Deep analysis: user BYOK first (Cerebras/Groq/OpenRouter/OpenAI), then system keys.
    candidates = _byok_candidates(user, "chat") + _system_ai_candidates("chat")

    if not candidates:
        return {
            "success": False,
            "detail": "⚠️ هیچ کلید AI تنظیم نشده است (Cerebras/Groq/OpenRouter/OpenAI).",
            "deterministic": deterministic,
            "cached": False,
        }

    errors = []
    import httpx
    for cand in candidates:
        api_key = cand["api_key"]
        if api_key.startswith("b'") and api_key.endswith("'"):
            api_key = api_key[2:-1]
        elif api_key.startswith('b"') and api_key.endswith('"'):
            api_key = api_key[2:-1]
        api_key = api_key.strip("'\"")
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        model_options = await _model_options_for(cand, kind="chat")
        token_budgets = [1600] if not cand["is_groq"] else [1200, 700]
        for model in model_options:
            for budget in token_budgets:
                payload = _adapt_payload_for_model(
                    {
                        "model": model,
                        "messages": [
                            {"role": "system", "content": deep_system_prompt},
                            {"role": "user", "content": user_block},
                        ],
                        "temperature": 0.5,
                        "max_tokens": budget,
                        **_ai_payload_extra(model),
                    },
                    model, cand["is_groq"],
                )
                try:
                    url = f"{cand['base_url']}/chat/completions"
                    logger.info(f"Deep analysis with {cand['provider']} ({model}, max_tokens={budget})")
                    async with httpx.AsyncClient(timeout=45.0) as client:
                        response = await client.post(url, headers=headers, json=payload)
                        response.raise_for_status()
                        data = response.json()
                        narrative = _strip_reasoning_blocks(data["choices"][0]["message"]["content"])
                        if not narrative:
                            raise RuntimeError("empty narrative after stripping reasoning chain")
                        result = {
                            "success": True,
                            "symbol": symbol,
                            "timeframe": tf,
                            "deterministic": deterministic,
                            "narrative": narrative,
                            "provider_used": cand["provider"],
                            "model": model,
                            "advisory_only": True,
                            "disclaimer": "روایت AI فقط مشاوره‌ای است؛ حکم قطعی با موتور determinstic سیستم است.",
                            "errors_overcome": errors,
                            "cached": False,
                            "cache_age_seconds": 0.0,
                        }
                        _DEEP_CACHE[cache_key] = (_time.time(), result)
                        return result
                except Exception as exc:
                    err_msg = str(exc)
                    if hasattr(exc, "response") and exc.response is not None:
                        try:
                            err_msg = exc.response.json().get("error", {}).get("message", exc.response.text)
                        except Exception:
                            err_msg = exc.response.text or str(exc)
                    lowered = err_msg.lower()
                    rate_limited = "otpm" in lowered or "tokens per minute" in lowered or "request too large" in lowered
                    if rate_limited and budget != token_budgets[-1]:
                        continue
                    logger.warning(f"Deep provider {cand['provider']} ({model}) failed: {err_msg}")
                    errors.append(f"{cand['provider']} [{model}]: {err_msg}")
                    break

    return {
        "success": False,
        "detail": "❌ خطا در تمام تلاش‌های هوش مصنوعی:\n" + "\n".join(errors),
        "deterministic": deterministic,
        "cached": False,
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
    "/api/v1/analysis/intraday-fusion/shadow/system-feasibility-panel",
    response_model=SignalShadowFeasibilityPanelResponse,
)
def get_system_intraday_fusion_shadow_feasibility_panel(user=Depends(current_user)):
    return signal_shadow_service.feasibility_panel(0)


@app.get(
    "/api/v1/analysis/intraday-fusion/shadow/feasibility-panel",
    response_model=SignalShadowFeasibilityPanelResponse,
)
def get_intraday_fusion_shadow_feasibility_panel(user=Depends(current_user)):
    return signal_shadow_service.feasibility_panel(user.id)


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


@app.post(
    "/api/v1/analysis/intraday-fusion/shadow/forward-holdout-plan/{source_snapshot_id}",
    response_model=SignalShadowForwardHoldoutPlanResponse,
)
def lock_intraday_fusion_shadow_forward_holdout_plan(
    source_snapshot_id: str,
    required_activated_outcomes: int = Query(default=30, ge=30, le=1000),
    user=Depends(current_user),
):
    try:
        return signal_shadow_service.lock_forward_holdout_plan(
            user.id,
            source_snapshot_id,
            required_activated_outcomes=required_activated_outcomes,
        )
    except SignalShadowError as exc:
        status_code = 404 if exc.code.endswith("not_found") else 400
        raise HTTPException(status_code=status_code, detail={"code": exc.code}) from exc


@app.post(
    "/api/v1/analysis/intraday-fusion/shadow/system-forward-holdout-plan/{source_snapshot_id}",
    response_model=SignalShadowForwardHoldoutPlanResponse,
)
def lock_system_intraday_fusion_shadow_forward_holdout_plan(
    source_snapshot_id: str,
    required_activated_outcomes: int = Query(default=30, ge=30, le=1000),
    user=Depends(current_user),
):
    try:
        return signal_shadow_service.lock_forward_holdout_plan(
            0,
            source_snapshot_id,
            required_activated_outcomes=required_activated_outcomes,
        )
    except SignalShadowError as exc:
        status_code = 404 if exc.code.endswith("not_found") else 400
        raise HTTPException(status_code=status_code, detail={"code": exc.code}) from exc


@app.get(
    "/api/v1/analysis/intraday-fusion/shadow/forward-holdout-plan/{plan_id}",
    response_model=SignalShadowForwardHoldoutPlanResponse,
)
def get_intraday_fusion_shadow_forward_holdout_plan(
    plan_id: str,
    user=Depends(current_user),
):
    try:
        return signal_shadow_service.get_forward_holdout_plan(user.id, plan_id)
    except SignalShadowError as exc:
        status_code = 404 if exc.code.endswith("not_found") else 400
        raise HTTPException(status_code=status_code, detail={"code": exc.code}) from exc


@app.get(
    "/api/v1/analysis/intraday-fusion/shadow/system-forward-holdout-plan/{plan_id}",
    response_model=SignalShadowForwardHoldoutPlanResponse,
)
def get_system_intraday_fusion_shadow_forward_holdout_plan(
    plan_id: str,
    user=Depends(current_user),
):
    try:
        return signal_shadow_service.get_forward_holdout_plan(0, plan_id)
    except SignalShadowError as exc:
        status_code = 404 if exc.code.endswith("not_found") else 400
        raise HTTPException(status_code=status_code, detail={"code": exc.code}) from exc


@app.post(
    "/api/v1/analysis/intraday-fusion/shadow/forward-holdout-plan/{plan_id}/consume",
    response_model=SignalShadowHoldoutConsumptionResponse,
)
def consume_intraday_fusion_shadow_forward_holdout(
    plan_id: str,
    request: SignalShadowHoldoutConsumeRequest,
    user=Depends(current_user),
):
    try:
        return signal_shadow_service.consume_forward_holdout_once(
            user.id,
            plan_id,
            request.acknowledgement,
        )
    except SignalShadowError as exc:
        status_code = 404 if exc.code.endswith("not_found") else 400
        raise HTTPException(status_code=status_code, detail={"code": exc.code}) from exc


@app.post(
    "/api/v1/analysis/intraday-fusion/shadow/system-forward-holdout-plan/{plan_id}/consume",
    response_model=SignalShadowHoldoutConsumptionResponse,
)
def consume_system_intraday_fusion_shadow_forward_holdout(
    plan_id: str,
    request: SignalShadowHoldoutConsumeRequest,
    user=Depends(current_user),
):
    try:
        return signal_shadow_service.consume_forward_holdout_once(
            0,
            plan_id,
            request.acknowledgement,
        )
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
    # v3.12: clients only need the indicator-pack summary; drop the raw pack (bandwidth)
    ind2 = report.get("indicators_v2")
    if isinstance(ind2, dict) and "pack" in ind2:
        report["indicators_v2"] = {"summary": ind2.get("summary")}
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
    # RTM lines (QML/MPL/DOL) are index-based like labels — rebase and cap them
    overlay["lines"] = _rebase_items(
        [ln for ln in (overlay.get("lines") or []) if str(ln.get("kind", "")) in ("QML", "MPL", "DOL")],
        offset, total,
    )[-4:]
    raw_by_kind: dict[str, list[dict]] = {"OB": [], "FVG": [], "iFVG": [], "BRK": [], "SD": []}
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
    # RTM supply/demand: at most one demand + one supply zone (strongest each)
    selected_sd = strongest_per_side(rebased_by_kind["SD"])

    # At most 2 OBs + 2 FVGs + 1 faint breaker + 2 RTM S/D zones, all with a
    # finite extension ending on the first price revisit. Institutional only.
    overlay["zones"] = (
        simple_killzones + selected_obs + selected_fvgs + selected_breakers + selected_sd
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
async def scan_signals(min_confluence: int = Query(default=55, ge=0, le=100)):
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
            flow = await enrich_orderflow(r, sym, mkt_eff, items, timeframe=tf, with_smt=False)
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
                    "micro_confluence": _micro_confluence_points(r.get("microstructure"), r.get("direction","neutral")),
                    "micro_net":((r.get("microstructure") or {}).get("filters") or {}).get("net_bias") or "neutral",
                    "ict_points": ((r.get("ict") or {}).get("points_bull") if r.get("direction")=="long" else ((r.get("ict") or {}).get("points_bear") if r.get("direction")=="short" else 0)) or 0,
                    "indicator_score": round((((r.get("indicator_confluence") or {}).get("score") or 0) + 100) / 2, 1),
                    "strategies_net": (r.get("strategies_v2") or {}).get("net_direction"),
                    "strategies_agreement_pct": (r.get("strategies_v2") or {}).get("agreement_pct"),
                    "strategies_active": [
                        {"name_fa": s.get("name_fa"), "direction": s.get("direction"), "quality": s.get("quality"),
                         "gate_ok": s.get("gate_ok"), "perf_ok": s.get("perf_ok")}
                        for s in ((r.get("strategies_v2") or {}).get("active") or [])[:3]
                    ],
                    "indicators_v2_net": ((r.get("indicators_v2") or {}).get("summary") or {}).get("net"),
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
    for row in candidates:
        mc = int(row.get("micro_confluence") or 0)
        rr_v = float(row.get("rr") or 0)
        ip = int(row.get("ict_points") or 0)
        isc = float(row.get("indicator_score") or 50)
        row["value_score"] = round(min(100.0, (
            float(row.get("confluence") or 0) * 0.25
            + float(row.get("probability") or 0) * 0.15
            + min(rr_v, 5.0) / 5.0 * 100 * 0.15
            + (mc / 15.0) * 100 * 0.20
            + (ip / 15.0) * 100 * 0.15
            + isc * 0.10
        )), 1)
        # v3.12: strategy pack evidence adjusts value and gates PRIME (no conflict allowed)
        s_net = row.get("strategies_net")
        s_dir = row.get("direction")
        s_conflict = bool(s_net in ("long", "short") and s_dir in ("long", "short") and s_net != s_dir)
        if s_net == s_dir and int(row.get("strategies_agreement_pct") or 0) >= 60:
            row["value_score"] = round(min(100.0, row["value_score"] + 4.0), 1)
        elif s_conflict:
            row["value_score"] = round(max(0.0, row["value_score"] - 6.0), 1)
        elif s_net == "conflict":
            row["value_score"] = round(max(0.0, row["value_score"] - 2.0), 1)
        row["strategies_conflict"] = s_conflict
        row["is_prime"] = bool(
            row.get("grade") in ("A+", "A") and rr_v >= 1.8 and mc >= 8 and not s_conflict
        )
    actionable.sort(key=lambda x: (-float(x.get("value_score") or 0), -x["confluence"], -x["rr"]))
    watching.sort(key=lambda x: (-float(x.get("value_score") or 0), -x["confluence"], -x["rr"]))
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
    handbook_details = StrategyGroundedHelper.map_setup_to_handbook(setup_type, direction)
    micro_obj = report.get("microstructure") or {}
    micro_points = _micro_confluence_points(micro_obj, direction)
    rr_value = float(report.get("rr") or 0)
    probability_value = int(report.get("probability") or 0)
    confluence_value = int(report.get("confluence") or 0)
    ict_obj = report.get("ict") or {}
    if direction == "long":
        ict_points = int(ict_obj.get("points_bull") or 0)
    elif direction == "short":
        ict_points = int(ict_obj.get("points_bear") or 0)
    else:
        ict_points = 0
    ind_obj = report.get("indicator_confluence") or {}
    ind_score = float(ind_obj.get("score") or 0)
    indicator_score = round((ind_score + 100) / 2, 1)  # 0..100 aligned to direction-agnostic grid
    value_score = round(min(100.0, (
        confluence_value * 0.25
        + probability_value * 0.15
        + min(rr_value, 5.0) / 5.0 * 100 * 0.15
        + (micro_points / 15.0) * 100 * 0.20
        + (ict_points / 15.0) * 100 * 0.15
        + indicator_score * 0.10
    )), 1)
    # v3.12: classic strategy pack evidence (deterministic adjustment ±)
    strat2 = report.get("strategies_v2") or {}
    strat_net = None
    strat_agree = 0
    strat_conflict = False
    if strat2.get("available") and direction in ("long", "short"):
        strat_net = strat2.get("net_direction")
        strat_agree = int(strat2.get("agreement_pct") or 0)
        if strat_net == direction and strat_agree >= 60:
            value_score = round(min(100.0, value_score + 4.0), 1)
        elif strat_net in ("long", "short") and strat_net != direction:
            strat_conflict = True
            value_score = round(max(0.0, value_score - 6.0), 1)
        elif strat_net == "conflict":
            value_score = round(max(0.0, value_score - 2.0), 1)
    grade_value = report.get("grade", "-")
    is_prime = bool(
        grade_value in ("A+", "A")
        and rr_value >= 1.8
        and micro_points >= 8
        and direction in ("long", "short")
        # v3.12 strictness: the classic strategy pack must not be fighting the setup
        and not strat_conflict
    )
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
        "micro_confluence": micro_points,
        "micro_net": (micro_obj.get("filters") or {}).get("net_bias") or "neutral",
        "ict_points": ict_points,
        "indicator_score": indicator_score,
        "ict_events": (report.get("ict") or {}).get("events") or [],
        "ict_strategy": StrategyGroundedHelper.map_setup_to_ict_pack(setup_type, report.get("ict")),
        "strategies_net": strat_net,
        "strategies_agreement_pct": strat_agree,
        "strategies_conflict": strat_conflict,
        "strategies_active": [
            {"name_fa": s.get("name_fa"), "direction": s.get("direction"), "quality": s.get("quality"),
             "gate_ok": s.get("gate_ok"), "perf_ok": s.get("perf_ok")}
            for s in ((report.get("strategies_v2") or {}).get("active") or [])[:4]
        ],
        "indicators_v2_net": ((report.get("indicators_v2") or {}).get("summary") or {}).get("net"),
        "indicators_v2_verdict": ((report.get("indicators_v2") or {}).get("summary") or {}).get("verdict"),
        "value_score": value_score,
        "is_prime": is_prime,
        "data_quality": report.get("data_quality") or {},
        "market_regime": report.get("market_regime") or {},
        "handbook_details": handbook_details,
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
                    flow = await enrich_orderflow(report, symbol, market, items, timeframe=timeframe, with_smt=False)
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
        def _by_value(item: dict) -> float:
            return -(float(item.get("value_score") or 0))

        forming = sorted(lifecycle["forming"], key=_by_value)[:20]
        armed = sorted(lifecycle["armed"], key=_by_value)[:20]
        confirmed = sorted(lifecycle["confirmed"], key=_by_value)[:20]
        triggered = sorted(lifecycle["triggered"], key=_by_value)[:20]
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


@app.get("/api/v1/microstructure/{symbol}")
async def get_microstructure_snapshot(
    symbol: str,
    market: str = Query(default="auto", pattern="^(auto|crypto|forex)$"),
    timeframe: str = Query(default="15m"),
    compact: bool = Query(default=False),
):
    """Real L2 depth + footprint + volume profile + order flow (deterministic)."""
    tf = norm_timeframe(timeframe)
    items: list[dict] = []
    try:
        market_for_candles = _auto_market(symbol, None if market == "auto" else market)
        candles = await fetch_live_candles(symbol, market_for_candles, tf)
        items = _norm_candles(candles)
    except Exception:
        items = []
    payload = await microstructure_service.get_microstructure(
        symbol.upper(), market, tf, candles=items, compact=compact
    )
    return {
        "symbol": symbol.upper(),
        "market": market,
        "timeframe": tf,
        "microstructure": payload,
    }


async def _evaluate_proximity(
    symbol: str,
    market: str,
    timeframe: str,
    price: float | None = None,
    with_micro: bool = True,
) -> dict:
    """Collect every real deterministic level and measure its distance to price.

    Sources: numbered liquidity pools, FVG edges, order-block edges, EQH/EQL
    (ICT), volume-profile POC/VAH/VAL and real L2 walls. Nothing is invented.
    """
    market_eff = _auto_market(symbol, None if market in (None, "", "auto") else market)
    tf = _canonical_timeframe(timeframe)
    raw = await fetch_live_candles(symbol, market_eff, tf)
    items = _norm_candles(raw)
    if len(items) < 30:
        return {"available": False, "detail": "insufficient_candles", "rows": []}
    price_eff = float(price or items[-1]["c"])
    from app.services.smc_engine import analyze
    report = analyze(items[-260:], symbol=symbol, timeframe=tf)
    atr_pct = proximity_alert_service.atr_percent(items)
    levels: list[dict] = []
    for idx, pool in enumerate(_numbered_liquidity(report), 1):
        levels.append({"kind": "liquidity", "price": pool["price"], "label": f"#{idx} {pool.get('kind') or 'liq'}"})
    for gap in _gap_list(report)[:6]:
        side = gap.get("side") or ""
        levels.append({"kind": "fvg_edge", "price": gap["bottom"], "label": f"FVG {side} کف".strip()})
        levels.append({"kind": "fvg_edge", "price": gap["top"], "label": f"FVG {side} سقف".strip()})
    for ob in _top_order_blocks(report)[:3]:
        edge = ob["top"] if price_eff <= float(ob["top"]) else ob["bottom"]
        levels.append({"kind": "order_block", "price": edge, "label": f"OB {ob.get('side') or ''}".strip()})
    try:
        eq = ict_engine.equal_levels(items[-200:])
        for row in (eq.get("eqh") or []):
            levels.append({"kind": "eqh", "price": row.get("price"), "label": f"EQH×{row.get('count')}"})
        for row in (eq.get("eql") or []):
            levels.append({"kind": "eql", "price": row.get("price"), "label": f"EQL×{row.get('count')}"})
    except Exception:
        pass
    if with_micro:
        micro = await get_micro_summary(symbol, market_eff, tf, timeout_s=6.0, compact=True)
        if micro and micro.get("is_real"):
            vp = micro.get("vp") or {}
            for key, label in (("poc", "POC"), ("vah", "VAH"), ("val", "VAL")):
                if vp.get(key):
                    levels.append({"kind": key, "price": float(vp[key]), "label": label})
            l2 = micro.get("l2") or {}
            for wall_key, kind in (("bid_wall", "l2_bid_wall"), ("ask_wall", "l2_ask_wall")):
                wall = l2.get(wall_key) or {}
                if wall.get("price"):
                    levels.append({"kind": kind, "price": float(wall["price"]), "label": f"×{wall.get('x_median')}"})
    rows = proximity_alert_service.evaluate_levels(price_eff, atr_pct, levels)
    return {
        "available": True,
        "symbol": symbol,
        "market": market_eff,
        "timeframe": tf,
        "price": price_eff,
        "atr_pct": round(atr_pct, 4) if atr_pct is not None else None,
        "levels_checked": len(levels),
        "rows": rows,
    }


@app.get("/api/v1/alerts/proximity")
async def get_proximity_alerts(
    symbol: str = Query(..., min_length=2, max_length=24),
    market: str = Query(default="auto", pattern="^(auto|crypto|forex)$"),
    timeframe: str = Query(default="15m"),
):
    """Deterministic proximity of the live price to real liquidity/L2/VP/FVG levels."""
    try:
        evaluation = await _evaluate_proximity(symbol.upper(), market, timeframe)
    except HTTPException:
        raise
    except Exception:
        return {"available": False, "detail": "evaluation_failed", "alerts": [], "nearest": []}
    rows = evaluation.get("rows") or []
    alerts = [
        {**row, "message_fa": proximity_alert_service.message_fa(symbol.upper(), row)}
        for row in rows if row.get("in_range")
    ]
    return {
        "available": bool(evaluation.get("available")),
        "symbol": symbol.upper(),
        "market": evaluation.get("market", market),
        "timeframe": evaluation.get("timeframe"),
        "price": evaluation.get("price"),
        "atr_pct": evaluation.get("atr_pct"),
        "levels_checked": evaluation.get("levels_checked", 0),
        "alerts": alerts[:10],
        "nearest": rows[:6],
        "created_by": "Amin Omidi",
    }


_PRIME_BT_CACHE: dict[str, tuple[float, dict]] = {}
_STRATEGY_BT_CACHE: dict[str, tuple[float, dict]] = {}


@app.get("/api/v1/backtest/prime")
async def backtest_prime_setups(
    symbol: str = Query("BTCUSDT", min_length=2, max_length=24),
    timeframe: str = Query("15m"),
    market: str = Query(default="auto", pattern="^(auto|crypto|forex)$"),
    candles: int = Query(default=1000, ge=200, le=2000),
    force: bool = Query(default=False),
):
    """Walk-forward replay of the live setup detector over real historical candles."""
    symbol = symbol.upper()
    tf = _canonical_timeframe(timeframe)
    market_eff = _auto_market(symbol, None if market == "auto" else market)
    cache_key = f"{symbol}|{tf}|{candles}"
    now = _time.time()
    cached = _PRIME_BT_CACHE.get(cache_key)
    if cached and now - cached[0] < 600 and not force:
        return {**cached[1], "cached": True, "cache_age_seconds": round(now - cached[0], 1)}
    if cached and force and now - cached[0] < 60:
        # same anti-hammer cooldown as /setups/scan: force refreshes at most once a minute
        return {**cached[1], "cached": True, "cache_age_seconds": round(now - cached[0], 1), "refresh_cooldown": True}

    items: list[dict] = []
    source = "none"
    if market_eff == "crypto":
        try:
            items = await prime_backtest_service.fetch_okx_deep_candles(symbol, tf, candles)
            source = "okx_history_candles"
        except Exception:
            items = []
    if len(items) < 160:
        try:
            raw = await fetch_live_candles(symbol, market_eff, tf)
            fallback = _norm_candles(raw)[-candles:]
            if len(fallback) > len(items):
                items = fallback
                source = "live_cache_260" if market_eff == "crypto" else "provider_live"
        except Exception:
            pass
    if len(items) < 160:
        return {
            "ok": False,
            "detail": "داده تاریخی کافی برای بک‌تست در دسترس نیست.",
            "candles": len(items),
            "required": 160,
        }

    result = await prime_backtest_service.run_async(items, symbol=symbol, timeframe=tf)
    result["data_source"] = source
    if result.get("ok"):
        _PRIME_BT_CACHE[cache_key] = (_time.time(), result)
    return result


@app.get("/api/v1/backtest/strategies")
async def backtest_classic_strategies(
    symbol: str = Query("BTCUSDT", min_length=2, max_length=24),
    timeframe: str = Query("15m"),
    market: str = Query(default="auto", pattern="^(auto|crypto|forex)$"),
    candles: int = Query(default=1000, ge=300, le=2000),
    min_quality: int = Query(default=55, ge=0, le=100),
    force: bool = Query(default=False),
):
    """Walk-forward replay of the 34-strategy classic pack over real history (raw pack — audit view).

    Answers the calibration question with data: does quality>=65 actually win
    more? Per-strategy books, conservative fills, honest small-sample verdicts.
    """
    symbol = symbol.upper()
    tf = _canonical_timeframe(timeframe)
    market_eff = _auto_market(symbol, None if market == "auto" else market)
    cache_key = f"{symbol}|{tf}|{candles}|{min_quality}"
    now = _time.time()
    cached = _STRATEGY_BT_CACHE.get(cache_key)
    if cached and now - cached[0] < 600 and not force:
        return {**cached[1], "cached": True, "cache_age_seconds": round(now - cached[0], 1)}
    if cached and force and now - cached[0] < 60:
        return {**cached[1], "cached": True, "cache_age_seconds": round(now - cached[0], 1), "refresh_cooldown": True}

    items: list[dict] = []
    source = "none"
    if market_eff == "crypto":
        try:
            items = await prime_backtest_service.fetch_okx_deep_candles(symbol, tf, candles)
            source = "okx_history_candles"
        except Exception:
            items = []
    if len(items) < 220:
        try:
            raw = await fetch_live_candles(symbol, market_eff, tf)
            fallback = _norm_candles(raw)[-candles:]
            if len(fallback) > len(items):
                items = fallback
                source = "live_cache_260" if market_eff == "crypto" else "provider_live"
        except Exception:
            pass
    if len(items) < 220:
        return {
            "ok": False,
            "detail": "داده تاریخی کافی برای بک‌تست استراتژی‌ها در دسترس نیست (حداقل ۲۲۰ کندل).",
            "candles": len(items),
            "required": 220,
        }

    result = await strategy_backtest_service.run_async(
        items, symbol=symbol, timeframe=tf, min_quality=min_quality
    )
    result["data_source"] = source
    if result.get("ok"):
        _STRATEGY_BT_CACHE[cache_key] = (_time.time(), result)
    return result


@app.websocket("/ws/market")
async def market_websocket(
    websocket: WebSocket,
    symbol: str = "BTCUSDT",
    market: str = "crypto",
    timeframe: str = "15m",
    alerts: bool = False,  # opt-in: older app builds must keep receiving snapshots only
):
    await websocket.accept()
    alert_state = proximity_alert_service.ProximityAlertState()
    tick = 0
    try:
        while True:
            snapshot = await fetch_live_snapshot(symbol=symbol.upper(), market=market)
            await websocket.send_json(snapshot.model_dump())
            tick += 1
            if alerts and tick % 5 == 0:
                try:
                    evaluation = await _evaluate_proximity(
                        symbol.upper(),
                        market,
                        timeframe,
                        price=float(snapshot.last_price or 0) or None,
                    )
                    new_alerts = alert_state.filter_new(symbol.upper(), evaluation.get("rows") or [])
                    if new_alerts:
                        await websocket.send_json({
                            "type": "proximity_alert",
                            "symbol": symbol.upper(),
                            "market": market,
                            "timeframe": timeframe,
                            "price": evaluation.get("price"),
                            "ts": int(_time.time()),
                            "alerts": [
                                {**row, "message_fa": proximity_alert_service.message_fa(symbol.upper(), row)}
                                for row in new_alerts
                            ],
                        })
                except Exception:
                    pass
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
