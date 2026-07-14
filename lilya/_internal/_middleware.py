from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache
from typing import Any, cast

from lilya.middleware.base import DefineMiddleware
from lilya.types import ASGIApp, Receive, Scope, Send

ROUTE_SCOPE_KEYS = ("route", "route_path_template", "handler")


@lru_cache(maxsize=1024)
def wrap_middleware(
    middleware: DefineMiddleware | Any,
) -> DefineMiddleware:
    """
    Wraps the given middleware into a DefineMiddleware instance if it is not already one.
    Or else it will assume its a Lilya middleware and wraps it.

    Args:
        middleware (Union[DefineMiddleware, Any]): The middleware to be wrapped.
    Returns:
        DefineMiddleware: The wrapped middleware instance.
    """
    if isinstance(middleware, DefineMiddleware):
        return middleware
    return DefineMiddleware(cast(Any, middleware))


def copy_scope_for_middleware(scope: Scope) -> Scope:
    """
    Return a scope copy suitable for handing to an ASGI middleware or child app.

    The ASGI specification recommends copying the connection scope before mutating it and
    passing it downstream, because otherwise values written by one middleware can leak back
    upstream or across mounted applications. Lilya also detaches the mutable request header
    container/list so middleware that rewrites request headers cannot mutate an upstream
    observer's scope by sharing the same nested header object.
    """
    copied_scope = dict(scope)
    if "headers" in copied_scope:
        headers = copied_scope["headers"]
        if hasattr(headers, "encoded_multi_items"):
            copied_scope["headers"] = list(headers.encoded_multi_items())
        else:
            copied_scope["headers"] = list(headers)
    return copied_scope


class ScopeIsolationMiddleware:
    """
    ASGI boundary that gives the wrapped application its own mutable scope copy.

    This is intentionally tiny and framework-owned. It lets Lilya compose both Lilya and
    third-party ASGI middleware in an ASGI-compliant way without requiring every middleware
    implementation to repeat the copy-before-mutate ceremony itself. Only Lilya-owned route
    metadata is copied back for response-side middleware such as tracing.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    def sync_route_metadata(self, source_scope: Scope, target_scope: Scope) -> None:
        """
        Copy Lilya-owned route metadata from the child scope into its parent scope.

        These keys are intentionally whitelisted: response-side middleware and error
        instrumentation need route metadata, but generic child scope mutations must remain
        isolated from upstream middleware.
        """
        for key in ROUTE_SCOPE_KEYS:
            if key in source_scope:
                target_scope[key] = source_scope[key]

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        child_scope = copy_scope_for_middleware(scope)

        async def send_with_route_metadata(message: Any) -> None:
            self.sync_route_metadata(child_scope, scope)
            await send(message)

        try:
            await self.app(child_scope, receive, send_with_route_metadata)
        finally:
            self.sync_route_metadata(child_scope, scope)


def apply_asgi_stack(app: ASGIApp, stack: Sequence[Any] | None) -> ASGIApp:
    """
    Compose ASGI middleware-like layers with scope isolation on both sides of each layer.

    Each layer receives a copy of its parent's scope. The child application passed into that
    layer also copies the layer's scope before continuing downstream. Downstream code still
    sees the layer's additions, but downstream mutations cannot leak back into the layer's
    response-side logic.

    Controller classes are passed directly to the first wrapping layer so Lilya's middleware
    and permission protocol metaclasses can keep their existing controller instantiation
    behavior. Once the controller is behind that first layer, normal ASGI isolation resumes.
    """
    if stack is None:
        return app

    for cls, args, options in reversed(stack):
        child_app = app if hasattr(app, "__is_controller__") else ScopeIsolationMiddleware(app)
        app = ScopeIsolationMiddleware(cls(child_app, *args, **options))
    return app
