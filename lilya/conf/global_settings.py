from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Dict, List, Optional, Sequence, Union

from typing_extensions import Annotated, Doc, Protocol

from lilya import __version__
from lilya.conf.enums import EnvironmentType
from lilya.types import ApplicationType, ASGIApp, ExceptionHandler, Lifespan, Receive, Scope, Send


@dataclass
class BaseSettings:
    """
    Base of all the settings for the system.
    """

    def dict(self, exclude_none: bool = False) -> Dict[str, Any]:
        """
        Dumps all the settings into a python dictionary.
        """
        if not exclude_none:
            return {k: v for k, v in self.__dict__.items()}
        return {k: v for k, v in self.__dict__.items() if v is not None}


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
    def exception_handlers(self) -> ExceptionHandler:
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
