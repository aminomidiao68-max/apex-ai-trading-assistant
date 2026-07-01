from __future__ import annotations

import httpx

from app.config import settings
from app.models import ConnectorStatus, OandaOrderRequest


class OandaConnector:
    def status(self) -> ConnectorStatus:
        ready = bool(settings.oanda_api_token and settings.oanda_account_id)
        mode = "live-enabled" if settings.enable_live_execution else "dry-run"
        notes = [f"base_url={settings.oanda_base_url}"]
        if not ready:
            notes.append("Missing OANDA token/account id")
        if not settings.enable_live_execution:
            notes.append("ENABLE_LIVE_EXECUTION=false so real order placement is blocked")
        return ConnectorStatus(connector="oanda", ready=ready, mode=mode, notes=notes)

    async def place_order(self, request: OandaOrderRequest) -> dict:
        if not settings.enable_live_execution:
            return {"ok": False, "mode": "dry-run", "reason": "Live execution is disabled"}
        if not settings.oanda_api_token or not settings.oanda_account_id:
            return {"ok": False, "reason": "Missing OANDA credentials"}

        order = {
            "type": "MARKET",
            "instrument": request.instrument.upper(),
            "units": str(request.units),
            "timeInForce": "FOK",
            "positionFill": "DEFAULT",
        }
        if request.stop_loss_price is not None:
            order["stopLossOnFill"] = {"price": f"{request.stop_loss_price:.5f}"}
        if request.take_profit_price is not None:
            order["takeProfitOnFill"] = {"price": f"{request.take_profit_price:.5f}"}

        headers = {
            "Authorization": f"Bearer {settings.oanda_api_token}",
            "Content-Type": "application/json",
        }
        url = f"{settings.oanda_base_url}/v3/accounts/{settings.oanda_account_id}/orders"

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json={"order": order})
            return {
                "ok": response.is_success,
                "status_code": response.status_code,
                "exchange": "oanda",
                "payload": response.json(),
            }
