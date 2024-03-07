from __future__ import annotations

import sys
from typing import Any, Awaitable, Callable, Mapping, Sequence, cast

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
from lilya.routing import BasePath, Include, Router
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

    !!! Tip
        All the parameters available in the object have defaults being loaded by the
        [settings system](https://lilya.dev/settings/) if nothing is provided.

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
            Settings | None,
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
        self.middleware_stack: ASGIApp | None = None

        self.router: Router = Router(
            routes=routes,
            redirect_slashes=redirect_slashes,
            permissions=self.custom_permissions,
            on_startup=self.__load_settings_value("on_startup", on_startup),
            on_shutdown=self.__load_settings_value("on_shutdown", on_shutdown),
            lifespan=self.__load_settings_value("lifespan", lifespan),
            include_in_schema=include_in_schema,
            settings_module=self.settings,
        )
        self.__set_settings_app(self.settings, self)

    @property
    def routes(self) -> list[BasePath]:
        return self.router.routes

    def __set_settings_app(self, settings_module: Settings, app: ASGIApp) -> None:
        if settings_module.app is None:
            self.router._set_settings_app(settings_module, app)

    def __load_settings_value(
        self, name: str, value: Any | None = None, is_boolean: bool = False
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
        namespace: str | None = None,
        pattern: str | None = None,
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
            exception_handlers=exception_handlers,
            include_in_schema=include_in_schema,
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
        self, middleware: type[MiddlewareProtocol], *args: P.args, **kwargs: P.kwargs
    ) -> None:
        """
        Adds an external middleware to the stack.
        """
        if self.middleware_stack is not None:
            raise RuntimeError("Middlewares cannot be added once the application has started.")
        self.custom_middleware.insert(0, DefineMiddleware(middleware, *args, **kwargs))

    def add_permission(
        self, permission: type[PermissionProtocol], *args: P.args, **kwargs: P.kwargs
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
        [settings system](https://lilya.dev/settings/) if nothing is provided.

    ## Example

    ```python
    from lilya.apps import Lilya, ChildLilya
    from lilya.routing import Include


    app = Lilya(routes=[Include('/child', app=ChildLilya(...))])
    ```
    """
