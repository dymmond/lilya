from __future__ import annotations

from collections.abc import MutableMapping
from time import perf_counter

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.propagate import extract
from opentelemetry.trace import Span, SpanKind, Status, StatusCode

from lilya.enums import ScopeType
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.requests import Request
from lilya.types import ASGIApp, Message, Receive, Scope, Send


class OpenTelemetryMiddleware(MiddlewareProtocol):
    """
    ASGI middleware responsible for creating and finalizing an OpenTelemetry trace span
    for every incoming HTTP request processed by the application.

    This middleware acts as the entry point for tracing, ensuring that requests are
    instrumented and context is propagated correctly.

    Key functionalities include:
    1. **Context Extraction:** It extracts trace context (e.g., Trace Context, B3) from
       incoming HTTP headers to link the request to a distributed trace.
    2. **Span Creation:** It starts a new server span (`SpanKind.SERVER`) using the global
       `TracerProvider`.
    3. **Attribute Recording:** It records essential HTTP request attributes based on the
       OpenTelemetry Semantic Conventions (e.g., `http.request.method`, `url.path`).
    4. **Status Management:** It captures the response status code and sets the final
       span status (OK or ERROR) based on the code or any uncaught exceptions.
    """

    def __init__(self, app: ASGIApp, span_name: str = "HTTP {method}") -> None:
        """
        Initializes the OpenTelemetry Middleware, wrapping the next ASGI application.

        Args:
            app: The next ASGI application in the middleware stack.
            span_name: The format string used to generate the span name. The `{method}`
                       placeholder is replaced by the HTTP request method (e.g., "HTTP GET").
        """
        super().__init__(app)
        self.app = app
        self.span_name: str = span_name

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        The ASGI callable implementation.

        This method executes the entire tracing lifecycle for an HTTP request:
        extracting context, starting the span, wrapping the application call, capturing
        the response status, and finalizing the span.

        Args:
            scope: The ASGI scope dictionary for the current connection.
            receive: The ASGI receive callable.
            send: The ASGI send callable.
        """
        if scope["type"] != ScopeType.HTTP:
            # Only process HTTP scopes; skip for WebSocket, lifespan, etc.
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        # The tracer is retrieved here to ensure it uses the TracerProvider active at request time.
        tracer: trace.Tracer = trace.get_tracer("lilya.contrib.opentelemetry")

        # Extract propagation context from headers
        # Converts headers (bytes/str) into a MutableMapping[str, str] required by opentelemetry.propagate.extract.
        carrier: MutableMapping[str, str] = {
            (k.decode() if isinstance(k, bytes) else str(k)): (
                v.decode() if isinstance(v, bytes) else str(v)
            )
            for k, v in getattr(request, "headers", {}).items()
        }

        parent: Context | None
        try:
            # Extract trace context from the carrier (HTTP headers)
            parent = extract(carrier)
        except Exception:  # noqa: E722
            # Fail silently if context extraction fails, starting a new root trace instead.
            parent = None

        name: str = self.span_name.format(method=request.method)
        start: float = perf_counter()

        with tracer.start_as_current_span(name, kind=SpanKind.SERVER, context=parent) as span:
            current_span: Span = span

            # --- Initial Request Attribute Recording ---
            current_span.set_attribute("http.request.method", request.method)
            current_span.set_attribute("server.address", request.url.hostname or "")

            if request.url.port:
                # Determine server port, defaulting based on scheme if missing
                port = request.url.port or (443 if request.url.scheme == "https" else 80)
                current_span.set_attribute("server.port", int(port))

            current_span.set_attribute("url.path", request.url.path)
            if request.url.query:
                current_span.set_attribute("url.query", request.url.query)

            if request.client:
                current_span.set_attribute("client.address", request.client.host)
                current_span.set_attribute("client.port", int(request.client.port))

            # Record Lilya route information (useful for aggregation/filtering)
            route = scope.get("route")
            if route and hasattr(route, "path"):
                # Low-cardinality route template
                current_span.set_attribute("lilya.route", route.path)
                current_span.set_attribute("http.route", route.path)
            else:
                # High-cardinality request path as fallback
                current_span.set_attribute("lilya.route", scope.get("path"))

            # Status code holder, defaults to 500 in case of non-handled crash before response start
            status_code_holder: dict[str, int] = {"value": 500}

            async def send_wrapper(message: Message) -> None:
                """
                A wrapper for the original send callable that intercepts the `http.response.start`
                message to capture the HTTP status code before it is sent to the client.
                """
                if message.get("type") == "http.response.start":
                    status_code = int(message.get("status", 200))
                    status_code_holder["value"] = status_code
                    # Record the status code attribute immediately
                    current_span.set_attribute("http.response.status_code", status_code)
                await send(message)

            error: Exception | None = None
            try:
                # Call the next ASGI application in the stack
                await self.app(scope, receive, send_wrapper)
            except Exception as exc:
                error = exc
                # Handle application exception
                current_span.record_exception(exc)
                current_span.set_status(Status(StatusCode.ERROR, description=str(exc)))
                raise

            finally:
                # --- Finalization and Status Setting ---
                duration_ms: float = (perf_counter() - start) * 1000
                current_span.set_attribute("http.server.duration_ms", duration_ms)

                # Redundant attributes (kept for functional consistency with original code's finalizer logic)
                current_span.set_attribute("http.request.method", scope["method"])
                current_span.set_attribute(
                    "server.address", scope.get("server", ["testserver"])[0]
                )
                current_span.set_attribute("url.path", scope.get("path"))

                route = scope.get("route")
                if route and hasattr(route, "path"):
                    current_span.set_attribute("lilya.route", route.path)
                else:
                    current_span.set_attribute("lilya.route", scope.get("path"))

                # Set final span status only if no exception was caught
                if error is None:
                    code: int = status_code_holder["value"]
                    # For server spans, 4xx and 5xx codes mandate an ERROR status.
                    if 400 <= code < 600:
                        current_span.set_status(Status(StatusCode.ERROR))
                    else:
                        current_span.set_status(Status(StatusCode.OK))
