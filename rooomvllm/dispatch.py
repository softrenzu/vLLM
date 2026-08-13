from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, Request
from fastapi.responses import Response

from .driver import DriverResponse
from .hedge import hedge_first_two
from .runtime import BackendRuntime

if TYPE_CHECKING:
    from .gateway import Gateway

CACHEABLE = {"/v1/chat/completions", "/v1/completions", "/v1/responses"}


async def dispatch(
    gateway: "Gateway", request: Request, path: str, body: dict[str, Any]
) -> Response:
    if body.get("stream"):
        raise HTTPException(501, "Streaming is not implemented by the local vLLM driver yet")

    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    model = str(body.get("model") or "auto")
    mode = request.headers.get("x-rooom-route", gateway.config.routing.mode)
    ranked = gateway.router.ranked(model, body, mode)
    if not ranked:
        raise HTTPException(503, f"No healthy backend can serve model '{model}'")

    cache_key = None
    if gateway.config.cache.enabled and path in CACHEABLE:
        cache_key = gateway.cache.key("POST", path, body)
        hit = await gateway.cache.get(cache_key)
        if hit:
            content, status, headers = hit
            gateway.metrics.cache_hits.labels(path).inc()
            headers = dict(headers) | {
                "x-rooom-cache": "hit", "x-rooom-request-id": request_id
            }
            return Response(content, status, headers=headers, media_type="application/json")

    candidates = list(ranked)
    response: DriverResponse | None = None
    used: BackendRuntime | None = None
    fallback_count = 0

    if (
        gateway.config.routing.hedge_delay_ms > 0
        and len(candidates) > 1
        and path in CACHEABLE
    ):
        response, used, candidates = await hedge_first_two(
            gateway, path, body, candidates, request_id
        )

    if response is None:
        for runtime, upstream_model, _ in candidates:
            try:
                result = await gateway.send(
                    path, body, runtime, upstream_model, request_id
                )
                if result.status_code < 500 and result.status_code != 429:
                    response, used = result, runtime
                    break
            except Exception:
                pass
            fallback_count += 1
            gateway.metrics.fallbacks.labels(path).inc()

    if response is None or used is None:
        raise HTTPException(503, "All matching vLLM engine profiles failed")

    headers = dict(response.headers) | {
        "x-rooom-backend": used.config.name,
        "x-rooom-request-id": request_id,
        "x-rooom-fallbacks": str(fallback_count),
        "x-rooom-cache": "miss" if cache_key else "bypass",
    }
    gateway.metrics.requests.labels(
        path, used.config.name, str(response.status_code)
    ).inc()
    if cache_key and response.status_code < 300:
        await gateway.cache.put(
            cache_key, response.content, response.status_code, headers
        )
    return Response(
        response.content,
        response.status_code,
        headers=headers,
        media_type=response.headers.get("content-type", "application/json"),
    )
