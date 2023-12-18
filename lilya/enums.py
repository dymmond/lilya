from enum import IntEnum
from typing import Dict, List

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

    @classmethod
    def to_dict(cls) -> Dict[str, int]:
        return {
            "http": cls.HTTP.value,
            "https": cls.HTTPS.value,
            "ws": cls.WS.value,
            "wss": cls.WSS.value,
        }


class ScopeType(BaseEnum):
    HTTP = "http"
    WEBSOCKET = "websocket"


class HTTPType(BaseEnum):
    HTTP = "http"
    HTTPS = "https"

    @classmethod
    def get_https_types(cls) -> List[str]:
        return [str(value) for value in cls]


class WebsocketType(BaseEnum):
    WS = "ws"
    WSS = "wss"

    @classmethod
    def get_https_types(cls) -> List[str]:
        return [str(value) for value in cls]


class Event(BaseEnum):
    HTTP_REQUEST = "http.request"
    HTTP_DISCONNECT = "http.disconnect"
    WEBSOCKET_CONNECT = "websocket.connect"
    WEBSOCKET_DISCONNECT = "websocket.disconnect"
