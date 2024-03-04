from __future__ import annotations

import pytest

from lilya.apps import ChildLilya
from lilya.controllers import Controller
from lilya.enums import MediaType
from lilya.exceptions import (
    InternalServerError,
    LilyaException,
    MethodNotAllowed,
    NotAuthorized,
    NotFound,
    PermissionDenied,
)
from lilya.requests import Request
from lilya.responses import Response
from lilya.routing import Include, Path
from lilya.status import HTTP_400_BAD_REQUEST
from lilya.testclient import create_client
from lilya.types import ExceptionHandler


@pytest.mark.parametrize(
    ["exc_to_raise", "expected_layer"],
    [
        (PermissionDenied, "router"),
        (InternalServerError, "router"),
        (MethodNotAllowed, "handler"),
        (NotFound, "handler"),
    ],
)
def test_exception_handling(exc_to_raise: Exception, expected_layer: str) -> None:
    caller = {"name": ""}

    def create_named_handler(
        caller_name: str, expected_exception: type[Exception]
    ) -> ExceptionHandler:
        def handler(req: Request, exc: Exception) -> Response:
            assert isinstance(exc, expected_exception)
            assert isinstance(req, Request)
            caller["name"] = caller_name
            return Response(
                media_type=MediaType.JSON,
                content={},
                status_code=HTTP_400_BAD_REQUEST,
            )

        return handler

    class ControllerWithHandler(Controller):
        async def get(self):
            raise exc_to_raise

    with create_client(
        routes=[
            Path(
                path="/base/test",
                handler=ControllerWithHandler,
                exception_handlers={
                    MethodNotAllowed: create_named_handler("handler", MethodNotAllowed),
                    NotFound: create_named_handler("handler", NotFound),
                },
            )
        ],
        exception_handlers={
            InternalServerError: create_named_handler("router", InternalServerError),
            PermissionDenied: create_named_handler("router", PermissionDenied),
        },
    ) as client:
        client.get("/base/test/")
        assert caller["name"] == expected_layer


@pytest.mark.parametrize(
    ["exc_to_raise", "expected_layer"],
    [
        (PermissionDenied, "router"),
        (InternalServerError, "include"),
        (MethodNotAllowed, "handler"),
        (NotFound, "handler"),
    ],
)
def test_exception_handling_with_include(exc_to_raise: Exception, expected_layer: str) -> None:
    caller = {"name": ""}

    def create_named_handler(
        caller_name: str, expected_exception: type[Exception]
    ) -> ExceptionHandler:
        def handler(req: Request, exc: Exception) -> Response:
            assert isinstance(exc, expected_exception)
            assert isinstance(req, Request)
            caller["name"] = caller_name
            return Response(
                media_type=MediaType.JSON,
                content={},
                status_code=HTTP_400_BAD_REQUEST,
            )

        return handler

    class ControllerWithHandler(Controller):

        def get(self) -> None:
            raise exc_to_raise

    with create_client(
        routes=[
            Include(
                "/",
                routes=[
                    Path(
                        path="/base/test",
                        handler=ControllerWithHandler,
                        exception_handlers={
                            MethodNotAllowed: create_named_handler("handler", MethodNotAllowed),
                            NotFound: create_named_handler("handler", NotFound),
                        },
                    )
                ],
                exception_handlers={
                    InternalServerError: create_named_handler("include", InternalServerError),
                    MethodNotAllowed: create_named_handler("include", MethodNotAllowed),
                },
            )
        ],
        exception_handlers={
            InternalServerError: create_named_handler("router", InternalServerError),
            PermissionDenied: create_named_handler("router", PermissionDenied),
        },
    ) as client:
        client.get("/base/test/")
        assert caller["name"] == expected_layer


