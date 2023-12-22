from enum import IntEnum
from typing import Dict, List

from lilya.conf.enums import StrEnum


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


class ScopeType(StrEnum):
    HTTP = "http"
    WEBSOCKET = "websocket"


class HTTPType(StrEnum):
    HTTP = "http"
    HTTPS = "https"

    @classmethod
    def get_https_types(cls) -> List[str]:
        return [str(value) for value in cls]


class WebsocketType(StrEnum):
    WS = "ws"
    WSS = "wss"

    @classmethod
    def get_https_types(cls) -> List[str]:
        return [str(value) for value in cls]


class Event(StrEnum):
    HTTP_REQUEST = "http.request"
    HTTP_DISCONNECT = "http.disconnect"
    WEBSOCKET_CONNECT = "websocket.connect"
    WEBSOCKET_DISCONNECT = "websocket.disconnect"


class Match(IntEnum):
    NONE = 0
    PARTIAL = 1
    FULL = 2


class HTTPMethod(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    TRACE = "TRACE"


class MediaType(StrEnum):
    JSON = "application/json"
    HTML = "text/html"
    TEXT = "text/plain"
    MESSAGE_PACK = "application/x-msgpack"
    TEXT_CHARSET = "text/plain; charset=utf-8"
    PNG = "image/png"
    OCTET = "application/octet-stream"
