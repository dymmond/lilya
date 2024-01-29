from __future__ import annotations

import inspect
import re
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Pattern,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
)

from lilya.core.urls import include
from lilya.datastructures import URLPath
from lilya.enums import HTTPMethod, Match, ScopeType
from lilya.exceptions import ImproperlyConfigured
from lilya.middleware.base import Middleware
from lilya.permissions.base import Permission
from lilya.responses import PlainText
from lilya.types import ASGIApp, Lifespan, Receive, Scope, Send
from lilya.websockets import WebSocketClose

T = TypeVar("T")


class NoMatchFound(Exception):
    """
    Raised by `.url_for(name, **path_params)` and `.url_path_for(name, **path_params)`
    if no matching route exists.
    """

    def __init__(self, name: str, path_params: Dict[str, Any]) -> None:
        params = ", ".join(list(path_params.keys()))
        super().__init__(f'No route exists for name "{name}" and params "{params}".')


def get_name(handler: Callable[..., Any]) -> str:
    """
    Returns the name of a given handler.
    """
    return (
        handler.__name__
        if inspect.isroutine(handler) or inspect.isclass(handler)
        else handler.__class__.__name__
    )


def replace_params(
    path: str,
    param_convertors: dict[str, Convertor[Any]],
    path_params: dict[str, str],
) -> tuple[str, dict[str, str]]:
    for key, value in list(path_params.items()):
        if "{" + key + "}" in path:
            convertor = param_convertors[key]
            value = convertor.to_string(value)
            path = path.replace("{" + key + "}", value)
            path_params.pop(key)
    return path, path_params


class Convertor(Generic[T]):
    def __init__(self, regex: str) -> None:
        self.regex = regex

    def convert(self, value: str) -> T:
        raise NotImplementedError()  # pragma: no cover

    def to_string(self, value: T) -> str:
        raise NotImplementedError()  # pragma: no cover


# Regular expression pattern to match parameter placeholders
PARAM_REGEX = re.compile(r"{([^:]+):([^}]+)}")

# Available converter types
CONVERTOR_TYPES: Dict[str, Convertor] = {
    "str": Convertor("[^/]+"),
    "int": Convertor(r"\d+"),
}


def compile_path(path: str) -> Tuple[Pattern[str], str, Dict[str, Convertor]]:
    """
    Compile a path or host string into a three-tuple of (regex, format, {param_name:convertor}).

    Args:
        path (str): The path or host string.

    Returns:
        Tuple[Pattern[str], str, Dict[str, Convertor[Any]]]: The compiled regex pattern, format string,
        and a dictionary of parameter names and converters.
    """
    is_host = not path.startswith("/")
    path_regex = "^"
    path_format = ""
    duplicated_params = set()

    idx = 0
    param_convertors = {}

    for match in PARAM_REGEX.finditer(path):
        param_name, convertor_type = match.groups("str")
        convertor_type = convertor_type.lstrip(":")

        assert convertor_type in CONVERTOR_TYPES, f"Unknown path convertor '{convertor_type}'"
        convertor = CONVERTOR_TYPES[convertor_type]

        path_regex += re.escape(path[idx : match.start()])
        path_regex += f"(?P<{param_name}>{convertor.regex})"

        path_format += path[idx : match.start()]
        path_format += "{%s}" % param_name

        if param_name in param_convertors:
            duplicated_params.add(param_name)

        param_convertors[param_name] = convertor
        idx = match.end()

    if duplicated_params:
        names = ", ".join(sorted(duplicated_params))
        ending = "s" if len(duplicated_params) > 1 else ""
        raise ValueError(f"Duplicated param name{ending} {names} at path {path}")

    if is_host:
        # Align with `Host.matches()` behavior, which ignores port.
        hostname = path[idx:].split(":")[0]
        path_regex += re.escape(hostname) + "$"
    else:
        path_regex += re.escape(path[idx:]) + "$"

    path_format += path[idx:]

    return re.compile(path_regex), path_format, param_convertors


