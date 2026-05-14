"""OpenTelemetry tracing setup (blueprint Part 14.2).

Uses OTLP/gRPC exporter to the sidecar collector. Also exposes a thin `span`
context-manager wrapper so hot-path code doesn't import `opentelemetry` directly
(avoids a 40 ms cold import on the first decision).
"""

from __future__ import annotations

import contextlib
from typing import Iterator

from findevil.config.settings import settings

_initialized = False


def init_tracing(service_name: str = "findevil") -> None:
    """Idempotent tracer-provider setup. No-op if already initialized."""
    global _initialized
    if _initialized:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:  # OTel extras may not be installed in some environments
        _initialized = True
        return

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.instance.id": settings.host_id,
            "deployment.environment": "lab",
        }
    )
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=settings.observability.otlp_endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _initialized = True


@contextlib.contextmanager
def span(name: str, **attributes) -> Iterator[object]:
    """Create a span if OTel is initialized; otherwise a no-op context manager."""
    try:
        from opentelemetry import trace
    except ImportError:
        yield None
        return
    tracer = trace.get_tracer("findevil")
    with tracer.start_as_current_span(name) as s:
        for k, v in attributes.items():
            try:
                s.set_attribute(k, v)
            except Exception:
                pass
        yield s
