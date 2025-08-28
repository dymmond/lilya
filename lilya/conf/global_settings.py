from __future__ import annotations

import inspect
import os
from collections.abc import Callable, Sequence
from functools import cached_property
from types import UnionType
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    ClassVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from lilya import __version__
from lilya.caches.memory import InMemoryCache
from lilya.conf.enums import EnvironmentType
from lilya.logging import LoggingConfig, StandardLoggingConfig
from lilya.protocols.cache import CacheBackend
from lilya.types import ApplicationType, Dependencies, Doc, ExceptionHandler

if TYPE_CHECKING:
    from lilya.middleware.base import DefineMiddleware
    from lilya.permissions.base import DefinePermission


def safe_get_type_hints(cls: type) -> dict[str, Any]:
    """
    Safely get type hints for a class, handling potential errors.
    This function attempts to retrieve type hints for the given class,
    and if it fails, it prints a warning and returns the class annotations.
    Args:
        cls (type): The class to get type hints for.
    Returns:
        dict[str, Any]: A dictionary of type hints for the class.
    """
    try:
        return get_type_hints(cls, include_extras=True)
    except Exception:
        return cls.__annotations__


class BaseSettings:
    """
    Base of all the settings for any system.
    """

    __type_hints__: dict[str, Any] = None
    __truthy__: set[str] = {"true", "1", "yes", "on", "y"}

    def __init__(self, **kwargs: Any) -> None:
        """
        Initializes the settings by loading environment variables
        and casting them to the appropriate types.
        This method uses type hints from the class attributes to determine
        the expected types of the settings.
        It will look for environment variables with the same name as the class attributes,
        converted to uppercase, and cast them to the specified types.
        If an environment variable is not set, it will use the default value
        defined in the class attributes.
        """
        cls = self.__class__
        if cls.__type_hints__ is None:
            cls.__type_hints__ = safe_get_type_hints(cls)

        if kwargs:
            for key, value in kwargs.items():
                setattr(self, key, value)

        for key, typ in cls.__type_hints__.items():
            base_type = self._extract_base_type(typ)

            env_value = os.getenv(key.upper(), None)
            if env_value is not None:
                value = self._cast(env_value, base_type)
            else:
                value = getattr(self, key, None)
            setattr(self, key, value)

        # Call post_init if it exists
        self.post_init()

    def post_init(self) -> None:
        """
        Post-initialization method that can be overridden by subclasses.
        This method is called after all settings have been initialized.
        """
        ...

    def _extract_base_type(self, typ: Any) -> Any:
        origin = get_origin(typ)
        if origin is Annotated:
            return get_args(typ)[0]
        return typ

    def _cast(self, value: str, typ: type[Any]) -> Any:
        """
        Casts the value to the specified type.
        If the type is `bool`, it checks for common truthy values.
        Raises a ValueError if the value cannot be cast to the type.

        Args:
            value (str): The value to cast.
            typ (type): The type to cast the value to.
        Returns:
            Any: The casted value.
        Raises:
            ValueError: If the value cannot be cast to the specified type.
        """
        try:
            origin = get_origin(typ)
            if origin is Union or origin is UnionType:
                non_none_types = [t for t in get_args(typ) if t is not type(None)]
                if len(non_none_types) == 1:
                    typ = non_none_types[0]
                else:
                    raise ValueError(f"Cannot cast to ambiguous Union type: {typ}")

            if typ is bool or str(typ) == "bool":
                return value.lower() in self.__truthy__
            return typ(value)
        except Exception:
            if get_origin(typ) is Union or get_origin(UnionType):
                type_name = " | ".join(
                    t.__name__ if hasattr(t, "__name__") else str(t) for t in get_args(typ)
                )
            else:
                type_name = getattr(typ, "__name__", str(typ))
            raise ValueError(f"Cannot cast value '{value}' to type '{type_name}'") from None

    def dict(
        self,
        exclude_none: bool = False,
        upper: bool = False,
        exclude: set[str] | None = None,
        include_properties: bool = False,
    ) -> dict[str, Any]:
        """
        Dumps all the settings into a python dictionary.
        """
        result = {}
        exclude = exclude or set()

        for key in self.__annotations__:
            if key in exclude:
                continue
            value = getattr(self, key, None)
            if exclude_none and value is None:
                continue
            result_key = key.upper() if upper else key
            result[result_key] = value

        if include_properties:
            for name, _ in inspect.getmembers(
                type(self),
                lambda o: isinstance(
                    o,
                    (property, cached_property),
                ),
            ):
                if name in exclude or name in self.__annotations__:
                    continue
                try:
                    value = getattr(self, name)
                    if exclude_none and value is None:
                        continue
                    result_key = name.upper() if upper else name
                    result[result_key] = value
                except Exception:
                    # Skip properties that raise errors
                    continue

        return result

    def tuple(
        self,
        exclude_none: bool = False,
        upper: bool = False,
        exclude: set[str] | None = None,
        include_properties: bool = False,
    ) -> list[tuple[str, Any]]:
        """
        Dumps all the settings into a tuple.
        """
        return list(
            self.dict(
                exclude_none=exclude_none,
                upper=upper,
                exclude=exclude,
                include_properties=include_properties,
            ).items()
        )


