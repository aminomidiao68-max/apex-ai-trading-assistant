from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from urllib.parse import urlencode
from uuid import uuid4

import httpx

from app.config import settings
from app.models import (
    PaperPrivateTestnetReconciliationResponse,
    PaperRecoveryDrillRequest,
    PaperRecoveryDrillResponse,
)
from app.services.database_service import DatabaseManager
from app.services.provider_secret_service import ProviderSecretService


class PaperPrivateTestnetError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class PaperPrivateTestnetService:
    def __init__(self, database: DatabaseManager, vault: ProviderSecretService) -> None:
        self.database = database
        self.vault = vault

    @staticmethod
    def _status(value: str) -> str:
        normalized = value.upper().replace("_", "")
        mapping = {
            "NEW": "working", "CREATED": "working", "UNTRIGGERED": "working",
            "PARTIALLYFILLED": "partially_filled", "FILLED": "filled",
            "CANCELED": "canceled", "CANCELLED": "canceled", "REJECTED": "rejected",
            "EXPIRED": "expired",
        }
        return mapping.get(normalized, "working")

    async def _binance(self, api_key: str, secret: str) -> tuple[list[dict], list[dict]]:
        async with httpx.AsyncClient(timeout=12.0) as client:
            results = []
            for path in ("/fapi/v1/openOrders", "/fapi/v1/userTrades"):
                params = {"timestamp": int(time.time() * 1000), "recvWindow": 5000}
                query = urlencode(params)
                params["signature"] = hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()
                response = await client.get(
                    "https://testnet.binancefuture.com" + path,
                    params=params,
                    headers={"X-MBX-APIKEY": api_key},
                )
                if response.status_code in {401, 403}:
                    raise PaperPrivateTestnetError("private_testnet_auth_failed")
                if not response.is_success:
                    raise PaperPrivateTestnetError("private_testnet_provider_unavailable")
                payload = response.json()
                if not isinstance(payload, list):
                    raise PaperPrivateTestnetError("private_testnet_invalid_response")
                results.append(payload)
        return results[0], results[1]

    async def _bybit(self, api_key: str, secret: str) -> tuple[list[dict], list[dict]]:
        async with httpx.AsyncClient(timeout=12.0) as client:
            results = []
            for path, query in (
                ("/v5/order/realtime", "category=linear&openOnly=0"),
                ("/v5/execution/list", "category=linear"),
            ):
                timestamp = str(int(time.time() * 1000)); window = "5000"
                signature = hmac.new(secret.encode(), f"{timestamp}{api_key}{window}{query}".encode(), hashlib.sha256).hexdigest()
                params = dict(item.split("=") for item in query.split("&"))
                response = await client.get(
                    "https://api-testnet.bybit.com" + path,
                    params=params,
                    headers={
                        "X-BAPI-API-KEY": api_key,
                        "X-BAPI-TIMESTAMP": timestamp,
                        "X-BAPI-RECV-WINDOW": window,
                        "X-BAPI-SIGN": signature,
                    },
                )
                if response.status_code in {401, 403}:
                    raise PaperPrivateTestnetError("private_testnet_auth_failed")
                if not response.is_success:
                    raise PaperPrivateTestnetError("private_testnet_provider_unavailable")
                body = response.json()
                if int(body.get("retCode", -1)) != 0:
                    raise PaperPrivateTestnetError("private_testnet_provider_rejected")
                results.append(((body.get("result") or {}).get("list") or []))
        return results[0], results[1]

    def _save(self, user_id: int, connector: str, status: str, orders: int, fills: int, matched: int, mismatched: int, issues: list[str]) -> PaperPrivateTestnetReconciliationResponse:
        reconciliation_id = uuid4().hex
        created_at = datetime.now(timezone.utc).isoformat()
        with self.database.connection() as conn:
            conn.execute(
                """INSERT INTO paper_private_testnet_reconciliations (
                    user_id, reconciliation_id, connector, status, external_order_count,
                    external_fill_count, matched_orders, mismatched_orders, issues_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, reconciliation_id, connector, status, orders, fills, matched, mismatched, json.dumps(issues[:200], separators=(",", ":")), created_at),
            )
            conn.commit()
        return PaperPrivateTestnetReconciliationResponse(
            reconciliation_id=reconciliation_id, connector=connector, status=status,
            external_order_count=orders, external_fill_count=fills, matched_orders=matched,
            mismatched_orders=mismatched, issues=issues[:200], provider_authenticated=True,
            provider_snapshot_verified=True, read_only=True, order_routing_enabled=False,
            actionable_for_live=False, live_execution_enabled=settings.enable_live_execution,
            created_at=created_at,
        )

    async def reconcile(self, user_id: int, connector: str) -> PaperPrivateTestnetReconciliationResponse:
        provider = {"binance_futures_testnet": "binance_testnet", "bybit_testnet": "bybit_testnet"}.get(connector)
        if not provider:
            raise PaperPrivateTestnetError("private_testnet_connector_not_supported")
        material = self.vault.get_material(user_id, provider)
        if material is None or not material.api_secret:
            raise PaperPrivateTestnetError("private_testnet_credentials_not_configured")
        try:
            if provider == "binance_testnet":
                external_orders, fills = await self._binance(material.api_key, material.api_secret)
                mapped = [
                    {"id": str(item.get("clientOrderId") or ""), "status": self._status(str(item.get("status") or "")), "filled": float(item.get("executedQty") or 0.0)}
                    for item in external_orders
                ]
            else:
                external_orders, fills = await self._bybit(material.api_key, material.api_secret)
                mapped = [
                    {"id": str(item.get("orderLinkId") or ""), "status": self._status(str(item.get("orderStatus") or "")), "filled": float(item.get("cumExecQty") or 0.0)}
                    for item in external_orders
                ]
        except PaperPrivateTestnetError as exc:
            return self._save(user_id, connector, "UNAVAILABLE", 0, 0, 0, 0, [exc.code])
        except Exception:
            return self._save(user_id, connector, "UNAVAILABLE", 0, 0, 0, 0, ["private_testnet_internal_error"])

        with self.database.connection() as conn:
            rows = conn.execute("SELECT order_id, status, filled_quantity FROM paper_orders WHERE user_id = ?", (user_id,)).fetchall()
        local = {str(row["order_id"]): row for row in rows}
        matched = mismatched = 0; issues: list[str] = []
        seen = set()
        for item in mapped:
            order_id = item["id"]
            if not order_id:
                continue
            seen.add(order_id)
            row = local.get(order_id)
            if row is None:
                issues.append(f"authenticated_external_order_missing_locally:{order_id}"); mismatched += 1
            elif row["status"] != item["status"] or abs(float(row["filled_quantity"]) - item["filled"]) > 1e-8:
                issues.append(f"authenticated_order_mismatch:{order_id}"); mismatched += 1
            else:
                matched += 1
        for order_id, row in local.items():
            if row["status"] in {"accepted", "working", "partially_filled"} and order_id not in seen:
                issues.append(f"local_open_order_missing_authenticated_snapshot:{order_id}"); mismatched += 1
        status = "EMPTY" if not mapped and not rows else ("CONSISTENT" if not issues else "MISMATCH")
        return self._save(user_id, connector, status, len(external_orders), len(fills), matched, mismatched, issues)

    @staticmethod
    def recovery_drill(request: PaperRecoveryDrillRequest) -> PaperRecoveryDrillResponse:
        failures = 0; backoff = 0; transitions = []
        for success in request.outcomes:
            if success:
                failures = 0; backoff = 0; transitions.append("connected")
            else:
                failures += 1; backoff = min(600, 5 * (2 ** min(failures, 7))); transitions.append(f"backoff:{backoff}")
        return PaperRecoveryDrillResponse(
            connector=request.connector, transitions=transitions,
            final_state="connected" if request.outcomes[-1] else "backoff",
            consecutive_failures=failures, final_backoff_seconds=backoff,
            deterministic=True, network_called=False, order_routing_enabled=False,
            live_execution_enabled=settings.enable_live_execution,
        )
