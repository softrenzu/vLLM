from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import generate_latest

from .config import AppConfig
from .gateway import Gateway


def install_meta_routes(app: FastAPI, gateway: Gateway, cfg: AppConfig) -> None:
    @app.get("/v1/health/live")
    async def live():
        return {"status": "live", "version": cfg.version}

    @app.get("/v1/health/ready")
    async def ready():
        names = [rt.config.name for rt in gateway.router.backends.values() if rt.is_available()]
        return JSONResponse(
            {"status": "ready" if names else "not_ready", "backends": names},
            status_code=200 if names else 503,
        )

    @app.get("/v1/version")
    async def version():
        return {"name": "RooomVLLM", "version": cfg.version}

    @app.get("/v1/metadata")
    async def metadata():
        return {
            "name": "RooomVLLM",
            "version": cfg.version,
            "routing_mode": cfg.routing.mode,
            "features": [
                "adaptive-routing", "fallback", "circuit-breaker",
                "hedged-requests", "response-cache",
                "multi-tenant-guard", "prometheus",
            ],
        }

    @app.get("/v1/manifest")
    async def manifest():
        return {
            "backends": [b.model_dump(exclude={"api_key"}) for b in cfg.backends],
            "routing": cfg.routing.model_dump(),
        }

    @app.get("/v1/models")
    async def models():
        ids = sorted(
            {m for b in cfg.backends for m in b.models if m != "*"}
            | {a for b in cfg.backends for a in b.model_aliases}
        )
        return {
            "object": "list",
            "data": [{"id": m, "object": "model", "owned_by": "rooomvllm"} for m in ids],
        }

    @app.get("/metrics")
    @app.get("/v1/metrics")
    async def metrics():
        return Response(generate_latest(gateway.metrics.registry), media_type="text/plain")

    @app.post("/v1/route/explain")
    async def explain(request: Request):
        body = await request.json()
        return {
            "candidates": gateway.router.explain(
                str(body.get("model") or "auto"),
                body,
                request.headers.get("x-rooom-route"),
            )
        }
