import pytest

from lilya.apps import Lilya
from lilya.middleware import DefineMiddleware
from lilya.responses import PlainText
from lilya.contrib.opentelemetry import OpenTelemetryMiddleware

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from lilya.testclient import create_client
from lilya.routing import Path

pytestmark = pytest.mark.asyncio

async def test_otlp_middleware_creates_span():
    if trace is None:
        pytest.skip("opentelemetry not installed")

    exporter = InMemorySpanExporter()
    provider = TracerProvider(resource=Resource.create({"service.name": "test"}))
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    async def hello(request):
        return PlainText("ok")

    with create_client(
        routes=[Path("/hello", hello)],
        middleware=[DefineMiddleware(OpenTelemetryMiddleware)],
        debug=True
    ) as client:
        response = client.get("/hello?x=1")
        assert response.status_code in (200, 404)

    spans = exporter.get_finished_spans()

    assert len(spans) == 1

    span = spans[0]

    assert span.kind.name == "SERVER"
    assert "http.request.method" in span.attributes
