import anyio
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


async def test_exception_recorded_and_status_error(otel_setup):
    async def boom(request):
        raise ValueError("crash test")

    async with create_async_client(
        routes=[Path("/boom", boom)],
        middleware=[DefineMiddleware(OpenTelemetryMiddleware)],
    ) as client:
        response = await client.get("/boom")
        assert response.status_code == 500

    spans = otel_setup.get_finished_spans()

    assert len(spans) == 1

    span = spans[0]

    assert span.status.status_code.name == "ERROR"
    assert any("ValueError" in e.attributes["exception.type"] for e in span.events)


async def test_span_includes_query_params(otel_setup):
    async def handler(request):
        return PlainText("ok")

    async with create_async_client(
        routes=[Path("/search", handler)], middleware=[DefineMiddleware(OpenTelemetryMiddleware)]
    ) as client:
        response = await client.get("/search?q=telemetry")

        assert response.status_code == 200

    spans = otel_setup.get_finished_spans()

    assert len(spans) == 1

    span = spans[0]

    assert "url.query" in span.attributes
    assert span.attributes["url.query"] == "q=telemetry"


async def test_span_sets_status_for_client_error(otel_setup):
    async def bad_request(request):
        return Response("bad", status_code=400)

    async with create_async_client(
        routes=[Path("/bad", bad_request)], middleware=[DefineMiddleware(OpenTelemetryMiddleware)]
    ) as client:
        response = await client.get("/bad")

        assert response.status_code == 400

    span = otel_setup.get_finished_spans()[0]

    assert span.status.status_code.name == "ERROR"


async def test_span_duration_is_positive(otel_setup):
    async def slow(request):
        await anyio.sleep(0.01)
        return PlainText("ok")

    async with create_async_client(
        routes=[Path("/slow", slow)], middleware=[DefineMiddleware(OpenTelemetryMiddleware)]
    ) as client:
        await client.get("/slow")

    span = otel_setup.get_finished_spans()[0]

    assert "http.server.duration_ms" in span.attributes
    assert span.attributes["http.server.duration_ms"] >= 0.01


async def test_concurrent_requests_generate_independent_spans(otel_setup):
    async def ok(request):
        return PlainText("ok")

    async with create_async_client(
        routes=[Path("/ok", ok)], middleware=[DefineMiddleware(OpenTelemetryMiddleware)]
    ) as client:
        results = []

        async def make_request():
            resp = await client.get("/ok")
            results.append(resp)

        async with anyio.create_task_group() as tg:
            for _ in range(3):
                tg.start_soon(make_request)

        assert all(r.status_code == 200 for r in results)

    spans = otel_setup.get_finished_spans()
    assert len(spans) == 3

    paths = [s.attributes["url.path"] for s in spans]

    assert paths.count("/ok") == 3


async def test_span_includes_server_port(otel_setup):
    async def index(request):
        return PlainText("ok")

    async with create_async_client(
        routes=[Path("/", index)], middleware=[DefineMiddleware(OpenTelemetryMiddleware)]
    ) as client:
        await client.get("/")

    span = otel_setup.get_finished_spans()[0]

    assert "server.address" in span.attributes
    assert span.attributes["server.address"] == "testserver"
