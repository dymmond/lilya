import sys

if sys.version_info >= (3, 11):
    from typing import assert_type
else:
    from typing_extensions import assert_type

from lilya.apps import Lilya
from lilya.contrib.openapi.config import OpenAPIConfig
from lilya.datastructures import ImmutableMultiDict
from lilya.dependencies import Provide
from lilya.middleware.base import DefineMiddleware
from lilya.permissions.base import DefinePermission
from lilya.requests import Request
from lilya.responses import Response
from lilya.routing import BasePath, Path, Router
from lilya.types import ASGIApp, ExceptionHandler


def _pass_through(app: ASGIApp) -> ASGIApp:
    return app


async def _endpoint(request: Request) -> Response:
    return Response("ok")


async def _handle_error(request: Request, exc: Exception) -> Response:
    return Response(str(exc), status_code=500)


def test_public_apis_accept_normal_list_and_dict_inputs():
    routes = [Path("/", _endpoint)]
    middleware = [DefineMiddleware(_pass_through)]
    permissions = [DefinePermission(_pass_through)]
    dependencies = {"value": Provide(lambda: "value")}
    exception_handlers: dict[type[Exception], ExceptionHandler] = {ValueError: _handle_error}

    app = Lilya(
        routes=routes,
        middleware=middleware,
        permissions=permissions,
        dependencies=dependencies,
        exception_handlers=exception_handlers,
    )
    router = Router(
        routes=routes,
        middleware=middleware,
        permissions=permissions,
        dependencies=dependencies,
    )
    Path(
        "/nested",
        _endpoint,
        middleware=middleware,
        permissions=permissions,
        dependencies=dependencies,
        exception_handlers=exception_handlers,
    )
    openapi_config = OpenAPIConfig(
        tags=["items"],
        servers=[{"url": "/"}],
    )
    immutable_multidict = ImmutableMultiDict({"key": "value"})

    assert_type(app.routes, list[BasePath])
    assert_type(router.routes, list[BasePath])
    assert_type(openapi_config.tags, list[str] | None)
    assert_type(immutable_multidict, ImmutableMultiDict[str])
    assert isinstance(app, Lilya)
    assert isinstance(router, Router)
    assert isinstance(immutable_multidict, ImmutableMultiDict)


def test_plain_dict_response_headers_are_accepted():
    response = Response("ok", headers={"x-test": "value"})

    assert response.headers["x-test"] == "value"
