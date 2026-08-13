from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator


class BackendConfig(BaseModel):
    name: str
    base_url: str
    api_key: str | None = None
    models: list[str] = Field(default_factory=lambda: ["*"])
    default_model: str | None = None
    model_aliases: dict[str, str] = Field(default_factory=dict)
    priority: int = 100
    weight: float = 1.0
    max_concurrency: int = 64
    timeout_s: float = 120.0
    health_path: str = "/health"
    enabled: bool = True
    cost_input_per_million: float = 0.0
    cost_output_per_million: float = 0.0
    tags: dict[str, str] = Field(default_factory=dict)

    @field_validator("base_url")
    @classmethod
    def strip_base_url(cls, value: str) -> str:
        return value.rstrip("/")

    def resolve_model(self, requested: str) -> str | None:
        if requested in self.model_aliases:
            return self.model_aliases[requested]
        if requested == "auto":
            return self.default_model or (self.models[0] if self.models and self.models[0] != "*" else None)
        if "*" in self.models or requested in self.models:
            return requested
        return None


class TenantPolicy(BaseModel):
    requests_per_minute: int = 600
    max_concurrency: int = 32


class RoutingConfig(BaseModel):
    mode: Literal["balanced", "latency", "cost"] = "balanced"
    latency_weight: float = 1.0
    load_weight: float = 350.0
    cost_weight: float = 500.0
    priority_weight: float = 10.0
    hedge_delay_ms: int = 0
    failure_threshold: int = 3
    circuit_open_seconds: float = 30.0


class CacheConfig(BaseModel):
    enabled: bool = True
    ttl_seconds: int = 30
    max_entries: int = 2048


class AppConfig(BaseModel):
    version: str = "0.1.0"
    bind: str = "0.0.0.0"
    port: int = 8000
    admin_token: str | None = None
    health_interval_seconds: float = 10.0
    routing: RoutingConfig = Field(default_factory=RoutingConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    tenant_keys: dict[str, str] = Field(default_factory=dict)
    tenants: dict[str, TenantPolicy] = Field(default_factory=lambda: {"anonymous": TenantPolicy()})
    backends: list[BackendConfig]


def load_config(path: str | os.PathLike[str] | None = None) -> AppConfig:
    config_path = Path(path or os.getenv("ROOOMVLLM_CONFIG", "config.yaml"))
    with config_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return AppConfig.model_validate(raw)
