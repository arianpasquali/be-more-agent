"""OpenTelemetry tracing for bmo, exporting to orq.ai's OTLP collector.

Idempotent setup() — safe to call multiple times. Uses GenAI semantic
conventions so spans render correctly in the orq Traces UI alongside
deployment / agent traces.

Endpoint: https://api.orq.ai/v2/otel/v1/traces
Auth:     Authorization: Bearer <ORQ_API_KEY> (passed via OTEL_EXPORTER_OTLP_HEADERS)
"""

from __future__ import annotations

import logging
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

__all__ = ["get_tracer", "setup_tracing"]

log = logging.getLogger(__name__)

ORQ_OTLP_TRACES_URL = "https://api.orq.ai/v2/otel/v1/traces"

_initialized = False


def setup_tracing(orq_api_key: str, service_name: str = "bmo") -> None:
    """Configure the global tracer provider once. No-op on repeat calls."""
    global _initialized
    if _initialized:
        return
    if not orq_api_key:
        log.warning("ORQ_API_KEY missing; skipping OTel setup (no traces exported)")
        return

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(
        endpoint=ORQ_OTLP_TRACES_URL,
        headers={"Authorization": f"Bearer {orq_api_key}"},
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _initialized = True
    log.info("OTel tracing → %s (service=%s)", ORQ_OTLP_TRACES_URL, service_name)


def get_tracer(name: str = "bmo") -> Any:
    return trace.get_tracer(name)
