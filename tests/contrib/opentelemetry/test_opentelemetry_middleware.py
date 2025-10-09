import pytest
import anyio

from lilya.apps import Lilya
from lilya.middleware import DefineMiddleware
from lilya.responses import PlainText, Response
from lilya.routing import Path
from lilya.contrib.opentelemetry import OpenTelemetryMiddleware
from lilya.testclient import create_client

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


pytestmark = pytest.mark.asyncio


@pytest.fixture()
def otel_setup():
    """Fixture to install an in-memory tracer provider before each test."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider(resource=Resource.create({"service.name": "test-lilya"}))
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    yield exporter
    exporter.clear()
    trace._TRACER_PROVIDER = None


async def test_basic_span_created(otel_setup):
    async def hello(request):
        return PlainText("hello world")

    with create_client(routes=[Path("/hello", hello)], middleware=[DefineMiddleware(OpenTelemetryMiddleware)]) as client:
        response = client.get("/hello")
        assert response.status_code == 200

    spans = otel_setup.get_finished_spans()
    assert len(spans) == 1

    span = spans[0]

    assert span.kind.name == "SERVER"
    assert span.name == "HTTP GET"
    assert span.attributes["http.request.method"] == "GET"
    assert "url.path" in span.attributes
    assert span.status.is_ok


async def test_span_contains_route_and_duration(otel_setup):
    async def route_handler(request):
        return PlainText("ok")

    async with create_client(routes=[Path("/items/{item_id}", route_handler)],
                middleware=[DefineMiddleware(OpenTelemetryMiddleware)]) as client:
        breakpoint()
        response = client.get("/items/123")
        assert response.status_code == 200

    breakpoint()
    span = otel_setup.get_finished_spans()[0]

    assert "lilya.route" in span.attributes
    assert span.attributes["lilya.route"] == "/items/{item_id}"
    assert "http.server.duration_ms" in span.attributes
    assert span.attributes["http.server.duration_ms"] >= 0


async def xtest_span_records_exception_on_error(otel_setup):
    async def broken(request):
        raise ValueError("boom")

    with create_client(routes=[Path("/broken", broken)],
                middleware=[DefineMiddleware(OpenTelemetryMiddleware)]) as client:
        response = client.get("/broken")
        assert response.status_code == 500

    span = otel_setup.get_finished_spans()[0]
    assert span.status.status_code.name == "ERROR"
    assert "exception.type" in span.events[0].attributes


async def xtest_client_metadata_and_status_codes(otel_setup):
    async def echo(request):
        return Response("ok", status_code=204)

    with create_client(routes=[Path("/echo", echo)], middleware=[DefineMiddleware(OpenTelemetryMiddleware)]) as client:
        response = await client.request("DELETE", "/echo")
        assert response.status_code == 204

    span = otel_setup.get_finished_spans()[0]
    assert span.attributes["client.address"]
    assert span.attributes["http.response.status_code"] == 204
    assert span.status.status_code.name == "OK"


async def xtest_noop_if_not_http_scope(otel_setup):
    async def ws(scope, receive, send):
        await send({"type": "websocket.close"})

    app = Lilya(routes=[], middleware=[DefineMiddleware(OpenTelemetryMiddleware)])
    scope = {"type": "websocket"}  # fake
    receive = lambda: None
    send = lambda message: None

    # Should not raise and should not create spans
    middleware = OpenTelemetryMiddleware(ws)
    await middleware(scope, receive, send)

    assert not otel_setup.get_finished_spans()
