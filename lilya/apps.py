from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Annotated, Any, ClassVar, ParamSpec, cast

from lilya._internal._connection import Connection  # noqa
from lilya._internal._middleware import wrap_middleware  # noqa
from lilya._internal._module_loading import import_string  # noqa
from lilya._internal._permissions import wrap_permission  # noqa
from lilya._utils import is_class_and_subclass
from lilya.conf import _monkay, settings as lilya_settings  # noqa
from lilya.conf.exceptions import FieldException
from lilya.conf.global_settings import Settings
from lilya.datastructures import State, URLPath
from lilya.logging import LoggingConfig, setup_logging
from lilya.middleware.asyncexit import AsyncExitStackMiddleware
from lilya.middleware.base import DefineMiddleware
from lilya.middleware.exceptions import ExceptionMiddleware
from lilya.middleware.global_context import (
    GlobalContextMiddleware,
    LifespanGlobalContextMiddleware,
)
from lilya.middleware.lilya_exception import LilyaExceptionMiddleware
from lilya.middleware.server_error import ServerErrorMiddleware
from lilya.permissions.base import DefinePermission
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.protocols.permissions import PermissionProtocol
from lilya.requests import Request
from lilya.responses import Response
from lilya.routing import BasePath, Include, Router, RoutingMethodsMixin
from lilya.types import (
    ApplicationType,
    ASGIApp,
    CallableDecorator,
    Dependencies,
    Doc,
    ExceptionHandler,
    Lifespan,
    Receive,
    Scope,
    Send,
)
from lilya.websockets import WebSocket

P = ParamSpec("P")


