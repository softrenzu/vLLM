from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request

from .gateway import Gateway


async def _forward(gateway: Gateway, request: Request, path: str):
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "JSON object required")
    return await gateway.execute(request, path, body)


def install_inference_routes(app: FastAPI, gateway: Gateway) -> None:
    @app.post("/v1/chat/completions")
    async def chat(request: Request):
        return await _forward(gateway, request, "/v1/chat/completions")

    @app.post("/v1/completions")
    async def completions(request: Request):
        return await _forward(gateway, request, "/v1/completions")

    @app.post("/v1/embeddings")
    async def embeddings(request: Request):
        return await _forward(gateway, request, "/v1/embeddings")

    @app.post("/v1/responses")
    async def responses(request: Request):
        return await _forward(gateway, request, "/v1/responses")

    @app.post("/v1/messages")
    async def messages(request: Request):
        return await _forward(gateway, request, "/v1/messages")

    @app.post("/v1/messages/count_tokens")
    async def count_tokens(request: Request):
        return await _forward(gateway, request, "/v1/messages/count_tokens")

    @app.post("/tokenize")
    async def tokenize(request: Request):
        return await _forward(gateway, request, "/tokenize")

    @app.post("/detokenize")
    async def detokenize(request: Request):
        return await _forward(gateway, request, "/detokenize")
