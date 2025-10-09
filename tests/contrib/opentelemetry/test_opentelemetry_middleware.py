import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from lilya.contrib.opentelemetry import OpenTelemetryMiddleware
from lilya.middleware import DefineMiddleware
from lilya.responses import PlainText, Response
from lilya.routing import Path
from lilya.testclient import create_async_client, create_client
from tests.contrib.opentelemetry.reset import reset_opentelemetry_globals

pytestmark = pytest.mark.anyio


@pytest.fixture(scope="function")
def otel_setup():
    reset_opentelemetry_globals()

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    processor = SimpleSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    yield exporter

    exporter.clear()
    reset_opentelemetry_globals()


async def test_basic_span_created(otel_setup):
    async def hello(request):
        return PlainText("hello world")

    async with create_async_client(
        routes=[Path("/hello", hello)], middleware=[DefineMiddleware(OpenTelemetryMiddleware)]
    ) as client:
        response = await client.get("/hello")
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

    async with create_async_client(
        routes=[Path("/items/{item_id}", route_handler)],
        middleware=[DefineMiddleware(OpenTelemetryMiddleware)],
    ) as client:
        response = await client.get("/items/123")
        assert response.status_code == 200

    spans = otel_setup.get_finished_spans()
    span = spans[0]

    assert len(spans) == 1

    assert "lilya.route" in span.attributes
    assert span.attributes["lilya.route"] == "/items/{item_id}"
    assert "http.server.duration_ms" in span.attributes
    assert span.attributes["http.server.duration_ms"] >= 0


async def test_span_records_exception_on_error(otel_setup):
    async def broken(request):
        raise ValueError("boom")

    with create_client(
        routes=[Path("/broken", broken)], middleware=[DefineMiddleware(OpenTelemetryMiddleware)]
    ) as client:
        response = client.get("/broken")
        assert response.status_code == 500

    span = otel_setup.get_finished_spans()[0]

    assert span.status.status_code.name == "ERROR"
    assert "exception.type" in span.events[0].attributes


async def test_client_metadata_and_status_codes(otel_setup):
    async def echo(request):
        return Response("ok", status_code=204)

    async with create_async_client(
        routes=[Path("/echo", echo, methods=["DELETE"])],
        middleware=[DefineMiddleware(OpenTelemetryMiddleware)],
    ) as client:
        response = await client.delete("/echo")
        assert response.status_code == 204

    span = otel_setup.get_finished_spans()[0]

    assert span.attributes["client.address"]
    assert span.attributes["http.response.status_code"] == 204
    assert span.status.status_code.name == "OK"


async def test_noop_if_not_http_scope(otel_setup):
    async def ws(scope, receive, send):
        await send({"type": "websocket.close"})

    scope = {"type": "websocket"}  # fake

    async def receive():
        return None

    async def send(message):
        return None

    # Should not raise and should not create spans
    middleware = OpenTelemetryMiddleware(ws)
    await middleware(scope, receive, send)

    assert not otel_setup.get_finished_spans()
