from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class OpenTelemetryConfig:
    """
    Configuration options for OpenTelemetry setup in Lilya.

    Used exclusively by :func:`setup_tracing` in
    ``lilya.contrib.opentelemetry.instrumentation``.
    """

    service_name: str = "lilya-service"
    """Logical service name reported to telemetry backends."""

    exporter: Literal["otlp", "console"] = "otlp"
    """Which exporter to use: 'otlp' for remote OTLP or 'console' for stdout."""

    otlp_endpoint: str | None = "http://localhost:4317"
    """Target OTLP endpoint (e.g., 'http://localhost:4317' or 'http://collector:4318')."""

    otlp_insecure: bool = True
    """If True, disables TLS verification for gRPC exporter."""

    sampler: Literal["parentbased_always_on", "always_on", "always_off"] = "parentbased_always_on"
    """Sampling strategy: ParentBased(ALWAYS_ON) by default."""
