# RooomVLLM

RooomVLLM is an adaptive control plane built directly on the vLLM Python engine.

Implemented: OpenAI-style chat/completions, latency/load/cost routing, model aliases, fallback, circuit breaker, hedged non-streaming requests, TTL cache, tenant limits, health/metadata APIs, route explanation, Prometheus metrics, request IDs, CI, and GPU-free control-plane tests.

This is a production-oriented MVP. It does not claim higher GPU throughput than NVIDIA NIM until both are benchmarked with the same model, GPU, precision, concurrency, and request mix.

Current local inference endpoints are `/v1/chat/completions` and `/v1/completions`. Streaming, embeddings, Responses, and Messages are roadmap items.

## Run

Docker is the recommended path; the Dockerfile is based on the official vLLM image. For a local Python install, install a compatible vLLM 0.26 release first, then install this package with `pip install -e .`.

Copy `config.example.yaml` to `config.yaml`, set `ROOOMVLLM_CONFIG=config.yaml`, and run `rooomvllm`.

Routing policy can be selected with `X-Rooom-Route: balanced`, `latency`, or `cost`.

## Roadmap

AsyncLLM streaming, embeddings, Responses/Messages, KV-cache-aware routing, budget enforcement, OpenTelemetry, OIDC/RBAC/mTLS, Kubernetes GPU discovery, Run:ai/OpenShift/KServe profiles, and a reproducible vLLM/RooomVLLM/NIM benchmark.

License: Apache-2.0.