class CacheSettings(BaseSettings):
    cache_backend: Annotated[
        CacheBackend,
        Doc(
            """
            Defines the cache backend to be used for caching operations within the application.
            By default, an in-memory cache is used, but this can be replaced with other
            implementations such as Redis or Memcached.

            The cache backend should implement the necessary methods for storing, retrieving,
            and invalidating cached data.

            Read more about this in the official [Esmerald documentation](https://esmerald.dev/caching/).

            !!! Tip
                For distributed applications, consider using an external caching backend
                like Redis instead of the default in-memory cache.
            """
        ),
    ] = InMemoryCache()
    cache_default_ttl: Annotated[int, Doc("Default time-to-live (TTL) for cached items.")] = 300


class ContribSettings(CacheSettings):
    timezone: Annotated[
        str,
        Doc(
            """
            Object of time `datetime.timezone` or string indicating the
            timezone for the application.

            **Note** - The timezone is internally used for the supported
            scheduler.
            """
        ),
    ] = "UTC"


class Internal(ContribSettings):
    ipython_args: ClassVar[list[str]] = ["--no-banner"]
    ptpython_config_file: Annotated[
        str,
        Doc(
            """
            Default configuration for ptpython
            """
        ),
    ] = "~/.config/ptpython/config.py"


class Settings(Internal):
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
    ] = False
    environment: Annotated[
        str | None,
        Doc(
            """
            Optional string indicating the environment where the settings are running.
            You won't probably need this but it is here in case you might want to use.
            """
        ),
    ] = EnvironmentType.PRODUCTION
    version: Annotated[
        str | int | float,
        Doc(
            """
            The version of the application and defaults to the current version of Lilya if
            not set.
            """
        ),
    ] = __version__

    include_in_schema: Annotated[
        bool,
        Doc(
            """
            If all the APIs of a Lylia Application should be included in the OpenAPI Schema.
            """
        ),
    ] = True
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
    ] = "route_patterns"
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
    ] = "INFO"
    enable_openapi: Annotated[
        bool,
        Doc(
            """
            Boolean indicating if the OpenAPI schema should be generated
            for the application.

            Read more about the [OpenAPI](https://lilya.dev/openapi/).
            """
        ),
    ] = False
    infer_body: Annotated[
        bool,
        Doc(
            """
            With this flag set as True, the body of the request is automatically inferred and the type, guessed.

            This is particularly useful if you want to use validation libraries such as Pydantic or msgspec.

            Because the inferred type needs to be evaluated at request time, **this can impact slightly** the performance.
            """
        ),
    ] = False
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
    root_path_in_servers: Annotated[
        bool,
        Doc(
            """
            Boolean flag use to disable the automatic URL generation in the `servers` field
            in the OpenAPI documentation.
            """
        ),
    ] = True
    root_path: Annotated[
        str | None,
        Doc(
            """
            A path prefix that is handled by a proxy not seen in the
            application but seen by external libraries.

            This affects the tools like the OpenAPI documentation.
            """
        ),
    ] = ""

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