@pytest.mark.parametrize(
    ["exc_to_raise", "expected_layer"],
    [
        (PermissionDenied, "router"),
        (NotAuthorized, "include"),
        (InternalServerError, "handler"),
        (MethodNotAllowed, "handler"),
        (NotFound, "handler"),
    ],
)
def test_exception_handling_with_include_exception_handler(
    exc_to_raise: Exception, expected_layer: str
) -> None:
    caller = {"name": ""}

    def create_named_handler(
        caller_name: str, expected_exception: type[Exception]
    ) -> ExceptionHandler:
        def handler(req: Request, exc: Exception) -> Response:
            assert isinstance(exc, expected_exception)
            assert isinstance(req, Request)
            caller["name"] = caller_name
            return Response(
                media_type=MediaType.JSON,
                content={},
                status_code=HTTP_400_BAD_REQUEST,
            )

        return handler

    class ControllerWithHandler(Controller):

        def get(self) -> None:
            raise exc_to_raise

    with create_client(
        routes=[
            Include(
                "/",
                routes=[
                    Path(
                        path="/base/test",
                        handler=ControllerWithHandler,
                        exception_handlers={
                            MethodNotAllowed: create_named_handler("handler", MethodNotAllowed),
                            NotFound: create_named_handler("handler", NotFound),
                            InternalServerError: create_named_handler(
                                "handler", InternalServerError
                            ),
                        },
                    )
                ],
                exception_handlers={NotAuthorized: create_named_handler("include", NotAuthorized)},
            )
        ],
        exception_handlers={
            InternalServerError: create_named_handler("router", InternalServerError),
            PermissionDenied: create_named_handler("router", PermissionDenied),
        },
    ) as client:
        client.get("/base/test/")
        assert caller["name"] == expected_layer


@pytest.mark.parametrize(
    ["exc_to_raise", "expected_layer"],
    [
        (PermissionDenied, "router"),
        (NotAuthorized, "include"),
        (LilyaException, "handler"),
        (InternalServerError, "handler"),
        (MethodNotAllowed, "handler"),
        (NotFound, "handler"),
    ],
)
def test_exception_handling_with_gateway_exception_handler(
    exc_to_raise: Exception, expected_layer: str
) -> None:
    caller = {"name": ""}

    def create_named_handler(
        caller_name: str, expected_exception: type[Exception]
    ) -> ExceptionHandler:
        def handler(req: Request, exc: Exception) -> Response:
            assert isinstance(exc, expected_exception)
            assert isinstance(req, Request)
            caller["name"] = caller_name
            return Response(
                media_type=MediaType.JSON,
                content={},
                status_code=HTTP_400_BAD_REQUEST,
            )

        return handler

    class ControllerWithHandler(Controller):

        def get(self) -> None:
            raise exc_to_raise

    with create_client(
        routes=[
            Include(
                "/",
                routes=[
                    Path(
                        path="/base/test",
                        handler=ControllerWithHandler,
                        exception_handlers={
                            LilyaException: create_named_handler("handler", LilyaException),
                            MethodNotAllowed: create_named_handler("handler", MethodNotAllowed),
                            NotFound: create_named_handler("handler", NotFound),
                            InternalServerError: create_named_handler(
                                "handler", InternalServerError
                            ),
                        },
                    )
                ],
                exception_handlers={NotAuthorized: create_named_handler("include", NotAuthorized)},
            )
        ],
        exception_handlers={
            InternalServerError: create_named_handler("router", InternalServerError),
            PermissionDenied: create_named_handler("router", PermissionDenied),
        },
    ) as client:
        client.get("/base/test/")
        assert caller["name"] == expected_layer


@pytest.mark.parametrize(
    ["exc_to_raise", "expected_layer"],
    [
        (InternalServerError, "handler"),
        (MethodNotAllowed, "handler"),
        (NotFound, "handler"),
    ],
)
def test_exception_handling_with_child_lilya(exc_to_raise: Exception, expected_layer: str) -> None:
    caller = {"name": ""}

    def create_named_handler(
        caller_name: str, expected_exception: type[Exception]
    ) -> ExceptionHandler:
        def handler(req: Request, exc: Exception) -> Response:
            assert isinstance(exc, expected_exception)
            assert isinstance(req, Request)
            caller["name"] = caller_name
            return Response(
                media_type=MediaType.JSON,
                content={},
                status_code=HTTP_400_BAD_REQUEST,
            )

        return handler

    class ControllerWithHandler(Controller):

        def get(self) -> None:
            raise exc_to_raise

    child_lilya = ChildLilya(
        routes=[
            Path(
                path="/base/test",
                handler=ControllerWithHandler,
                exception_handlers={
                    MethodNotAllowed: create_named_handler("handler", MethodNotAllowed),
                    NotFound: create_named_handler("handler", NotFound),
                    InternalServerError: create_named_handler("handler", InternalServerError),
                },
            )
        ]
    )

    with create_client(
        routes=[
            Include(
                "/",
                routes=[Include(path="/child", app=child_lilya)],
                exception_handlers={NotAuthorized: create_named_handler("include", NotAuthorized)},
            )
        ],
        exception_handlers={
            InternalServerError: create_named_handler("router", InternalServerError),
        },
    ) as client:
        client.get("/child/base/test/")
        assert caller["name"] == expected_layer
