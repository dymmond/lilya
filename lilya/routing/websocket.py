from __future__ import annotations

import functools
import inspect
import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from lilya._internal._middleware import wrap_middleware
from lilya._internal._module_loading import import_string
from lilya._internal._path import clean_path, compile_path, get_route_path, replace_params
from lilya._internal._permissions import wrap_permission
from lilya._internal._responses import BaseHandler
from lilya.compat import is_async_callable
from lilya.concurrency import run_in_threadpool
from lilya.conf import _monkay
from lilya.datastructures import URLPath
from lilya.dependencies import wrap_dependency
from lilya.enums import Match, ScopeType
from lilya.exceptions import ImproperlyConfigured
from lilya.middleware.base import DefineMiddleware
from lilya.permissions.base import DefinePermission
from lilya.types import Dependencies, ExceptionHandler, Receive, Scope, Send

from .base import BasePath
from .types import NoMatchFound, get_name


class WebSocketPath(BaseHandler, BasePath):
    __slots__ = (
        "path",
        "handler",
        "name",
        "include_in_schema",
        "middleware",
        "permissions",
        "exception_handlers",
        "before_request",
        "after_request",
        "__handler_app__",
        "_signature",
        "dependencies",
    )

    def __init__(
        self,
        path: str,
        handler: Callable[..., Any] | str,
        *,
        name: str | None = None,
        include_in_schema: bool = True,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
    ) -> None:
        assert path.startswith("/"), "Paths must start with '/'"
        self.path = clean_path(path)

        handler = import_string(handler) if isinstance(handler, str) else handler
        self.handler = handler

        self.name = get_name(handler) if name is None else name
        self.include_in_schema = include_in_schema

        # Wrap dependencies
        _dependencies = dependencies if dependencies is not None else {}
        self.dependencies = {key: wrap_dependency(dep) for key, dep in _dependencies.items()}

        # Definition of the app
        self.__handler_app__ = handler
        while isinstance(self.__handler_app__, functools.partial):
            self.__handler_app__ = self.__handler_app__.func

        if inspect.isfunction(self.__handler_app__) or inspect.ismethod(self.__handler_app__):
            self.app = self.handle_websocket_session(handler)
        else:
            self.app = handler

        if middleware is not None:
            self.middleware = [wrap_middleware(mid) for mid in middleware]
        else:
            self.middleware = middleware or []

        self.permissions = permissions if permissions is not None else []
        self.exception_handlers = {} if exception_handlers is None else dict(exception_handlers)

        self.wrapped_permissions = [
            wrap_permission(permission) for permission in permissions or []
        ]

        self.before_request = before_request if before_request is not None else []
        self.after_request = after_request if after_request is not None else []

        self._apply_controller_options()

        self._apply_permissions(self.wrapped_permissions)
        self._apply_middleware(self.middleware)

        self.path_regex, self.path_format, self.param_convertors, self.path_start = compile_path(
            self.path
        )

    @property
    def signature(self) -> inspect.Signature:
        if not hasattr(self, "_signature"):
            self._signature: inspect.Signature = inspect.signature(self.__handler_app__)
            self.handle_signature()
        return self._signature

    @signature.setter
    def signature(self, value: inspect.Signature) -> None:
        self._signature = value

    def handle_signature(self) -> None:
        """
        Validates the return annotation of a handler
        if `enforce_return_annotation` is set to True.
        """
        if not _monkay.settings.enforce_return_annotation:
            return None

        if self.signature.return_annotation is inspect._empty:
            raise ImproperlyConfigured(
                "A return value of a route handler function should be type annotated. "
                "If your function doesn't return a value or returns None, annotate it as returning 'NoReturn' or 'None' respectively."
            )

    def _apply_controller_options(self) -> None:
        """
        Apply controller options to the path.
        """
        if hasattr(self.app, "__is_controller__"):
            controller = self.app
            if controller.permissions:  # type: ignore[attr-defined]
                self.wrapped_permissions.extend(
                    [wrap_permission(permission) for permission in controller.permissions]  # type: ignore[attr-defined]
                )

            if controller.middleware:  # type: ignore[attr-defined]
                self.middleware.extend([wrap_middleware(mid) for mid in controller.middleware])  # type: ignore[attr-defined]

            if controller.exception_handlers:  # type: ignore[attr-defined]
                self.exception_handlers.update(controller.exception_handlers)  # type: ignore[attr-defined]

            if controller.dependencies and self.dependencies:  # type: ignore[attr-defined]
                self.dependencies.update(controller.dependencies)  # type: ignore[attr-defined]

            if controller.before_request:  # type: ignore[attr-defined]
                self.before_request.extend(controller.before_request)  # type: ignore[attr-defined]

            if controller.after_request:  # type: ignore[attr-defined]
                self.after_request.extend(controller.after_request)  # type: ignore[attr-defined]

    def _apply_middleware(self, middleware: Sequence[DefineMiddleware] | None) -> None:
        """
        Apply middleware to the app.

        Args:
            middleware (Union[Sequence[DefineMiddleware], None]): The middleware.

        Returns:
            None
        """
        if middleware is not None:
            for cls, args, options in reversed(middleware):
                self.app = cls(app=self.app, *args, **options)

    def _apply_permissions(self, permissions: Sequence[DefinePermission] | None) -> None:
        """
        Apply permissions to the app.

        Args:
            permissions (Union[Sequence[DefinePermission], None]): The permissions.

        Returns:
            None
        """
        if permissions is not None:
            for cls, args, options in reversed(permissions):
                self.app = cls(app=self.app, *args, **options)

    def search(self, scope: Scope) -> tuple[Match, Scope]:
        """
        Searches within the route patterns and matches against the regex.

        If found, then dispatches the request to the handler of the object.

        Args:
            scope (Scope): The request scope.

        Returns:
            Tuple[Match, Scope]: The match result and child scope.
        """
        if scope["type"] == ScopeType.WEBSOCKET:
            route_path = get_route_path(scope)
            match = self.path_regex.match(route_path)

            if match:
                return self.handle_match(scope, match)

        return Match.NONE, {}

    def handle_match(self, scope: Scope, match: re.Match) -> tuple[Match, Scope]:
        """
        Handles the case when a match is found in the route patterns.

        Args:
            scope (Scope): The request scope.
            match: The match object from the regex.

        Returns:
            Tuple[Match, Scope]: The match result and child scope.
        """
        matched_params = {
            key: self.param_convertors[key].transform(value)
            for key, value in match.groupdict().items()
        }
        path_params = {**scope.get("path_params", {}), **matched_params}
        upstream = list(scope.get("dependencies", []))
        child_scope = {
            "handler": self.handler,
            "path_params": path_params,
            "dependencies": upstream + [self.dependencies],
        }

        return Match.FULL, child_scope

    async def handle_dispatch(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handles the dispatch of the request to the appropriate handler.

        Args:
            scope (Scope): The request scope.
            receive (Receive): The receive channel.
            send (Send): The send channel.

        Returns:
            None
        """
        try:
            for before_request in self.before_request:
                if inspect.isclass(before_request):
                    before_request = before_request()

                if is_async_callable(before_request):
                    await before_request(scope, receive, send)
                else:
                    await run_in_threadpool(before_request, scope, receive, send)

            await self.app(scope, receive, send)

            for after_request in self.after_request:
                if inspect.isclass(after_request):
                    after_request = after_request()

                if is_async_callable(after_request):
                    await after_request(scope, receive, send)
                else:
                    await run_in_threadpool(after_request, scope, receive, send)
        except Exception as ex:
            await self.handle_exception_handlers(scope, receive, send, ex)

    def path_for(self, name: str, /, **path_params: Any) -> URLPath:
        """
        Generates a URL path for the specified route name and parameters.

        Args:
            name (str): The name of the route.
            path_params (dict): The path parameters.

        Returns:
            URLPath: The generated URL path.

        Raises:
            NoMatchFound: If there is no match for the given name and parameters.

        """
        return self.url_path_for(name, **path_params)

    def url_path_for(self, name: str, /, **path_params: Any) -> URLPath:
        """
        Generates a URL path for the specified route name and parameters.

        Args:
            name (str): The name of the route.
            path_params (dict): The path parameters.

        Returns:
            URLPath: The generated URL path.

        Raises:
            NoMatchFound: If there is no match for the given name and parameters.

        """
        self.validate_params(name, path_params)

        path, remaining_params = replace_params(
            self.path_format, self.param_convertors, path_params
        )
        assert not remaining_params
        return URLPath(path=path, protocol=ScopeType.WEBSOCKET.value)

    def validate_params(self, name: str, path_params: dict) -> None:
        """
        Validates the route name and path parameters.

        Args:
            name (str): The name of the route.
            path_params (dict): The path parameters.

        Raises:
            NoMatchFound: If there is a mismatch in route name or parameters.
        """
        seen_params = set(path_params.keys())
        expected_params = set(self.param_convertors.keys())

        if name != self.name or seen_params != expected_params:
            raise NoMatchFound(name, path_params)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(path={self.path!r}, name={self.name!r})"
