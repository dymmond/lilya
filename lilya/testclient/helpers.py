from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any, Literal, cast

import httpx

from lilya.apps import Lilya
from lilya.conf.global_settings import Settings
from lilya.permissions.base import Permission
from lilya.testclient import TestClient
from lilya.types import ApplicationType, Dependencies, ExceptionHandler, Lifespan


def create_client(
    routes: Sequence[Any] | None = None,
    *,
    settings_module: type[Settings] | str | None = None,
    base_url: str = "http://testserver",
    backend: Literal["asyncio", "trio"] = "asyncio",
    backend_options: dict[str, Any] | None = None,
    permissions: Sequence[Permission] | None = None,
    middleware: Sequence[Any] | None = None,
    exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
    on_startup: Sequence[Callable[[], Any]] | None = None,
    on_shutdown: Sequence[Callable[[], Any]] | None = None,
    include_in_schema: bool = True,
    raise_server_exceptions: bool = True,
    check_asgi_conformance: bool = True,
    lifespan: Lifespan[ApplicationType] | None = None,
    dependencies: Dependencies | None = None,
    redirect_slashes: bool = True,
    debug: bool = False,
    root_path: str = "",
    cookies: httpx._types.CookieTypes | None = None,
    before_request: Sequence[Callable[..., Any]] | None = None,
    after_request: Sequence[Callable[..., Any]] | None = None,
    enable_openapi: bool = True,
    openapi_config: Any | None = None,
    enable_intercept_global_exceptions: bool = True,
    **kwargs: Any,
) -> TestClient:
    """
    Context function used for the purposes of testing.

    # Example

    ```python
    from lilya.testclient import create_client


    with create_client(routes=...) as client:
        response = client.get("/")
    ```
    """
    return TestClient(
        app=Lilya(
            settings_module=settings_module,
            debug=debug,
            routes=cast("Any", routes if isinstance(routes, list) else [routes]),
            permissions=permissions,
            middleware=middleware,
            exception_handlers=exception_handlers,
            dependencies=dependencies,
            on_shutdown=on_shutdown,
            on_startup=on_startup,
            lifespan=lifespan,
            redirect_slashes=redirect_slashes,
            include_in_schema=include_in_schema,
            before_request=before_request,
            after_request=after_request,
            enable_openapi=enable_openapi,
            openapi_config=openapi_config,
            enable_intercept_global_exceptions=enable_intercept_global_exceptions,
            **kwargs,
        ),
        base_url=base_url,
        backend=backend,
        backend_options=backend_options,
        root_path=root_path,
        raise_server_exceptions=raise_server_exceptions,
        check_asgi_conformance=check_asgi_conformance,
        cookies=cookies,
    )
