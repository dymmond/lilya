from typing import (
    Any,
    AsyncContextManager,
    Awaitable,
    Callable,
    Dict,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Set,
    Type,
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

# HTTPExceptionHandler = Callable[["Request", Exception], Union["Response", Awaitable["Response"]]]
# WebSocketExceptionHandler = Callable[["WebSocket", Exception], Awaitable[None]]
# ExceptionHandler = Union[HTTPExceptionHandler, WebSocketExceptionHandler]

HTTPExceptionHandler = Callable[[Any, Exception], Union[Any, Awaitable[Any]]]
WebSocketExceptionHandler = Callable[[Any, Exception], Awaitable[None]]
ExceptionHandler = Union[HTTPExceptionHandler, WebSocketExceptionHandler]
