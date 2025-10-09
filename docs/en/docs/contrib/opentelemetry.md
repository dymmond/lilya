# OpenTelemetry

Instrument your Lilya apps with [OpenTelemetry](https://opentelemetry.io/) to get distributed traces out-of-the-box.
This integration lives under `lilya.contrib.opentelemetry` and provides:

* A small **instrumentation helper** to configure an OpenTelemetry `TracerProvider` and exporter.
* A production-ready **ASGI middleware** that creates one **SERVER** span per HTTP request.
* A simple **config object** you can wire from settings or environment.

## What you get

- One span per request (name: `HTTP {method}`).
- Trace context extraction from inbound headers (W3C TraceContext / B3 etc).
- Standard HTTP attributes on spans (method, path, query, status code, client & server info, duration).
- Error recording & `StatusCode.ERROR` for 4xx/5xx or exceptions.
- Works with **OTLP gRPC (4317)** and **OTLP HTTP (4318)** out of the box.
- Easy to test in isolation—no collector required.

## Install

To use the Lilya OpenTelemetry integration, install the following packages:

```bash
pip install opentelemetry-sdk opentelemetry-api opentelemetry-exporter-otlp

# Optional, if you want console output instead of OTLP:
pip install opentelemetry-sdk  # (Console exporter ships with SDK)
```

!!! Note
    gRPC exporter uses port **4317** by convention and HTTP exporter uses port **4318** by convention.

## Quick start

### Configure tracing at startup

```python
# app.py
from lilya.contrib.opentelemetry.instrumentation import setup_tracing
from lilya.contrib.opentelemetry.config import OpenTelemetryConfig

# Option A: default config → OTLP to http://localhost:4317
setup_tracing()

# Option B: explicit config
cfg = OpenTelemetryConfig(
    service_name="billing-api",
    exporter="otlp",
    otlp_endpoint="http://otel-collector:4318",  # HTTP exporter when not ending with :4317
    otlp_insecure=True,                           # only applies to gRPC exporter
    sampler="parentbased_always_on",
)
setup_tracing(cfg)
```

### Add the middleware

```python
from lilya.contrib.opentelemetry import OpenTelemetryMiddleware
from lilya.middleware import DefineMiddleware
from lilya.apps import Lilya

app = Lilya(
    routes=[...],
    middleware=[DefineMiddleware(OpenTelemetryMiddleware)]
)
```

That's it, your requests now produce spans.

## Configuration reference

```python
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
    """'otlp' for remote OTLP or 'console' for stdout."""

    otlp_endpoint: str | None = "http://localhost:4317"
    """Target OTLP endpoint, e.g. 'http://localhost:4317' or 'http://collector:4318'."""

    otlp_insecure: bool = True
    """If True, disables TLS verification for **gRPC** exporter."""

    sampler: Literal["parentbased_always_on", "always_on", "always_off"] = "parentbased_always_on"
    """Sampling strategy: ParentBased(ALWAYS_ON) by default."""
```

### Exporter selection rules

`setup_tracing` chooses the exporter like this:

- If `exporter == "console"` → use `ConsoleSpanExporter` (prints JSON-ish spans to stdout).
- Else (OTLP):
    * If `otlp_endpoint` **ends with `:4317`** → use **OTLP gRPC** exporter (`OTLPgRPCExporter`), honoring `otlp_insecure`.
    * Otherwise → use **OTLP HTTP** exporter (`OTLPHTTPExporter`).

!!! Tip
    Want HTTP exporter? Use an endpoint that **doesn't** end with `:4317` (e.g., `http://localhost:4318`).

## What the middleware records

Each request span includes (non-exhaustive):

- `http.request.method` — HTTP method.
- `http.response.status_code` — response status.
- `url.path`, `url.query` — path and query string.
- `server.address` (and `server.port` if known).
- `client.address`, `client.port` (if available).
- `lilya.route` — the matched route pattern (e.g. `/items/{id}`).
- `http.server.duration_ms` — handling latency in milliseconds.

**Errors**:

* Exceptions are recorded via `span.record_exception`.
* 4xx/5xx responses mark `span.status = ERROR`, others `OK`.

**Propagation**:

* Incoming context is extracted from request headers (`opentelemetry.propagate.extract`), so your spans join upstream traces automatically.

## Real-world recipes

### Local development (console exporter)

```python
from lilya.contrib.opentelemetry.instrumentation import setup_tracing
from lilya.contrib.opentelemetry.config import OpenTelemetryConfig

setup_tracing(OpenTelemetryConfig(
    service_name="lilya-dev",
    exporter="console",
))
```

Run your app and watch spans print to the console.

### Send to OpenTelemetry Collector (Docker)

**docker-compose.yaml** (minimal)

```yaml
services:
  otel-collector:
    image: otel/opentelemetry-collector:latest
    command: ["--config=/etc/otelcol/config.yaml"]
    volumes:
      - ./otelcol.yaml:/etc/otelcol/config.yaml
    ports:
      - "4317:4317" # gRPC
      - "4318:4318" # HTTP

  app:
    build: .
    environment:
      OTEL_ENDPOINT: http://otel-collector:4317
    depends_on: [otel-collector]
```

**app.py**

```python
import os
from lilya.contrib.opentelemetry.instrumentation import setup_tracing
from lilya.contrib.opentelemetry.config import OpenTelemetryConfig

setup_tracing(OpenTelemetryConfig(
    service_name="checkout",
    exporter="otlp",
    otlp_endpoint=os.getenv("OTEL_ENDPOINT", "http://localhost:4317"),
))
```

**otelcol.yaml** (export to Tempo/Jaeger/etc—illustrative)

```yaml
receivers:
  otlp:
    protocols:
      grpc:
      http:

exporters:
  otlphttp:
    endpoint: http://tempo:4318
  logging: {}

processors:
  batch: {}

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [logging, otlphttp]
```

### Send to Grafana Tempo (HTTP 4318)

```python
setup_tracing(OpenTelemetryConfig(
    service_name="user-service",
    exporter="otlp",
    otlp_endpoint="http://tempo:4318",  # uses OTLP HTTP exporter
))
```

### Send to Jaeger via Collector (gRPC 4317)

```python
setup_tracing(OpenTelemetryConfig(
    service_name="orders",
    exporter="otlp",
    otlp_endpoint="http://otel-collector:4317",  # uses gRPC exporter
    otlp_insecure=True,
))
```

## Advanced usage

### Add custom attributes inside a route

```python
from lilya.responses import PlainText

from opentelemetry import trace

tracer = trace.get_tracer("lilya.contrib.opentelemetry")

async def create_order(request):
    with tracer.start_as_current_span("db.save", record_exception=True) as span:
        span.set_attribute("db.system", "postgresql")
        span.set_attribute("order.id", "abc-123")
        # ... do work ...
    return PlainText("ok")
```

These child spans appear underneath the request span in your trace viewer.

## Performance notes

- The integration uses **`BatchSpanProcessor`** by default to reduce overhead (buffer + background export).
- For tests, prefer `SimpleSpanProcessor` + `InMemorySpanExporter`.
- Keep attributes minimal; excessive per-request attributes can add CPU/allocations.

## FAQ

**Q: Can I call `setup_tracing()` multiple times?**
A: Yes. It's idempotent within this package; subsequent calls are ignored once a provider is set.

**Q: `server.port` is sometimes missing. Why?**
A: The middleware sets it when the request URL includes (or implies) a port. In test clients the host/port may be virtual.

**Q: How do I disable all tracing in certain environments?**
A: Don't call `setup_tracing()` and don't add the middleware. Or configure `sampler="always_off"`.

## End-to-end example

```python
from lilya.apps import Lilya
from lilya.routing import Path
from lilya.responses import PlainText
from lilya.middleware import DefineMiddleware
from lilya.contrib.opentelemetry import OpenTelemetryMiddleware
from lilya.contrib.opentelemetry.instrumentation import setup_tracing
from lilya.contrib.opentelemetry.config import OpenTelemetryConfig

setup_tracing(OpenTelemetryConfig(
    service_name="payments",
    exporter="otlp",
    otlp_endpoint="http://otel-collector:4317",  # gRPC
    otlp_insecure=True,
))

async def health(_):
    return PlainText("ok")

app = Lilya(
    routes=[Path("/health", health)],
    middleware=[DefineMiddleware(OpenTelemetryMiddleware)],
)
```

Deploy alongside an OTel Collector, and you'll see request traces in Jaeger/Tempo/Datadog/etc. with Lilya route names, status codes, and durations attached.
