from __future__ import annotations

from pathlib import Path

from app.config import settings
from app.models import ReadinessItem, SystemReadinessResponse


class ReadinessService:
    def build(self) -> SystemReadinessResponse:
        items: list[ReadinessItem] = []

        items.append(self._app_env_check())
        items.append(self._firebase_project_check())
        items.append(self._firebase_service_account_check())
        items.append(self._twelvedata_check())
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
        if not settings.firebase_service_account_json:
            return ReadinessItem(category="firebase", key="FIREBASE_SERVICE_ACCOUNT_JSON", status="missing", message="Firebase service account path is missing")
        service_path = Path(settings.firebase_service_account_json)
        if service_path.exists() and service_path.is_file():
            return ReadinessItem(category="firebase", key="FIREBASE_SERVICE_ACCOUNT_JSON", status="ready", message="Firebase service account file exists")
        return ReadinessItem(category="firebase", key="FIREBASE_SERVICE_ACCOUNT_JSON", status="missing", message="Firebase service account path does not exist on this server")

    def _twelvedata_check(self) -> ReadinessItem:
        if settings.twelve_data_api_key:
            return ReadinessItem(category="data", key="TWELVEDATA_API_KEY", status="ready", message="Forex and gold data provider key is configured")
        return ReadinessItem(category="data", key="TWELVEDATA_API_KEY", status="warning", message="Forex live scan will stay limited until TwelveData API key is configured")

    def _live_execution_check(self) -> ReadinessItem:
        if settings.enable_live_execution:
            return ReadinessItem(category="execution", key="ENABLE_LIVE_EXECUTION", status="warning", message="Live execution is enabled; use only after full demo/testnet validation")
        return ReadinessItem(category="execution", key="ENABLE_LIVE_EXECUTION", status="ready", message="Live execution is currently disabled, which is the safer state before final activation")

    def _connector_checks(self) -> list[ReadinessItem]:
        items: list[ReadinessItem] = []
        items.append(
            ReadinessItem(
                category="connector",
                key="BINANCE_FUTURES",
                status="ready" if (settings.binance_api_key and settings.binance_api_secret) else "missing",
                message="Binance Futures credentials configured" if (settings.binance_api_key and settings.binance_api_secret) else "Binance Futures credentials are missing",
            )
        )
        items.append(
            ReadinessItem(
                category="connector",
                key="BYBIT",
                status="ready" if (settings.bybit_api_key and settings.bybit_api_secret) else "missing",
                message="Bybit credentials configured" if (settings.bybit_api_key and settings.bybit_api_secret) else "Bybit credentials are missing",
            )
        )
        items.append(
            ReadinessItem(
                category="connector",
                key="OANDA",
                status="ready" if (settings.oanda_api_token and settings.oanda_account_id) else "missing",
                message="OANDA credentials configured" if (settings.oanda_api_token and settings.oanda_account_id) else "OANDA credentials are missing",
            )
        )
        items.append(
            ReadinessItem(
                category="connector",
                key="MT5",
                status="warning" if (settings.mt5_server and settings.mt5_login and settings.mt5_password) else "missing",
                message="MT5 credentials exist but bridge integration is still required" if (settings.mt5_server and settings.mt5_login and settings.mt5_password) else "MT5 credentials/bridge setup are missing",
            )
        )
        items.append(
            ReadinessItem(
                category="connector",
                key="CTRADER",
                status="warning" if (settings.ctrader_client_id and settings.ctrader_access_token) else "missing",
                message="cTrader credentials exist but full routing/session integration is still required" if (settings.ctrader_client_id and settings.ctrader_access_token) else "cTrader credentials/session setup are missing",
            )
        )
        return items
