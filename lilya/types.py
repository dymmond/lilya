from collections.abc import Awaitable, Callable, Mapping, MutableMapping, Sequence
from contextlib import AbstractAsyncContextManager
from typing import (
    Any,
    TypeVar,
    Union,
)

try:
    from typing_extensions import Doc
except ModuleNotFoundError:
    # stub

    class Doc:  # type: ignore[no-redef]
        def __init__(self, documentation: str, /) -> None:
            self.documentation = documentation


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
