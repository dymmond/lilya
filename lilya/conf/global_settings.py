from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Annotated, Any, ClassVar

from lilya import __version__
from lilya.conf.enums import EnvironmentType
from lilya.logging import LoggingConfig, StandardLoggingConfig
from lilya.types import ApplicationType, Dependencies, Doc, ExceptionHandler

if TYPE_CHECKING:
    from lilya.middleware.base import DefineMiddleware
    from lilya.permissions.base import DefinePermission


@dataclass
class _BaseSettings:
    """
    Base of all the settings for any system.
    """

    def dict(self, exclude_none: bool = False, upper: bool = False) -> dict[str, Any]:
        """
        Dumps all the settings into a python dictionary.
        """
        original = asdict(self)

        if not exclude_none:
            if not upper:
                return original
            return {k.upper(): v for k, v in original.items()}

        if not upper:
            return {k: v for k, v in original.items() if v is not None}
        return {k.upper(): v for k, v in original.items() if v is not None}

    def tuple(self, exclude_none: bool = False, upper: bool = False) -> list[tuple[str, Any]]:
        """
        Dumps all the settings into a tuple.
        """
        original = asdict(self)

        if not exclude_none:
            if not upper:
                return list(original.items())
            return list({k.upper(): v for k, v in original.items()}.items())

        if not upper:
            return [(k, v) for k, v in original.items() if v is not None]
        return [(k.upper(), v) for k, v in original.items() if v is not None]


@dataclass
class _Internal(_BaseSettings):
    debug: Annotated[
        bool,
        Doc(
            """
            Boolean indicating if the application should return the debug tracebacks on
            server errors, in other words, if you want to have debug errors being displayed.

            !!! Tip
                Do not use this in production as `True`.
            """
        ),
    ] = field(default=False)
    environment: Annotated[
        str | None,
        Doc(
            """
            Optional string indicating the environment where the settings are running.
            You won't probably need this but it is here in case you might want to use.
            """
        ),
    ] = field(default=EnvironmentType.PRODUCTION)
    version: Annotated[
        str | int | float,
        Doc(
            """
            The version of the application and defaults to the current version of the settings
            system if not set.
            """
        ),
    ] = field(default=__version__)
    ipython_args: ClassVar[list[str]] = ["--no-banner"]
    ptpython_config_file: Annotated[
        str,
        Doc(
            """
            Default configuration for ptpython
            """
        ),
    ] = "~/.config/ptpython/config.py"


