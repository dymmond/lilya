from __future__ import annotations

import sys
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Type,
    Union,
    cast,
)

from typing_extensions import Annotated, Doc

from lilya._utils import is_class_and_subclass
from lilya.conf import settings as lilya_settings
from lilya.conf.exceptions import FieldException
from lilya.conf.global_settings import Settings
from lilya.datastructures import State, URLPath
from lilya.middleware.asyncexit import AsyncExitStackMiddleware
from lilya.middleware.base import DefineMiddleware
from lilya.middleware.exceptions import ExceptionMiddleware
from lilya.middleware.server_error import ServerErrorMiddleware
from lilya.permissions.base import DefinePermission
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.protocols.permissions import PermissionProtocol
from lilya.requests import Request
from lilya.responses import Response
from lilya.routing import BasePath, Router
from lilya.types import ApplicationType, ASGIApp, ExceptionHandler, Lifespan, Receive, Scope, Send
from lilya.websockets import WebSocket

if sys.version_info >= (3, 10):  # pragma: no cover
    from typing import ParamSpec
else:  # pragma: no cover
    from typing_extensions import ParamSpec

P = ParamSpec("P")


class Lilya:
    """
    Initialize the Lilya ASGI framework.

    **Example**:

    ```python
    from lilya import Lilya

    app = Lilya(debug=True, routes=[...], middleware=[...], ...)
    ```
    """

    def __init__(
        self,
        debug: Annotated[bool, Doc("Enable or disable debug mode. Defaults to False.")] = False,
        settings_module: Annotated[
            Optional[Settings],
            Doc(
                """
                Alternative settings parameter. This parameter is an alternative to
                `SETTINGS_MODULE` way of loading your settings into an Lilya application.

                When the `settings_module` is provided, it will make sure it takes priority over
                any other settings provided for the instance.
                """
            ),
        ] = None,
        routes: Annotated[
            Union[Sequence[Any], None],
            Doc(
                """
                A sequence of routes for the application.
                """
            ),
        ] = None,
        middleware: Annotated[
            Union[Sequence[DefineMiddleware], None],
            Doc(
                """
                A sequence of middleware components for the application.
                """
            ),
        ] = None,
        exception_handlers: Annotated[
            Union[Mapping[Any, ExceptionHandler], None],
            Doc(
                """
                A mapping of exception types to handlers for the application.
                """
            ),
        ] = None,
        permissions: Annotated[
            Union[Sequence[DefinePermission], None],
            Doc(
                """
                A sequence of permission components for the application.
                """
            ),
        ] = None,
        on_startup: Annotated[
            Union[Sequence[Callable[[], Any]], None],
            Doc(
                """
                A sequence of startup functions to be called when the application starts.
                """
            ),
        ] = None,
        on_shutdown: Annotated[
            Union[Sequence[Callable[[], Any]], None],
            Doc(
                """
                A sequence of shutdown functions to be called when the application stops.
                """
            ),
        ] = None,
        redirect_slashes: Annotated[
            bool,
            Doc(
                """
                Enable or disable automatic trailing slash redirection for HTTP routes.
                """
            ),
        ] = True,
        lifespan: Annotated[
            Optional[Lifespan[ApplicationType]],
            Doc(
                """
                An optional lifespan handler for managing startup and shutdown events.
                """
            ),
        ] = None,
        include_in_schema: Annotated[
            bool,
            Doc(
                """
                Enable or disable inclusion of the application in the OpenAPI schema.
                """
            ),
        ] = True,
    ) -> None:
        self.settings_module: Settings = None

        if settings_module:
            if not isinstance(settings_module, Settings) and not is_class_and_subclass(
                settings_module, Settings
            ):  # type: ignore
                raise FieldException("'settings_module' must be a subclass of Settings")
            elif isinstance(settings_module, Settings):
                self.settings_module = settings_module
            elif is_class_and_subclass(settings_module, Settings):  # type: ignore
                self.settings_module = settings_module()

        self.debug = self.__load_settings_value("debug", debug, is_boolean=True)
        self.exception_handlers = {} if exception_handlers is None else dict(exception_handlers)
        self.custom_middleware = self.__load_settings_value("middleware", middleware)
        self.custom_permissions = self.__load_settings_value("permissions", permissions)

        self.state = State()
        self.middleware_stack: Union[ASGIApp, None] = None

        self.router: Router = Router(
            routes=routes,
            redirect_slashes=redirect_slashes,
            permissions=self.custom_permissions,
            on_startup=self.__load_settings_value("on_startup", on_startup),
            on_shutdown=self.__load_settings_value("on_shutdown", on_shutdown),
            lifespan=self.__load_settings_value("lifespan", lifespan),
            include_in_schema=include_in_schema,
        )

    @property
    def routes(self) -> List[BasePath]:
        return self.router.routes

    def __load_settings_value(
        self, name: str, value: Optional[Any] = None, is_boolean: bool = False
    ) -> Any:
        """
        Loader used to get the settings defaults and custom settings
        of the application.
        """
        if not is_boolean:
            if not value:
                return self.__get_settings_value(
                    self.settings_module, cast(Settings, lilya_settings), name
                )
            return value

        if value is not None:
            return value
        return self.__get_settings_value(
            self.settings_module, cast(Settings, lilya_settings), name
        )

    def __get_settings_value(
        self,
        local_settings: Optional[Settings],
        global_settings: Settings,
        value: str,
    ) -> Any:
        """Obtains the value from a settings module or defaults to the global settings"""
        setting_value = None

        if local_settings:
            setting_value = getattr(local_settings, value, None)
        if setting_value is None:
            return getattr(global_settings, value, None)
        return setting_value

    @property
    def settings(self) -> Settings:
        """
        Returns the Lilya settings object for easy access.

        This `settings` are the ones being used by the application upon
        initialisation.

        **Example**

        ```python
        from lilya.app import Lilya

        app = Lilya()
        app.settings
        ```
        """
        general_settings = self.settings_module if self.settings_module else lilya_settings
        return cast(Settings, general_settings)

    def path_for(self, name: str, /, **path_params: Any) -> URLPath:
        return self.router.path_for(name, **path_params)

    def build_middleware_stack(self) -> ASGIApp:
        """
        Build the optimized middleware stack for the Lilya application.

        Returns:
            ASGIApp: The ASGI application with the middleware stack.
        """
        error_handler = self._get_error_handler()
        exception_handlers = self._get_exception_handlers()

        middleware = [
            DefineMiddleware(ServerErrorMiddleware, handler=error_handler, debug=self.debug),
            *self.custom_middleware,
            DefineMiddleware(ExceptionMiddleware, handlers=exception_handlers, debug=self.debug),
            DefineMiddleware(AsyncExitStackMiddleware),
        ]

        app = self.router
        for middleware_class, args, options in reversed(middleware):
            app = middleware_class(app=app, *args, **options)

        return app

    def _get_error_handler(self) -> Optional[Callable[[Request, Exception], Response]]:
        """
        Get the error handler for middleware based on the exception handlers.

        Returns:
            Optional[Callable[[Request, Exception], Response]]: The error handler function.
        """
        return self.exception_handlers.get(500) or self.exception_handlers.get(Exception)  # type: ignore

    def _get_exception_handlers(self) -> Dict[Exception, ExceptionHandler]:
        """
        Get the exception handlers for middleware based on the application's exception handlers.

        Returns:
            Dict: The exception handlers.
        """
        return {
            key: value
            for key, value in self.exception_handlers.items()
            if key not in (500, Exception)
        }

    def on_event(self, event_type: str) -> Callable:
        return self.router.on_event(event_type)

    def include(
        self,
        path: str,
        app: ASGIApp,
        name: Union[str, None] = None,
        middleware: Union[Sequence[DefineMiddleware], None] = None,
        permissions: Union[Sequence[DefinePermission], None] = None,
        namespace: Union[str, None] = None,
        pattern: Union[str, None] = None,
        include_in_schema: bool = True,
    ) -> None:
        """
        Adds an Include application into the routes.
        """
        self.router.include(
            path=path,
            app=app,
            name=name,
            middleware=middleware,
            permissions=permissions,
            namespace=namespace,
            pattern=pattern,
            include_in_schema=include_in_schema,
        )

    def host(self, host: str, app: ASGIApp, name: Union[str, None] = None) -> None:
        """
        Adds a Host application into the routes.
        """
        self.router.host(host=host, app=app, name=name)

    def add_route(
        self,
        path: str,
        handler: Callable[[Request], Union[Awaitable[Response], Response]],
        methods: Union[List[str], None] = None,
        name: Union[str, None] = None,
        middleware: Union[Sequence[DefineMiddleware], None] = None,
        permissions: Union[Sequence[DefinePermission], None] = None,
        include_in_schema: bool = True,
    ) -> None:
        """
        Manually creates a `Path`` from a given handler.
        """
        self.router.add_route(
            path=path,
            handler=handler,
            methods=methods,
            name=name,
            middleware=middleware,
            permissions=permissions,
            include_in_schema=include_in_schema,
        )

    def add_websocket_route(
        self,
        path: str,
        handler: Callable[[WebSocket], Awaitable[None]],
        name: Union[str, None] = None,
        middleware: Union[Sequence[DefineMiddleware], None] = None,
        permissions: Union[Sequence[DefinePermission], None] = None,
    ) -> None:
        """
        Manually creates a `WebSocketPath` from a given handler.
        """
        self.router.add_websocket_route(
            path=path, handler=handler, name=name, middleware=middleware, permissions=permissions
        )

    def add_middleware(
        self, middleware: Type[MiddlewareProtocol], *args: P.args, **kwargs: P.kwargs
    ) -> None:
        """
        Adds an external middleware to the stack.
        """
        if self.middleware_stack is not None:
            raise RuntimeError("Middlewares cannot be added once the application has started.")
        self.custom_middleware.insert(0, DefineMiddleware(middleware, *args, **kwargs))

    def add_permission(
        self, permission: Type[PermissionProtocol], *args: P.args, **kwargs: P.kwargs
    ) -> None:
        """
        Adds an external permissions to the stack.
        """
        if self.router.permission_started:
            raise RuntimeError("Permissions cannot be added once the application has started.")
        self.router.permissions.insert(0, DefinePermission(permission, *args, **kwargs))

    def add_exception_handler(
        self,
        exception_cls_or_status_code: Union[int, Type[Exception]],
        handler: ExceptionHandler,
    ) -> None:
        self.exception_handlers[exception_cls_or_status_code] = handler

    def add_event_handler(self, event_type: str, func: Callable[[], Any]) -> None:
        self.router.add_event_handler(event_type, func)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        scope["app"] = self
        if self.middleware_stack is None:
            self.middleware_stack = self.build_middleware_stack()
        await self.middleware_stack(scope, receive, send)


class ChildLilya(Lilya):
    """
    `ChildLilya` application object. The main entry-point for a modular application/API
    with Lilya.

    The `ChildLilya` inherits directly from the `Lilya` object which means all the same
    parameters, attributes and functions of Lilya ara also available in the `ChildLilya`.


    !!! Tip
        All the parameters available in the object have defaults being loaded by the
        [settings system](https://esmerald.dev/application/settings/) if nothing is provided.

    ## Example

    ```python
    from lilya.app import Lilya, ChildLilya
    from lilya.routing import Include

    app = Lilya(routes=[Include('/child', app=ChildLilya(...))])
    ```
    """
