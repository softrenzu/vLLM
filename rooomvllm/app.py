from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .config import AppConfig, load_config
from .gateway import Gateway
from .routes_inference import install_inference_routes
from .routes_meta import install_meta_routes


def create_app(config: AppConfig | None = None) -> FastAPI:
    cfg = config or load_config()
    gateway = Gateway(cfg)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if cfg.health_interval_seconds > 0:
            gateway.health_task = asyncio.create_task(gateway.health_loop())
        yield
        await gateway.close()

    app = FastAPI(title="RooomVLLM", version=cfg.version, lifespan=lifespan)
    app.state.gateway = gateway

    @app.middleware("http")
    async def tenant_limit(request: Request, call_next):
        public = request.url.path.startswith("/v1/health") or request.url.path in {
            "/metrics", "/v1/metrics", "/v1/version"
        }
        if public:
            return await call_next(request)
        tenant = gateway.guard.tenant_for_key(gateway.tenant_key(request))
        if tenant == "__unauthorized__":
            return JSONResponse({"error": {"message": "Invalid API key"}}, status_code=401)
        ok, reason = await gateway.guard.acquire(tenant)
        if not ok:
            return JSONResponse({"error": {"message": reason}}, status_code=429)
        try:
            response = await call_next(request)
            response.headers["x-rooom-tenant"] = tenant
            return response
        finally:
            await gateway.guard.release(tenant)

    install_meta_routes(app, gateway, cfg)
    install_inference_routes(app, gateway)
    return app
