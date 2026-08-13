from __future__ import annotations

import asyncio
import time
from typing import Any

from fastapi import Request

from .config import AppConfig
from .dispatch import dispatch
from .driver import DriverResponse, InferenceDriver
from .metrics import Metrics
from .runtime import BackendRuntime, ResponseCache, Router, TenantGuard
from .vllm_driver import LocalVLLMDriver


class Gateway:
    def __init__(self, config: AppConfig, driver: InferenceDriver | None = None):
        self.config = config
        self.router = Router(config)
        self.cache = ResponseCache(config.cache.ttl_seconds, config.cache.max_entries)
        self.guard = TenantGuard(config)
        self.metrics = Metrics()
        self.driver: InferenceDriver = driver or LocalVLLMDriver()
        self.health_task: asyncio.Task | None = None

    async def close(self):
        if self.health_task:
            self.health_task.cancel()
            await asyncio.gather(self.health_task, return_exceptions=True)

    async def health_loop(self):
        while True:
            self.check_health()
            await asyncio.sleep(self.config.health_interval_seconds)

    def check_health(self):
        now = time.time()
        for runtime in self.router.backends.values():
            runtime.healthy = runtime.config.enabled
            runtime.last_health_at = now

    @staticmethod
    def tenant_key(request: Request) -> str | None:
        return request.headers.get("x-rooom-api-key")

    async def send(
        self,
        path: str,
        body: dict[str, Any],
        runtime: BackendRuntime,
        upstream_model: str,
        request_id: str,
    ) -> DriverResponse:
        payload = dict(body)
        payload["model"] = upstream_model
        started = time.perf_counter()
        runtime.in_flight += 1
        self.metrics.inflight.labels(runtime.config.name).set(runtime.in_flight)
        try:
            result = await self.driver.infer(
                runtime, path, payload, request_id
            )
            elapsed = time.perf_counter() - started
            self.metrics.latency.labels(runtime.config.name, path).observe(elapsed)
            if result.status_code >= 500 or result.status_code == 429:
                runtime.record_failure(
                    self.config, f"engine status {result.status_code}"
                )
            else:
                runtime.record_success(elapsed * 1000)
            return result
        except Exception as exc:
            runtime.record_failure(self.config, str(exc))
            raise
        finally:
            runtime.in_flight = max(0, runtime.in_flight - 1)
            self.metrics.inflight.labels(runtime.config.name).set(runtime.in_flight)

    async def execute(
        self, request: Request, path: str, body: dict[str, Any]
    ):
        return await dispatch(self, request, path, body)
