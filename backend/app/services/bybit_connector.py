from __future__ import annotations

import hashlib
import hmac
import json
import time

import httpx

from app.config import settings
from app.models import BybitOrderRequest, ConnectorStatus


class BybitConnector:
    def status(self) -> ConnectorStatus:
        ready = bool(settings.bybit_api_key and settings.bybit_api_secret)
        mode = "live-enabled" if settings.enable_live_execution else "dry-run"
        notes = [f"base_url={settings.bybit_base_url}"]
        if not ready:
            notes.append("Missing Bybit API credentials")
        if not settings.enable_live_execution:
            notes.append("ENABLE_LIVE_EXECUTION=false so real order placement is blocked")
        notes.append("Uses Bybit V5 order create endpoint when enabled")
        return ConnectorStatus(connector="bybit", ready=ready, mode=mode, notes=notes)

    async def place_order(self, request: BybitOrderRequest) -> dict:
        if not settings.enable_live_execution:
            return {"ok": False, "mode": "dry-run", "reason": "Live execution is disabled"}
        if not settings.bybit_api_key or not settings.bybit_api_secret:
            return {"ok": False, "reason": "Missing Bybit credentials"}

        payload = {
            "category": request.category,
            "symbol": request.symbol.upper(),
            "side": request.side,
            "orderType": request.order_type,
            "qty": str(request.quantity),
            "reduceOnly": request.reduce_only,
        }
        body = json.dumps(payload, separators=(",", ":"))
        timestamp = str(int(time.time() * 1000))
        recv_window = "5000"
        raw = f"{timestamp}{settings.bybit_api_key}{recv_window}{body}"
        signature = hmac.new(
            settings.bybit_api_secret.encode(),
            raw.encode(),
            hashlib.sha256,
        ).hexdigest()

        headers = {
            "X-BAPI-API-KEY": settings.bybit_api_key,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-RECV-WINDOW": recv_window,
            "X-BAPI-SIGN": signature,
            "Content-Type": "application/json",
        }
        url = f"{settings.bybit_base_url}/v5/order/create"
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, content=body)
            return {
                "ok": response.is_success,
                "status_code": response.status_code,
                "exchange": "bybit",
                "payload": response.json(),
            }
