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
from opentelemetry.sdk.trace.sampling import ALWAYS_OFF, ALWAYS_ON, ParentBased, Sampler

from lilya.contrib.opentelemetry.config import OpenTelemetryConfig

_provider: TracerProvider | None = None


def get_tracer_provider() -> TracerProvider | None:
    """
    Retrieves the globally set OpenTelemetry TracerProvider instance.

    Returns:
        The configured TracerProvider or None if tracing has not been set up.
    """
    return _provider


def _build_sampler(name: str) -> Sampler | Any:
    """
    Builds an OpenTelemetry sampler based on the provided configuration name.

    Args:
        name: The name of the sampler to use (e.g., "always_on", "always_off").

    Returns:
        A configured OpenTelemetry Sampler instance. Defaults to ParentBased(ALWAYS_ON).
    """
    if name == "always_off":
        return ALWAYS_OFF
    if name == "always_on":
        return ALWAYS_ON

    # Defaulting to ParentBased(ALWAYS_ON) as a safe fallback
    return ParentBased(ALWAYS_ON)


def setup_tracing(config: OpenTelemetryConfig | None = None) -> None:
    """
    Initialize the global OpenTelemetry TracerProvider and SpanExporter.

    This function is safe to call multiple times; subsequent calls are ignored
    if a TracerProvider has already been set (`_provider` is not None).

    Args:
        config: An optional OpenTelemetryConfig object to customize tracing.
                If None, it defaults to a new instance of OpenTelemetryConfig.

    Raises:
        RuntimeError: If the necessary OpenTelemetry packages are not installed.
    """
    global _provider

    if trace is None:
        raise RuntimeError(
            "OpenTelemetry packages not installed. Install 'opentelemetry-sdk' and an exporter."
        )

    if _provider is not None:
        # TracerProvider is already set, so skip initialization.
        return

    # Use provided config or default to a new configuration instance
    cfg: OpenTelemetryConfig = config or OpenTelemetryConfig()

    # Define service-level information for the traces
    resource: Resource = Resource.create(
        {
            "service.name": cfg.service_name,
            # Including a version for auto-instrumentation identification
            "telemetry.auto.version": "1.0.0",
        }
    )

    # Initialize the TracerProvider with the resource and configured sampler
    provider: TracerProvider = TracerProvider(
        resource=resource, sampler=_build_sampler(cfg.sampler)
    )

    # Configure the exporter based on the config settings
    if cfg.exporter == "console":
        # Export spans to the console (stdout)
        exporter = ConsoleSpanExporter()
    else:
        # Configure OTLP (OpenTelemetry Protocol) exporter
        endpoint: str = cfg.otlp_endpoint or "http://localhost:4317"

        # Determine protocol (gRPC vs. HTTP) based on the default OTLP gRPC port
        if endpoint.endswith(":4317"):
            exporter = OTLPgRPCExporter(endpoint=endpoint, insecure=cfg.otlp_insecure)  # type: ignore
        else:
            # Assume HTTP/JSON protocol for other endpoints
            exporter = OTLPHTTPExporter(endpoint=endpoint)  # type: ignore

    # Use BatchSpanProcessor for asynchronous, efficient export
    provider.add_span_processor(BatchSpanProcessor(exporter))
    # Set the provider as the global instance for all tracers
    trace.set_tracer_provider(provider)
    # Store the provider locally
    _provider = provider
