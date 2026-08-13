import json

from fastapi.testclient import TestClient

from rooomvllm.app import create_app
from rooomvllm.config import AppConfig, BackendConfig, CacheConfig, RoutingConfig
from rooomvllm.driver import DriverResponse


def build_config() -> AppConfig:
    return AppConfig(
        health_interval_seconds=0,
        routing=RoutingConfig(hedge_delay_ms=0, failure_threshold=1),
        cache=CacheConfig(enabled=True, ttl_seconds=30, max_entries=20),
        backends=[
            BackendConfig(name="first", base_url="local://first", models=["m"], default_model="m", priority=1),
            BackendConfig(name="second", base_url="local://second", models=["m"], default_model="m", priority=2),
        ],
    )


class FakeDriver:
    def __init__(self):
        self.calls = {"first": 0, "second": 0}

    async def infer(self, backend, path, body, request_id):
        name = backend.config.name
        self.calls[name] += 1
        if name == "first":
            return DriverResponse(500, b'{"error":"failed"}', {"content-type": "application/json"})
        payload = {"id": "ok", "choices": [{"text": "hello"}], "usage": {"total_tokens": 2}}
        return DriverResponse(200, json.dumps(payload).encode(), {"content-type": "application/json"})


def test_health_and_metadata():
    app = create_app(build_config())
    with TestClient(app) as client:
        assert client.get("/v1/health/live").status_code == 200
        assert client.get("/v1/health/ready").status_code == 200
        metadata = client.get("/v1/metadata").json()
        assert metadata["name"] == "RooomVLLM"
        assert "adaptive-routing" in metadata["features"]


def test_fallback_and_cache():
    app = create_app(build_config())
    driver = FakeDriver()
    app.state.gateway.driver = driver
    with TestClient(app) as client:
        r1 = client.post("/v1/completions", json={"model": "m", "prompt": "hello"})
        assert r1.status_code == 200
        assert r1.headers["x-rooom-backend"] == "second"
        assert r1.headers["x-rooom-fallbacks"] == "1"
        r2 = client.post("/v1/completions", json={"model": "m", "prompt": "hello"})
        assert r2.status_code == 200
        assert r2.headers["x-rooom-cache"] == "hit"
        assert driver.calls == {"first": 1, "second": 1}


def test_tenant_authentication():
    config = build_config()
    config.tenant_keys = {"good-key": "team-a"}
    config.tenants["team-a"] = config.tenants["anonymous"]
    app = create_app(config)
    with TestClient(app) as client:
        assert client.get("/v1/models").status_code == 401
        assert client.get("/v1/models", headers={"X-Rooom-API-Key": "good-key"}).status_code == 200
