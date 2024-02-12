from typing import (
    Any,
    AsyncContextManager,
    Awaitable,
    Callable,
    Mapping,
    MutableMapping,
    Sequence,
    TypeVar,
    Union,
)

ApplicationType = TypeVar("ApplicationType")

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]

Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]

ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

StatelessLifespan = Callable[[ApplicationType], AsyncContextManager[None]]
StatefulLifespan = Callable[[ApplicationType], AsyncContextManager[Mapping[str, Any]]]
Lifespan = Union[StatelessLifespan[ApplicationType], StatefulLifespan[ApplicationType]]

LifespanEvent = Sequence[Callable[[], Any]]

HTTPExceptionHandler = Callable[[Any, Exception], Union[Any, Awaitable[Any]]]
WebSocketExceptionHandler = Callable[[Any, Exception], Awaitable[None]]
ExceptionHandler = Union[HTTPExceptionHandler, WebSocketExceptionHandler]


class Empty:
    """A placeholder class."""
