from __future__ import annotations

import asyncio
import math
import time
from statistics import median
from typing import Any

import httpx

# Real VP/Footprint from microstructure (re-use deterministic calculators)
try:
    from app.services.okx_ws_service import okx_ws_service
except Exception:
    okx_ws_service = None

try:
    from app.services.microstructure_service import compute_volume_profile, compute_footprint
    _HAS_VP = True
except Exception:
    _HAS_VP = False


class OrderFlowService:
    """Provider-aware order flow with honest real/proxy labeling."""

    def __init__(self, ttl_seconds: int = 10) -> None:
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, tuple[float, dict]] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._previous_oi: dict[str, tuple[float, float]] = {}

    async def get_snapshot(self, symbol: str, market: str, candles: list[dict]) -> dict:
        if market != "crypto":
            return build_ohlcv_proxy(candles, source="forex_ohlcv_proxy", market=market)

        key = symbol.upper()
        now = time.monotonic()
        cached = self._cache.get(key)
        if cached and now - cached[0] < self.ttl_seconds:
            return {**cached[1], "cached": True, "cache_age_seconds": round(now - cached[0], 2)}

        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            now = time.monotonic()
            cached = self._cache.get(key)
            if cached and now - cached[0] < self.ttl_seconds:
                return {**cached[1], "cached": True, "cache_age_seconds": round(now - cached[0], 2)}
            try:
                snapshot = await self._fetch_okx_swap(key)
                self._cache[key] = (time.monotonic(), snapshot)
                return snapshot
            except Exception:
                proxy = build_ohlcv_proxy(candles, source="crypto_ohlcv_fallback", market=market)
                proxy["fallback_reason"] = "real_orderflow_provider_unavailable"
                return proxy

    async def _fetch_okx_swap(self, symbol: str) -> dict:
        inst_id = normalize_okx_swap(symbol)
        # Try WebSocket live cache first (<2s) for <1s latency — honest fallback to REST
        if okx_ws_service is not None:
            try:
                await okx_ws_service.ensure_subscribed(inst_id)
                ws_trades, ws_book = await okx_ws_service.get_cached(inst_id, max_age_s=2.5)
                if ws_trades and ws_book and len(ws_trades) >= 30:
                    # Need OI/funding still via REST (no WS for them)
                    base = "https://www.okx.com/api/v5"
                    headers = {"User-Agent": "APEX-Omega-Pro/3.0", "Accept": "application/json"}
                    async with httpx.AsyncClient(timeout=8.0, headers=headers) as client:
                        oi_resp, fund_resp = await asyncio.gather(
                            client.get(f"{base}/public/open-interest", params={"instType": "SWAP", "instId": inst_id}),
                            client.get(f"{base}/public/funding-rate", params={"instId": inst_id}),
                            return_exceptions=True,
                        )
                    oi_rows = None
                    fund_rows = None
                    if not isinstance(oi_resp, Exception) and getattr(oi_resp, "is_success", False):
                        try:
                            d = oi_resp.json()
                            if str(d.get("code")) == "0":
                                oi_rows = d.get("data") or []
                        except Exception:
                            pass
                    if not isinstance(fund_resp, Exception) and getattr(fund_resp, "is_success", False):
                        try:
                            d = fund_resp.json()
                            if str(d.get("code")) == "0":
                                fund_rows = d.get("data") or []
                        except Exception:
                            pass
                    previous_oi = self._previous_oi.get(inst_id)
                    snapshot = analyze_okx_payloads(
                        trades=ws_trades,
                        depth=ws_book,
                        open_interest=oi_rows[0] if oi_rows else None,
                        funding=fund_rows[0] if fund_rows else None,
                        previous_oi=previous_oi,
                    )
                    oi_value = snapshot.get("open_interest_usd")
                    if oi_value is not None:
                        self._previous_oi[inst_id] = (time.monotonic(), float(oi_value))
                    snapshot["symbol"] = symbol
                    snapshot["instrument"] = inst_id
                    snapshot["components"] = ["trades_ws", "depth_ws", "open_interest", "funding"]
                    snapshot["cached"] = False
                    snapshot["cache_age_seconds"] = 0.0
                    snapshot["source_detail"] = "okx_ws_live"
                    return snapshot
            except Exception:
                pass
        base = "https://www.okx.com/api/v5"
        headers = {"User-Agent": "APEX-Omega-Pro/3.0", "Accept": "application/json"}
        # Window: 45 minutes (2700s) to cover 15m x3 with history pagination up to 2600 trades
        window_sec = 2700
        max_trades = 2600
        max_pages = 12
        async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
            # Parallel fetch for books/OI/funding, sequential for trades with history pagination
            book_task = client.get(f"{base}/market/books", params={"instId": inst_id, "sz": 400})
            oi_task = client.get(f"{base}/public/open-interest", params={"instType": "SWAP", "instId": inst_id})
            funding_task = client.get(f"{base}/public/funding-rate", params={"instId": inst_id})
            trades_resp = await client.get(f"{base}/market/trades", params={"instId": inst_id, "limit": 500})
            # Fetch history pagination for trades to reach window_sec coverage
            trades = []
            if trades_resp.is_success:
                data = trades_resp.json()
                if str(data.get("code")) == "0":
                    trades = list(data.get("data") or [])
                    cutoff_ms = int((time.time() - window_sec) * 1000)
                    guard = 0
                    while trades and len(trades) < max_trades and guard < max_pages:
                        oldest = trades[-1]
                        try:
                            oldest_ts = int(_safe_float(oldest.get("ts")))
                        except Exception:
                            break
                        if oldest_ts <= cutoff_ms:
                            break
                        try:
                            page_resp = await client.get(f"{base}/market/history-trades", params={"instId": inst_id, "after": oldest.get("tradeId"), "limit": 100})
                            if not page_resp.is_success:
                                break
                            page_data = page_resp.json()
                            if str(page_data.get("code")) != "0":
                                break
                            page_rows = page_data.get("data") or []
                            if not page_rows:
                                break
                            trades.extend(page_rows)
                            guard += 1
                        except Exception:
                            break
            # Now fetch remaining parallel components
            book_resp, oi_resp, funding_resp = await asyncio.gather(book_task, oi_task, funding_task, return_exceptions=True)
            # Normalize payloads
            payloads: list[Any] = []
            components = []
            names = ["trades", "depth", "open_interest", "funding"]
            # trades already handled
            for name, response in zip(names, [trades_resp, book_resp, oi_resp, funding_resp]):
                if name == "trades":
                    if trades:
                        payloads.append(trades)
                        components.append(name)
                    else:
                        payloads.append(None)
                    continue
                if isinstance(response, Exception) or not getattr(response, "is_success", False):
                    payloads.append(None)
                    continue
                try:
                    data = response.json()
                except Exception:
                    payloads.append(None)
                    continue
                if str(data.get("code")) != "0":
                    payloads.append(None)
                    continue
                payloads.append(data.get("data") or [])
                components.append(name)

            trades, depth_rows, oi_rows, funding_rows = payloads
        if not trades or not depth_rows:
            raise RuntimeError("real order flow core components unavailable")

        previous_oi = self._previous_oi.get(inst_id)
        snapshot = analyze_okx_payloads(
            trades=trades,
            depth=depth_rows[0],
            open_interest=oi_rows[0] if oi_rows else None,
            funding=funding_rows[0] if funding_rows else None,
            previous_oi=previous_oi,
        )
        oi_value = snapshot.get("open_interest_usd")
        if oi_value is not None:
            self._previous_oi[inst_id] = (time.monotonic(), float(oi_value))
        snapshot["symbol"] = symbol
        snapshot["instrument"] = inst_id
        snapshot["components"] = components
        snapshot["cached"] = False
        snapshot["cache_age_seconds"] = 0.0
        return snapshot


