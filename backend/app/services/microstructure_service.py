"""Real market microstructure: Level-2 depth, Footprint, Volume Profile, Order Flow.

Data source: OKX public REST (real executed trades + real order book).
Honest labeling: every block carries ``is_real`` and, when a proxy instrument is
used (e.g. XAUUSD -> PAXG/USDT tokenized physical gold), it is explicitly stated.

All computations are deterministic; nothing here can override the strict
decision engine — this module only produces measured facts and filters.
"""
from __future__ import annotations

import asyncio
import math
import re
import time
from statistics import median
from typing import Any

import httpx

OKX_BASE = "https://www.okx.com/api/v5"
_UA = {"User-Agent": "APEX-Omega-Pro/3.0", "Accept": "application/json"}

TF_SECONDS = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}

# XAUUSD has no central L2 tape; tokenized physical gold (1 token = 1 troy oz)
# is a genuinely traded gold instrument with a public order book and trade tape.
GOLD_PROXY = {
    "XAUUSD": ("PAXG-USDT", "SPOT", "XAUUSD"),
    "XAUUSDT": ("PAXG-USDT", "SPOT", "XAUUSD"),
    "GOLD": ("PAXG-USDT", "SPOT", "XAUUSD"),
}

FOREX_SPOT_PROXY = {
    "EURUSD": "EUR-USDT",
    "GBPUSD": "GBP-USDT",
}

_ALIAS_TO_SYMBOL = {
    "GOLD": "XAUUSD",
    "XAU": "XAUUSD",
    "XAUUSD": "XAUUSD",
    "XAUUSDT": "XAUUSD",
    "BTC": "BTCUSDT",
    "BITCOIN": "BTCUSDT",
    "ETH": "ETHUSDT",
    "ETHEREUM": "ETHUSDT",
    "SOL": "SOLUSDT",
    "BNB": "BNBUSDT",
    "XRP": "XRPUSDT",
    "DOGE": "DOGEUSDT",
    "ADA": "ADAUSDT",
    "EURUSD": "EURUSD",
    "GBPUSD": "GBPUSD",
    "USDJPY": "USDJPY",
    "AUDUSD": "AUDUSD",
    "USDCAD": "USDCAD",
    "EURJPY": "EURJPY",
    "GBPJPY": "GBPJPY",
}


def norm_timeframe(timeframe: str | None) -> str:
    tf = (timeframe or "15m").strip().lower()
    if "min" in tf:
        tf = tf.replace("min", "m")
    if tf in ("60m", "60"):
        tf = "1h"
    if tf in ("15",):
        tf = "15m"
    if tf in ("5",):
        tf = "5m"
    if tf in ("1",):
        tf = "1m"
    return tf if tf in TF_SECONDS else "15m"


