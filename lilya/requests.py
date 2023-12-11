from typing import Any, Iterator, Mapping, Union

from lilya.enums import ScopeType
from lilya.types import Receive, Scope

try:
    from multipart.multipart import parse_options_header
except ModuleNotFoundError:  # pragma: nocover
    parse_options_header = None


class ClientDisconnect(Exception):
    ...


class Connection(Mapping[str, Any]):
    """
    The Base for all Connections.
    """

    def __init__(self, scope: Scope, receive: Union[Receive, None] = None) -> None:
        assert scope["type"] in (ScopeType.HTTP, ScopeType.WEBSOCKET)
        self.scope = scope

    def __getitem__(self, __key: str) -> Any:
        return self.scope[__key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.scope)

    def __len__(self) -> int:
        return len(self.scope)

    __eq__ = object.__eq__
    __hash__ = object.__hash__