@dataclass
class Settings(_Internal):
    debug: Annotated[
        bool,
        Doc(
            """
            Boolean indicating if the application should return the debug tracebacks on
            server errors, in other words, if you want to have debug errors being displayed.

            !!! Tip
                Do not use this in production as `True`.
            """
        ),
    ] = field(default=False)
    environment: Annotated[
        str | None,
        Doc(
            """
            Optional string indicating the environment where the settings are running.
            You won't probably need this but it is here in case you might want to use.
            """
        ),
    ] = field(default=EnvironmentType.PRODUCTION)
    version: Annotated[
        str | int | float,
        Doc(
            """
            The version of the application and defaults to the current version of Lilya if
            not set.
            """
        ),
    ] = field(default=__version__)

    include_in_schema: Annotated[
        bool,
        Doc(
            """
            If all the APIs of a Lylia Application should be included in the OpenAPI Schema.
            """
        ),
    ] = field(default=True)

    default_route_pattern: Annotated[
        str,
        Doc(
            """
            The default patterns used with the `Include` when looking up.
            When nothing is specified or changed, it will default to lookup
            for a `route_patterns` inside the specified namespace.

            **Example**

            ```python
            from lilya.routing import Include

            Include(path="/", namespace="myapp.urls")
            ```
            """
        ),
    ] = field(default="route_patterns")
    enforce_return_annotation: Annotated[
        bool,
        Doc(
            """
            Boolean flag indicating if the return signature for the callable should be enforced
            or not.

            If the flag is `True` and no return signature, then raises an `ImproperlyConfigured`.

            **Example with flag as False**

            ```python
            from lilya.routing import Path

            def home():
                ...

            Path(path="/", handler=home)
            ```

            **Example with flag as True**

            ```python
            from lilya.routing import Path
            from lilya.responses import Response


            def home() -> Response:
                ...

            Path(path="/", handler=home)
            ```
            """
        ),
    ] = False
    x_frame_options: Annotated[
        str | None,
        Doc(
            """
            Set the X-Frame-Options HTTP header in HTTP responses.

            To enable the response to be loaded on a frame within the same site, set
            x_frame_options to 'SAMEORIGIN'.

            This flag is to be used when `XFrameOptionsMiddleware` is added to the
            application.
            """
        ),
    ] = None
    before_request: Annotated[
        Sequence[Callable[..., Any]] | None,
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
    ] = None
    after_request: Annotated[
        Sequence[Callable[..., Any]] | None,
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
    ] = None
    logging_level: Annotated[
        str,
        Doc(
            """
            The logging level for the application. Defaults to `DEBUG`.
            This is used by the `StandardLoggingConfig` to set the logging level.
            """
        ),
    ] = field(default="INFO")
    enable_openapi: Annotated[
        bool,
        Doc(
            """
            Boolean indicating if the OpenAPI schema should be generated
            for the application.

            Read more about the [OpenAPI](https://lilya.dev/openapi/).
            """
        ),
    ] = field(default=False)
    infer_body: Annotated[
        bool,
        Doc(
            """
            With this flag set as True, the body of the request is automatically inferred and the type, guessed.

            This is particularly useful if you want to use validation libraries such as Pydantic or msgspec.

            Because the inferred type needs to be evaluated at request time, **this can impact slightly** the performance.
            """
        ),
    ] = field(default=False)
    enable_intercept_global_exceptions: Annotated[
        bool,
        Doc(
            """
            By default, exception handlers are raised when a handler triggers but not
            by middlewares.

            With this flag enable, Lilya custom middleware activates those.
            """
        ),
    ] = False

    @property
    def routes(self) -> list[Any]:
        """
        The initial Lilya application routes.
        """
        return []

    @property
    def dependencies(self) -> Dependencies | None:
        """
        Returns a dictionary like containing all the dependencies that are globally
        assigned and can be used across the application layers.

        This can be particularly useful, for example, if a dabatabse session is shared
        across all the application.
        """
        return None

    @property
    def middleware(self) -> Sequence[DefineMiddleware]:
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
        from dataclasses imoprt dataclass

        from lilya.apps import Lilya
        from lilya.middleware import DefineMiddleware
        from lilya.middleware.httpsredirect import HTTPSRedirectMiddleware
        from lilya.middleware.trustedhost import TrustedHostMiddleware
        from lilya.settings import Settings


        @dataclass
        class AppSettings(Settings):

            @property
            def middleware(self) -> Sequence[DefineMiddleware]:
                return [
                    DefineMiddleware(
                        TrustedHostMiddleware, allowed_hosts=["example.com", "*.example.com"]
                    )
                ]

        ```
        """
        return []

    @property
    def permissions(self) -> Sequence[DefinePermission]:
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
        from dataclasses import dataclass

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


        @dataclass
        class AppSettings(Settings):
            @property
            def permissions(self) -> Sequence[DefinePermission]:
                return [DefineMiddleware(AllowAccess)]
        ```
        """
        return []

    @property
    def exception_handlers(self) -> ExceptionHandler | dict[Any, Any]:
        """
        A global dictionary with handlers for exceptions.

        Read more about the [Exception handlers](https://lilya.dev/exceptions/).

        **Example**

        ```python
        from dataclasses import dataclass

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


        @dataclass
        class AppSettings(Settings):
            @property
            def exception_handler(self) -> Union[ExceptionHandler, Dict[Any, Any]]:
                return {
                    TypeError: handle_type_error,
                    ValueError: handle_value_error,
                }
        ```
        """
        return {}

    @property
    def on_startup(self) -> Sequence[Callable[[], Any]]:
        """
        A `list` of events that are trigger upon the application
        starts.

        Read more about the [events](https://lilya.dev.dev/lifespan/).

        **Example**

        ```python
        from dataclasses import dataclass

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


        @dataclass
        class AppSettings(Settings):
            @property
            def on_startup(self) -> Sequence[Callable[[], Any]]:
                return [database.connect]
        ```
        """
        return None

    @property
    def on_shutdown(self) -> Sequence[Callable[[], Any]]:
        """
        A `list` of events that are trigger upon the application
        shuts down.

        Read more about the [events](https://lilya.dev.dev/lifespan/).

        **Example**

        ```python
        from dataclasses import dataclass

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


        @dataclass
        class AppSettings(Settings):
            @property
            def on_shutdown(self) -> Sequence[Callable[[], Any]]:
                return [database.disconnect]
        ```
        """
        return None

    @property
    def lifespan(self) -> ApplicationType | None:
        """
        A `lifespan` context manager handler. This is an alternative
        to `on_startup` and `on_shutdown` and you **cannot used all combined**.

        Read more about the [lifespan](https://lilya.dev/lifespan/).
        """
        return None

    @property
    def logging_config(self) -> LoggingConfig | None:  # noqa
        """
        An instance of [LoggingConfig](https://lilya.dev/logging/).

        Default:
            StandardLogging()

        **Example**

        ```python
        from lilya.conf import Settings


        class AppSettings(Settings):
            @property
            def logging_config(self) -> LoggingConfig:
                LoggingConfig(
                    log_level="INFO",
                    log_format="%(levelname)s - %(message)s",
                    log_file="app.log",
                )
        ```
        """
        return StandardLoggingConfig(level=self.logging_level)

    @property
    def openapi_config(self) -> Any | None:
        """
        An instance of [OpenAPIConfig](https://lilya.dev/openapi/).

        Default:
            OpenAPIConfig()

        **Example**

        ```python
        from lilya.conf import Settings
        from lilya.contrib.openapi.config import OpenAPIConfig

        class AppSettings(Settings):
            @property
            def openapi_config(self) -> OpenAPIConfig:
                return OpenAPIConfig(
                    title="My API",
                    version="1.0.0",
                    description="This is my API description.",
                )
        ```
        """
        return None
