from __future__ import annotations

import hashlib
import ipaddress
import json
import logging
import re
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Callable
from uuid import uuid4

from app.config import settings


_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
_HEAVY_PREFIXES = (
    "/api/v1/backtest/",
    "/api/v1/setups/scan",
    "/api/v1/signals/scan",
    "/api/v1/analysis/smc",
)


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int
    group: str


class SlidingWindowRateLimiter:
    def __init__(self, now_fn: Callable[[], float] = time.monotonic) -> None:
        self._now = now_fn
        self._events: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def policy(self, path: str) -> tuple[str, int]:
        if path in {"/api/v1/auth/login", "/api/v1/auth/register"}:
            return "auth", max(1, settings.rate_limit_auth_per_minute)
        if path == "/api/v1/ai/explain":
            return "ai", max(1, settings.rate_limit_ai_per_minute)
        if path.startswith(_HEAVY_PREFIXES):
            return "heavy", max(1, settings.rate_limit_heavy_per_minute)
        return "default", max(1, settings.rate_limit_default_per_minute)

    def check(self, identity: str, path: str) -> RateLimitDecision:
        group, limit = self.policy(path)
        now = self._now()
        cutoff = now - 60.0
        key = (identity, group)
        with self._lock:
            if key not in self._events and len(self._events) >= 20_000:
                key = ("overflow", group)
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(1, int(60.0 - (now - events[0]) + 0.999))
                return RateLimitDecision(False, limit, 0, retry_after, group)
            events.append(now)
            remaining = max(0, limit - len(events))
            if len(self._events) > 20_000:
                self._prune(cutoff)
            return RateLimitDecision(True, limit, remaining, 0, group)

    def _prune(self, cutoff: float) -> None:
        stale = []
        for key, events in self._events.items():
            while events and events[0] <= cutoff:
                events.popleft()
            if not events:
                stale.append(key)
        for key in stale:
            self._events.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


class MonitoringService:
    def __init__(self, now_fn: Callable[[], float] = time.monotonic) -> None:
        self._now = now_fn
        self.started_at = now_fn()
        self._lock = threading.Lock()
        self._requests = 0
        self._errors = 0
        self._rate_limited = 0
        self._status_counts: dict[str, int] = defaultdict(int)
        self._route_counts: dict[str, int] = defaultdict(int)
        self._latencies_ms: deque[int] = deque(maxlen=2000)

    def record(self, route: str, status_code: int, latency_ms: int) -> None:
        safe_route = route[:160] if route else "unknown"
        with self._lock:
            self._requests += 1
            if status_code >= 500:
                self._errors += 1
            self._status_counts[str(status_code)] += 1
            self._route_counts[safe_route] += 1
            self._latencies_ms.append(max(0, latency_ms))

    def record_rate_limited(self) -> None:
        with self._lock:
            self._rate_limited += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            latencies = sorted(self._latencies_ms)
            p95 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))] if latencies else 0
            average = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
            return {
                "uptime_seconds": max(0, int(self._now() - self.started_at)),
                "requests_total": self._requests,
                "server_errors_total": self._errors,
                "rate_limited_total": self._rate_limited,
                "latency_average_ms": average,
                "latency_p95_ms": p95,
                "status_counts": dict(self._status_counts),
                "route_counts": dict(sorted(self._route_counts.items())),
                "sample_window": len(latencies),
            }


def request_id(value: str | None) -> str:
    candidate = (value or "").strip()
    if _REQUEST_ID_RE.fullmatch(candidate):
        return candidate
    return uuid4().hex


def client_identity(client_host: str | None, forwarded_for: str | None = None) -> str:
    host = (client_host or "unknown").strip()
    if settings.trust_proxy_headers and forwarded_for:
        candidate = forwarded_for.split(",", 1)[0].strip()
        try:
            host = str(ipaddress.ip_address(candidate))
        except ValueError:
            pass
    # Store only a stable short digest in limiter/log state, never a raw IP.
    return hashlib.sha256(host.encode("utf-8")).hexdigest()[:24]


def structured_http_log(
    logger: logging.Logger,
    *,
    req_id: str,
    method: str,
    route: str,
    status_code: int,
    latency_ms: int,
    identity: str,
    error_type: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "event": "http_request",
        "request_id": req_id,
        "method": method,
        "route": route[:160],
        "status_code": status_code,
        "latency_ms": max(0, latency_ms),
        "client_hash": identity,
    }
    if error_type:
        payload["error_type"] = error_type[:80]
    logger.info(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


rate_limiter = SlidingWindowRateLimiter()
monitoring_service = MonitoringService()
http_logger = logging.getLogger("apex.http")
