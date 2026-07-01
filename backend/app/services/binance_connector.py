from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import urlencode

import httpx

from app.config import settings
from app.models import BinanceFuturesOrderRequest, ConnectorStatus


class BinanceFuturesConnector:
    def status(self) -> ConnectorStatus:
        ready = bool(settings.binance_api_key and settings.binance_api_secret)
        mode = "live-enabled" if settings.enable_live_execution else "dry-run"
        notes = [f"base_url={settings.binance_futures_base_url}"]
        if not ready:
            notes.append("Missing Binance API credentials")
        if not settings.enable_live_execution:
            notes.append("ENABLE_LIVE_EXECUTION=false so real order placement is blocked")
        return ConnectorStatus(connector="binance_futures", ready=ready, mode=mode, notes=notes)

    async def place_order(self, request: BinanceFuturesOrderRequest) -> dict:
        if not settings.enable_live_execution:
            return {"ok": False, "mode": "dry-run", "reason": "Live execution is disabled"}
        if not settings.binance_api_key or not settings.binance_api_secret:
            return {"ok": False, "reason": "Missing Binance credentials"}

        params = {
            "symbol": request.symbol.upper(),
            "side": request.side.upper(),
            "type": request.order_type,
            "quantity": request.quantity,
            "reduceOnly": str(request.reduce_only).lower(),
            "timestamp": int(time.time() * 1000),
        }
        query_string = urlencode(params)
        signature = hmac.new(
            settings.binance_api_secret.encode(),
            query_string.encode(),
            hashlib.sha256,
        ).hexdigest()

        headers = {"X-MBX-APIKEY": settings.binance_api_key}
        url = f"{settings.binance_futures_base_url}/fapi/v1/order"

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                url,
                params={**params, "signature": signature},
                headers=headers,
            )
            return {
                "ok": response.is_success,
                "status_code": response.status_code,
                "exchange": "binance_futures",
                "payload": response.json(),
            }