FX_MAJORS = {"EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "EURJPY", "GBPJPY"}


def resolve_instrument(symbol: str, market: str | None = None) -> dict | None:
    """Map an app symbol to an OKX instrument with real tape/book access."""
    raw = (symbol or "").upper().replace("-", "").replace("/", "").strip()
    raw = _ALIAS_TO_SYMBOL.get(raw, raw)
    if raw in GOLD_PROXY:
        inst_id, inst_type, proxy_for = GOLD_PROXY[raw]
        return {
            "inst_id": inst_id,
            "inst_type": inst_type,
            "proxy_for": proxy_for,
            "note": "Real gold proxy: tokenized physical gold, 1 token = 1 troy oz (PAXG/USDT).",
        }
    if raw in FOREX_SPOT_PROXY and market in (None, "", "auto", "forex"):
        return {
            "inst_id": FOREX_SPOT_PROXY[raw],
            "inst_type": "SPOT",
            "proxy_for": raw,
            "note": "Stablecoin FX pair on OKX used as a real FX proxy; liquidity is thinner than interbank.",
        }
    if market == "forex" or raw in FX_MAJORS:
        return None
    base = raw[:-4] if raw.endswith("USDT") else raw
    return {"inst_id": f"{base}-USDT-SWAP", "inst_type": "SWAP", "proxy_for": None, "note": None}


def detect_symbol_from_text(text: str) -> str:
    if not text:
        return ""
    tokens = re.findall(r"[A-Za-z]{3,8}", text.upper())
    for token in tokens:
        if token in _ALIAS_TO_SYMBOL:
            return _ALIAS_TO_SYMBOL[token]
    for token in tokens:
        if token.endswith("USDT") and len(token) >= 6:
            return token
    return ""


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        return number if math.isfinite(number) else default
    except (TypeError, ValueError):
        return default


def _r(value: float, digits: int = 4) -> float:
    return round(value, digits)


class MicrostructureService:
    """Cached, provider-aware real microstructure (L2 / footprint / VP / flow)."""

    def __init__(
        self,
        ttl_seconds: int = 45,
        max_history_pages: int = 12,
        max_trades: int = 2600,
        fetch_timeout: float = 6.0,
        max_concurrency: int = 4,
    ) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_history_pages = max_history_pages
        self.max_trades = max_trades
        self.fetch_timeout = fetch_timeout
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._cache: dict[str, tuple[float, dict]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    # ---------------------------------------------------------------- public
    async def get_microstructure(
        self,
        symbol: str,
        market: str | None = "auto",
        timeframe: str | None = "15m",
        candles: list[dict] | None = None,
        compact: bool = False,
    ) -> dict:
        tf = norm_timeframe(timeframe)
        raw_symbol = (symbol or "").upper()
        key = f"{raw_symbol}|{tf}"
        now = time.monotonic()
        cached = self._cache.get(key)
        if cached and now - cached[0] < self.ttl_seconds:
            payload = cached[1]
            out = dict(payload)
            out["cached"] = True
            out["cache_age_seconds"] = round(now - cached[0], 2)
            return compact_micro(out) if compact else out

        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            now = time.monotonic()
            cached = self._cache.get(key)
            if cached and now - cached[0] < self.ttl_seconds:
                payload = cached[1]
                out = dict(payload)
                out["cached"] = True
                out["cache_age_seconds"] = round(now - cached[0], 2)
                return compact_micro(out) if compact else out
            payload = await self._build(raw_symbol, market, tf, candles or [])
            self._cache[key] = (time.monotonic(), payload)
            return compact_micro(payload) if compact else payload

    # ---------------------------------------------------------------- fetch
    async def _build(self, symbol: str, market: str | None, tf: str, candles: list[dict]) -> dict:
        tf_sec = TF_SECONDS[tf]
        instrument = resolve_instrument(symbol, market)
        window_sec = min(max(3 * tf_sec, 900), 4 * 3600)

        if instrument is None:
            return self._kline_fallback(symbol, market or "forex", tf, candles, reason="no_real_instrument")

        errors: list[str] = []
        deadline = time.monotonic() + self.fetch_timeout
        try:
            async with self._semaphore:
                async with httpx.AsyncClient(timeout=self.fetch_timeout, headers=_UA) as client:
                    trades, fetch_errors = await self._fetch_trades(
                        client, instrument["inst_id"], tf_sec, window_sec, deadline
                    )
                    errors.extend(fetch_errors)
                    book, book_err = await self._fetch_book(client, instrument["inst_id"])
                    if book_err:
                        errors.append(book_err)
                    oi = funding = None
                    if instrument["inst_type"] == "SWAP":
                        oi, funding, der_err = await self._fetch_derivatives(client, instrument["inst_id"])
                        if der_err:
                            errors.append(der_err)
        except Exception as exc:  # network layer hard failure
            errors.append(f"transport: {exc}")
            trades, book, oi, funding = [], None, None, None

        if len(trades) < 30 or book is None:
            fallback = self._kline_fallback(symbol, market or "auto", tf, candles, reason="real_tape_unavailable")
            fallback["errors"] = errors
            fallback["instrument"] = instrument
            return fallback

        flow = compute_flow_metrics(trades)
        vp = compute_volume_profile(trades)
        fp = compute_footprint(trades, tf_sec)
        l2 = compute_l2(book)
        price = flow.get("last_price") or l2.get("mid") or vp.get("poc") or 0.0
        filters = apply_filters(price, flow, vp, l2, fp)

        covered = (flow["window_end_ts"] - flow["window_start_ts"]) / 1000.0
        payload: dict[str, Any] = {
            "symbol": symbol,
            "market": market if market in ("crypto", "forex") else "auto",
            "timeframe": tf,
            "instrument": instrument,
            "source": "okx_public",
            "is_real": True,
            "confidence": _confidence(trades_count=len(trades), book=book, oi=oi, funding=funding),
            "window": {
                "start_ts": flow["window_start_ts"],
                "end_ts": flow["window_end_ts"],
                "covered_seconds": int(covered),
                "requested_seconds": window_sec,
                "full_coverage": covered >= window_sec * 0.8,
                "trades": len(trades),
            },
            "order_flow": flow,
            "volume_profile": vp,
            "footprint": fp,
            "level2": l2,
            "filters": filters,
            "derivatives": {"open_interest_usd": oi, "funding_rate": funding}
            if instrument["inst_type"] == "SWAP"
            else None,
            "errors": errors,
            "fetched_at": int(time.time()),
            "cached": False,
            "cache_age_seconds": 0.0,
            "disclaimer": (
                "Real executed trades and resting orders from one central venue (OKX); "
                "not global consolidated tape."
            ),
        }
        return payload

    async def _fetch_trades(
        self,
        client: httpx.AsyncClient,
        inst_id: str,
        tf_sec: int,
        window_sec: int,
        deadline: float,
    ) -> tuple[list[dict], list[str]]:
        errors: list[str] = []
        response = await client.get(
            f"{OKX_BASE}/market/trades", params={"instId": inst_id, "limit": 500}
        )
        response.raise_for_status()
        data = response.json()
        if str(data.get("code")) != "0":
            return [], [f"trades: {data.get('msg')}"]
        rows = data.get("data") or []
        trades = list(rows)
        cutoff_ms = int((time.time() - window_sec) * 1000)
        guard = 0
        while (
            trades
            and len(trades) < self.max_trades
            and guard < self.max_history_pages
            and time.monotonic() < deadline
        ):
            oldest = trades[-1]
            if int(_safe_float(oldest.get("ts"))) <= cutoff_ms:
                break
            try:
                page_response = await client.get(
                    f"{OKX_BASE}/market/history-trades",
                    params={"instId": inst_id, "after": oldest.get("tradeId"), "limit": 100},
                )
                page_response.raise_for_status()
                page_data = page_response.json()
                if str(page_data.get("code")) != "0":
                    errors.append(f"history_trades: {page_data.get('msg')}")
                    break
                page_rows = page_data.get("data") or []
                if not page_rows:
                    break
                trades.extend(page_rows)
                guard += 1
            except Exception as exc:
                errors.append(f"history_trades: {exc}")
                break
        return trades, errors

    async def _fetch_book(self, client: httpx.AsyncClient, inst_id: str) -> tuple[dict | None, str | None]:
        try:
            response = await client.get(
                f"{OKX_BASE}/market/books", params={"instId": inst_id, "sz": 400}
            )
            response.raise_for_status()
            data = response.json()
            if str(data.get("code")) != "0" or not data.get("data"):
                return None, f"books: {data.get('msg')}"
            return data["data"][0], None
        except Exception as exc:
            return None, f"books: {exc}"

    async def _fetch_derivatives(
        self, client: httpx.AsyncClient, inst_id: str
    ) -> tuple[float | None, float | None, str | None]:
        oi = funding = None
        errors: list[str] = []
        try:
            response = await client.get(
                f"{OKX_BASE}/public/open-interest",
                params={"instType": "SWAP", "instId": inst_id},
            )
            data = response.json()
            rows = data.get("data") or []
            if str(data.get("code")) == "0" and rows:
                oi = _safe_float(rows[0].get("oiUsd")) or None
        except Exception as exc:
            errors.append(f"oi: {exc}")
        try:
            response = await client.get(
                f"{OKX_BASE}/public/funding-rate", params={"instId": inst_id}
            )
            data = response.json()
            rows = data.get("data") or []
            if str(data.get("code")) == "0" and rows:
                funding = _safe_float(rows[0].get("fundingRate")) or 0.0
        except Exception as exc:
            errors.append(f"funding: {exc}")
        return oi, funding, "; ".join(errors) if errors else None

    # ------------------------------------------------------------- fallback
    def _kline_fallback(self, symbol: str, market: str, tf: str, candles: list[dict], reason: str) -> dict:
        sample = [c for c in candles[-60:] if _safe_float(c.get("v")) > 0]
        vp: dict[str, Any] = {
            "is_real": False,
            "poc": None,
            "vah": None,
            "val": None,
            "bins": [],
            "hvn": [],
            "lvn": [],
        }
        if sample:
            bin_count = 36
            low = min(_safe_float(c.get("l")) for c in sample)
            high = max(_safe_float(c.get("h")) for c in sample)
            width = max((high - low) / bin_count, 1e-12)
            bins = [0.0] * bin_count
            for candle in sample:
                c_low, c_high = _safe_float(c.get("l")), _safe_float(c.get("h"))
                volume = _safe_float(c.get("v"))
                start_bin = max(0, min(bin_count - 1, int((c_low - low) / width)))
                end_bin = max(0, min(bin_count - 1, int((c_high - low) / width)))
                spread = end_bin - start_bin + 1
                per = volume / spread
                for index in range(start_bin, end_bin + 1):
                    bins[index] += per
            poc_index = max(range(bin_count), key=lambda i: bins[i])
            vp.update(
                {
                    "poc": _r(low + (poc_index + 0.5) * width, 6),
                    "bins": [
                        {"p": _r(low + (i + 0.5) * width, 6), "b": None, "s": None, "t": _r(v, 4)}
                        for i, v in enumerate(bins)
                        if v > 0
                    ][:48],
                }
            )
        return {
            "symbol": symbol,
            "market": market,
            "timeframe": tf,
            "source": "ohlcv_kline_proxy",
            "is_real": False,
            "confidence": 0.25,
            "window": {"trades": 0, "covered_seconds": 0, "requested_seconds": TF_SECONDS[tf], "full_coverage": False},
            "order_flow": {"is_real": False, "delta": 0.0, "pressure": "neutral", "cvd_curve": []},
            "volume_profile": vp,
            "footprint": {"is_real": False, "candles": [], "totals": {"candles_covered": 0}},
            "level2": {"is_real": False, "mid": None, "spread_bps": None, "bands": {}, "walls": {}},
            "filters": {"net_bias": "neutral", "score": 0.0, "rows": []},
            "fallback_reason": reason,
            "disclaimer": "Real microstructure unavailable; showing OHLCV approximation only.",
            "fetched_at": int(time.time()),
            "cached": False,
            "cache_age_seconds": 0.0,
        }


def _confidence(trades_count: int, book: dict | None, oi: float | None, funding: float | None) -> float:
    confidence = 0.55
    if trades_count >= 200:
        confidence += 0.10
    if trades_count >= 800:
        confidence += 0.05
    bids = (book or {}).get("bids") or []
    asks = (book or {}).get("asks") or []
    if len(bids) >= 100 and len(asks) >= 100:
        confidence += 0.10
    if oi is not None:
        confidence += 0.05
    if funding is not None:
        confidence += 0.03
    return min(confidence, 0.98)


# ------------------------------------------------------------------ flow
def compute_flow_metrics(trades: list[dict]) -> dict:
    ordered = sorted(trades, key=lambda item: (int(_safe_float(item.get("ts"))), str(item.get("tradeId"))))
    buy_size = sell_size = 0.0
    buy_notional = sell_notional = 0.0
    cvd = 0.0
    curve: list[dict] = []
    sizes: list[float] = []
    notionals: list[tuple[float, str]] = []
    prices: list[float] = []
    first_ts = last_ts = 0

    for item in ordered:
        size = _safe_float(item.get("sz"))
        price = _safe_float(item.get("px"))
        ts = int(_safe_float(item.get("ts")))
        if size <= 0 or price <= 0:
            continue
        side = str(item.get("side") or "").lower()
        if side == "buy":
            buy_size += size
            buy_notional += size * price
        else:
            sell_size += size
            sell_notional += size * price
        cvd += size if side == "buy" else -size
        sizes.append(size)
        notionals.append((size * price, side))
        prices.append(price)
        first_ts = first_ts or ts
        last_ts = ts
        curve.append({"t": ts // 1000, "cvd": _r(cvd, 4)})

    total_size = buy_size + sell_size
    delta_ratio = (buy_size - sell_size) / total_size if total_size else 0.0
    pressure = "buy" if delta_ratio >= 0.12 else "sell" if delta_ratio <= -0.12 else "neutral"
    price_change_bps = 0.0
    if len(prices) >= 2 and prices[0]:
        price_change_bps = (prices[-1] - prices[0]) / prices[0] * 10_000

    large_threshold = sorted(notionals)[int(len(notionals) * 0.90)][0] if notionals else 0.0
    large_buy = large_sell = 0.0
    for notional, side in notionals:
        if notional < large_threshold:
            continue
        if side == "buy":
            large_buy += notional
        else:
            large_sell += notional
    large_total = large_buy + large_sell
    large_imbalance = (large_buy - large_sell) / large_total if large_total else 0.0

    divergence = None
    if delta_ratio > 0.12 and price_change_bps < -3:
        divergence = "bearish"
    elif delta_ratio < -0.12 and price_change_bps > 3:
        divergence = "bullish"

    step = max(1, len(curve) // 80)
    return {
        "is_real": True,
        "delta": _r(delta_ratio),
        "delta_base": _r(buy_size - sell_size, 4),
        "buy_notional": _r(buy_notional, 2),
        "sell_notional": _r(sell_notional, 2),
        "aggressive_buy_ratio": _r(buy_size / total_size, 4) if total_size else None,
        "aggressive_sell_ratio": _r(sell_size / total_size, 4) if total_size else None,
        "cvd": _r(cvd, 4),
        "cvd_curve": curve[::step][-80:],
        "large_trade_imbalance": _r(large_imbalance, 4),
        "large_trade_threshold_notional": _r(large_threshold, 2),
        "price_change_bps": _r(price_change_bps, 3),
        "last_price": prices[-1] if prices else None,
        "pressure": pressure,
        "absorption": abs(delta_ratio) >= 0.18 and abs(price_change_bps) <= 4.0,
        "climax": abs(large_imbalance) >= 0.45 and abs(price_change_bps) >= 8.0,
        "cvd_divergence": divergence,
        "window_start_ts": first_ts,
        "window_end_ts": last_ts,
        "trades": len(prices),
    }


# ------------------------------------------------------------ volume profile
def compute_volume_profile(trades: list[dict], bin_count: int = 48) -> dict:
    points = [
        (_safe_float(item.get("px")), _safe_float(item.get("sz")), str(item.get("side") or "").lower())
        for item in trades
    ]
    points = [(p, s, side) for p, s, side in points if p > 0 and s > 0]
    if not points:
        return {"is_real": True, "poc": None, "vah": None, "val": None, "bins": [], "hvn": [], "lvn": []}

    low = min(p for p, _, _ in points)
    high = max(p for p, _, _ in points)
    width = max((high - low) / bin_count, 1e-12)
    buy_bins = [0.0] * bin_count
    sell_bins = [0.0] * bin_count
    for price, size, side in points:
        index = max(0, min(bin_count - 1, int((price - low) / width)))
        if side == "buy":
            buy_bins[index] += size
        else:
            sell_bins[index] += size
    totals = [b + s for b, s in zip(buy_bins, sell_bins)]
    grand_total = sum(totals)
    poc_index = max(range(bin_count), key=lambda i: totals[i])

    # Standard 70% value-area expansion around POC.
    upper = lower = poc_index
    acc = totals[poc_index]
    target = grand_total * 0.70
    while acc < target and (lower > 0 or upper < bin_count - 1):
        up = totals[upper + 1] if upper < bin_count - 1 else -1.0
        down = totals[lower - 1] if lower > 0 else -1.0
        if up >= down:
            upper += 1
            acc += totals[upper]
        else:
            lower -= 1
            acc += totals[lower]

    positive = [t for t in totals if t > 0]
    mean_total = (grand_total / len(positive)) if positive else 0.0
    hvn = [
        _r(low + (i + 0.5) * width, 6)
        for i, t in enumerate(totals)
        if t >= mean_total * 1.5
    ]
    lvn = [
        _r(low + (i + 0.5) * width, 6)
        for i, t in enumerate(totals)
        if 0 < t <= mean_total * 0.5
    ]

    return {
        "is_real": True,
        "bin_width": _r(width, 8),
        "poc": _r(low + (poc_index + 0.5) * width, 6),
        "vah": _r(low + (upper + 1) * width, 6),
        "val": _r(low + lower * width, 6),
        "value_area_volume_pct": _r(acc / grand_total * 100, 2) if grand_total else 0.0,
        "hvn": hvn[:8],
        "lvn": lvn[:8],
        "total_volume": _r(grand_total, 4),
        "bins": [
            {
                "p": _r(low + (i + 0.5) * width, 6),
                "b": _r(b, 4),
                "s": _r(s, 4),
                "t": _r(t, 4),
            }
            for i, (b, s, t) in enumerate(zip(buy_bins, sell_bins, totals))
            if t > 0
        ][:48],
    }


# ---------------------------------------------------------------- footprint
def compute_footprint(trades: list[dict], tf_sec: int, max_candles: int = 6, rows_per_candle: int = 12) -> dict:
    buckets: dict[int, list[tuple[int, float, float, str]]] = {}
    for item in trades:
        price = _safe_float(item.get("px"))
        size = _safe_float(item.get("sz"))
        ts = int(_safe_float(item.get("ts")))
        if price <= 0 or size <= 0:
            continue
        side = str(item.get("side") or "").lower()
        buckets.setdefault(ts // 1000 // tf_sec, []).append((ts, price, size, side))

    if not buckets:
        return {"is_real": True, "timeframe_sec": tf_sec, "candles": [], "totals": {"candles_covered": 0}}

    keys = sorted(buckets.keys())[-max_candles:]
    last_key = max(buckets.keys())
    candles_out: list[dict] = []
    cvd = 0.0
    curve: list[dict] = []
    delta_sum = 0.0
    max_stacked_buy = 0
    max_stacked_sell = 0

    for key in keys:
        rows_raw = sorted(buckets[key])
        prices = [p for _, p, _, _ in rows_raw]
        low, high = min(prices), max(prices)
        width = max((high - low) / rows_per_candle, 1e-12)
        buy = [0.0] * rows_per_candle
        sell = [0.0] * rows_per_candle
        for _, price, size, side in rows_raw:
            index = max(0, min(rows_per_candle - 1, int((price - low) / width)))
            if side == "buy":
                buy[index] += size
            else:
                sell[index] += size
        candle_delta = sum(buy) - sum(sell)
        cvd += candle_delta
        delta_sum += candle_delta
        curve.append({"t": key * tf_sec, "cvd": _r(cvd, 4)})

        buy_imb: list[float] = []
        sell_imb: list[float] = []
        for i in range(rows_per_candle):
            # Classic footprint diagonals: aggressive buys at level P vs sells one
            # level below; aggressive sells at level P vs buys one level above.
            if i > 0 and sell[i - 1] > 0 and buy[i] >= 3.0 * sell[i - 1] and buy[i] > 0:
                buy_imb.append(_r(low + (i + 0.5) * width, 6))
            if i < rows_per_candle - 1 and buy[i + 1] > 0 and sell[i] >= 3.0 * buy[i + 1] and sell[i] > 0:
                sell_imb.append(_r(low + (i + 0.5) * width, 6))

        stacked_buy_count = _max_run(buy_imb, rows_per_candle, low, width) if buy_imb else 0
        stacked_sell_count = _max_run(sell_imb, rows_per_candle, low, width) if sell_imb else 0
        max_stacked_buy = max(max_stacked_buy, stacked_buy_count)
        max_stacked_sell = max(max_stacked_sell, stacked_sell_count)

        top_buy = buy[-1]
        top_sell = sell[-1]
        bottom_buy = buy[0]
        bottom_sell = sell[0]
        unfinished = {
            "high": top_buy >= 4.0 * top_sell and top_buy > 0,
            "low": bottom_sell >= 4.0 * bottom_buy and bottom_sell > 0,
        }

        poc_index = max(range(rows_per_candle), key=lambda i: buy[i] + sell[i])
        rows = [
            {
                "p": _r(low + (i + 0.5) * width, 6),
                "b": _r(buy[i], 4),
                "s": _r(sell[i], 4),
                "d": _r(buy[i] - sell[i], 4),
            }
            for i in range(rows_per_candle)
            if buy[i] + sell[i] > 0
        ]
        candles_out.append(
            {
                "t": key * tf_sec,
                "partial": key == last_key,
                "first": rows_raw[0][0],
                "last": rows_raw[-1][0],
                "high": _r(high, 8),
                "low": _r(low, 8),
                "buy": _r(sum(buy), 4),
                "sell": _r(sum(sell), 4),
                "delta": _r(candle_delta, 4),
                "poc": _r(low + (poc_index + 0.5) * width, 6),
                "trades": len(rows_raw),
                "rows": rows,
                "buy_imbalance_prices": buy_imb[:8],
                "sell_imbalance_prices": sell_imb[:8],
                "stacked_buy": stacked_buy_count,
                "stacked_sell": stacked_sell_count,
                "unfinished": unfinished,
            }
        )

    return {
        "is_real": True,
        "timeframe_sec": tf_sec,
        "candles": candles_out,
        "totals": {
            "candles_covered": len(candles_out),
            "delta_sum": _r(delta_sum, 4),
            "cvd": _r(cvd, 4),
            "max_stacked_buy": max_stacked_buy,
            "max_stacked_sell": max_stacked_sell,
        },
        "cvd_curve": curve[-80:],
    }


def _max_run(prices: list[float], rows: int, low: float, width: float) -> int:
    """Longest run of consecutive bins containing an imbalance."""
    flags = [False] * rows
    for price in prices:
        index = max(0, min(rows - 1, int((price - low) / width)))
        flags[index] = True
    best = current = 0
    for flag in flags:
        current = current + 1 if flag else 0
        best = max(best, current)
    return best


# -------------------------------------------------------------------- L2
def compute_l2(book: dict) -> dict:
    bids = [
        (_safe_float(row[0]), _safe_float(row[1]))
        for row in (book.get("bids") or [])
        if len(row) >= 2
    ]
    asks = [
        (_safe_float(row[0]), _safe_float(row[1]))
        for row in (book.get("asks") or [])
        if len(row) >= 2
    ]
    if not bids or not asks:
        return {"is_real": True, "mid": None, "spread_bps": None, "bands": {}, "walls": {}, "liquidity_within_pct": {}}

    best_bid, best_ask = bids[0][0], asks[0][0]
    mid = (best_bid + best_ask) / 2 if best_bid and best_ask else 0.0
    spread_bps = (best_ask - best_bid) / mid * 10_000 if mid else None

    def notional(levels: list[tuple[float, float]], count: int) -> float:
        return sum(p * s for p, s in levels[:count])

    bands: dict[str, Any] = {}
    for name, count in (("top5", 5), ("top10", 10), ("top25", 25), ("top50", 50)):
        bid_n = notional(bids, count)
        ask_n = notional(asks, count)
        total = bid_n + ask_n
        bands[name] = {
            "bid_notional": _r(bid_n, 2),
            "ask_notional": _r(ask_n, 2),
            "imbalance": _r((bid_n - ask_n) / total, 4) if total else 0.0,
        }

    bid_median = median([p * s for p, s in bids[:100]]) if len(bids) >= 10 else 0.0
    ask_median = median([p * s for p, s in asks[:100]]) if len(asks) >= 10 else 0.0

    def walls(levels: list[tuple[float, float]], level_median: float) -> list[dict]:
        if level_median <= 0:
            return []
        candidates = [
            {"price": p, "notional": _r(p * s, 2), "x_median": _r(p * s / level_median, 2)}
            for p, s in levels[:100]
            if p * s >= 6.0 * level_median
        ]
        candidates.sort(key=lambda row: row["notional"], reverse=True)
        return candidates[:3]

    liquidity: dict[str, Any] = {}
    if mid:
        for pct in (0.1, 0.25, 0.5):
            band = mid * pct / 100
            bid_n = sum(p * s for p, s in bids if p >= mid - band)
            ask_n = sum(p * s for p, s in asks if p <= mid + band)
            total = bid_n + ask_n
            liquidity[str(pct)] = {
                "bid_notional": _r(bid_n, 2),
                "ask_notional": _r(ask_n, 2),
                "imbalance": _r((bid_n - ask_n) / total, 4) if total else 0.0,
            }

    return {
        "is_real": True,
        "ts": int(_safe_float(book.get("ts"))) or int(time.time() * 1000),
        "mid": _r(mid, 8) if mid else None,
        "spread_bps": _r(spread_bps, 4) if spread_bps is not None else None,
        "best_bid": best_bid,
        "best_ask": best_ask,
        "levels": {"bids": len(bids), "asks": len(asks)},
        "bands": bands,
        "walls": {"bids": walls(bids, bid_median), "asks": walls(asks, ask_median)},
        "liquidity_within_pct": liquidity,
    }


# ----------------------------------------------------------------- filters
def apply_filters(price: float, flow: dict, vp: dict, l2: dict, fp: dict) -> dict:
    rows: list[dict] = []
    score = 0.0

    delta = float(flow.get("delta") or 0.0)
    delta_signal = "buy_pressure" if delta >= 0.12 else "sell_pressure" if delta <= -0.12 else "neutral"
    contribution = 0.30 * (1 if delta_signal == "buy_pressure" else -1 if delta_signal == "sell_pressure" else 0)
    score += contribution
    rows.append({"name": "delta", "value": _r(delta), "signal": delta_signal, "weight": 0.30, "contribution": _r(contribution)})

    l2_imbalance = ((l2.get("bands") or {}).get("top25") or {}).get("imbalance")
    l2_signal = "bid_heavy" if (l2_imbalance or 0) >= 0.15 else "ask_heavy" if (l2_imbalance or 0) <= -0.15 else "neutral"
    contribution = 0.20 * (1 if l2_signal == "bid_heavy" else -1 if l2_signal == "ask_heavy" else 0)
    score += contribution
    rows.append({"name": "l2_imbalance_top25", "value": l2_imbalance, "signal": l2_signal, "weight": 0.20, "contribution": _r(contribution)})

    totals = fp.get("totals") or {}
    stacked_buy = int(totals.get("max_stacked_buy") or 0)
    stacked_sell = int(totals.get("max_stacked_sell") or 0)
    if stacked_buy >= 3 and stacked_buy > stacked_sell:
        fp_signal = "stacked_buy_imbalance"
        contribution = 0.15
    elif stacked_sell >= 3 and stacked_sell > stacked_buy:
        fp_signal = "stacked_sell_imbalance"
        contribution = -0.15
    else:
        fp_signal = "neutral"
        contribution = 0.0
    score += contribution
    rows.append({"name": "footprint_stacked", "value": {"buy": stacked_buy, "sell": stacked_sell}, "signal": fp_signal, "weight": 0.15, "contribution": _r(contribution)})

    poc = vp.get("poc")
    if poc and price:
        if price > poc:
            vp_signal = "above_poc"
            contribution = 0.10
        else:
            vp_signal = "below_poc"
            contribution = -0.10
    else:
        vp_signal = "unknown"
        contribution = 0.0
    score += contribution
    vah, val = vp.get("vah"), vp.get("val")
    if price and vah and val:
        if price > vah:
            vp_signal = "extended_above_value"
        elif price < val:
            vp_signal = "extended_below_value"
        else:
            vp_signal = f"{vp_signal}_inside_value"
    rows.append({"name": "vp_position", "value": {"price": price, "poc": poc, "vah": vah, "val": val}, "signal": vp_signal, "weight": 0.10, "contribution": _r(contribution)})

    divergence = flow.get("cvd_divergence")
    if divergence == "bullish":
        contribution = 0.15
    elif divergence == "bearish":
        contribution = -0.15
    else:
        contribution = 0.0
    score += contribution
    rows.append({"name": "cvd_divergence", "value": divergence, "signal": divergence or "none", "weight": 0.15, "contribution": _r(contribution)})

    if flow.get("absorption"):
        rows.append({"name": "absorption", "value": True, "signal": "absorption_caution", "weight": 0.0, "contribution": 0.0})
    if flow.get("climax"):
        rows.append({"name": "climax", "value": True, "signal": "climax_caution", "weight": 0.0, "contribution": 0.0})

    score = max(-1.0, min(1.0, score))
    net_bias = "bullish" if score >= 0.18 else "bearish" if score <= -0.18 else "neutral"
    return {
        "net_bias": net_bias,
        "score": _r(score, 4),
        "rows": rows,
        "note": "Deterministic filters computed from real exchange data; informational only.",
    }


# ------------------------------------------------------------------ views
def compact_micro(payload: dict) -> dict:
    if not payload.get("is_real"):
        return {
            "is_real": False,
            "source": payload.get("source"),
            "confidence": payload.get("confidence"),
            "timeframe": payload.get("timeframe"),
            "fallback_reason": payload.get("fallback_reason"),
            "filters": {"net_bias": "neutral", "score": 0.0, "rows": []},
        }
    vp = payload.get("volume_profile") or {}
    l2 = payload.get("level2") or {}
    fp = payload.get("footprint") or {}
    flow = payload.get("order_flow") or {}
    candles = fp.get("candles") or []
    last_candle = candles[-1] if candles else {}
    totals = fp.get("totals") or {}
    window = payload.get("window") or {}
    top25 = ((l2.get("bands") or {}).get("top25") or {})
    bid_walls = ((l2.get("walls") or {}).get("bids") or [])
    ask_walls = ((l2.get("walls") or {}).get("asks") or [])
    filters = payload.get("filters") or {}
    return {
        "is_real": True,
        "source": payload.get("source"),
        "confidence": payload.get("confidence"),
        "timeframe": payload.get("timeframe"),
        "instrument": payload.get("instrument"),
        "window_trades": window.get("trades"),
        "covered_seconds": window.get("covered_seconds"),
        "full_coverage": window.get("full_coverage"),
        "flow": {
            "delta": flow.get("delta"),
            "pressure": flow.get("pressure"),
            "cvd": flow.get("cvd"),
            "absorption": flow.get("absorption"),
            "climax": flow.get("climax"),
            "cvd_divergence": flow.get("cvd_divergence"),
        },
        "vp": {
            "poc": vp.get("poc"),
            "vah": vp.get("vah"),
            "val": vp.get("val"),
            "hvn": vp.get("hvn"),
            "lvn": vp.get("lvn"),
        },
        "footprint": {
            "candles_covered": totals.get("candles_covered"),
            "last_delta": last_candle.get("delta"),
            "last_poc": last_candle.get("poc"),
            "stacked_buy": totals.get("max_stacked_buy"),
            "stacked_sell": totals.get("max_stacked_sell"),
            "unfinished_high": (last_candle.get("unfinished") or {}).get("high"),
            "unfinished_low": (last_candle.get("unfinished") or {}).get("low"),
        },
        "l2": {
            "mid": l2.get("mid"),
            "spread_bps": l2.get("spread_bps"),
            "imbalance_top25": top25.get("imbalance"),
            "bid_wall": bid_walls[0] if bid_walls else None,
            "ask_wall": ask_walls[0] if ask_walls else None,
            "liquidity_within_pct": l2.get("liquidity_within_pct") or {},
        },
        "filters": {
            "net_bias": filters.get("net_bias"),
            "score": filters.get("score"),
            "signals": [
                f"{row.get('name')}:{row.get('signal')}"
                for row in (filters.get("rows") or [])
                if row.get("signal") not in (None, "neutral", "none")
            ],
        },
        "cached": payload.get("cached", False),
        "cache_age_seconds": payload.get("cache_age_seconds", 0.0),
    }


def build_ai_context_text(payload: dict) -> str:
    """Compact Persian context block for AI prompts, grounded in real numbers."""
    if not payload.get("is_real"):
        return (
            "⚠️ داده‌های خردساختار واقعی (L2/Footprint/Order Flow) برای این نماد در دسترس نیست؛ "
            "فقط تخمین OHLCV موجود است. در تحلیل به این موضوع صادقانه اشاره کن و اعداد واقعی جعل نکن."
        )
    instrument = payload.get("instrument") or {}
    window = payload.get("window") or {}
    flow = payload.get("order_flow") or {}
    vp = payload.get("volume_profile") or {}
    fp = payload.get("footprint") or {}
    l2 = payload.get("level2") or {}
    filters = payload.get("filters") or {}
    candles = fp.get("candles") or []
    last_candle = candles[-1] if candles else {}
    totals = fp.get("totals") or {}
    top25 = ((l2.get("bands") or {}).get("top25") or {})
    bid_walls = ((l2.get("walls") or {}).get("bids") or [])
    ask_walls = ((l2.get("walls") or {}).get("asks") or [])

    proxy_for = instrument.get("proxy_for")
    instrument_note = (
        f"{instrument.get('inst_id')} (پروکسی واقعی برای {proxy_for})"
        if proxy_for
        else str(instrument.get("inst_id"))
    )
    coverage_note = (
        "پوشش کامل پنجره"
        if window.get("full_coverage")
        else f"پوشش جزئی: آخرین {window.get('covered_seconds')} ثانیه"
    )

    def fmt(value: Any) -> str:
        if value is None:
            return "-"
        if isinstance(value, float):
            return f"{value:g}"
        return str(value)

    lines = [
        f"منبع: OKX | ابزار: {instrument_note} | اعداد واقعی هستند، نه حدس.",
        f"پنجره داده: {fmt(window.get('trades'))} معامله واقعی | {coverage_note}",
        (
            f"Order Flow: دلتا={fmt(flow.get('delta'))} | فشار={flow.get('pressure')} | CVD={fmt(flow.get('cvd'))} | "
            f"جذب (absorption)={'بله' if flow.get('absorption') else 'خیر'} | کلایمکس={'بله' if flow.get('climax') else 'خیر'} | "
            f"واگرایی CVD={flow.get('cvd_divergence') or 'ندارد'}"
        ),
        (
            f"Volume Profile: POC={fmt(vp.get('poc'))} | VAH={fmt(vp.get('vah'))} | VAL={fmt(vp.get('val'))} | "
            f"HVN={fmt((vp.get('hvn') or [None])[:2])} | LVN={fmt((vp.get('lvn') or [None])[:2])}"
        ),
        (
            f"Footprint ({payload.get('timeframe')}): دلتای آخرین کندل={fmt(last_candle.get('delta'))} | "
            f"POC کندل={fmt(last_candle.get('poc'))} | Imbalance روی‌هم: خرید={fmt(totals.get('max_stacked_buy'))} فروش={fmt(totals.get('max_stacked_sell'))} | "
            f"اتمام‌نیافته: بالا={'بله' if (last_candle.get('unfinished') or {}).get('high') else 'خیر'} پایین={'بله' if (last_candle.get('unfinished') or {}).get('low') else 'خیر'}"
        ),
        (
            f"Level-2: mid={fmt(l2.get('mid'))} | اسپرد={fmt(l2.get('spread_bps'))}bp | عدم‌توازن ۲۵ سطح={fmt(top25.get('imbalance'))} | "
            f"دیوار خرید={fmt((bid_walls[0] or {}).get('price') if bid_walls else None)} | دیوار فروش={fmt((ask_walls[0] or {}).get('price') if ask_walls else None)}"
        ),
        f"فیلترهای قطعی سیستم: بایاس خالص={filters.get('net_bias')} | امتیاز={fmt(filters.get('score'))}",
    ]
    return "\n".join(lines)
