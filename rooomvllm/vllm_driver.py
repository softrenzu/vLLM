from __future__ import annotations

import asyncio
from typing import Any

from .driver import DriverResponse
from .format_openai import chat, completion
from .runtime import BackendRuntime


class LocalVLLMDriver:
    """Lazy in-process vLLM driver."""

    def __init__(self):
        self._engines: dict[str, Any] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    @staticmethod
    def model_name(backend: BackendRuntime) -> str:
        cfg = backend.config
        model = cfg.default_model or next((m for m in cfg.models if m != "*"), None)
        if not model:
            raise RuntimeError(f"Backend {cfg.name} has no concrete model")
        return model

    async def engine(self, backend: BackendRuntime):
        name = backend.config.name
        if name in self._engines:
            return self._engines[name]
        lock = self._locks.setdefault(name, asyncio.Lock())
        async with lock:
            if name not in self._engines:
                self._engines[name] = await asyncio.to_thread(self._load, backend)
        return self._engines[name]

    def _load(self, backend: BackendRuntime):
        from vllm import LLM

        kwargs = {}
        kwargs.setdefault("model", self.model_name(backend))
        kwargs.setdefault("generation_config", "vllm")
        return LLM(**kwargs)

    @staticmethod
    def sampling(body: dict[str, Any]):
        from vllm import SamplingParams

        names = {
            "n", "best_of", "presence_penalty", "frequency_penalty",
            "repetition_penalty", "temperature", "top_p", "top_k", "min_p",
            "seed", "stop", "stop_token_ids", "ignore_eos", "max_tokens",
            "min_tokens", "logprobs", "prompt_logprobs", "skip_special_tokens",
        }
        return SamplingParams(**{k: body[k] for k in names if body.get(k) is not None})

    @staticmethod
    def messages(body: dict[str, Any]) -> list[dict[str, Any]]:
        if isinstance(body.get("messages"), list):
            return body["messages"]
        if isinstance(body.get("input"), list):
            return body["input"]
        return [{"role": "user", "content": str(body.get("input") or "")}]

    def run(self, engine: Any, path: str, body: dict[str, Any], model: str, request_id: str) -> DriverResponse:
        params = self.sampling(body)
        if path == "/v1/completions":
            output = engine.generate(body.get("prompt", ""), params, use_tqdm=False)[0]
            return completion(output, model, request_id)
        output = engine.chat(self.messages(body), params, use_tqdm=False)[0]
        return chat(output, model, request_id)

    async def infer(self, backend: BackendRuntime, path: str, body: dict[str, Any], request_id: str) -> DriverResponse:
        supported = {"/v1/chat/completions", "/v1/completions"}
        if path not in supported:
            return DriverResponse(
                501,
                b'{"error":{"message":"Endpoint not implemented by local driver"}}',
                {"content-type": "application/json"},
            )
        engine = await self.engine(backend)
        model = backend.config.resolve_model(str(body.get("model") or "auto")) or self.model_name(backend)
        return await asyncio.to_thread(self.run, engine, path, body, model, request_id)
