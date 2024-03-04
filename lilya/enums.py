from __future__ import annotations

from enum import IntEnum

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
    def to_dict(cls) -> dict[str, int]:
        return {
            "http": cls.HTTP.value,
            "https": cls.HTTPS.value,
            "ws": cls.WS.value,
            "wss": cls.WSS.value,
        }


class ScopeType(StrEnum):
    HTTP = "http"
    WEBSOCKET = "websocket"
    LIFESPAN = "lifespan"


class EventType(StrEnum):
    ON_STARTUP = "on_startup"
    ON_SHUTDOWN = "on_shutdown"


class SignatureDefault(StrEnum):
    REQUEST = "request"
    WEBSOCKET = "websocket"


class HTTPType(StrEnum):
    HTTP = "http"
    HTTPS = "https"

    @classmethod
    def get_https_types(cls) -> list[str]:
        return [str(value) for value in cls]


class WebsocketType(StrEnum):
    WS = "ws"
    WSS = "wss"

    @classmethod
    def get_https_types(cls) -> list[str]:
        return [str(value) for value in cls]


class Event(StrEnum):
    HTTP_REQUEST = "http.request"
    HTTP_DISCONNECT = "http.disconnect"
    WEBSOCKET_CONNECT = "websocket.connect"
    WEBSOCKET_DISCONNECT = "websocket.disconnect"
    WEBSOCKET_ACCEPT = "websocket.accept"
    WEBSOCKET_RECEIVE = "websocket.receive"
    WEBSOCKET_CLOSE = "websocket.close"
    WEBSOCKET_SEND = "websocket.send"


class MessageMode(StrEnum):
    TEXT = "text"
    BYTES = "bytes"
    BINARY = "binary"


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

    @classmethod
    def to_list(cls) -> list[str]:
        return [method.value for method in cls]


class HTTPCorsEnum(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"

    @classmethod
    def to_tuple(cls) -> tuple[str, ...]:
        return tuple(method.value for method in cls)


class HeaderEnum(StrEnum):
    ACCEPT = "Accept"
    ACCEPT_LANGUAGE = "Accept-Language"
    CONTENT_LANGUAGE = "Content-Language"
    CONTENT_TYPE = "Content-Type"

    @classmethod
    def to_set(cls) -> set[str]:
        return {method.value for method in cls}


class MediaType(StrEnum):
    JSON = "application/json"
    HTML = "text/html"
    TEXT = "text/plain"
    MESSAGE_PACK = "application/x-msgpack"
    TEXT_CHARSET = "text/plain; charset=utf-8"
    PNG = "image/png"
    OCTET = "application/octet-stream"


class WebSocketState(IntEnum):
    CONNECTING = 0
    CONNECTED = 1
    DISCONNECTED = 2


class FormMessage(IntEnum):
    FIELD_START = 1
    FIELD_NAME = 2
    FIELD_DATA = 3
    FIELD_END = 4
    END = 5
