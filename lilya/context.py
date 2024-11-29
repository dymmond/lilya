from __future__ import annotations

import contextvars
import copy
import warnings
from typing import TYPE_CHECKING, Annotated, Any

from lilya.datastructures import URL
from lilya.types import Doc, Scope

if TYPE_CHECKING:
    from lilya.requests import Request
    from lilya.routing import BasePath


class Context:
    """
    `Context` class is used for the handlers context of the
    scope of the call.

    When a `context` is passed through the handler,
    the context will be aware of the decoractor handler
    itself.

    You will probably not need the context or change it but it is here in
    case you decide to use it.

    !!! Tip
        The context only exists in the handlers and nothing else which you can also
        see it as `request context` sort of approach.

    **Example**

    ```python
    from lilya.apps import Lilya
    from lilya.requests import Request
    from lilya.context import Context


    async def home(context: Context) -> None: ...
    ```
    """

    def __init__(
        self,
        __handler__: Annotated[
            BasePath,
            Doc(
                """
                The [handler](https://lilya.dev/routing) where the context will be. placed.

                To avoid any adulteration of the the original route handler, the context performs
                a shallow copy of the original handler itself.
                """
            ),
        ],
        __request__: Annotated[
            Request,
            Doc(
                """
                A [Request](https://lilya.dev/references/request/) class object.
                """
            ),
        ],
    ) -> None:
        self.__handler__ = copy.copy(__handler__)
        self.__request__ = __request__

    @property
    def handler(self) -> BasePath:
        return self.__handler__

    @property
    def request(self) -> Request:
        return self.__request__

    @property
    def user(self) -> Any:
        return self.request.user

    @property
    def settings(self) -> Any:
        return self.request.app.settings

    @property
    def scope(self) -> Scope:
        return self.request.scope

    @property
    def app(self) -> Any:
        return self.request.scope["app"]

    def add_to_context(
        self,
        key: Annotated[
            Any,
            Doc(
                """
                The key value to be added to the context dictionary.
                """
            ),
        ],
        value: Annotated[
            Any,
            Doc(
                """
                The value value to be added to the context dictionary and map with the key.
                """
            ),
        ],
    ) -> None:
        """
        Adds a key to the context of an handler.

        This can be particularly useful if you are programatically
        building the handler or for any other specific and unique operation.

        **Example**

        ```python
        from typing import Any
        from lilya.context import Context

        async def get_data(context: Context) -> Any:
            context.update{"name": "Lilya"}
            return context.get_context_data()
        ```
        """
        if key in self.__dict__:
            warnings.warn(
                f"The key: '{key} already exists in context and it will be overritten.",
                stacklevel=2,
            )
        setattr(self, key, value)

    def get_context_data(self, **kwargs: Any) -> dict[Any, Any]:
        """
        Returns the context in a python dictionary like structure.
        """
        context_data = {
            k: v
            for k, v in self.__dict__.items()
            if not k.startswith("__") and not k.endswith("__")
        }
        return context_data

    def path_for(
        self,
        name: Annotated[
            str,
            Doc(
                """
                The `name` given in a `Gateway` or `Include` objects.

                **Example**

                ```python
                from lilya import Lilya, Gateway

                Gateway(handler=..., name="view-users")
                ```
                """
            ),
        ],
        **path_params: Annotated[
            Any,
            Doc(
                """
                Any additional *path_params* declared in the URL of the
                handler and are needed to *reverse* the names and return
                the proper URL.
                """
            ),
        ],
    ) -> str:
        url: URL = self.request.path_for(name, **path_params)
        return str(url)


class G:
    """
    This objects represents a global state of the application.
    This can be used for Lilya requests and to store global
    properties on a request context of the application and share
    the state across.

    This diverges from `state` of the application object and state
    that is only accessible within the handler itself.
    """

    _context: contextvars.ContextVar = contextvars.ContextVar("g_context", default={})

    @property
    def store(self) -> Any:
        return self._context.get()

    def __getattr__(self, name: str) -> Any:
        if name in self.store:
            return self.store[name]
        raise AttributeError(f"'G' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        if name in ["store", "_context"]:
            return super().__setattr__(name, value)
        else:
            self.store[name] = value

    def __delattr__(self, name: str) -> None:
        if name in self.store:
            del self.store[name]
        raise AttributeError(f"'G' object has no attribute '{name}'")

    def clear(self) -> None:
        self._context.set({})

    def __len__(self) -> int:
        return len(self.store)


g = G()
