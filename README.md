# RooomInfer — Adaptive LLM Inference Control Plane

Version: `0.3.0`

RooomInfer is a source-available adaptive control plane for LLM inference clusters. It uses vLLM as one supported inference engine and adds routing, resilience, cost controls, multi-tenancy, observability, and policy features around the serving layer.

> RooomInfer is not the official vLLM project. The upstream vLLM engine and its dependencies remain governed by their own licenses.

## Core features

- OpenAI-style chat and completions endpoints
- Latency, load, cost, and policy-aware routing
- Model aliases and fallback chains
- Circuit breaker and hedged non-streaming requests
- TTL response cache
- Tenant limits and request IDs
- Route explanation and health/metadata APIs
- Prometheus-compatible metrics
- GPU-free control-plane tests

RooomInfer does not claim higher GPU throughput than NVIDIA NIM or upstream vLLM without same-hardware, same-model benchmark results.

## Run

Docker is the recommended path. The Dockerfile uses the upstream vLLM runtime image.

For a local Python install, install a compatible vLLM release first and then:

```bash
pip install -e .
cp config.example.yaml config.yaml
export ROOOMVLLM_CONFIG=config.yaml
rooom-infer
```

`rooomvllm` is retained as a compatibility command alias in the `0.3.x` line.

Routing policy can be selected with `X-Rooom-Route: balanced`, `latency`, or `cost`.

## Roadmap

- AsyncLLM streaming
- Embeddings and Responses/Messages APIs
- KV-cache-aware routing
- Budget enforcement
- OpenTelemetry
- OIDC/RBAC/mTLS
- Kubernetes GPU discovery
- Run:ai/OpenShift/KServe deployment profiles
- Reproducible RooomInfer/vLLM/NIM benchmarks

## Licensing and enterprise support

Starting with version `0.3.0`, ROOOMTECH-authored code is offered under either the PolyForm Noncommercial License 1.0.0 for uses permitted by that license, or a separate paid ROOOMTECH Commercial Software License for business/commercial-purpose uses and other uses outside the PolyForm permission.

ROOOMTECH provides commercial license agreements, paid maintenance and technical support, implementation and integration assistance, upgrades, security support, SLA options, private builds, and custom development.

Contact: `support@rooomtech.com`

PolyForm Noncommercial License 1.0.0: https://polyformproject.org/licenses/noncommercial/1.0.0

Earlier RooomInfer/RooomVLLM releases remain governed by the license terms published with those releases. Upstream vLLM and all third-party software remain under their respective licenses. See `LICENSE`.