class BaseLilya:
    router_class: ClassVar[type[Router] | None] = Router
    router: Router
    register_as_global_instance: ClassVar[bool] = False
    populate_global_context: (
        Callable[[Connection], dict[str, Any] | Awaitable[dict[str, Any]]] | None
    ) = None

    @property
    def routes(self) -> list[BasePath]:
        return self.router.routes

    def load_settings_value(
        self, name: str, value: Any | None = None, is_boolean: bool = False
    ) -> Any:
        """
        Loader used to get the settings defaults and custom settings
        of the application.
        """
        if not is_boolean:
            if not value:
                return self.__get_settings_value(self.settings_module, lilya_settings, name)
            return value

        if value is not None:
            return value
        return self.__get_settings_value(self.settings_module, lilya_settings, name)

    def __get_settings_value(
        self,
        local_settings: Settings | None,
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

    def path_for(self, name: str, /, **path_params: Any) -> URLPath:
        return self.router.path_for(name, **path_params)

    def url_for(self, name: str, /, **path_params: Any) -> str:
        return self.path_for(name, **path_params)

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
            DefineMiddleware(
                GlobalContextMiddleware, populate_context=self.populate_global_context
            ),
            DefineMiddleware(LifespanGlobalContextMiddleware),
            *self.custom_middleware,
            DefineMiddleware(ExceptionMiddleware, handlers=exception_handlers, debug=self.debug),
            DefineMiddleware(AsyncExitStackMiddleware, debug=self.debug),
        ]

        if self.enable_intercept_global_exceptions:
            middleware.insert(
                1, DefineMiddleware(LilyaExceptionMiddleware, handlers=exception_handlers)
            )

        app = self.router
        for middleware_class, args, options in reversed(middleware):
            app = middleware_class(app=app, *args, **options)

        return app

    def _get_error_handler(self) -> Callable[[Request, Exception], Response] | None:
        """
        Get the error handler for middleware based on the exception handlers.

        Returns:
            Optional[Callable[[Request, Exception], Response]]: The error handler function.
        """
        return self.exception_handlers.get(500) or self.exception_handlers.get(Exception)  # type: ignore

    def _get_exception_handlers(self) -> dict[Exception, ExceptionHandler]:
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
        name: str | None = None,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        namespace: str | None = None,
        pattern: str | None = None,
        include_in_schema: bool = True,
        before_request: Sequence[Callable[[], Any]] | None = None,
        after_request: Sequence[Callable[[], Any]] | None = None,
        redirect_slashes: bool = True,
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
            exception_handlers=exception_handlers,
            dependencies=dependencies,
            include_in_schema=include_in_schema,
            before_request=before_request,
            after_request=after_request,
            redirect_slashes=redirect_slashes,
        )

    def host(self, host: str, app: ASGIApp, name: str | None = None) -> None:
        """
        Adds a Host application into the routes.
        """
        self.router.host(host=host, app=app, name=name)

    def add_route(
        self,
        path: Annotated[
            str,
            Doc(
                """
                Relative path of the `Path`.
                The path can contain parameters in a dictionary like format.
                """
            ),
        ],
        handler: Annotated[
            Callable[[Request], Awaitable[Response] | Response],
            Doc(
                """
                A python callable.
                """
            ),
        ],
        methods: Annotated[
            list[str] | None,
            Doc(
                """
                List of HTTP verbs (GET, POST, PUT, DELETE, HEAD...) allowed in
                the route.
                """
            ),
        ] = None,
        name: Annotated[
            str | None,
            Doc(
                """
                The name for the PAth. The name can be reversed by `path_for()` or `reverse()`.
                """
            ),
        ] = None,
        middleware: Annotated[
            Sequence[DefineMiddleware] | None,
            Doc(
                """
                A list of middleware to run for every request.
                """
            ),
        ] = None,
        permissions: Annotated[
            Sequence[DefinePermission] | None,
            Doc(
                """
                A list of [permissions](https://lilya.dev/permissions/) to serve the application incoming requests (HTTP and Websockets).
                """
            ),
        ] = None,
        exception_handlers: Annotated[
            Mapping[Any, ExceptionHandler] | None,
            Doc(
                """
                A dictionary of [exception types](https://lilya.dev/exceptions/) (or custom exceptions) and the handler functions on an application top level. Exception handler callables should be of the form of `handler(request, exc) -> response` and may be be either standard functions, or async functions.
                """
            ),
        ] = None,
        include_in_schema: Annotated[
            bool,
            Doc(
                """
                Boolean flag indicating if it should be added to the OpenAPI docs.
                """
            ),
        ] = True,
    ) -> None:
        """
        Adds a [Path](https://lilya.dev/routing/)
        to the application routing.

        This is a dynamic way of adding routes on the fly.

        **Example**

        ```python
        from lilya.apps import Lilya


        async def hello():
            return "Hello, World!"


        app = Lilya()
        app.add_route(path="/hello", handler=hello)
        ```
        """
        self.router.add_route(
            path=path,
            handler=handler,
            methods=methods,
            name=name,
            middleware=middleware,
            permissions=permissions,
            exception_handlers=exception_handlers,
            include_in_schema=include_in_schema,
        )

    def add_websocket_route(
        self,
        path: Annotated[
            str,
            Doc(
                """
                Relative path of the `Path`.
                The path can contain parameters in a dictionary like format.
                """
            ),
        ],
        handler: Annotated[
            Callable[[WebSocket], Awaitable[None]],
            Doc(
                """
                A python callable.
                """
            ),
        ],
        name: Annotated[
            str | None,
            Doc(
                """
                The name for the WebSocketPath. The name can be reversed by `path_for()` or `reverse()`.
                """
            ),
        ] = None,
        middleware: Annotated[
            Sequence[DefineMiddleware] | None,
            Doc(
                """
                A list of middleware to run for every request.
                """
            ),
        ] = None,
        permissions: Annotated[
            Sequence[DefinePermission] | None,
            Doc(
                """
                A list of [permissions](https://lilya.dev/permissions/) to serve the application incoming requests (HTTP and Websockets).
                """
            ),
        ] = None,
        exception_handlers: Annotated[
            Mapping[Any, ExceptionHandler] | None,
            Doc(
                """
                A dictionary of [exception types](https://lilya.dev/exceptions/) (or custom exceptions) and the handler functions on an application top level. Exception handler callables should be of the form of `handler(request, exc) -> response` and may be be either standard functions, or async functions.
                """
            ),
        ] = None,
    ) -> None:
        """
        Adds a websocket [WebsocketPath](https://lilya.dev/routing/)
        to the application routing.

        This is a dynamic way of adding routes on the fly.

        **Example**

        ```python
        from lilya.apps import Lilya


        async def websocket_route(websocket):
            await websocket.accept()
            data = await websocket.receive_json()

            assert data
            await websocket.send_json({"data": "lilya"})
            await websocket.close()


        app = Lilya()
        app.add_websocket_route(path="/ws", handler=websocket_route)
        ```
        """
        self.router.add_websocket_route(
            path=path,
            handler=handler,
            name=name,
            middleware=middleware,
            permissions=permissions,
            exception_handlers=exception_handlers,
        )

    def add_middleware(
        self, middleware: type[MiddlewareProtocol[P]], *args: P.args, **kwargs: P.kwargs
    ) -> None:
        """
        Adds an external middleware to the stack.
        """
        if self.middleware_stack is not None:
            raise RuntimeError("Middlewares cannot be added once the application has started.")
        self.custom_middleware.insert(0, DefineMiddleware(middleware, *args, **kwargs))

    def add_permission(
        self, permission: type[PermissionProtocol[P]], *args: P.args, **kwargs: P.kwargs
    ) -> None:
        """
        Adds an external permissions to the stack.
        """
        if self.router.permission_started:
            raise RuntimeError("Permissions cannot be added once the application has started.")
        self.router.permissions.insert(0, DefinePermission(permission, *args, **kwargs))

    def add_exception_handler(
        self,
        exception_cls_or_status_code: int | type[Exception],
        handler: ExceptionHandler,
    ) -> None:
        self.exception_handlers[exception_cls_or_status_code] = handler

    def add_event_handler(self, event_type: str, func: Callable[[], Any]) -> None:
        self.router.add_event_handler(event_type, func)

    def add_child_lilya(
        self,
        path: str,
        child: Annotated[
            ChildLilya,
            Doc(
                """
                The [ChildLilya](https://lilya.dev/routing/#childlilya-application) instance
                to be added.
                """
            ),
        ],
        name: str | None = None,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        include_in_schema: bool | None = True,
        deprecated: bool | None = None,
    ) -> None:
        """
        Adds a [ChildLilya](https://lilya.dev/routing/#childlilya-application) directly to the active application router.

        **Example**

        ```python
        from lilya.apps import ChildLilya, Lilya
        from lilya.routing import Path, Include


        async def hello(self):
            return "Hello, World!"

        child = ChildLilya(routes=[Path("/", handler=hello)])

        app = Lilya()
        app.add_child_lilya(path"/child", child=child)
        ```
        """
        if not isinstance(child, ChildLilya):
            raise ValueError("The child must be an instance of a ChildLilya.")

        self.router.routes.append(
            Include(
                path=path,
                name=name,
                app=child,
                middleware=middleware,
                permissions=permissions,
                exception_handlers=exception_handlers,
                include_in_schema=include_in_schema,
                deprecated=deprecated,
            )
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        scope["app"] = self
        with _monkay.with_settings(self.settings), _monkay.with_instance(self):
            if self.root_path:
                scope["root_path"] = self.root_path

            if self.middleware_stack is None:
                self.middleware_stack = self.build_middleware_stack()
            await self.middleware_stack(scope, receive, send)


class Lilya(RoutingMethodsMixin, BaseLilya):
    """
    Initialize the Lilya ASGI framework.

    !!! Tip
        All the parameters available in the object have defaults being loaded by the
        [settings system](https://lilya.dev/settings/) if nothing is provided.

    **Example**:

    ```python
    from lilya import Lilya

    app = Lilya(debug=True, routes=[...], middleware=[...], ...)
    ```
    """

    register_as_global_instance: ClassVar[bool] = True

    def __init__(
        self,
        debug: Annotated[bool, Doc("Enable or disable debug mode. Defaults to False.")] = False,
        settings_module: Annotated[
            type[Settings] | str | None,
            Doc(
                """
                Alternative settings parameter. This parameter is an alternative to
                `LILYA_SETTINGS_MODULE` way of loading your settings into a Lilya application.

                When the `settings_module` is provided, it will make sure it takes priority over
                any other settings provided for the instance.

                Read more about the [settings module](https://lilya.dev/settings/)
                and how you can leverage it in your application.

                !!! Tip
                    The settings module can be very useful if you want to have, for example, a
                    [ChildLilya](https://lilya.dev/routing/#childlilya-application) that needs completely different settings
                    from the main app.

                    Example: A `ChildLilya` that takes care of the authentication into a cloud
                    provider such as AWS and handles the `boto3` module.
                """
            ),
        ] = None,
        routes: Annotated[
            Sequence[Any] | None,
            Doc(
                """
                A global `list` of lilya routes. Those routes may vary and those can
                be `Path`, `WebSocketPath` or even `Include`.

                This is also the entry-point for the routes of the application itself.

                Read more about how to use and leverage
                the [routing system](https://lilya.dev/routing/).

                **Example**

                ```python
                from lilya.apps import Lilya, Request
                from lilya.requests import Request
                from lilya.routing import Path


                async def homepage(request: Request) -> str:
                    return "Hello, home!"

                async def another(request: Request) -> str:
                    return "Hello, another!"


                app = Lilya(
                    routes=[
                        Path(
                            "/", handler=homepage,
                        ),
                        Include("/nested", routes=[
                            Path("/another", another)
                        ])
                    ]
                )
                ```

                !!! Note
                    The routing system is very powerful and this example
                    is not enough to understand what more things you can do.
                    Read in [more detail](https://lilya.dev/routing/) about this.
                """
            ),
        ] = None,
        middleware: Annotated[
            Sequence[DefineMiddleware] | None,
            Doc(
                """
                A global sequence of Lilya middlewares that are
                used by the application.

                Read more about the [Middleware](https://lilya.dev/middleware/).

                **All middlewares must be wrapped inside the `DefineMiddleware`**

                ```python
                from lilya.middleware import DefineMiddleware
                ```

                **Example**

                ```python
                from lilya.apps import Lilya
                from lilya.middleware import DefineMiddleware
                from lilya.middleware.httpsredirect import HTTPSRedirectMiddleware
                from lilya.middleware.trustedhost import TrustedHostMiddleware

                app = Lilya(
                    routes=[...],
                    middleware=[
                        DefineMiddleware(
                            TrustedHostMiddleware,
                            allowed_hosts=["example.com", "*.example.com"],
                        ),
                        DefineMiddleware(HTTPSRedirectMiddleware),
                    ],
                )
                ```
                """
            ),
        ] = None,
        exception_handlers: Annotated[
            Mapping[Any, ExceptionHandler] | None,
            Doc(
                """
                A global dictionary with handlers for exceptions.

                Read more about the [Exception handlers](https://lilya.dev/exceptions/).

                **Example**

                ```python
                from json import loads

                from lilya import status
                from lilya.apps import Lilya
                from lilya.requests import Request
                from lilya.responses import JSONResponse
                from lilya.routing import Include, Path


                async def handle_type_error(request: Request, exc: TypeError):
                    status_code = status.HTTP_400_BAD_REQUEST
                    details = loads(exc.json()) if hasattr(exc, "json") else exc.args[0]
                    return JSONResponse({"detail": details}, status_code=status_code)


                async def handle_value_error(request: Request, exc: ValueError):
                    status_code = status.HTTP_400_BAD_REQUEST
                    details = loads(exc.json()) if hasattr(exc, "json") else exc.args[0]
                    return JSONResponse({"detail": details}, status_code=status_code)


                async def me():
                    return "Hello, world!"


                app = Lilya(
                    routes=[
                        Include(
                            "/",
                            routes=[
                                Path(
                                    "/me",
                                    handler=me,
                                )
                            ],
                        )
                    ],
                    exception_handlers={
                        TypeError: handle_type_error,
                        ValueError: handle_value_error,
                    },
                )
                ```
                """
            ),
        ] = None,
        dependencies: Annotated[
            Dependencies | None,
            Doc(
                """
                A global dependencies for the application.
                """
            ),
        ] = None,
        permissions: Annotated[
            Sequence[DefinePermission] | None,
            Doc(
                """
                A global sequence of Lilya permissions that are
                used by the application.

                Read more about the [Permissions](https://lilya.dev/permissions/).

                **All permissions must be wrapped inside the `DefinePermission`**

                ```python
                from lilya.permissions import DefinePermission
                ```

                **Example**

                ```python
                from lilya.apps import Lilya
                from lilya.exceptions import PermissionDenied
                from lilya.permissions import DefinePermission
                from lilya.protocols.permissions import PermissionProtocol
                from lilya.requests import Request
                from lilya.responses import Ok
                from lilya.routing import Path
                from lilya.types import ASGIApp, Receive, Scope, Send


                class AllowAccess(PermissionProtocol):
                    def __init__(self, app: ASGIApp, *args, **kwargs):
                        super().__init__(app, *args, **kwargs)
                        self.app = app

                    async def __call__(self, scope: Scope, receive: Receive, send: Send):
                        request = Request(scope=scope, receive=receive, send=send)

                        if "allow-admin" in request.headers:
                            await self.app(scope, receive, send)
                            return
                        raise PermissionDenied()


                def user(user: str):
                    return Ok({"message": f"Welcome {user}"})


                app = Lilya(
                    routes=[Path("/{user}", user)],
                    permissions=[DefinePermission(AllowAccess)],
                )
                ```
                """
            ),
        ] = None,
        on_startup: Annotated[
            Sequence[Callable[[], Any]] | None,
            Doc(
                """
                A `list` of events that are trigger upon the application
                starts.

                Read more about the [events](https://lilya.dev.dev/lifespan/).

                **Example**

                ```python
                from saffier import Database, Registry

                from lilya.apps import Lilya
                from lilya.requests import Request
                from lilya.routing import Path

                database = Database("postgresql+asyncpg://user:password@host:port/database")
                registry = Registry(database=database)


                async def create_user(request: Request):
                    # Logic to create the user
                    data = await request.json()
                    ...


                app = Lilya(
                    routes=[Path("/create", handler=create_user)],
                    on_startup=[database.connect],
                )
                ```
                """
            ),
        ] = None,
        on_shutdown: Annotated[
            Sequence[Callable[[], Any]] | None,
            Doc(
                """
                A `list` of events that are trigger upon the application
                shuts down.

                Read more about the [events](https://lilya.dev/lifespan/).

                **Example**

                ```python
                from saffier import Database, Registry

                from lilya.apps import Lilya
                from lilya.requests import Request
                from lilya.routing import Path

                database = Database("postgresql+asyncpg://user:password@host:port/database")
                registry = Registry(database=database)


                async def create_user(request: Request):
                    # Logic to create the user
                    data = await request.json()
                    ...


                app = Lilya(
                    routes=[Path("/create", handler=create_user)],
                    on_shutdown=[database.disconnect],
                )
                ```
                """
            ),
        ] = None,
        before_request: Annotated[
            Sequence[Callable[[], Any]] | None,
            Doc(
                """
                A `list` of events that are trigger before the application
                processes the request.

                Read more about the [events](https://lilya.dev/lifespan/).

                **Example**

                ```python
                from edgy import Database, Registry

                from lilya.apps import Lilya
                from lilya.requests import Request
                from lilya.routing import Path

                database = Database("postgresql+asyncpg://user:password@host:port/database")
                registry = Registry(database=database)


                async def create_user(request: Request):
                    # Logic to create the user
                    data = await request.json()
                    ...


                app = Lilya(
                    routes=[Path("/create", handler=create_user)],
                    before_request=[database.connect],
                )
                ```
                """
            ),
        ] = None,
        after_request: Annotated[
            Sequence[Callable[[], Any]] | None,
            Doc(
                """
                A `list` of events that are trigger after the application
                processes the request.

                Read more about the [events](https://lilya.dev/lifespan/).

                **Example**

                ```python
                from edgy import Database, Registry

                from lilya.apps import Lilya
                from lilya.requests import Request
                from lilya.routing import Path

                database = Database("postgresql+asyncpg://user:password@host:port/database")
                registry = Registry(database=database)


                async def create_user(request: Request):
                    # Logic to create the user
                    data = await request.json()
                    ...


                app = Lilya(
                    routes=[Path("/create", handler=create_user)],
                    after_request=[database.disconnect],
                )
                ```
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
            Lifespan[ApplicationType] | None,
            Doc(
                """
                A `lifespan` context manager handler. This is an alternative
                to `on_startup` and `on_shutdown` and you **cannot used all combined**.

                Read more about the [lifespan](https://lilya.dev/lifespan/).
                """
            ),
        ] = None,
        include_in_schema: Annotated[
            bool,
            Doc(
                """
                Enable or disable inclusion of the application in a OpenAPI schema integration.

                !!! Note
                    Lilya is not tight to any OpenAPI provider but provides some out of the box
                    flags that can be used for any possible integration.
                """
            ),
        ] = True,
        logging_config: Annotated[
            LoggingConfig | None,
            Doc(
                """
                An instance of [LoggingConfig](https://lilya.dev/logging)
                """
            ),
        ] = None,
        populate_global_context: Annotated[
            Callable[[Connection], dict[str, Any] | Awaitable[dict[str, Any]]] | None,
            Doc(
                """
                An function to populate the global connection context (per connection/request).
                This can be useful for context data every request should share.
                It is also possible here to copy from a parent global context.
                **Example**

                ```python
                from edgy import Registry

                from lilya.apps import Lilya
                from lilya.requests import Connection
                registry = Registry("postgresql+asyncpg://user:password@host:port/database")


                async def populate_g(connection: Connection):
                    return {
                        "amount_users": await registry.get_model("User").query.count()
                    }

                app = registry.asgi(Lilya(
                    routes=[...],
                    populate_global_context=populate_g,
                ))
                ```
                """
            ),
        ] = None,
        enable_openapi: Annotated[
            bool,
            Doc(
                """
                Enable or disable OpenAPI documentation generation. Defaults to False.
                """
            ),
        ] = False,
        openapi_config: Annotated[
            Any | None,
            Doc(
                """
                A custom OpenAPIConfig instance to override defaults if provided.
                """
            ),
        ] = None,
        enable_intercept_global_exceptions: Annotated[
            bool,
            Doc(
                """
                By default, exception handlers are raised when a handler triggers but not
                by middlewares.

                With this flag enable, Lilya custom middleware activates those.
                """
            ),
        ] = False,
        root_path: Annotated[
            str | None,
            Doc(
                """
                A path prefix that is handled by a proxy not seen in the
                application but seen by external libraries.

                This affects the tools like the OpenAPI documentation.

                **Example**

                ```python
                from lilya.apps import Lilya

                app = Lilya(root_path="/api/v3")
                ```
                """
            ),
        ] = None,
    ) -> None:
        self.populate_global_context = populate_global_context
        self.settings_module: Settings | None = None

        if settings_module is not None and isinstance(settings_module, str):
            settings_module = import_string(settings_module)

        if settings_module:
            if not isinstance(settings_module, Settings) and not is_class_and_subclass(
                settings_module, Settings
            ):
                raise FieldException("'settings_module' must be a subclass of Settings")
            elif isinstance(settings_module, Settings):
                self.settings_module = settings_module  # type: ignore
            elif is_class_and_subclass(settings_module, Settings):
                self.settings_module = settings_module()

        self.debug = self.load_settings_value("debug", debug, is_boolean=True)

        self.exception_handlers = (
            self.load_settings_value("exception_handlers", exception_handlers) or {}
        )
        self.custom_middleware = [
            wrap_middleware(middleware)
            for middleware in self.load_settings_value("middleware", middleware) or []
        ]

        self.custom_permissions = [
            wrap_permission(permission)
            for permission in self.load_settings_value("permissions", permissions) or []
        ]

        self.before_request_callbacks = (
            self.load_settings_value("before_request", before_request) or []
        )

        self.after_request_callbacks = (
            self.load_settings_value("after_request", after_request) or []
        )
        self.dependencies = self.load_settings_value("dependencies", dependencies) or {}

        self.logging_config = self.load_settings_value("logging_config", logging_config)
        self.state = State()
        self.middleware_stack: ASGIApp | None = None
        self.enable_openapi = self.load_settings_value(
            "enable_openapi", enable_openapi, is_boolean=True
        )
        self.openapi_config = self.load_settings_value("openapi_config", openapi_config)
        self.enable_intercept_global_exceptions = self.load_settings_value(
            "enable_intercept_global_exceptions", enable_intercept_global_exceptions
        )
        self.root_path = self.load_settings_value("root_path", root_path)

        if self.router_class is not None:
            self.router = self.router_class(
                routes=routes,
                redirect_slashes=redirect_slashes,
                permissions=self.custom_permissions,
                on_startup=on_startup,
                on_shutdown=on_shutdown,
                lifespan=lifespan,
                include_in_schema=include_in_schema,
                settings_module=self.settings,
                before_request=self.before_request_callbacks,
                after_request=self.after_request_callbacks,
            )

        if self.logging_config is not None:
            setup_logging(self.logging_config)

        if self.enable_openapi:
            self.configure_openapi(self.openapi_config)

        if self.register_as_global_instance:
            _monkay.set_instance(self)

    def configure_openapi(self, openapi_config: Any | None = None) -> None:
        from lilya.contrib.openapi.config import OpenAPIConfig

        config_to_use = openapi_config or OpenAPIConfig()
        config_to_use.enable(self)

    @property
    def version(self) -> str:
        """
        Returns the Lilya version.

        **Example**

        ```python
        from lilya.apps import Lilya

        app = Lilya()
        print(app.version)
        ```
        """
        return cast(str, self.settings.version)

    @property
    def settings(self) -> Settings:
        """
        Returns the Lilya settings object for easy access.

        This `settings` are the ones being used by the application upon
        initialisation.

        **Example**

        ```python
        from lilya.apps import Lilya

        app = Lilya()
        app.settings
        ```
        """
        general_settings = self.settings_module if self.settings_module else _monkay.settings
        return general_settings

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
        return cast(
            "Callable[..., Any]",
            getattr(self.router, method.lower())(
                path=path,
                name=name,
                middleware=middleware,
                permissions=permissions,
                exception_handlers=exception_handlers,
                dependencies=dependencies,
                include_in_schema=include_in_schema,
                before_request=before_request,
                after_request=after_request,
            ),
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
    ) -> Callable[[CallableDecorator], CallableDecorator]:
        """
        Decorator for defining a generic route.

        Args:
            path (str): The URL path pattern for the route.
            methods (list[str] | None, optional): The HTTP methods allowed for the route. Defaults to None.
            name (str | None, optional): The name of the route. Defaults to None.
            middleware (Sequence[DefineMiddleware] | None, optional): The middleware functions to apply to the route. Defaults to None.
            permissions (Sequence[DefinePermission] | None, optional): The permissions required for the route. Defaults to None.
            exception_handlers (Mapping[Any, ExceptionHandler] | None, optional): The exception handlers for the route. Defaults to None.
            dependencies (Dependencies | None, optional): Dependencies to be injected into the route. Defaults to None.
            include_in_schema (bool, optional): Whether to include the route in the API schema. Defaults to True.
            before_request (Sequence[Callable[..., Any]] | None, optional): Callbacks to be executed before the request is processed. Defaults to None.
            after_request (Sequence[Callable[..., Any]] | None, optional): Callbacks to be executed after the request is processed. Defaults to None.

        Returns:
            Callable[[CallableDecorator], CallableDecorator]: The decorated function.
        """

        return self.router.route(
            path=path,
            methods=methods,
            name=name,
            middleware=middleware,
            permissions=permissions,
            exception_handlers=exception_handlers,
            dependencies=dependencies,
            include_in_schema=include_in_schema,
            before_request=before_request,
            after_request=after_request,
        )

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
    ) -> Callable[[CallableDecorator], CallableDecorator]:
        """
        Decorator for defining a WebSocket route.

        Args:
            path (str): The URL path for the WebSocket route.
            name (str, optional): The name of the route. Defaults to None.
            middleware (Sequence[DefineMiddleware], optional): The middleware to apply to the route. Defaults to None.
            permissions (Sequence[DefinePermission], optional): The permissions required for the route. Defaults to None.
            exception_handlers (Mapping[Any, ExceptionHandler], optional): The exception handlers for the route. Defaults to None.
            dependencies (Dependencies, optional): Dependencies to be injected into the route. Defaults to None.
            before_request (Sequence[Callable[..., Any]], optional): Callbacks to be executed before the request is processed. Defaults to None.
            after_request (Sequence[Callable[..., Any]], optional): Callbacks to be executed after the request is processed. Defaults to None.

        Returns:
            Callable[[CallableDecorator], CallableDecorator]: The decorated function.

        """

        return self.router.websocket(
            path=path,
            name=name,
            middleware=middleware,
            permissions=permissions,
            exception_handlers=exception_handlers,
            dependencies=dependencies,
            before_request=before_request,
            after_request=after_request,
        )


class ChildLilya(Lilya):
    """
    `ChildLilya` application object. The main entry-point for a modular application/API
    with Lilya.

    The `ChildLilya` inherits directly from the `Lilya` object which means all the same
    parameters, attributes and functions of Lilya ara also available in the `ChildLilya`.


    !!! Tip
        All the parameters available in the object have defaults being loaded by the
        [settings system](https://lilya.dev/settings/) if nothing is provided.

    ## Example

    ```python
    from lilya.apps import Lilya, ChildLilya
    from lilya.routing import Include


    app = Lilya(routes=[Include("/child", app=ChildLilya(...))])
    ```
    """

    register_as_global_instance: ClassVar[bool] = False
