from __future__ import annotations

import contextvars
import copy
import warnings
from functools import lru_cache
from typing import TYPE_CHECKING, Annotated, Any, cast

from lilya.datastructures import URL
from lilya.exceptions import ImproperlyConfigured
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
    This object represents a global state of the application.
    This can be used for Lilya requests and to store global
    properties on a request context of the application and share
    the state across.

    This diverges from `state` of the application object and state
    that is only accessible within the handler itself.
    """

    _context: dict[str, Any]

    def __init__(self, context: dict[str, Any] | None = None):
        if context is None:
            context = {}
        super().__setattr__("_context", context)

    @property
    def store(self) -> Any:
        return self._context

    def __setattr__(self, key: Any, value: Any) -> None:
        self._context[key] = value

    def __getattr__(self, key: Any) -> Any:
        try:
            return self._context[key]
        except KeyError:
            message = "'{}' object has no attribute '{}'"
            raise AttributeError(message.format(self.__class__.__name__, key)) from None

    def __delattr__(self, key: Any) -> None:
        del self._context[key]

    def __copy__(self) -> G:
        return self.__class__(copy.copy(self._context))

    def __len__(self) -> int:
        return len(self._context)

    def __getitem__(self, key: str) -> Any:
        return self._context[key]

    def copy(self) -> G:
        return copy.copy(self)

    def clear(self) -> None:
        self._context.clear()

    def __repr__(self: G) -> str:
        return f"{self.__class__.__name__}()"


@lru_cache
def get_g() -> G:
    return G()


g = get_g()


class LazyRequestProxy:
    """
    A proxy to lazily evaluate attributes of the current request.
    """

    def __init__(self, request_getter: Any) -> None:
        self._request_getter = request_getter

    def __getattr__(self, item: str) -> Any:
        request = self._request_getter()
        if not request:
            raise ImproperlyConfigured(
                "Request context requires the 'RequestContextMiddleware' to be installed."
            )
        return getattr(request, item)

    def __repr__(self: LazyRequestProxy) -> str:
        if self._request_getter is None:
            return "<LazyRequestProxy [Unevaluated]>"
        return '<LazyRequestProxy "Request()">'


class RequestContext:
    """
    Similar to the request, this object makes it available to the handler
    to be access anywhere in the application that does not require the handler directly.
    """

    _request_context: contextvars.ContextVar[Request] = contextvars.ContextVar("request_context")

    # Lazily access the request object
    lazy_request = LazyRequestProxy(lambda: RequestContext._request_context.get(None))

    @classmethod
    def set_request(cls, request: Request) -> None:
        """
        Set the current request in the context.
        """
        cls._request_context.set(request)

    @classmethod
    def get_request(cls) -> Request:
        """
        Retrieve the current request from the context.
        """
        try:
            return cls._request_context.get()
        except LookupError:
            raise RuntimeError(
                "Request context requires the 'RequestContextMiddleware' to be installed."
            ) from None

    @classmethod
    def reset_request(cls, token: Any) -> None:
        """
        Reset the context variable.
        """
        cls._request_context.reset(token)

    def __str__(self) -> str:
        return "<Request()>"

    def __repr__(self) -> str:
        return str(self)


request_context: Request = cast("Request", RequestContext.lazy_request)
