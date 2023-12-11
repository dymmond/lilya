from enum import Enum

from lilya.conf.enums import BaseEnum


class DefaultPort(int, Enum):
    """
    Enum representing the default ports.
    """

    HTTP = 80
    HTTPS = 443
    WS = 80
    WSS = 443

    def __int__(self) -> int:
        return self.value

    def __repr__(self) -> str:
        return int(self)


class ScopeType(BaseEnum):
    HTTP = "http"
    WEBSOCKET = "websocket"
