from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections import OrderedDict, defaultdict, deque
from dataclasses import dataclass
from typing import Any

from .config import AppConfig, BackendConfig, TenantPolicy


@dataclass
class BackendRuntime:
    config: BackendConfig
    ewma_latency_ms: float = 500.0
    consecutive_failures: int = 0
    open_until: float = 0.0
    in_flight: int = 0
    healthy: bool | None = None
    last_error: str | None = None
    last_health_at: float | None = None

    def is_available(self, now: float | None = None) -> bool:
        now = now or time.monotonic()
        return self.config.enabled and now >= self.open_until and self.in_flight < self.config.max_concurrency and self.healthy is not False

    def record_success(self, latency_ms: float) -> None:
        alpha = 0.2
        self.ewma_latency_ms = latency_ms if self.ewma_latency_ms <= 0 else (alpha * latency_ms + (1 - alpha) * self.ewma_latency_ms)
        self.consecutive_failures = 0
        self.last_error = None
        self.healthy = True

    def record_failure(self, config: AppConfig, error: str) -> None:
        self.consecutive_failures += 1
        self.last_error = error[:500]
        if self.consecutive_failures >= config.routing.failure_threshold:
            self.open_until = time.monotonic() + config.routing.circuit_open_seconds
            self.healthy = False

    def reset_circuit(self) -> None:
        self.consecutive_failures = 0
        self.open_until = 0.0
        self.healthy = None
        self.last_error = None


class Router:
    def __init__(self, config: AppConfig):
        self.config = config
        self.backends = {b.name: BackendRuntime(b) for b in config.backends}

    @staticmethod
    def estimate_input_tokens(body: dict[str, Any]) -> int:
        if "messages" in body:
            text = json.dumps(body["messages"], ensure_ascii=False)
        else:
            text = str(body.get("prompt") or body.get("input") or "")
        return max(1, len(text) // 4)

    def _score(self, runtime: BackendRuntime, body: dict[str, Any], preference: str) -> float:
        cfg = self.config.routing
        load = runtime.in_flight / max(1, runtime.config.max_concurrency)
        est_tokens = self.estimate_input_tokens(body)
        est_cost = est_tokens / 1_000_000 * runtime.config.cost_input_per_million
        priority = runtime.config.priority * cfg.priority_weight
        weight_penalty = 100.0 / max(runtime.config.weight, 0.01)

        if preference == "latency":
            return priority + runtime.ewma_latency_ms * 2.0 + load * cfg.load_weight + est_cost * 50.0 + weight_penalty
        if preference == "cost":
            return priority + runtime.ewma_latency_ms * 0.2 + load * cfg.load_weight + est_cost * 5000.0 + weight_penalty
        return priority + runtime.ewma_latency_ms * cfg.latency_weight + load * cfg.load_weight + est_cost * cfg.cost_weight + weight_penalty

    def ranked(self, requested_model: str, body: dict[str, Any], preference: str | None = None) -> list[tuple[BackendRuntime, str, float]]:
        preference = preference if preference in {"balanced", "latency", "cost"} else self.config.routing.mode
        ranked: list[tuple[BackendRuntime, str, float]] = []
        for runtime in self.backends.values():
            resolved = runtime.config.resolve_model(requested_model)
            if resolved is None or not runtime.is_available():
                continue
            ranked.append((runtime, resolved, self._score(runtime, body, preference)))
        ranked.sort(key=lambda x: (x[2], x[0].config.name))
        return ranked

    def explain(self, requested_model: str, body: dict[str, Any], preference: str | None = None) -> list[dict[str, Any]]:
        chosen = self.ranked(requested_model, body, preference)
        return [
            {
                "backend": rt.config.name,
                "upstream_model": upstream_model,
                "score": round(score, 4),
                "ewma_latency_ms": round(rt.ewma_latency_ms, 2),
                "in_flight": rt.in_flight,
                "max_concurrency": rt.config.max_concurrency,
                "estimated_input_tokens": self.estimate_input_tokens(body),
                "cost_input_per_million": rt.config.cost_input_per_million,
            }
            for rt, upstream_model, score in chosen
        ]


class ResponseCache:
    def __init__(self, ttl_seconds: int, max_entries: int):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._data: OrderedDict[str, tuple[float, bytes, int, dict[str, str]]] = OrderedDict()
        self._lock = asyncio.Lock()

    @staticmethod
    def key(method: str, path: str, body: dict[str, Any]) -> str:
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(f"{method}\n{path}\n{canonical}".encode("utf-8")).hexdigest()

    async def get(self, key: str) -> tuple[bytes, int, dict[str, str]] | None:
        async with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            expires_at, content, status, headers = item
            if expires_at <= time.monotonic():
                self._data.pop(key, None)
                return None
            self._data.move_to_end(key)
            return content, status, headers

    async def put(self, key: str, content: bytes, status: int, headers: dict[str, str]) -> None:
        async with self._lock:
            self._data[key] = (time.monotonic() + self.ttl_seconds, content, status, headers)
            self._data.move_to_end(key)
            while len(self._data) > self.max_entries:
                self._data.popitem(last=False)


class TenantGuard:
    def __init__(self, config: AppConfig):
        self.config = config
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._inflight: dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    def tenant_for_key(self, key: str | None) -> str:
        if not self.config.tenant_keys:
            return "anonymous"
        if key and key in self.config.tenant_keys:
            return self.config.tenant_keys[key]
        return "__unauthorized__"

    def policy(self, tenant: str) -> TenantPolicy:
        return self.config.tenants.get(tenant) or self.config.tenants.get("anonymous") or TenantPolicy()

    async def acquire(self, tenant: str) -> tuple[bool, str | None]:
        policy = self.policy(tenant)
        now = time.monotonic()
        async with self._lock:
            q = self._requests[tenant]
            while q and q[0] < now - 60:
                q.popleft()
            if len(q) >= policy.requests_per_minute:
                return False, "rate_limit"
            if self._inflight[tenant] >= policy.max_concurrency:
                return False, "concurrency_limit"
            q.append(now)
            self._inflight[tenant] += 1
            return True, None

    async def release(self, tenant: str) -> None:
        async with self._lock:
            self._inflight[tenant] = max(0, self._inflight[tenant] - 1)
