from __future__ import annotations

from app.config import settings
from app.models import CTraderOrderRequest, ConnectorStatus


class CTraderConnector:
    def status(self) -> ConnectorStatus:
        ready = bool(
            settings.ctrader_client_id
            and settings.ctrader_client_secret
            and settings.ctrader_access_token
        )
        mode = "live-enabled" if settings.enable_live_execution else "dry-run"
        notes = [f"base_url={settings.ctrader_base_url}", "cTrader Open API foundation only"]
        if not ready:
            notes.append("Missing cTrader credentials/token")
        if not settings.enable_live_execution:
            notes.append("ENABLE_LIVE_EXECUTION=false so real order placement is blocked")
        notes.append("Next phase: map broker symbols and implement order routing")
        return ConnectorStatus(connector="ctrader", ready=ready, mode=mode, notes=notes)

    async def place_order(self, request: CTraderOrderRequest) -> dict:
        return {
            "ok": False,
            "mode": "foundation-only",
            "exchange": "ctrader",
            "reason": "cTrader order routing requires full Open API session and account mapping",
            "request": request.model_dump(),
        }
