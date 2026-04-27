"""OpenTelemetry tracing for bmo, exporting to orq.ai's OTLP collector.

Idempotent setup() — safe to call multiple times. Uses GenAI semantic
conventions so spans render correctly in the orq Traces UI alongside
deployment / agent traces.

Endpoint: https://api.orq.ai/v2/otel/v1/traces
Auth:     Authorization: Bearer <ORQ_API_KEY> (passed via OTEL_EXPORTER_OTLP_HEADERS)
"""

from __future__ import annotations

import logging
import os
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

__all__ = ["force_flush", "get_tracer", "setup_tracing"]

log = logging.getLogger(__name__)

ORQ_OTLP_TRACES_URL = "https://api.orq.ai/v2/otel/v1/traces"

_provider: TracerProvider | None = None


def setup_tracing(orq_api_key: str, service_name: str = "bmo") -> None:
    """Configure the global tracer provider once. No-op on repeat calls."""
    global _provider
    if _provider is not None:
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
    # Use SimpleSpanProcessor so each span ships immediately instead of
    # batching for up to 5s. Booth sessions are short — batching loses
    # spans when the script exits before the batch flushes.
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    if os.environ.get("BMO_OTEL_DEBUG") == "1":
        # Mirror every span to stdout — useful to confirm spans are emitted
        # before debugging the wire/auth path.
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        log.info("BMO_OTEL_DEBUG=1 — also printing spans to stdout")

    trace.set_tracer_provider(provider)
    _provider = provider
    # Make OTel exporter errors visible (auth failures, network, schema).
    logging.getLogger("opentelemetry.exporter.otlp.proto.http").setLevel(logging.WARNING)
    logging.getLogger("opentelemetry.sdk.trace.export").setLevel(logging.WARNING)
    log.info("OTel tracing → %s (service=%s)", ORQ_OTLP_TRACES_URL, service_name)


def force_flush(timeout_ms: int = 5000) -> None:
    """Drain pending spans before process exit / between sessions."""
    if _provider is None:
        return
    _provider.force_flush(timeout_millis=timeout_ms)


def get_tracer(name: str = "bmo") -> Any:
    return trace.get_tracer(name)
