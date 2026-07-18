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
    PaperTestnetExecutionControl,
    PaperTestnetExecutionControlUpdate,
    PaperTestnetOrder,
    PaperTestnetOrderListResponse,
    PaperTestnetOrderRequest,
)
from app.services.database_service import DatabaseManager
from app.services.provider_secret_service import ProviderSecretService


class PaperTestnetExecutionError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


_OPEN = {"submission_pending", "accepted", "working", "partially_filled", "cancel_pending", "unknown"}


class PaperTestnetExecutionService:
    def __init__(self, database: DatabaseManager, vault: ProviderSecretService) -> None:
        self.database = database
        self.vault = vault

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _hash(payload: dict) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()

    def _ensure_control(self, conn, user_id: int) -> None:
        now = self._now()
        conn.execute(
            """INSERT INTO paper_testnet_execution_controls (
                user_id, enabled, kill_switch_engaged, max_order_notional,
                max_open_orders, allowed_symbols_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(user_id) DO NOTHING""",
            (user_id, 0, 1, 100.0, 2, '["BTCUSDT"]', now),
        )

    def get_control(self, user_id: int) -> PaperTestnetExecutionControl:
        with self.database.connection() as conn:
            self._ensure_control(conn, user_id); conn.commit()
            row = conn.execute("SELECT * FROM paper_testnet_execution_controls WHERE user_id = ?", (user_id,)).fetchone()
        return PaperTestnetExecutionControl(
            enabled=bool(row["enabled"]), kill_switch_engaged=bool(row["kill_switch_engaged"]),
            max_order_notional=float(row["max_order_notional"]), max_open_orders=int(row["max_open_orders"]),
            allowed_symbols=json.loads(row["allowed_symbols_json"]), environment=settings.app_env,
            testnet_execution_flag=settings.enable_testnet_execution,
            live_execution_enabled=settings.enable_live_execution, updated_at=row["updated_at"],
        )

    def update_control(self, user_id: int, request: PaperTestnetExecutionControlUpdate) -> PaperTestnetExecutionControl:
        if request.enabled and (settings.app_env != "staging" or not settings.enable_testnet_execution or settings.enable_live_execution):
            raise PaperTestnetExecutionError("testnet_environment_gate_failed")
        now = self._now()
        with self.database.connection() as conn:
            self._ensure_control(conn, user_id)
            conn.execute(
                """UPDATE paper_testnet_execution_controls SET enabled=?, kill_switch_engaged=?,
                    max_order_notional=?, max_open_orders=?, allowed_symbols_json=?, updated_at=? WHERE user_id=?""",
                (int(request.enabled), int(request.kill_switch_engaged), request.max_order_notional,
                 request.max_open_orders, json.dumps(request.allowed_symbols), now, user_id),
            )
            if request.kill_switch_engaged or not request.enabled:
                conn.execute("UPDATE paper_testnet_orders SET status='unknown', last_error_code='testnet_kill_switch', updated_at=? WHERE user_id=? AND status IN ('submission_pending','accepted','working','partially_filled','cancel_pending')", (now, user_id))
            conn.commit()
        return self.get_control(user_id)

    def _from_row(self, row, replay: bool = False) -> PaperTestnetOrder:
        return PaperTestnetOrder(
            order_id=row["order_id"], client_order_id=row["client_order_id"], connector=row["connector"],
            symbol=row["symbol"], side=row["side"], quantity=float(row["quantity"]),
            reference_price=float(row["reference_price"]), reduce_only=bool(row["reduce_only"]),
            status=row["status"], external_order_id=row["external_order_id"],
            last_error_code=row["last_error_code"], idempotent_replay=replay,
            testnet_only=True, live_routed=False, created_at=row["created_at"], updated_at=row["updated_at"],
        )

    async def _binance_place(self, material, request, client_id):
        params={"symbol":request.symbol.upper(),"side":request.side.upper(),"type":"MARKET","quantity":request.quantity,"reduceOnly":str(request.reduce_only).lower(),"newClientOrderId":client_id,"timestamp":int(time.time()*1000),"recvWindow":5000}
        query=urlencode(params);params["signature"]=hmac.new(material.api_secret.encode(),query.encode(),hashlib.sha256).hexdigest()
        async with httpx.AsyncClient(timeout=15) as client:
            response=await client.post("https://testnet.binancefuture.com/fapi/v1/order",params=params,headers={"X-MBX-APIKEY":material.api_key})
        if not response.is_success: raise PaperTestnetExecutionError("testnet_provider_rejected")
        data=response.json();return str(data.get("orderId") or ""), "accepted"

    async def _bybit_place(self, material, request, client_id):
        body={"category":"linear","symbol":request.symbol.upper(),"side":"Buy" if request.side=="buy" else "Sell","orderType":"Market","qty":str(request.quantity),"reduceOnly":request.reduce_only,"orderLinkId":client_id}
        raw=json.dumps(body,separators=(",",":"));ts=str(int(time.time()*1000));window="5000";sig=hmac.new(material.api_secret.encode(),f"{ts}{material.api_key}{window}{raw}".encode(),hashlib.sha256).hexdigest()
        async with httpx.AsyncClient(timeout=15) as client:
            response=await client.post("https://api-testnet.bybit.com/v5/order/create",content=raw,headers={"X-BAPI-API-KEY":material.api_key,"X-BAPI-TIMESTAMP":ts,"X-BAPI-RECV-WINDOW":window,"X-BAPI-SIGN":sig,"Content-Type":"application/json"})
        data=response.json()
        if not response.is_success or int(data.get("retCode",-1))!=0: raise PaperTestnetExecutionError("testnet_provider_rejected")
        return str((data.get("result") or {}).get("orderId") or ""), "accepted"

    async def place(self, user_id: int, request: PaperTestnetOrderRequest) -> PaperTestnetOrder:
        payload=request.model_dump(mode="json");request_hash=self._hash(payload);symbol=request.symbol.upper();now=self._now()
        with self.database.connection() as conn:
            self._ensure_control(conn,user_id);conn.commit()
            existing=conn.execute("SELECT * FROM paper_testnet_orders WHERE user_id=? AND idempotency_key=?",(user_id,request.idempotency_key)).fetchone()
            if existing:
                if existing["request_hash"]!=request_hash: raise PaperTestnetExecutionError("testnet_idempotency_conflict")
                return self._from_row(existing,True)
            control=conn.execute("SELECT * FROM paper_testnet_execution_controls WHERE user_id=?",(user_id,)).fetchone()
            if settings.app_env!="staging" or not settings.enable_testnet_execution or settings.enable_live_execution: raise PaperTestnetExecutionError("testnet_environment_gate_failed")
            if not bool(control["enabled"]) or bool(control["kill_switch_engaged"]): raise PaperTestnetExecutionError("testnet_execution_not_armed")
            if symbol not in json.loads(control["allowed_symbols_json"]): raise PaperTestnetExecutionError("testnet_symbol_not_allowed")
            if request.quantity*request.reference_price>float(control["max_order_notional"]): raise PaperTestnetExecutionError("testnet_notional_limit_exceeded")
            count=conn.execute("SELECT COUNT(*) AS count FROM paper_testnet_orders WHERE user_id=? AND status IN ('submission_pending','accepted','working','partially_filled','cancel_pending','unknown')",(user_id,)).fetchone()
            if int(count["count"])>=int(control["max_open_orders"]): raise PaperTestnetExecutionError("testnet_max_open_orders")
            order_id=uuid4().hex;client_id="apx_"+hashlib.sha256(order_id.encode()).hexdigest()[:28]
            conn.execute("INSERT INTO paper_testnet_orders (order_id,user_id,idempotency_key,request_hash,client_order_id,connector,symbol,side,quantity,reference_price,reduce_only,status,external_order_id,last_error_code,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(order_id,user_id,request.idempotency_key,request_hash,client_id,request.connector,symbol,request.side,request.quantity,request.reference_price,int(request.reduce_only),"submission_pending",None,None,now,now));conn.commit()
        provider="binance_testnet" if request.connector=="binance_futures_testnet" else "bybit_testnet";material=self.vault.get_material(user_id,provider)
        if material is None or not material.api_secret: error="testnet_credentials_not_configured"
        else:
            try:
                external,status=await (self._binance_place(material,request,client_id) if provider=="binance_testnet" else self._bybit_place(material,request,client_id));error=None
            except PaperTestnetExecutionError as exc: external=None;status="rejected";error=exc.code
            except Exception: external=None;status="unknown";error="testnet_transport_unknown"
        with self.database.connection() as conn:
            if error=="testnet_credentials_not_configured": status="rejected"
            conn.execute("UPDATE paper_testnet_orders SET status=?,external_order_id=?,last_error_code=?,updated_at=? WHERE order_id=?",(status,external,error,self._now(),order_id))
            if status=="unknown": conn.execute("UPDATE paper_testnet_execution_controls SET kill_switch_engaged=1,enabled=0,updated_at=? WHERE user_id=?",(self._now(),user_id))
            conn.commit();row=conn.execute("SELECT * FROM paper_testnet_orders WHERE order_id=?",(order_id,)).fetchone()
        return self._from_row(row)

    async def _cancel_provider(self, material, row):
        if row["connector"] == "binance_futures_testnet":
            params={"symbol":row["symbol"],"origClientOrderId":row["client_order_id"],"timestamp":int(time.time()*1000),"recvWindow":5000}
            query=urlencode(params);params["signature"]=hmac.new(material.api_secret.encode(),query.encode(),hashlib.sha256).hexdigest()
            async with httpx.AsyncClient(timeout=15) as client:
                response=await client.delete("https://testnet.binancefuture.com/fapi/v1/order",params=params,headers={"X-MBX-APIKEY":material.api_key})
            if not response.is_success: raise PaperTestnetExecutionError("testnet_cancel_rejected")
        else:
            body={"category":"linear","symbol":row["symbol"],"orderLinkId":row["client_order_id"]};raw=json.dumps(body,separators=(",",":"));ts=str(int(time.time()*1000));window="5000";sig=hmac.new(material.api_secret.encode(),f"{ts}{material.api_key}{window}{raw}".encode(),hashlib.sha256).hexdigest()
            async with httpx.AsyncClient(timeout=15) as client:
                response=await client.post("https://api-testnet.bybit.com/v5/order/cancel",content=raw,headers={"X-BAPI-API-KEY":material.api_key,"X-BAPI-TIMESTAMP":ts,"X-BAPI-RECV-WINDOW":window,"X-BAPI-SIGN":sig,"Content-Type":"application/json"})
            data=response.json()
            if not response.is_success or int(data.get("retCode",-1))!=0: raise PaperTestnetExecutionError("testnet_cancel_rejected")

    async def cancel(self,user_id:int,order_id:str)->PaperTestnetOrder:
        if settings.app_env!="staging" or not settings.enable_testnet_execution or settings.enable_live_execution: raise PaperTestnetExecutionError("testnet_environment_gate_failed")
        with self.database.connection() as conn:
            row=conn.execute("SELECT * FROM paper_testnet_orders WHERE user_id=? AND order_id=?",(user_id,order_id)).fetchone()
            if row is None: raise PaperTestnetExecutionError("testnet_order_not_found")
            if row["status"]=="canceled": return self._from_row(row,True)
            if row["status"] not in _OPEN: raise PaperTestnetExecutionError("testnet_order_not_cancelable")
            conn.execute("UPDATE paper_testnet_orders SET status='cancel_pending',updated_at=? WHERE order_id=?",(self._now(),order_id));conn.commit()
        provider="binance_testnet" if row["connector"]=="binance_futures_testnet" else "bybit_testnet";material=self.vault.get_material(user_id,provider)
        try:
            if material is None or not material.api_secret: raise PaperTestnetExecutionError("testnet_credentials_not_configured")
            await self._cancel_provider(material,row);status="canceled";error=None
        except PaperTestnetExecutionError as exc: status="unknown";error=exc.code
        except Exception: status="unknown";error="testnet_cancel_transport_unknown"
        with self.database.connection() as conn:
            conn.execute("UPDATE paper_testnet_orders SET status=?,last_error_code=?,updated_at=? WHERE order_id=?",(status,error,self._now(),order_id))
            if status=="unknown": conn.execute("UPDATE paper_testnet_execution_controls SET kill_switch_engaged=1,enabled=0,updated_at=? WHERE user_id=?",(self._now(),user_id))
            conn.commit();updated=conn.execute("SELECT * FROM paper_testnet_orders WHERE order_id=?",(order_id,)).fetchone()
        return self._from_row(updated)

    def list(self,user_id:int)->PaperTestnetOrderListResponse:
        with self.database.connection() as conn: rows=conn.execute("SELECT * FROM paper_testnet_orders WHERE user_id=? ORDER BY created_at DESC",(user_id,)).fetchall()
        return PaperTestnetOrderListResponse(items=[self._from_row(row) for row in rows],count=len(rows),live_execution_enabled=settings.enable_live_execution)
