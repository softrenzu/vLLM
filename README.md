# RooomVLLM

RooomVLLM is an experimental control plane built directly on the vLLM Python engine. It adds enterprise serving policy while leaving model execution to vLLM.

Implemented today: OpenAI-style chat/completions, adaptive latency/load/cost routing, virtual model aliases, automatic fallback, circuit breaker, hedged non-streaming requests, TTL cache, per-tenant limits, health/metadata/model APIs, route explanation, Prometheus metrics, request IDs, CI, and GPU-free control-plane tests.

This is a production-oriented MVP. It does not claim higher GPU throughput than NVIDIA NIM without an identical-hardware benchmark. The current local driver supports `/v1/chat/completions` and `/v1/completions`; streaming, embeddings, Responses, and Messages are next milestones.

## Run

Copy `config.example.yaml` to `config.yaml`, install `pip install -e '.[engine]'`, set `ROOOMVLLM_CONFIG=config.yaml`, then run `rooomvllm`.

Use `X-Rooom-Route: balanced`, `latency`, or `cost` to change routing policy.

## Test

Install `.[dev]`, then run `python -m compileall -q rooomvllm` and `pytest -q`.

## Roadmap

AsyncLLM token streaming, embeddings, full Responses/Messages support, KV-cache-aware routing, token/dollar budgets, OpenTelemetry, OIDC/RBAC/mTLS, Kubernetes GPU discovery, Run:ai/OpenShift/KServe profiles, and a reproducible direct-vLLM/RooomVLLM/NIM benchmark.

License: Apache-2.0.
