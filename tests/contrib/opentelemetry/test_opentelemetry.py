import pytest
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import ProxyTracerProvider

from lilya.contrib.opentelemetry import OpenTelemetryMiddleware, instrumentation
from lilya.middleware import DefineMiddleware
from lilya.responses import PlainText
from lilya.routing import Path
from lilya.testclient import create_client

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def reset_global_tracer(monkeypatch):
    monkeypatch.setattr(trace, "_TRACER_PROVIDER", None, raising=False)
    monkeypatch.setattr(trace, "_PROXY_TRACER_PROVIDER", ProxyTracerProvider(), raising=False)
    monkeypatch.setattr(instrumentation, "_provider", None, raising=False)

    provider = TracerProvider()
    trace._PROXY_TRACER_PROVIDER._delegate = provider  # type: ignore[attr-defined]
    trace.set_tracer_provider(provider)

    yield

    # Clean up after each test
    monkeypatch.setattr(trace, "_TRACER_PROVIDER", None, raising=False)
    monkeypatch.setattr(trace, "_PROXY_TRACER_PROVIDER", ProxyTracerProvider(), raising=False)
    monkeypatch.setattr(instrumentation, "_provider", None, raising=False)


async def test_otlp_middleware_creates_span(monkeypatch):
    exporter = InMemorySpanExporter()
    provider = TracerProvider(resource=Resource.create({"service.name": "test"}))
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    # Monkeypatch Lilya’s middleware to use this provider instead of the global
    monkeypatch.setattr(trace, "get_tracer_provider", lambda: provider)

    async def hello(request):
        return PlainText("ok")

    with create_client(
        routes=[Path("/hello", hello)],
        middleware=[DefineMiddleware(OpenTelemetryMiddleware)],
        debug=True,
    ) as client:
        response = client.get("/hello?x=1")
        assert response.status_code in (200, 404)

    spans = exporter.get_finished_spans()
    assert len(spans) == 1

    span = spans[0]
    assert span.kind.name == "SERVER"
    assert "http.request.method" in span.attributes
