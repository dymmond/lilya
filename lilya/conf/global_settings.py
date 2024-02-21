from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Dict, List, Optional, Sequence, Union

from dymmond_settings import Settings as BaseSettings
from dymmond_settings.enums import EnvironmentType
from typing_extensions import Annotated, Doc

from lilya import __version__
from lilya.types import ApplicationType, ASGIApp, ExceptionHandler

if TYPE_CHECKING:
    from lilya.middleware.base import DefineMiddleware
    from lilya.permissions.base import DefinePermission


@dataclass
class _Internal(BaseSettings):
    app: Annotated[
        ASGIApp | None,
        Doc(
            """
            The global application where the global settings is hooked.
            It is advised, unless you are confortable with it, **not to change it**.
            """
        ),
    ] = None
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
        Optional[str],
        Doc(
            """
            Optional string indicating the environment where the settings are running.
            You won't probably need this but it is here in case you might want to use.
            """
        ),
    ] = field(default=EnvironmentType.PRODUCTION)
    version: Annotated[
        Union[str, int, float],
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
            Boolean flag indicating if the return signature for the handler should be enforced
            or not.

            If the flag is True and no return signature, then raises an ImproperlyConfigured.

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

    @property
    def routes(self) -> List[Any]:
        return []

    @property
    def middleware(self) -> Sequence[DefineMiddleware]:
        return []

    @property
    def permissions(self) -> Sequence[DefinePermission]:
        return []

    @property
    def exception_handlers(self) -> Union[ExceptionHandler, Dict[Any, Any]]:
        return {}

    @property
    def on_startup(self) -> Sequence[Callable[[], Any]]:
        return None

    @property
    def on_shutdown(self) -> Sequence[Callable[[], Any]]:
        return None

    @property
    def lifespan(self) -> Optional[ApplicationType]:
        return None
