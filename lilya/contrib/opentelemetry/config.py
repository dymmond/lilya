from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class OpenTelemetryConfig:
    """
    Configuration for OpenTelemetry setup.

    Only used by :func:`setup_tracing`. If you don't call that helper,
    you can configure OpenTelemetry yourself and still use the middleware.
    """

    service_name: str = "lilya-app"
    exporter: Literal["otlp", "console"] = "otlp"
    otlp_endpoint: str | None = None  # e.g. http://localhost:4317 or :4318
    otlp_insecure: bool = True
    sampler: Literal["parentbased_always_on", "always_on", "always_off"] = "parentbased_always_on"
