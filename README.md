# RooomVLLM

RooomVLLM is a production control plane and adaptive OpenAI-compatible gateway for vLLM clusters.

It adds adaptive latency/load/cost routing, automatic fallback, circuit breaking, hedged requests, response caching, multi-tenant limits, NIM-style health/metadata endpoints, Prometheus metrics, Docker packaging, and Helm deployment while keeping vLLM as the inference engine.

Status: early production-oriented MVP. Control-plane behavior is GPU-free tested; GPU performance depends on the underlying vLLM/model/hardware deployment.

## Core features

- OpenAI-compatible proxy for chat completions, completions, embeddings, Responses API, and Anthropic-style Messages pass-through
- Adaptive `balanced`, `latency`, and `cost` routing
- Virtual model aliases and `model=auto`
- Automatic fallback and circuit breaker
- Hedged requests to reduce p95/p99 latency
- Exact response cache with TTL
- Per-tenant RPM and concurrency limits
- `/v1/health/live`, `/v1/health/ready`, `/v1/version`, `/v1/metadata`, `/v1/manifest`, `/v1/license`
- `/metrics` and `/v1/metrics` Prometheus endpoints
- `POST /v1/route/explain` for routing inspection
- Docker and Kubernetes/Helm deployment
- GPU-free mock-backend tests

## Quick start

```bash
cp config.example.yaml config.yaml
pip install -e .
ROOOMVLLM_CONFIG=config.yaml rooomvllm
```

## Kubernetes / Helm

```bash
helm upgrade --install rooomvllm deploy/helm/rooomvllm \
  --set image.repository=YOUR_REGISTRY/rooomvllm \
  --set image.tag=YOUR_TAG
```

## Validation

```bash
pip install -e '.[dev]'
pytest -q
ruff check rooomvllm tests
```

## License

Apache-2.0.
