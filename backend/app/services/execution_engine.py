from __future__ import annotations

from app.config import settings
from app.models import ConnectorCapability, ExecutionPreviewRequest, ExecutionPreviewResponse


class ExecutionEngine:
    """
    Broker/exchange execution guardrails and previews.

    Security notes:
    - Store API keys in a secure vault
    - Enforce allow-listed symbols
    - Enforce server-side risk checks before order placement
    - Keep auto-trading disabled by default
    """

    def validate_pre_trade(self, signal_score: float, trade_allowed: bool) -> dict:
        if signal_score < 75:
            return {"ok": False, "reason": "Signal score below execution threshold"}
        if not trade_allowed:
            return {"ok": False, "reason": "Risk engine rejected trade"}
        return {"ok": True, "reason": "Eligible for semi-auto execution"}

    def capabilities(self) -> list[ConnectorCapability]:
        return [
            ConnectorCapability(
                connector="binance_futures",
                market_type="crypto",
                maturity="active",
                supports_live_route=True,
                status_endpoint="/api/v1/execution/status",
                execution_endpoint="/api/v1/execution/binance/order",
                notes=["Market orders", "Testnet-ready", "Requires API key and secret"],
            ),
            ConnectorCapability(
                connector="bybit",
                market_type="crypto",
                maturity="active-foundation",
                supports_live_route=True,
                status_endpoint="/api/v1/execution/status",
                execution_endpoint="/api/v1/execution/bybit/order",
                notes=["Bybit V5 order create", "Testnet supported", "Requires API key and secret"],
            ),
            ConnectorCapability(
                connector="oanda",
                market_type="forex",
                maturity="active",
                supports_live_route=True,
                status_endpoint="/api/v1/execution/status",
                execution_endpoint="/api/v1/execution/oanda/order",
                notes=["Practice account supported", "Market execution foundation"],
            ),
            ConnectorCapability(
                connector="mt5",
                market_type="forex",
                maturity="foundation-only",
                supports_live_route=False,
                status_endpoint="/api/v1/execution/status",
                execution_endpoint="/api/v1/execution/mt5/order",
                notes=["Needs MetaAPI or local MT5 bridge", "Symbol mapping required"],
            ),
            ConnectorCapability(
                connector="ctrader",
                market_type="forex",
                maturity="foundation-only",
                supports_live_route=False,
                status_endpoint="/api/v1/execution/status",
                execution_endpoint="/api/v1/execution/ctrader/order",
                notes=["Needs cTrader Open API session", "Account mapping required"],
            ),
        ]

    def preview_order(self, request: ExecutionPreviewRequest) -> ExecutionPreviewResponse:
        guard = self.validate_pre_trade(
            signal_score=request.signal_score,
            trade_allowed=request.risk_approved,
        )
        connector = request.connector
        warnings: list[str] = []
        requires_credentials = True
        mode = "live-enabled" if settings.enable_live_execution else "dry-run"

        if connector == "binance_futures":
            route = "/api/v1/execution/binance/order"
            payload = {
                "symbol": request.symbol.upper(),
                "side": request.side.upper(),
                "quantity": request.quantity,
                "order_type": "MARKET",
            }
            if not settings.binance_api_key or not settings.binance_api_secret:
                warnings.append("Missing Binance credentials")
        elif connector == "bybit":
            route = "/api/v1/execution/bybit/order"
            payload = {
                "symbol": request.symbol.upper(),
                "side": "Buy" if request.side == "buy" else "Sell",
                "quantity": request.quantity,
                "category": "linear",
                "order_type": "Market",
            }
            if not settings.bybit_api_key or not settings.bybit_api_secret:
                warnings.append("Missing Bybit credentials")
        elif connector == "oanda":
            route = "/api/v1/execution/oanda/order"
            payload = {
                "instrument": request.symbol.upper(),
                "units": int(request.quantity if request.side == "buy" else -request.quantity),
            }
            if not settings.oanda_api_token or not settings.oanda_account_id:
                warnings.append("Missing OANDA token/account id")
        elif connector == "mt5":
            route = "/api/v1/execution/mt5/order"
            payload = {
                "symbol": request.symbol.upper(),
                "side": request.side,
                "volume": request.quantity,
            }
            warnings.append("MT5 is foundation-only until bridge/API integration is completed")
            if not settings.mt5_server or not settings.mt5_login or not settings.mt5_password:
                warnings.append("Missing MT5 bridge credentials/configuration")
        else:
            route = "/api/v1/execution/ctrader/order"
            payload = {
                "symbol": request.symbol.upper(),
                "side": request.side,
                "volume": request.quantity,
            }
            warnings.append("cTrader is foundation-only until Open API routing is completed")
            if not settings.ctrader_client_id or not settings.ctrader_access_token:
                warnings.append("Missing cTrader credentials/token")

        if not settings.enable_live_execution:
            warnings.append("ENABLE_LIVE_EXECUTION=false so order would not be routed live")

        if not guard["ok"]:
            warnings.append(guard["reason"])

        return ExecutionPreviewResponse(
            connector=connector,
            eligible=guard["ok"],
            normalized_side=request.side,
            route=route,
            mode=mode,
            requires_credentials=requires_credentials,
            live_execution_enabled=settings.enable_live_execution,
            warnings=warnings,
            preview_payload=payload,
        )
