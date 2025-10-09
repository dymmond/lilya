from __future__ import annotations

from time import perf_counter
from typing import Any

from opentelemetry import trace
from opentelemetry.propagate import extract
from opentelemetry.trace import SpanKind, Status, StatusCode

from lilya.enums import ScopeType
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.requests import Request
from lilya.types import ASGIApp, Receive, Scope, Send


class OpenTelemetryMiddleware(MiddlewareProtocol):
    """
    ASGI middleware that creates a span per HTTP request.

    * Uses the current global TracerProvider (set up via :func:`setup_tracing`).
    * Extracts parent context from incoming headers for trace propagation.
    * Records standard HTTP attributes on spans.
    """

    def __init__(self, app: ASGIApp, span_name: str = "HTTP {method}") -> None:
        super().__init__(app)
        self.app = app
        self.span_name = span_name

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != ScopeType.HTTP:
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        tracer = trace.get_tracer("lilya.contrib.opentelemetry")

        # Extract propagation context from headers
        carrier = {
            (k.decode() if isinstance(k, bytes) else str(k)): (
                v.decode() if isinstance(v, bytes) else str(v)
            )
            for k, v in getattr(request, "headers", {}).items()
        }

        try:
            parent = extract(carrier)
        except Exception:  # noqa
            parent = None

        name = self.span_name.format(method=request.method)
        start = perf_counter()

        with tracer.start_as_current_span(name, kind=SpanKind.SERVER, context=parent) as span:
            span.set_attribute("http.request.method", request.method)
            span.set_attribute("server.address", request.url.hostname or "")
            if request.url.port:
                span.set_attribute("server.port", int(request.url.port))
            span.set_attribute("url.path", request.url.path)
            if request.url.query:
                span.set_attribute("url.query", request.url.query)

            if request.client:
                span.set_attribute("client.address", request.client.host)
                span.set_attribute("client.port", int(request.client.port))

            route = scope.get("route")
            if route and hasattr(route, "path"):
                span.set_attribute("lilya.route", route.path)
            else:
                span.set_attribute("lilya.route", scope.get("path"))

            status_code_holder: dict[str, int] = {"value": 200}

            async def send_wrapper(message: Any) -> None:
                if message.get("type") == "http.response.start":
                    status_code = int(message.get("status", 200))
                    status_code_holder["value"] = status_code
                    span.set_attribute("http.response.status_code", status_code)
                await send(message)

            error: Exception | None = None
            try:
                await self.app(scope, receive, send_wrapper)
            except Exception as exc:
                error = exc
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, description=str(exc)))
                raise

            finally:
                duration_ms = (perf_counter() - start) * 1000
                span.set_attribute("http.server.duration_ms", duration_ms)
                span.set_attribute("http.request.method", scope["method"])
                span.set_attribute("server.address", scope.get("server", ["testserver"])[0])
                span.set_attribute("url.path", scope.get("path"))

                route = scope.get("route")
                if route and hasattr(route, "path"):
                    span.set_attribute("lilya.route", route.path)
                else:
                    span.set_attribute("lilya.route", scope.get("path"))

                if error is None:
                    code = status_code_holder["value"]
                    if 400 <= code < 600:
                        span.set_status(Status(StatusCode.ERROR))
                    else:
                        span.set_status(Status(StatusCode.OK))
