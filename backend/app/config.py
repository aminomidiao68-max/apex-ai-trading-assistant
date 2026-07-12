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
    app_version: str = os.getenv("APP_VERSION", "2.1.9")
    default_timezone: str = os.getenv("DEFAULT_TIMEZONE", "UTC")

    # Browser CORS is disabled by default in production. Native Android clients
    # do not need CORS. Configure a comma-separated allowlist for web clients.
    cors_allowed_origins: list[str] = _csv(os.getenv("CORS_ALLOWED_ORIGINS"))

    twelve_data_api_key: str = os.getenv("TWELVEDATA_API_KEY", "")
    finnhub_api_key: str = os.getenv("FINNHUB_API_KEY", "")

    enable_live_execution: bool = _to_bool(os.getenv("ENABLE_LIVE_EXECUTION"), False)
    seed_demo_user: bool = _to_bool(
        os.getenv("SEED_DEMO_USER"),
        default=os.getenv("APP_ENV", "development").lower() != "production",
    )

    database_path: str = os.getenv("DATABASE_PATH", "")
    session_ttl_hours: int = int(os.getenv("SESSION_TTL_HOURS", "168"))

    binance_api_key: str = os.getenv("BINANCE_API_KEY", "")
    binance_api_secret: str = os.getenv("BINANCE_API_SECRET", "")
    binance_futures_base_url: str = os.getenv(
        "BINANCE_FUTURES_BASE_URL", "https://testnet.binancefuture.com"
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
