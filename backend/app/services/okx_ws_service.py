"""OKX WebSocket live feed — trades + orderbook L2 400, <1s latency.

Polling via REST is 10-20s. This service keeps a persistent WebSocket to
wss://ws.okx.com:8443/ws/v5/public and caches the latest 500 trades and 400
levels per instrument. OrderFlowService will prefer this cache when fresh
(<2s). If WebSocket disconnects, it falls back to REST honestly — no fake data.

Requires `websockets` (already in requirements.txt). Runs as a background
asyncio task; Render free tier may sleep — on wake, it reconnects.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from typing import Any

import websockets

OKX_WS_PUBLIC = "wss://ws.okx.com:8443/ws/v5/public"
# Also support alternative: ws.okx.com:8443
MAX_TRADES_CACHE = 600
MAX_BOOKS_CACHE = 1  # only latest book

class OkxWsService:
    def __init__(self) -> None:
        self._trades: dict[str, deque] = {}  # instId -> deque of trades
        self._books: dict[str, dict] = {}  # instId -> latest book dict
        self._last_update: dict[str, float] = {}  # instId -> monotonic
        self._lock = asyncio.Lock()
        self._task: asyncio.Task | None = None
        self._subscribed: set[str] = set()
        self._running = False

    async def ensure_subscribed(self, inst_id: str) -> None:
        async with self._lock:
            if inst_id in self._subscribed:
                return
            self._subscribed.add(inst_id)
            if not self._running:
                self._running = True
                self._task = asyncio.create_task(self._run())

    async def get_cached(self, inst_id: str, max_age_s: float = 2.0) -> tuple[list[dict] | None, dict | None]:
        async with self._lock:
            last = self._last_update.get(inst_id, 0)
            if time.monotonic() - last > max_age_s:
                return None, None
            trades = list(self._trades.get(inst_id, deque())) if inst_id in self._trades else None
            book = self._books.get(inst_id)
            return trades, book

    def is_fresh(self, inst_id: str, max_age_s: float = 2.0) -> bool:
        last = self._last_update.get(inst_id, 0)
        return (time.monotonic() - last) <= max_age_s

    async def _run(self) -> None:
        backoff = 1.0
        while self._running:
            try:
                async with websockets.connect(OKX_WS_PUBLIC, ping_interval=20, ping_timeout=10) as ws:
                    # subscribe to all current instruments
                    async with self._lock:
                        pending = list(self._subscribed)
                    if pending:
                        args = []
                        for inst in pending:
                            args.append({"channel": "trades", "instId": inst})
                            args.append({"channel": "books", "instId": inst})
                        await ws.send(json.dumps({"op": "subscribe", "args": args}))
                    backoff = 1.0
                    async for raw in ws:
                        try:
                            msg = json.loads(raw)
                        except Exception:
                            continue
                        # OKX trades/books format
                        data = msg.get("data")
                        arg = msg.get("arg") or {}
                        channel = arg.get("channel")
                        inst = arg.get("instId")
                        if not inst or not data:
                            # handle subscription confirmation or event
                            if msg.get("event") == "subscribe":
                                continue
                            # trades from books channel may have different structure
                            continue
                        async with self._lock:
                            # allow dynamic new subscriptions without reconnect
                            # check if new inst added while running
                            current_subs = set(self._subscribed)
                            # if new inst not yet subscribed, send subscribe
                            # (simple: on next loop we will handle, but also handle now)
                            # update cache
                            if channel == "trades":
                                dq = self._trades.setdefault(inst, deque(maxlen=MAX_TRADES_CACHE))
                                for tr in data:
                                    # normalize to REST shape: px, sz, side, ts, tradeId
                                    dq.appendleft({
                                        "px": tr.get("px"),
                                        "sz": tr.get("sz"),
                                        "side": tr.get("side"),
                                        "ts": tr.get("ts"),
                                        "tradeId": tr.get("tradeId") or tr.get("id") or "",
                                    })
                                self._last_update[inst] = time.monotonic()
                            elif channel == "books":
                                # books: data is list of {bids, asks, ts}
                                book = data[0] if isinstance(data, list) and data else data
                                if isinstance(book, dict) and "bids" in book:
                                    self._books[inst] = book
                                    self._last_update[inst] = time.monotonic()
                            # check for new subscriptions that arrived after initial subscribe
                            new_insts = current_subs - set([a.get("instId") for a in args]) if 'args' in locals() else set()
                            if new_insts:
                                new_args = []
                                for ni in new_insts:
                                    new_args.append({"channel": "trades", "instId": ni})
                                    new_args.append({"channel": "books", "instId": ni})
                                try:
                                    await ws.send(json.dumps({"op": "subscribe", "args": new_args}))
                                    args.extend(new_args)
                                except Exception:
                                    pass
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 1.8, 30.0)
                # re-subscribe on reconnect
                continue

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

# Global singleton
okx_ws_service = OkxWsService()
