from __future__ import annotations

from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter as OTLPgRPCExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter as OTLPHTTPExporter,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.trace.sampling import ALWAYS_OFF, ALWAYS_ON, ParentBased

from lilya.contrib.opentelemetry.config import OpenTelemetryConfig

_provider: TracerProvider | None = None


def get_tracer_provider() -> TracerProvider | None:
    return _provider


def _build_sampler(name: str) -> ParentBased | Any:
    if name == "always_off":
        return ALWAYS_OFF
    if name == "always_on":
        return ALWAYS_ON
    return ParentBased(ALWAYS_ON)


def setup_tracing(config: OpenTelemetryConfig | None = None) -> None:
    """
    Initialize the global TracerProvider and exporter.

    Safe to call multiple times; subsequent calls are ignored unless nothing was set.
    """
    global _provider

    if trace is None:
        raise RuntimeError(
            "OpenTelemetry packages not installed. Install 'opentelemetry-sdk' and an exporter."
        )

    if _provider is not None:
        return

    cfg = config or OpenTelemetryConfig()

    resource = Resource.create(
        {
            "service.name": cfg.service_name,
            "telemetry.auto.version": "1.0.0",
        }
    )

    provider = TracerProvider(resource=resource, sampler=_build_sampler(cfg.sampler))

    if cfg.exporter == "console":
        exporter = ConsoleSpanExporter()
    else:
        endpoint = cfg.otlp_endpoint or "http://localhost:4317"
        if endpoint.endswith(":4317"):
            exporter = OTLPgRPCExporter(endpoint=endpoint, insecure=cfg.otlp_insecure)  # type: ignore
        else:
            exporter = OTLPHTTPExporter(endpoint=endpoint)  # type: ignore

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _provider = provider