def normalize_okx_swap(symbol: str) -> str:
    upper = symbol.upper().replace("-", "")
    if upper.endswith("USDT"):
        return f"{upper[:-4]}-USDT-SWAP"
    return upper


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        return number if math.isfinite(number) else default
    except (TypeError, ValueError):
        return default


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int((len(ordered) - 1) * percentile)
    return ordered[max(0, min(index, len(ordered) - 1))]


def analyze_okx_payloads(
    trades: list[dict],
    depth: dict,
    open_interest: dict | None,
    funding: dict | None,
    previous_oi: tuple[float, float] | None = None,
) -> dict:
    ordered_trades = sorted(trades, key=lambda item: int(item.get("ts") or 0))
    buy_size = 0.0
    sell_size = 0.0
    buy_notional = 0.0
    sell_notional = 0.0
    sizes = []
    signed_curve = []
    cvd = 0.0
    prices = []
    for item in ordered_trades:
        size = _safe_float(item.get("sz"))
        price = _safe_float(item.get("px"))
        if size <= 0 or price <= 0:
            continue
        side = str(item.get("side") or "").lower()
        signed = size if side == "buy" else -size
        if side == "buy":
            buy_size += size
            buy_notional += size * price
        else:
            sell_size += size
            sell_notional += size * price
        cvd += signed
        sizes.append(size)
        prices.append(price)
        signed_curve.append({"t": int(item.get("ts") or 0) // 1000, "cvd": round(cvd, 4)})

    total_size = buy_size + sell_size
    delta_size = buy_size - sell_size
    delta_ratio = delta_size / total_size if total_size else 0.0
    aggressive_buy_ratio = buy_size / total_size if total_size else 0.5
    aggressive_sell_ratio = sell_size / total_size if total_size else 0.5
    pressure = "buy" if delta_ratio >= 0.12 else "sell" if delta_ratio <= -0.12 else "neutral"
    price_change_bps = (
        (prices[-1] - prices[0]) / prices[0] * 10_000 if len(prices) >= 2 and prices[0] else 0.0
    )

    large_threshold = _percentile(sizes, 0.90)
    large_buys = large_sells = 0.0
    for item in ordered_trades:
        size = _safe_float(item.get("sz"))
        if size < large_threshold or large_threshold <= 0:
            continue
        if str(item.get("side") or "").lower() == "buy":
            large_buys += size
        else:
            large_sells += size
    large_total = large_buys + large_sells
    large_trade_imbalance = (
        (large_buys - large_sells) / large_total if large_total else 0.0
    )

    bids = depth.get("bids") or []
    asks = depth.get("asks") or []
    bid_levels = [(_safe_float(row[0]), _safe_float(row[1])) for row in bids if len(row) >= 2]
    ask_levels = [(_safe_float(row[0]), _safe_float(row[1])) for row in asks if len(row) >= 2]
    bid_notional = sum(price * size for price, size in bid_levels[:25])
    ask_notional = sum(price * size for price, size in ask_levels[:25])
    depth_total = bid_notional + ask_notional
    depth_imbalance = (bid_notional - ask_notional) / depth_total if depth_total else 0.0
    best_bid = bid_levels[0][0] if bid_levels else 0.0
    best_ask = ask_levels[0][0] if ask_levels else 0.0
    mid = (best_bid + best_ask) / 2 if best_bid and best_ask else 0.0
    spread_bps = (best_ask - best_bid) / mid * 10_000 if mid else None

    bid_sizes = [size for _, size in bid_levels]
    ask_sizes = [size for _, size in ask_levels]
    bid_median = median(bid_sizes) if bid_sizes else 0.0
    ask_median = median(ask_sizes) if ask_sizes else 0.0
    bid_wall = max(bid_levels, key=lambda row: row[1]) if bid_levels else (None, 0.0)
    ask_wall = max(ask_levels, key=lambda row: row[1]) if ask_levels else (None, 0.0)
    bid_wall_strength = bid_wall[1] / bid_median if bid_median else 0.0
    ask_wall_strength = ask_wall[1] / ask_median if ask_median else 0.0

    oi_usd = _safe_float((open_interest or {}).get("oiUsd"), default=0.0) or None
    oi_contracts = _safe_float((open_interest or {}).get("oi"), default=0.0) or None
    oi_change_pct = None
    if oi_usd is not None and previous_oi and previous_oi[1] > 0:
        oi_change_pct = (oi_usd - previous_oi[1]) / previous_oi[1] * 100
    funding_rate = _safe_float((funding or {}).get("fundingRate"), default=0.0)

    absorption = abs(delta_ratio) >= 0.18 and abs(price_change_bps) <= 4.0
    climax = abs(large_trade_imbalance) >= 0.45 and abs(price_change_bps) >= 8.0
    divergence = None
    if delta_ratio > 0.12 and price_change_bps < -3:
        divergence = "bearish"
    elif delta_ratio < -0.12 and price_change_bps > 3:
        divergence = "bullish"

    # v3.31: this number is DATA COMPLETENESS of the exchange snapshot, not a
    # statistical confidence in the trade. Base lowered from a hardcoded 0.70 so
    # an incomplete snapshot can no longer pass the real-flow evidence gate.
    confidence = 0.45
    if len(ordered_trades) >= 100:
        confidence += 0.08
    if len(bid_levels) >= 20 and len(ask_levels) >= 20:
        confidence += 0.08
    if oi_usd is not None:
        confidence += 0.07
    if funding is not None:
        confidence += 0.05
    confidence = min(confidence, 0.98)

    # --- Real VP(20) / Footprint(6x12) from live trades (no proxy) ---
    _vp = None
    _fp = None
    if _HAS_VP:
        try:
            _vp = compute_volume_profile(trades, bin_count=20)
        except Exception:
            _vp = None
        try:
            _fp = compute_footprint(trades, tf_sec=60, max_candles=6, rows_per_candle=12)
        except Exception:
            _fp = None

    return {
        "source": "okx_swap_public",
        "is_real": True,
        "confidence": round(confidence, 2),
        "confidence_is_data_completeness": True,
        "pressure": pressure,
        "delta": round(delta_ratio, 4),
        "delta_contracts": round(delta_size, 4),
        "buy_contracts": round(buy_size, 4),
        "sell_contracts": round(sell_size, 4),
        "buy_notional_proxy": round(buy_notional, 2),
        "sell_notional_proxy": round(sell_notional, 2),
        "aggressive_buy_ratio": round(aggressive_buy_ratio, 4),
        "aggressive_sell_ratio": round(aggressive_sell_ratio, 4),
        "large_trade_threshold": round(large_threshold, 4),
        "large_trade_imbalance": round(large_trade_imbalance, 4),
        "cvd": round(cvd, 4),
        "cvd_curve": signed_curve[-80:],
        "price_change_bps": round(price_change_bps, 3),
        "depth_imbalance": round(depth_imbalance, 4),
        "bid_depth_notional_proxy": round(bid_notional, 2),
        "ask_depth_notional_proxy": round(ask_notional, 2),
        "best_bid": best_bid or None,
        "best_ask": best_ask or None,
        "spread_bps": round(spread_bps, 4) if spread_bps is not None else None,
        "bid_wall_price": bid_wall[0],
        "bid_wall_strength": round(bid_wall_strength, 2),
        "ask_wall_price": ask_wall[0],
        "ask_wall_strength": round(ask_wall_strength, 2),
        "open_interest": oi_contracts,
        "open_interest_usd": round(oi_usd, 2) if oi_usd is not None else None,
        "open_interest_change_pct": round(oi_change_pct, 4) if oi_change_pct is not None else None,
        "funding_rate": funding_rate,
        "funding_rate_pct": round(funding_rate * 100, 6),
        "absorption": absorption,
        "climax": climax,
        "cvd_divergence": divergence,
        "volume_spike": abs(large_trade_imbalance) >= 0.35,
        "sample_trades": len(ordered_trades),
        "volume_profile": _vp,
        "footprint": _fp,
        "depth_levels": len(bid_levels) + len(ask_levels),
        "depth_requested": 400,
        "disclaimer": "Centralized exchange derivatives order flow (400 L2 levels, up to 2600 trades) + real VP(20)/Footprint(6x12) from live trades; not global consolidated tape.",
    }


def build_ohlcv_proxy(candles: list[dict], source: str, market: str) -> dict:
    sample = candles[-80:]
    if not sample:
        return {
            "source": source,
            "is_real": False,
            "confidence": 0.0,
            "pressure": "neutral",
            "delta": 0.0,
            "cvd": 0.0,
            "cvd_curve": [],
            "disclaimer": "No order flow data available.",
        }

    volumes = [max(_safe_float(item.get("v")), 0.0) for item in sample]
    volume_coverage = sum(1 for value in volumes if value > 0) / len(volumes)
    ranges = [max(_safe_float(item.get("h")) - _safe_float(item.get("l")), 1e-9) for item in sample]
    median_range = median(ranges) if ranges else 1.0
    signed_values = []
    cvd_curve = []
    cvd = 0.0
    for item, volume, candle_range in zip(sample, volumes, ranges):
        open_price = _safe_float(item.get("o"))
        close = _safe_float(item.get("c"))
        high = _safe_float(item.get("h"))
        low = _safe_float(item.get("l"))
        body_pressure = (close - open_price) / candle_range
        close_location = ((close - low) / candle_range - 0.5) * 2
        weight = volume if volume > 0 else candle_range / max(median_range, 1e-9)
        signed = ((body_pressure * 0.65) + (close_location * 0.35)) * weight
        signed_values.append(signed)
        cvd += signed
        cvd_curve.append({"t": int(_safe_float(item.get("t"))), "cvd": round(cvd, 4)})

    absolute = sum(abs(item) for item in signed_values)
    delta_ratio = sum(signed_values) / absolute if absolute else 0.0
    pressure = "buy" if delta_ratio >= 0.18 else "sell" if delta_ratio <= -0.18 else "neutral"
    recent_volumes = volumes[-20:]
    baseline = median([value for value in volumes if value > 0]) if any(volumes) else 0.0
    volume_spike = bool(baseline and recent_volumes and recent_volumes[-1] >= baseline * 2)
    last = sample[-1]
    last_range = max(_safe_float(last.get("h")) - _safe_float(last.get("l")), 1e-9)
    last_body = abs(_safe_float(last.get("c")) - _safe_float(last.get("o"))) / last_range
    absorption = volume_spike and last_body < 0.25
    climax = volume_spike and last_body > 0.7
    confidence = 0.42 if volume_coverage >= 0.7 else 0.30 if volume_coverage >= 0.2 else 0.22

    return {
        "source": source,
        "is_real": False,
        "confidence": confidence,
        "pressure": pressure,
        "delta": round(delta_ratio, 4),
        "delta_proxy": round(sum(signed_values), 4),
        "cvd": round(cvd, 4),
        "cvd_curve": cvd_curve[-80:],
        "volume_coverage": round(volume_coverage, 3),
        "volume_spike": volume_spike,
        "absorption": absorption,
        "climax": climax,
        "cvd_divergence": None,
        "depth_imbalance": None,
        "spread_bps": None,
        "open_interest": None,
        "open_interest_usd": None,
        "open_interest_change_pct": None,
        "funding_rate": None,
        "aggressive_buy_ratio": None,
        "aggressive_sell_ratio": None,
        "disclaimer": (
            "Forex order flow proxy derived from OHLCV/tick-volume; not centralized bid/ask flow."
            if market == "forex"
            else "Fallback OHLCV proxy; real exchange order flow unavailable."
        ),
    }
