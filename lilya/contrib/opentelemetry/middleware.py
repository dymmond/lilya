from __future__ import annotations

import time
from typing import Any

from lilya.protocols.middleware import MiddlewareProtocol
from lilya.types import ASGIApp, Scope, Receive, Send
from lilya.requests import Request
from opentelemetry import trace, context
from opentelemetry.propagate import get_global_textmap, extract
from opentelemetry.trace import SpanKind, Status, StatusCode
from lilya.enums import ScopeType



class OpenTelemetryMiddleware(MiddlewareProtocol):
    """
    ASGI middleware that creates a span per HTTP request.

    * Uses the current global TracerProvider (set up via :func:`setup_tracing`).
    * Extracts parent context from incoming headers for trace propagation.
    * Records standard HTTP attributes on spans.
    """

    def __init__(self, app: ASGIApp, span_name: str = "HTTP {method}") -> None:
        self.app = app
        self.span_name = span_name

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if trace is None:  # OpenTelemetry not installed; no-op
            await self.app(scope, receive, send)
            return

        if scope["type"] != ScopeType.HTTP:
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        tracer = trace.get_tracer("lilya.contrib.opentelemetry")

        # Extract remote context from headers
        carrier = {
            k.decode() if isinstance(k, bytes) else k:
            v.decode() if isinstance(v, bytes) else v
            for k, v in request.headers.items()
        }
        parent = None
        try:
            if extract:
                result = extract(carrier)
                if isinstance(result, tuple):
                    parent = result[0]
                else:
                    parent = result
            elif get_global_textmap:
                propagator = get_global_textmap()
                if hasattr(propagator, "extract"):
                    parent = propagator.extract(carrier)
        except Exception:
            parent = None  # fallback safe

        name = self.span_name.format(method=request.method)
        start_time_ns = time.time_ns()

        with tracer.start_as_current_span(name, kind=SpanKind.SERVER, context=parent) as span:  # type: ignore[arg-type]
            span.set_attribute("http.request.method", request.method)
            span.set_attribute("server.address", request.url.hostname or "")
            if request.url.port:
                span.set_attribute("server.port", int(request.url.port))
            span.set_attribute("url.path", request.url.path)
            if request.url.query:
                span.set_attribute("url.query", request.url.query)

            client = request.client
            if client:
                span.set_attribute("client.address", client.host)
                span.set_attribute("client.port", int(client.port))

            route = scope.get("route")
            if route and hasattr(route, "path"):
                span.set_attribute("lilya.route", getattr(route, "path", ""))

            status_code_holder = {"value": 200}

            async def send_wrapper(message: Any) -> None:
                if message.get("type") == "http.response.start":
                    status_code = int(message.get("status", 200))
                    status_code_holder["value"] = status_code
                    span.set_attribute("http.response.status_code", status_code)
                await send(message)

            error: Exception | None = None
            try:
                await self.app(scope, receive, send_wrapper)
            except Exception as exc:  # noqa: BLE001
                error = exc
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, description=str(exc)))
                raise
            finally:
                duration_ms = (time.time_ns() - start_time_ns) / 1_000_000
                span.set_attribute("http.server.duration_ms", duration_ms)
                if error is None:
                    code = status_code_holder["value"]
                    if 400 <= code < 600:
                        span.set_status(Status(StatusCode.ERROR))
                    else:
                        span.set_status(Status(StatusCode.OK))
