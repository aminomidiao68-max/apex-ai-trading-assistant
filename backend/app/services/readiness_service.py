from __future__ import annotations

from pathlib import Path

from app.config import settings
from app.models import ReadinessItem, SystemReadinessResponse
from app.services.database_service import DatabaseManager


class ReadinessService:
    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def build(self) -> SystemReadinessResponse:
        items: list[ReadinessItem] = []

        items.append(self._app_env_check())
        items.append(self._firebase_project_check())
        items.append(self._firebase_service_account_check())
        items.append(self._twelvedata_check())
        items.append(self._finnhub_check())
        items.append(self._ai_provider_check())
        items.append(self._database_persistence_check())
        items.append(self._backup_policy_check())
        items.append(self._rate_limit_check())
        items.append(self._live_execution_check())
        items.extend(self._connector_checks())

        ready_count = sum(1 for item in items if item.status == "ready")
        warning_count = sum(1 for item in items if item.status == "warning")
        missing_count = sum(1 for item in items if item.status == "missing")

        if missing_count == 0 and warning_count == 0:
            overall = "ready"
        elif missing_count == 0:
            overall = "partial"
        else:
            overall = "blocked"

        return SystemReadinessResponse(
            overall_status=overall,
            ready_count=ready_count,
            warning_count=warning_count,
            missing_count=missing_count,
            items=items,
        )

    def _app_env_check(self) -> ReadinessItem:
        if settings.app_env.lower() == "production":
            return ReadinessItem(category="system", key="APP_ENV", status="ready", message="Application is configured for production mode")
        return ReadinessItem(category="system", key="APP_ENV", status="warning", message=f"Current environment is '{settings.app_env}', not production")

    def _firebase_project_check(self) -> ReadinessItem:
        if settings.firebase_project_id:
            return ReadinessItem(category="firebase", key="FIREBASE_PROJECT_ID", status="ready", message="Firebase project id is configured")
        return ReadinessItem(category="firebase", key="FIREBASE_PROJECT_ID", status="missing", message="Firebase project id is missing")

    def _firebase_service_account_check(self) -> ReadinessItem:
        raw_value = settings.firebase_service_account_json.strip()
        if not raw_value:
            return ReadinessItem(category="firebase", key="FIREBASE_SERVICE_ACCOUNT_JSON", status="missing", message="Firebase service account is missing")
        if raw_value.startswith("{") and '"project_id"' in raw_value and '"private_key"' in raw_value:
            return ReadinessItem(category="firebase", key="FIREBASE_SERVICE_ACCOUNT_JSON", status="ready", message="Firebase service account JSON is configured via environment variable")
        service_path = Path(raw_value)
        if service_path.exists() and service_path.is_file():
            return ReadinessItem(category="firebase", key="FIREBASE_SERVICE_ACCOUNT_JSON", status="ready", message="Firebase service account file exists")
        return ReadinessItem(category="firebase", key="FIREBASE_SERVICE_ACCOUNT_JSON", status="missing", message="Firebase service account path does not exist on this server")

    def _twelvedata_check(self) -> ReadinessItem:
        if settings.twelve_data_api_key:
            return ReadinessItem(category="data", key="TWELVEDATA_API_KEY", status="ready", message="Forex and gold data provider key is configured")
        return ReadinessItem(category="data", key="TWELVEDATA_API_KEY", status="warning", message="Forex live scan will stay limited until TwelveData API key is configured")

    def _finnhub_check(self) -> ReadinessItem:
        if settings.finnhub_api_key:
            return ReadinessItem(
                category="news",
                key="FINNHUB_API_KEY",
                status="ready",
                message="Finnhub news provider is configured",
            )
        return ReadinessItem(
            category="news",
            key="FINNHUB_API_KEY",
            status="warning",
            message="Finnhub is not configured; the offline news fallback will be used",
        )

    def _ai_provider_check(self) -> ReadinessItem:
        provider = settings.ai_provider
        if not settings.ai_external_enabled or provider == "deterministic":
            return ReadinessItem(
                category="ai",
                key="AI_PROVIDER",
                status="ready",
                message="Deterministic evidence explainer is active; external AI is optional and cannot override decisions",
            )
        configured = (
            provider == "openai_compatible"
            and bool(settings.ai_openai_api_key and settings.ai_openai_model)
        ) or (
            provider == "gemini"
            and bool(settings.ai_gemini_api_key and settings.ai_gemini_model)
        )
        if configured:
            return ReadinessItem(
                category="ai",
                key="AI_PROVIDER",
                status="ready",
                message=f"External {provider} explainer is configured with deterministic fallback and verification",
            )
        return ReadinessItem(
            category="ai",
            key="AI_PROVIDER",
            status="warning",
            message="Selected external AI provider is not configured; deterministic verified fallback remains active",
        )

    def _database_persistence_check(self) -> ReadinessItem:
        health = self.database.health()
        if not health["connected"] or not health["migration_current"]:
            return ReadinessItem(
                category="database",
                key="DATABASE_URL",
                status="missing",
                message="Database is unavailable or schema migration is not current",
            )
        if health["backend"] == "postgresql" and health["persistent"]:
            return ReadinessItem(
                category="database",
                key="DATABASE_URL",
                status="ready",
                message="PostgreSQL persistence is connected and schema migration is current",
            )
        status = "missing" if settings.app_env.lower() == "production" else "warning"
        return ReadinessItem(
            category="database",
            key="DATABASE_URL",
            status=status,
            message="SQLite is available for local/test use; PostgreSQL is required for production RC",
        )

    def _backup_policy_check(self) -> ReadinessItem:
        if self.database.backend == "postgresql":
            return ReadinessItem(
                category="database",
                key="BACKUP_POLICY",
                status="ready",
                message=f"PostgreSQL pg_dump/restore runbook configured with {settings.backup_retention_days}-day retention",
            )
        return ReadinessItem(
            category="database",
            key="BACKUP_POLICY",
            status="warning",
            message="SQLite online backup is available; production requires PostgreSQL backup automation",
        )

    def _rate_limit_check(self) -> ReadinessItem:
        if settings.rate_limit_enabled:
            return ReadinessItem(
                category="security",
                key="RATE_LIMIT_ENABLED",
                status="ready",
                message="Auth, AI, heavy and default sliding-window rate-limit policies are enabled",
            )
        return ReadinessItem(
            category="security",
            key="RATE_LIMIT_ENABLED",
            status="warning",
            message="Rate limiting is disabled",
        )

    def _live_execution_check(self) -> ReadinessItem:
        if settings.enable_live_execution:
            return ReadinessItem(category="execution", key="ENABLE_LIVE_EXECUTION", status="warning", message="Live execution is enabled; use only after full demo/testnet validation")
        return ReadinessItem(category="execution", key="ENABLE_LIVE_EXECUTION", status="ready", message="Live execution is currently disabled, which is the safer state before final activation")

    def _connector_checks(self) -> list[ReadinessItem]:
        items: list[ReadinessItem] = []
        # Broker credentials are optional while the global live-execution switch
        # is off. Treat them as warnings instead of blocking unrelated market,
        # analysis, journal and backtest features.
        inactive_status = "missing" if settings.enable_live_execution else "warning"
        optional_suffix = "" if settings.enable_live_execution else " (optional while live execution is disabled)"
        items.append(
            ReadinessItem(
                category="connector",
                key="BINANCE_FUTURES",
                status="ready" if (settings.binance_api_key and settings.binance_api_secret) else inactive_status,
                message="Binance Futures credentials configured" if (settings.binance_api_key and settings.binance_api_secret) else "Binance Futures credentials are not configured" + optional_suffix,
            )
        )
        items.append(
            ReadinessItem(
                category="connector",
                key="BYBIT",
                status="ready" if (settings.bybit_api_key and settings.bybit_api_secret) else inactive_status,
                message="Bybit credentials configured" if (settings.bybit_api_key and settings.bybit_api_secret) else "Bybit credentials are not configured" + optional_suffix,
            )
        )
        items.append(
            ReadinessItem(
                category="connector",
                key="OANDA",
                status="ready" if (settings.oanda_api_token and settings.oanda_account_id) else inactive_status,
                message="OANDA credentials configured" if (settings.oanda_api_token and settings.oanda_account_id) else "OANDA credentials are not configured" + optional_suffix,
            )
        )
        items.append(
            ReadinessItem(
                category="connector",
                key="MT5",
                status="warning" if (settings.mt5_server and settings.mt5_login and settings.mt5_password) else inactive_status,
                message="MT5 credentials exist but bridge integration is still required" if (settings.mt5_server and settings.mt5_login and settings.mt5_password) else "MT5 credentials/bridge are not configured" + optional_suffix,
            )
        )
        items.append(
            ReadinessItem(
                category="connector",
                key="CTRADER",
                status="warning" if (settings.ctrader_client_id and settings.ctrader_access_token) else inactive_status,
                message="cTrader credentials exist but full routing/session integration is still required" if (settings.ctrader_client_id and settings.ctrader_access_token) else "cTrader credentials/session are not configured" + optional_suffix,
            )
        )
        return items

