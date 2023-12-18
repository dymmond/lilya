from __future__ import annotations

import inspect
from typing import Any, Callable, List, Sequence, Set, Tuple, Union

from lilya.datastructures import URLPath
from lilya.enums import HTTPMethod, Match
from lilya.middleware.base import Middleware
from lilya.permissions.base import Permission
from lilya.types import Receive, Scope, Send


def get_name(handler: Callable[..., Any]) -> str:
    """
    Returns the name of a given handler.
    """
    return (
        handler.__name__
        if inspect.isroutine(handler) or inspect.isclass(handler)
        else handler.__class__.__name__
    )


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
