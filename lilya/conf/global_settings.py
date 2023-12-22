from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

from dymmond_settings import Settings as BaseSettings
from dymmond_settings.enums import EnvironmentType
from typing_extensions import Annotated, Doc

from lilya import __version__
from lilya.types import ApplicationType, ExceptionHandler


@dataclass
class Settings(BaseSettings):
    debug: Annotated[
        bool,
        Doc(
            """
            Boolean indicating if the application should return the debug tracebacks on
            server errors, in other words, if you want to have debug errors being displayed.

            Read more about this in the official [Starlette documentation](https://www.starlette.io/applications/#instantiating-the-application).

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

    @property
    def routes(self) -> List[Any]:
        return []

    @property
    def middleware(self) -> Sequence[Any]:
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
