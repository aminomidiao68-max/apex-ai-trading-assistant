from __future__ import annotations

import os

from pydantic import BaseModel


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip().rstrip("/") for item in value.split(",") if item.strip()]


class Settings(BaseModel):
    app_name: str = os.getenv("APP_NAME", "Arena Smart Money AI Trader API")
    app_env: str = os.getenv("APP_ENV", "development")
    app_version: str = os.getenv("APP_VERSION", "3.7.0-signal-alpha18")
    default_timezone: str = os.getenv("DEFAULT_TIMEZONE", "UTC")

    # Browser CORS is disabled by default in production. Native Android clients
    # do not need CORS. Configure a comma-separated allowlist for web clients.
    cors_allowed_origins: list[str] = _csv(os.getenv("CORS_ALLOWED_ORIGINS"))

    twelve_data_api_key: str = os.getenv("TWELVEDATA_API_KEY", "")
    finnhub_api_key: str = os.getenv("FINNHUB_API_KEY", "")

    # External AI is opt-in. The deterministic evidence explainer is always
    # available and remains the default decision-safe provider.
    ai_provider: str = os.getenv("AI_PROVIDER", "deterministic").strip().lower()
    ai_external_enabled: bool = _to_bool(os.getenv("AI_EXTERNAL_ENABLED"), False)
    ai_openai_base_url: str = os.getenv("AI_OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    ai_openai_api_key: str = os.getenv("AI_OPENAI_API_KEY", "")
    ai_openai_model: str = os.getenv("AI_OPENAI_MODEL", "gpt-4.1-mini")
    ai_gemini_base_url: str = os.getenv(
        "AI_GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"
    ).rstrip("/")
    ai_gemini_api_key: str = os.getenv("AI_GEMINI_API_KEY", "")
    ai_gemini_model: str = os.getenv("AI_GEMINI_MODEL", "gemini-2.5-flash")
    ai_timeout_seconds: float = float(os.getenv("AI_TIMEOUT_SECONDS", "8"))
    ai_cache_ttl_seconds: int = int(os.getenv("AI_CACHE_TTL_SECONDS", "90"))
    ai_circuit_failure_threshold: int = int(os.getenv("AI_CIRCUIT_FAILURE_THRESHOLD", "3"))
    ai_circuit_cooldown_seconds: int = int(os.getenv("AI_CIRCUIT_COOLDOWN_SECONDS", "120"))

    enable_live_execution: bool = _to_bool(os.getenv("ENABLE_LIVE_EXECUTION"), False)
    enable_testnet_execution: bool = _to_bool(os.getenv("ENABLE_TESTNET_EXECUTION"), False)
    paper_chaos_enabled: bool = _to_bool(os.getenv("PAPER_CHAOS_ENABLED"), False)
    signal_shadow_worker_enabled: bool = _to_bool(os.getenv("SIGNAL_SHADOW_WORKER_ENABLED"), False)
    signal_shadow_interval_seconds: int = int(os.getenv("SIGNAL_SHADOW_INTERVAL_SECONDS", "900"))
    signal_shadow_symbols: list[str] = _csv(
        os.getenv("SIGNAL_SHADOW_SYMBOLS", "BTCUSDT,ETHUSDT,XRPUSDT,XAUUSD,EURUSD,GBPUSD,USDJPY,NAS100,US30")
    )
    signal_shadow_cron_token: str = os.getenv("SIGNAL_SHADOW_CRON_TOKEN", "").strip()
    paper_feed_worker_enabled: bool = _to_bool(os.getenv("PAPER_FEED_WORKER_ENABLED"), True)
    paper_feed_worker_sweep_seconds: float = float(
        os.getenv("PAPER_FEED_WORKER_SWEEP_SECONDS", "2")
    )
    paper_feed_worker_batch_size: int = int(os.getenv("PAPER_FEED_WORKER_BATCH_SIZE", "20"))
    paper_feed_provider_timeout_seconds: float = float(
        os.getenv("PAPER_FEED_PROVIDER_TIMEOUT_SECONDS", "8")
    )
    seed_demo_user: bool = _to_bool(
        os.getenv("SEED_DEMO_USER"),
        default=os.getenv("APP_ENV", "development").lower() != "production",
    )

    database_url: str = os.getenv("DATABASE_URL", "").strip()
    database_path: str = os.getenv("DATABASE_PATH", "")
    database_pool_max_size: int = int(os.getenv("DATABASE_POOL_MAX_SIZE", "8"))
    database_connect_timeout_seconds: float = float(
        os.getenv("DATABASE_CONNECT_TIMEOUT_SECONDS", "8")
    )
    backup_retention_days: int = int(os.getenv("BACKUP_RETENTION_DAYS", "14"))
    user_secret_master_key: str = os.getenv("USER_SECRET_MASTER_KEY", "").strip()
    user_secret_key_version: int = int(os.getenv("USER_SECRET_KEY_VERSION", "1"))
    session_ttl_hours: int = int(os.getenv("SESSION_TTL_HOURS", "168"))

    rate_limit_enabled: bool = _to_bool(os.getenv("RATE_LIMIT_ENABLED"), True)
    rate_limit_default_per_minute: int = int(os.getenv("RATE_LIMIT_DEFAULT_PER_MINUTE", "120"))
    rate_limit_auth_per_minute: int = int(os.getenv("RATE_LIMIT_AUTH_PER_MINUTE", "10"))
    rate_limit_ai_per_minute: int = int(os.getenv("RATE_LIMIT_AI_PER_MINUTE", "20"))
    rate_limit_heavy_per_minute: int = int(os.getenv("RATE_LIMIT_HEAVY_PER_MINUTE", "15"))
    trust_proxy_headers: bool = _to_bool(os.getenv("TRUST_PROXY_HEADERS"), False)
    max_request_body_bytes: int = int(os.getenv("MAX_REQUEST_BODY_BYTES", "2097152"))

    binance_api_key: str = os.getenv("BINANCE_API_KEY", "")
    binance_api_secret: str = os.getenv("BINANCE_API_SECRET", "")
    binance_futures_base_url: str = os.getenv(
        "BINANCE_FUTURES_BASE_URL", "https://demo-fapi.binance.com"
    )

    bybit_api_key: str = os.getenv("BYBIT_API_KEY", "")
    bybit_api_secret: str = os.getenv("BYBIT_API_SECRET", "")
    bybit_base_url: str = os.getenv("BYBIT_BASE_URL", "https://api.bybit.com")

    oanda_api_token: str = os.getenv("OANDA_API_TOKEN", "")
    oanda_account_id: str = os.getenv("OANDA_ACCOUNT_ID", "")
    oanda_base_url: str = os.getenv("OANDA_BASE_URL", "https://api-fxpractice.oanda.com")

    mt5_server: str = os.getenv("MT5_SERVER", "")
    mt5_login: str = os.getenv("MT5_LOGIN", "")
    mt5_password: str = os.getenv("MT5_PASSWORD", "")

    ctrader_client_id: str = os.getenv("CTRADER_CLIENT_ID", "")
    ctrader_client_secret: str = os.getenv("CTRADER_CLIENT_SECRET", "")
    ctrader_access_token: str = os.getenv("CTRADER_ACCESS_TOKEN", "")
    ctrader_base_url: str = os.getenv("CTRADER_BASE_URL", "https://demo.ctraderapi.com")

    firebase_project_id: str = os.getenv("FIREBASE_PROJECT_ID", "")
    firebase_service_account_json: str = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")


settings = Settings()
