from collections.abc import Awaitable, Callable, Mapping, MutableMapping, Sequence
from contextlib import AbstractAsyncContextManager
from typing import (
    Any,
    TypeVar,
)

ApplicationType = TypeVar("ApplicationType")

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]

Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]

ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

StatelessLifespan = Callable[[ApplicationType], AbstractAsyncContextManager[None]]
StatefulLifespan = Callable[[ApplicationType], AbstractAsyncContextManager[Mapping[str, Any]]]
Lifespan = StatelessLifespan[ApplicationType] | StatefulLifespan[ApplicationType]

LifespanEvent = Sequence[Callable[[], Any]]

HTTPExceptionHandler = Callable[[Any, Exception], Any | Awaitable[Any]]
WebSocketExceptionHandler = Callable[[Any, Exception], Awaitable[None]]
ExceptionHandler = HTTPExceptionHandler | WebSocketExceptionHandler
CallableDecorator = TypeVar("CallableDecorator", bound=Callable[..., Any])
AnyCallable = Callable[..., Any]
Dependencies = dict[str, Callable[..., Any]] | dict[str, Any] | Any


class Empty: ...


EmptyType = type[Empty]