class BasePath:
    """
    The base of all paths (routes) for any ASGI application
    with Lilya.
    """

    def search(self, scope: Scope) -> Tuple[Match, Scope]:
        """
        Searches for a matching route.
        """
        raise NotImplementedError()  # pragma: no cover

    def path_for(self, name: str, /, **path_params: Any) -> URLPath:
        """
        Returns a URL of a matching route.
        """
        raise NotImplementedError()  # pragma: no cover

    async def dispatch(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handles the matched ASGI route.
        """
        raise NotImplementedError()  # pragma: no cover

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        match, child_scope = self.matches(scope)
        if match == Match.NONE:
            if scope["type"] == ScopeType.HTTP:
                response = PlainText("Not Found", status_code=404)
                await response(scope, receive, send)
            elif scope["type"] == "websocket":
                websocket_close = WebSocketClose()
                await websocket_close(scope, receive, send)
            return

        scope.update(child_scope)
        await self.dispatch(scope, receive, send)


class Router:
    """
    A Lilya router object.
    """

    def __init__(
        self,
        routes: Union[Sequence[BasePath], None] = None,
        redirect_slashes: bool = True,
        default: Union[ASGIApp, None] = None,
        on_startup: Union[Sequence[Callable[[], Any]], None] = None,
        on_shutdown: Union[Sequence[Callable[[], Any]], None] = None,
        lifespan: Union[Lifespan[Any], None] = None,
        *,
        middleware: Union[Sequence[Middleware], None] = None,
        permissions: Union[Sequence[Permission], None] = None,
        include_in_schema: bool = True,
    ) -> None:
        self.routes = [] if routes is None else list(routes)
        self.redirect_slashes = redirect_slashes
        self.default = self.raise_404 if default is None else default
        self.on_startup = [] if on_startup is None else list(on_startup)
        self.on_shutdown = [] if on_shutdown is None else list(on_shutdown)
        self.include_in_schema = include_in_schema

        self.middleware = middleware if middleware is not None else list(middleware)
        self.permissions = permissions if permissions is not None else list(permissions)

        # Execute the middlewares
        if middleware is not None:
            for cls, options in reversed(middleware):
                self.middleware_stack = cls(app=self.app, **options)

        # Execute the permissions
        if permissions is not None:
            for cls, options in reversed(permissions):
                self.permission_stack = cls(app=self.app, **options)

    async def raise_404(self, scope: Scope, receive: Receive, send: Send) -> None: ...

    def path_for(self, name: str, /, **path_params: Any) -> URLPath:
        for route in self.routes:
            try:
                return route.path_for(name, **path_params)
            except NoMatchFound:
                ...
        raise NoMatchFound(name, path_params)


class Path(BasePath):
    """
    The way you can define a route in Lilya and apply the corresponding
    path definition.

    ## Example

    ```python
    from lilya.routing import Path

    Path('/home', callable=..., name="home")
    ```
    """

    def __init__(
        self,
        path: str,
        handler: Callable[..., Any],
        *,
        methods: Union[List[str], None] = None,
        name: Union[str, None] = None,
        include_in_schema: bool = True,
        middleware: Union[Sequence[Middleware], None] = None,
        permissions: Union[Sequence[Permission], None] = None,
    ) -> None:
        assert path.startswith("/"), "Paths must start with '/'"
        self.path = path
        self.handler = handler
        self.name = get_name(handler) if name is None else name
        self.include_in_schema = include_in_schema
        self.methods: Union[List[str], Set[str], None] = methods

        # Defition of the app
        self.app = handler

        # Execute the middlewares
        if middleware is not None:
            for cls, options in reversed(middleware):
                self.app = cls(app=self.app, **options)

        # Execute the permissions
        if permissions is not None:
            for cls, options in reversed(permissions):
                self.app = cls(app=self.app, **options)

        if self.methods is not None:
            self.methods = {method.upper() for method in methods}
            if HTTPMethod.GET in self.methods:
                self.methods.add(HTTPMethod.HEAD)

        self.path_regex, self.path_format, self.param_convertors = compile_path(path)

    async def path_for(self, name: str, /, **path_params: Any) -> URLPath:
        seen_params = set(path_params.keys())
        expected_params = set(self.param_convertors.keys())

        if name != self.name or seen_params != expected_params:
            raise NoMatchFound(name, path_params)

        path, remaining_params = replace_params(
            self.path_format, self.param_convertors, path_params
        )
        assert not remaining_params
        return URLPath(path=path, protocol="http")


class WebsocketPath(BasePath):
    def __init__(
        self,
        path: str,
        handler: Callable[..., Any],
        *,
        methods: Union[List[str], None] = None,
        name: Union[str, None] = None,
        include_in_schema: bool = True,
        middleware: Union[Sequence[Middleware], None] = None,
        permissions: Union[Sequence[Permission], None] = None,
    ) -> None:
        assert path.startswith("/"), "Paths must start with '/'"
        self.path = path
        self.handler = handler
        self.name = get_name(handler) if name is None else name
        self.include_in_schema = include_in_schema
        self.methods: Union[List[str], Set[str], None] = methods

        # Execute the middlewares
        if middleware is not None:
            for cls, options in reversed(middleware):
                self.app = cls(app=self.app, **options)

        # Execute the permissions
        if permissions is not None:
            for cls, options in reversed(permissions):
                self.app = cls(app=self.app, **options)


class Include(BasePath):
    __slots__ = (
        "path",
        "app",
        "namespace",
        "pattern",
        "name",
        "exception_handlers",
        "permissions",
        "middleware",
    )

    def __init__(
        self,
        path: str,
        app: Union[ASGIApp, None] = None,
        routes: Union[Sequence[BasePath], None] = None,
        namespace: Union[str, None] = None,
        pattern: Union[str, None] = None,
        name: Union[str, None] = None,
        *,
        middleware: Union[Sequence[Middleware], None] = None,
        permissions: Union[Sequence[Permission], None] = None,
        include_in_schema: bool = True,
    ) -> None:
        assert path == "" or path.startswith("/"), "Routed paths must start with '/'"
        assert (
            app is not None or routes is not None
        ), "Either 'app=...', or 'routes=' must be specified"
        self.path = path.rstrip("/")

        assert (
            namespace is None or routes is None
        ), "Either 'namespace=...' or 'routes=', not both."

        if namespace and not isinstance(namespace, str):
            raise ImproperlyConfigured("Namespace must be a string. Example: 'myapp.routes'.")

        if pattern and not isinstance(pattern, str):
            raise ImproperlyConfigured("Pattern must be a string. Example: 'route_patterns'.")

        if pattern and routes:
            raise ImproperlyConfigured("Pattern must be used only with namespace.")

        if namespace is not None:
            routes = include(namespace, pattern)

        if app is not None:
            self._base_app: ASGIApp = app
        else:
            self._base_app = Router(routes=routes)  # type: ignore
        self.app = self._base_app

        # if middleware is not None:
        #     for cls, options in reversed(middleware):
        #         self.app = cls(app=self.app, **options)

        # if permissions is not None:
        #     for cls, options in reversed(permissions):
        #         self.app = cls(app=self.app, **options)

        self.name = name
        self.include_in_schema = include_in_schema
        self.middleware = middleware if middleware is not None else list(middleware)
        self.permissions = permissions if permissions is not None else list(permissions)


class Host(BasePath): ...
