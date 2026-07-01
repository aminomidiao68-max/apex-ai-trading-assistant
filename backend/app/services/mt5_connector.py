from __future__ import annotations

from app.config import settings
from app.models import ConnectorStatus, Mt5OrderRequest


class Mt5Connector:
    def status(self) -> ConnectorStatus:
        ready = bool(settings.mt5_server and settings.mt5_login and settings.mt5_password)
        mode = "live-enabled" if settings.enable_live_execution else "dry-run"
        notes = ["MetaTrader 5 bridge foundation only"]
        if settings.mt5_server:
            notes.append(f"server={settings.mt5_server}")
        if not ready:
            notes.append("Missing MT5 bridge credentials/configuration")
        if not settings.enable_live_execution:
            notes.append("ENABLE_LIVE_EXECUTION=false so real order placement is blocked")
        notes.append("Next phase: integrate MetaAPI or local MT5 bridge execution")
        return ConnectorStatus(connector="mt5", ready=ready, mode=mode, notes=notes)

    async def place_order(self, request: Mt5OrderRequest) -> dict:
        return {
            "ok": False,
            "mode": "foundation-only",
            "exchange": "mt5",
            "reason": "MT5 order routing needs MetaAPI or a local MT5 bridge before live execution",
            "request": request.model_dump(),
        }
