# observability.py — request tracing, timing, and LLM metrics
from __future__ import annotations

import time
import uuid
from collections import defaultdict

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

log = structlog.get_logger()

# In-memory metrics store (replace with Prometheus client in production)
_metrics: dict[str, list[float]] = defaultdict(list)
_MAX_METRICS = 1000  # keep last N entries per metric


def record_metric(name: str, value: float) -> None:
    """Record a metric value. Thread-safe enough for single-process."""
    bucket = _metrics[name]
    bucket.append(value)
    if len(bucket) > _MAX_METRICS:
        _metrics[name] = bucket[-_MAX_METRICS:]


def get_metrics_snapshot() -> dict[str, dict[str, float]]:
    """Return current metrics with avg/p95/count per metric name."""
    snapshot = {}
    for name, values in _metrics.items():
        if not values:
            continue
        sorted_vals = sorted(values)
        count = len(sorted_vals)
        snapshot[name] = {
            "count": count,
            "avg": sum(sorted_vals) / count,
            "p50": sorted_vals[count // 2],
            "p95": sorted_vals[int(count * 0.95)] if count > 1 else sorted_vals[0],
            "max": sorted_vals[-1],
        }
    return snapshot


def format_prometheus_metrics() -> str:
    """Format metrics in Prometheus text exposition format."""
    lines: list[str] = []
    for name, values in _metrics.items():
        if not values:
            continue
        safe_name = name.replace(".", "_").replace("-", "_")
        sorted_vals = sorted(values)
        count = len(sorted_vals)
        total = sum(sorted_vals)

        lines.append(f"# HELP {safe_name} {name}")
        lines.append(f"# TYPE {safe_name} summary")
        lines.append(f'{safe_name}_count {count}')
        lines.append(f'{safe_name}_sum {total:.2f}')
        lines.append(f'{safe_name}{{quantile="0.5"}} {sorted_vals[count // 2]:.2f}')
        lines.append(f'{safe_name}{{quantile="0.95"}} {sorted_vals[int(count * 0.95)]:.2f}')
        lines.append(f'{safe_name}{{quantile="1.0"}} {sorted_vals[-1]:.2f}')
    return "\n".join(lines) + "\n"


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Middleware that adds trace IDs, request timing, and structured logging."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4())[:8])
        start = time.perf_counter()

        # Bind trace_id to structlog context for this request
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(trace_id=trace_id)

        response: Response
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            record_metric("http.request.duration_ms", duration_ms)
            log.error(
                "http.request.error",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 1),
            )
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        record_metric("http.request.duration_ms", duration_ms)
        record_metric(f"http.status.{response.status_code}", 1)

        # Add trace ID to response headers
        response.headers["X-Trace-Id"] = trace_id
        response.headers["X-Response-Time"] = f"{duration_ms:.1f}ms"

        # Log request (skip health checks and metrics)
        if request.url.path not in ("/health", "/metrics"):
            log.info(
                "http.request",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=round(duration_ms, 1),
            )

        return response


def record_llm_metric(
    provider: str,
    latency_ms: float,
    input_tokens_est: int = 0,
    quality_score: float = 0.0,
    cache_hit: bool = False,
) -> None:
    """Record LLM-specific metrics."""
    record_metric(f"llm.{provider}.latency_ms", latency_ms)
    record_metric(f"llm.{provider}.input_tokens_est", input_tokens_est)
    if quality_score > 0:
        record_metric(f"llm.{provider}.quality_score", quality_score)
    record_metric("llm.cache_hit", 1.0 if cache_hit else 0.0)

    log.info(
        "llm.call",
        provider=provider,
        latency_ms=round(latency_ms, 1),
        input_tokens_est=input_tokens_est,
        quality_score=round(quality_score, 2),
        cache_hit=cache_hit,
    )
