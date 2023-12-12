from enum import IntEnum
from typing import List

from lilya.conf.enums import BaseEnum


class DefaultPort(IntEnum):
    """
    Enum representing the default ports.
    """

    HTTP = 80
    HTTPS = 443
    WS = 80
    WSS = 443

    def __int__(self) -> int:
        return self.value

    def __repr__(self) -> int:  # type: ignore
        return int(self)


class ScopeType(BaseEnum):
    HTTP = "http"
    WEBSOCKET = "websocket"


class HTTPType(BaseEnum):
    HTTP = "http"
    HTTPS = "https"

    @classmethod
    def get_https_types(cls) -> List[str]:
        return [str(value) for value in cls]
