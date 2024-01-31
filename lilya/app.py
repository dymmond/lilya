from __future__ import annotations

from typing import Any, Awaitable, Callable, List, Mapping, Optional, Sequence, Union

from typing_extensions import Annotated, Doc

from lilya._utils import is_class_and_subclass
from lilya.conf.exceptions import FieldException
from lilya.conf.global_settings import Settings
from lilya.datastructures import State, URLPath
from lilya.middleware.base import Middleware
from lilya.permissions.base import Permission
from lilya.requests import Request
from lilya.responses import Response
from lilya.routing import BasePath, Router
from lilya.types import ApplicationType, ASGIApp, ExceptionHandler, Lifespan, Receive, Scope, Send
from lilya.websockets import WebSocket


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
                `SETTINGS_MODULE` way of loading your settings into an Esmerald application.

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
            Union[Sequence[Middleware], None],
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
            Union[Sequence[Permission], None],
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
        self.settings_module = None

        if settings_module:
            if not isinstance(settings_module, Settings) and not is_class_and_subclass(
                settings_module, Settings
            ):  # type: ignore
                raise FieldException("'settings_module' must be a subclass of Settings")
            elif isinstance(settings_module, Settings):
                self.settings_module = settings_module
            elif is_class_and_subclass(settings_module, Settings):  # type: ignore
                self.settings_module = settings_module()

        self.debug = debug
        self.state = State()
        self.exception_handlers = {} if exception_handlers is None else dict(exception_handlers)
        self.permissions = [] if permissions is None else list(permissions)
        self.middleware_stack: Union[ASGIApp, None] = None
        self.custom_middleware = [] if middleware is None else list(middleware)
        self.router: Router = Router(
            routes=routes,
            redirect_slashes=redirect_slashes,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            lifespan=lifespan,
            middleware=middleware,
            permissions=permissions,
            include_in_schema=include_in_schema,
        )

    @property
    def routes(self) -> List[BasePath]:
        return self.router.routes

    def path_for(self, name: str, /, **path_params: Any) -> URLPath:
        return self.router.path_for(name, **path_params)

    def build_middleware_stack(self) -> ASGIApp: ...

    #     debug = self.debug
    #     error_handler = None
    #     exception_handlers: Dict[Any, Callable[[Request, Exception], Response]] = {}

    #     for key, value in self.exception_handlers.items():
    #         if key in (500, Exception):
    #             error_handler = value
    #         else:
    #             exception_handlers[key] = value

    #     middleware = (
    #         [Middleware(ServerErrorMiddleware, handler=error_handler, debug=debug)]
    #         + self.custom_middleware
    #         + [Middleware(ExceptionMiddleware, handlers=exception_handlers, debug=debug)]
    #     )

    #     app = self.router
    #     for cls, options in reversed(middleware):
    #         app = cls(app=app, **options)
    #     return app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        scope["app"] = self
        if self.middleware_stack is None:
            self.middleware_stack = self.build_middleware_stack()
        await self.middleware_stack(scope, receive, send)

    def on_event(self, event_type: str) -> Callable:
        return self.router.on_event(event_type)

    def include(
        self,
        path: str,
        app: ASGIApp,
        name: Union[str, None] = None,
        middleware: Union[Sequence[Middleware], None] = None,
        permissions: Union[Sequence[Permission], None] = None,
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
        middleware: Union[Sequence[Middleware], None] = None,
        permissions: Union[Sequence[Permission], None] = None,
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
        middleware: Union[Sequence[Middleware], None] = None,
        permissions: Union[Sequence[Permission], None] = None,
    ) -> None:
        """
        Manually creates a `WebsocketPath` from a given handler.
        """
        self.router.add_websocket_route(
            path=path, handler=handler, name=name, middleware=middleware, permissions=permissions
        )

    def add_event_handler(self, event_type: str, func: Callable[[], Any]) -> None:
        self.router.add_event_handler(event_type, func)
