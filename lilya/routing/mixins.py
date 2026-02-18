from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from lilya.middleware.base import DefineMiddleware
from lilya.permissions.base import DefinePermission
from lilya.types import Dependencies, ExceptionHandler


class RoutingMethodsMixin:
    def get(
        self,
        path: str,
        name: str | None = None,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        include_in_schema: bool = True,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
    ) -> Callable[..., Any]:
        """
        Decorator for defining a GET route.

        Args:
            path (str): The URL path pattern for the route.
            name (str | None, optional): The name of the route. Defaults to None.
            middleware (Sequence[DefineMiddleware] | None, optional): The middleware functions to apply to the route. Defaults to None.
            permissions (Sequence[DefinePermission] | None, optional): The permissions required for the route. Defaults to None.
            exception_handlers (Mapping[Any, ExceptionHandler] | None, optional): The exception handlers for the route. Defaults to None.
            dependencies (Dependencies | None, optional): Dependencies to inject into the route handler. Defaults to None.
            include_in_schema (bool, optional): Whether to include the route in the API schema. Defaults to True.
            before_request (Sequence[Callable[..., Any]] | None, optional): Functions to run before the request is processed. Defaults to None.
            after_request (Sequence[Callable[..., Any]] | None, optional): Functions to run after the request is processed. Defaults to None.

        Returns:
            Callable[..., Any]: The decorated function.
        """

        return self.forward_single_method_route(
            path=path,
            method="GET",
            name=name,
            middleware=middleware,
            permissions=permissions,
            exception_handlers=exception_handlers,
            dependencies=dependencies,
            include_in_schema=include_in_schema,
            before_request=before_request,
            after_request=after_request,
        )

    def head(
        self,
        path: str,
        name: str | None = None,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        include_in_schema: bool = True,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
    ) -> Callable[..., Any]:
        """
        Decorator for defining a HEAD route.

        Args:
            path (str): The URL path pattern for the route.
            name (str | None, optional): The name of the route. Defaults to None.
            middleware (Sequence[DefineMiddleware] | None, optional): The middleware functions to apply to the route. Defaults to None.
            permissions (Sequence[DefinePermission] | None, optional): The permissions required for the route. Defaults to None.
            exception_handlers (Mapping[Any, ExceptionHandler] | None, optional): The exception handlers for the route. Defaults to None.
            dependencies (Dependencies | None, optional): Dependencies to inject into the route handler. Defaults to None.
            include_in_schema (bool, optional): Whether to include the route in the API schema. Defaults to True.
            before_request (Sequence[Callable[..., Any]] | None, optional): Functions to run before the request is processed. Defaults to None.
            after_request (Sequence[Callable[..., Any]] | None, optional): Functions to run after the request is processed. Defaults to None.

        Returns:
            Callable[..., Any]: The decorated function.
        """

        return self.forward_single_method_route(
            path=path,
            method="HEAD",
            name=name,
            middleware=middleware,
            permissions=permissions,
            exception_handlers=exception_handlers,
            dependencies=dependencies,
            include_in_schema=include_in_schema,
            before_request=before_request,
            after_request=after_request,
        )

    def post(
        self,
        path: str,
        name: str | None = None,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        include_in_schema: bool = True,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
    ) -> Callable[..., Any]:
        """
        Decorator for defining a POST route.

        Args:
            path (str): The URL path pattern for the route.
            name (str | None, optional): The name of the route. Defaults to None.
            middleware (Sequence[DefineMiddleware] | None, optional): The middleware functions to apply to the route. Defaults to None.
            permissions (Sequence[DefinePermission] | None, optional): The permissions required for the route. Defaults to None.
            exception_handlers (Mapping[Any, ExceptionHandler] | None, optional): The exception handlers for the route. Defaults to None.
            dependencies (Dependencies | None, optional): Dependencies to inject into the route handler. Defaults to None.
            include_in_schema (bool, optional): Whether to include the route in the API schema. Defaults to True.
            before_request (Sequence[Callable[..., Any]] | None, optional): Functions to run before the request is processed. Defaults to None.
            after_request (Sequence[Callable[..., Any]] | None, optional): Functions to run after the request is processed. Defaults to None.

        Returns:
            Callable[..., Any]: The decorated function.
        """

        return self.forward_single_method_route(
            path=path,
            method="POST",
            name=name,
            middleware=middleware,
            permissions=permissions,
            exception_handlers=exception_handlers,
            dependencies=dependencies,
            include_in_schema=include_in_schema,
            before_request=before_request,
            after_request=after_request,
        )

    def put(
        self,
        path: str,
        name: str | None = None,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        include_in_schema: bool = True,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
    ) -> Callable[..., Any]:
        """
        Decorator for defining a PUT route.

        Args:
            path (str): The URL path pattern for the route.
            name (str | None, optional): The name of the route. Defaults to None.
            middleware (Sequence[DefineMiddleware] | None, optional): The middleware functions to apply to the route. Defaults to None.
            permissions (Sequence[DefinePermission] | None, optional): The permissions required for the route. Defaults to None.
            exception_handlers (Mapping[Any, ExceptionHandler] | None, optional): The exception handlers for the route. Defaults to None.
            dependencies (Dependencies | None, optional): Dependencies to inject into the route handler. Defaults to None.
            include_in_schema (bool, optional): Whether to include the route in the API schema. Defaults to True.
            before_request (Sequence[Callable[..., Any]] | None, optional): Functions to run before the request is processed. Defaults to None.
            after_request (Sequence[Callable[..., Any]] | None, optional): Functions to run after the request is processed. Defaults to None.

        Returns:
            Callable[..., Any]: The decorated function.
        """

        return self.forward_single_method_route(
            path=path,
            method="PUT",
            name=name,
            middleware=middleware,
            permissions=permissions,
            exception_handlers=exception_handlers,
            dependencies=dependencies,
            include_in_schema=include_in_schema,
            before_request=before_request,
            after_request=after_request,
        )

    def patch(
        self,
        path: str,
        name: str | None = None,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        include_in_schema: bool = True,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
    ) -> Callable[..., Any]:
        """
        Decorator for defining a PATCH route.

        Args:
            path (str): The URL path pattern for the route.
            name (str | None, optional): The name of the route. Defaults to None.
            middleware (Sequence[DefineMiddleware] | None, optional): The middleware functions to apply to the route. Defaults to None.
            permissions (Sequence[DefinePermission] | None, optional): The permissions required for the route. Defaults to None.
            exception_handlers (Mapping[Any, ExceptionHandler] | None, optional): The exception handlers for the route. Defaults to None.
            dependencies (Dependencies | None, optional): Dependencies to inject into the route handler. Defaults to None.
            include_in_schema (bool, optional): Whether to include the route in the API schema. Defaults to True.
            before_request (Sequence[Callable[..., Any]] | None, optional): Functions to run before the request is processed. Defaults to None.
            after_request (Sequence[Callable[..., Any]] | None, optional): Functions to run after the request is processed. Defaults to None.

        Returns:
            Callable[..., Any]: The decorated function.
        """

        return self.forward_single_method_route(
            path=path,
            method="PATCH",
            name=name,
            middleware=middleware,
            permissions=permissions,
            exception_handlers=exception_handlers,
            dependencies=dependencies,
            include_in_schema=include_in_schema,
            before_request=before_request,
            after_request=after_request,
        )

    def delete(
        self,
        path: str,
        name: str | None = None,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        include_in_schema: bool = True,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
    ) -> Callable[..., Any]:
        """
        Decorator for defining a DELETE route.

        Args:
            path (str): The URL path pattern for the route.
            name (str | None, optional): The name of the route. Defaults to None.
            middleware (Sequence[DefineMiddleware] | None, optional): The middleware functions to apply to the route. Defaults to None.
            permissions (Sequence[DefinePermission] | None, optional): The permissions required for the route. Defaults to None.
            exception_handlers (Mapping[Any, ExceptionHandler] | None, optional): The exception handlers for the route. Defaults to None.
            dependencies (Dependencies | None, optional): Dependencies to inject into the route handler. Defaults to None.
            include_in_schema (bool, optional): Whether to include the route in the API schema. Defaults to True.
            before_request (Sequence[Callable[..., Any]] | None, optional): Functions to run before the request is processed. Defaults to None.
            after_request (Sequence[Callable[..., Any]] | None, optional): Functions to run after the request is processed. Defaults to None.

        Returns:
            Callable[..., Any]: The decorated function.
        """

        return self.forward_single_method_route(
            path=path,
            method="DELETE",
            name=name,
            middleware=middleware,
            permissions=permissions,
            exception_handlers=exception_handlers,
            dependencies=dependencies,
            include_in_schema=include_in_schema,
            before_request=before_request,
            after_request=after_request,
        )

    def trace(
        self,
        path: str,
        name: str | None = None,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        include_in_schema: bool = True,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
    ) -> Callable[..., Any]:
        """
        Decorator for defining a TRACE route.

        Args:
            path (str): The URL path pattern for the route.
            name (str | None, optional): The name of the route. Defaults to None.
            middleware (Sequence[DefineMiddleware] | None, optional): The middleware functions to apply to the route. Defaults to None.
            permissions (Sequence[DefinePermission] | None, optional): The permissions required for the route. Defaults to None.
            exception_handlers (Mapping[Any, ExceptionHandler] | None, optional): The exception handlers for the route. Defaults to None.
            dependencies (Dependencies | None, optional): Dependencies to inject into the route handler. Defaults to None.
            include_in_schema (bool, optional): Whether to include the route in the API schema. Defaults to True.
            before_request (Sequence[Callable[..., Any]] | None, optional): Functions to run before the request is processed. Defaults to None.
            after_request (Sequence[Callable[..., Any]] | None, optional): Functions to run after the request is processed. Defaults to None.

        Returns:
            Callable[..., Any]: The decorated function.
        """

        return self.forward_single_method_route(
            path=path,
            method="TRACE",
            name=name,
            middleware=middleware,
            permissions=permissions,
            exception_handlers=exception_handlers,
            dependencies=dependencies,
            include_in_schema=include_in_schema,
            before_request=before_request,
            after_request=after_request,
        )

    def options(
        self,
        path: str,
        name: str | None = None,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        include_in_schema: bool = True,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
    ) -> Callable[..., Any]:
        """
        Decorator for defining a OPTIONS route.

        Args:
            path (str): The URL path pattern for the route.
            name (str | None, optional): The name of the route. Defaults to None.
            middleware (Sequence[DefineMiddleware] | None, optional): The middleware functions to apply to the route. Defaults to None.
            permissions (Sequence[DefinePermission] | None, optional): The permissions required for the route. Defaults to None.
            exception_handlers (Mapping[Any, ExceptionHandler] | None, optional): The exception handlers for the route. Defaults to None.
            dependencies (Dependencies | None, optional): Dependencies to inject into the route handler. Defaults to None.
            include_in_schema (bool, optional): Whether to include the route in the API schema. Defaults to True.
            before_request (Sequence[Callable[..., Any]] | None, optional): Functions to run before the request is processed. Defaults to None.
            after_request (Sequence[Callable[..., Any]] | None, optional): Functions to run after the request is processed. Defaults to None.

        Returns:
            Callable[..., Any]: The decorated function.
        """

        return self.forward_single_method_route(
            path=path,
            method="OPTIONS",
            name=name,
            middleware=middleware,
            permissions=permissions,
            exception_handlers=exception_handlers,
            dependencies=dependencies,
            include_in_schema=include_in_schema,
            before_request=before_request,
            after_request=after_request,
        )

    def forward_single_method_route(
        self,
        path: str,
        method: str,
        name: str | None = None,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        include_in_schema: bool = True,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
    ) -> Callable[..., Any]:
        """For customization, defaults to route."""
        return self.route(
            path=path,
            methods=[method],
            name=name,
            middleware=middleware,
            permissions=permissions,
            exception_handlers=exception_handlers,
            dependencies=dependencies,
            include_in_schema=include_in_schema,
            before_request=before_request,
            after_request=after_request,
        )

    def route(
        self,
        path: str,
        methods: list[str],
        name: str | None = None,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        include_in_schema: bool = True,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
    ) -> Callable[..., Any]:
        """
        Decorator for defining a generic route.

        Args:
            path (str): The URL path pattern for the route.
            methods (list[str] | None, optional): The HTTP methods allowed for the route. Defaults to None.
            name (str | None, optional): The name of the route. Defaults to None.
            middleware (Sequence[DefineMiddleware] | None, optional): The middleware functions to apply to the route. Defaults to None.
            permissions (Sequence[DefinePermission] | None, optional): The permissions required for the route. Defaults to None.
            exception_handlers (Mapping[Any, ExceptionHandler] | None, optional): The exception handlers for the route. Defaults to None.
            dependencies (Dependencies | None, optional): Dependencies to inject into the route handler. Defaults to None.
            include_in_schema (bool, optional): Whether to include the route in the API schema. Defaults to True.
            before_request (Sequence[Callable[..., Any]] | None, optional): Functions to run before the request is processed. Defaults to None.
            after_request (Sequence[Callable[..., Any]] | None, optional): Functions to run after the request is processed. Defaults to None.

        Returns:
            Callable[..., Any]: The decorated function.
        """
        raise NotImplementedError()

    def websocket(
        self,
        path: str,
        name: str | None = None,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
    ) -> Callable[..., Any]:
        """
        Decorator for defining a WebSocket route.

        Args:
            path (str): The URL path for the WebSocket route.
            name (str, optional): The name of the route. Defaults to None.
            middleware (Sequence[DefineMiddleware], optional): The middleware to apply to the route. Defaults to None.
            permissions (Sequence[DefinePermission], optional): The permissions required for the route. Defaults to None.
            exception_handlers (Mapping[Any, ExceptionHandler], optional): The exception handlers for the route. Defaults to None.
            dependencies (Dependencies | None, optional): Dependencies to inject into the route handler. Defaults to None.
            before_request (Sequence[Callable[..., Any]] | None, optional): Functions to run before the request is processed. Defaults to None.
            after_request (Sequence[Callable[..., Any]] | None, optional): Functions to run after the request is processed. Defaults to None.

        Returns:
            Callable[..., Any]: The decorated function.
        """
        raise NotImplementedError()
