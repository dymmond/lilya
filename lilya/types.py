from collections.abc import Awaitable, Mapping, MutableMapping, Sequence
from contextlib import AbstractAsyncContextManager
from typing import (
    Any,
    Callable,
    TypeVar,
    Union,
)

ApplicationType = TypeVar("ApplicationType")

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]

Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]

ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

StatelessLifespan = Callable[[ApplicationType], AbstractAsyncContextManager[None]]
StatefulLifespan = Callable[[ApplicationType], AbstractAsyncContextManager[Mapping[str, Any]]]
Lifespan = Union[StatelessLifespan[ApplicationType], StatefulLifespan[ApplicationType]]

LifespanEvent = Sequence[Callable[[], Any]]

HTTPExceptionHandler = Callable[[Any, Exception], Union[Any, Awaitable[Any]]]
WebSocketExceptionHandler = Callable[[Any, Exception], Awaitable[None]]
ExceptionHandler = Union[HTTPExceptionHandler, WebSocketExceptionHandler]
CallableDecorator = TypeVar("CallableDecorator", bound=Callable[..., Any])


class Empty: ...
