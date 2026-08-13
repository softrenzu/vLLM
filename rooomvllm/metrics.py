from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram


class Metrics:
    def __init__(self):
        self.registry = CollectorRegistry()
        self.requests = Counter("rooomvllm_requests_total", "Requests", ["path", "backend", "status"], registry=self.registry)
        self.latency = Histogram("rooomvllm_engine_latency_seconds", "Engine latency", ["backend", "path"], registry=self.registry)
        self.fallbacks = Counter("rooomvllm_fallbacks_total", "Fallbacks", ["path"], registry=self.registry)
        self.cache_hits = Counter("rooomvllm_cache_hits_total", "Cache hits", ["path"], registry=self.registry)
        self.inflight = Gauge("rooomvllm_backend_inflight", "Backend inflight", ["backend"], registry=self.registry)
