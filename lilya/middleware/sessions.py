from __future__ import annotations

import json
from base64 import b64decode, b64encode
from collections.abc import Callable
from typing import Any, Literal

import itsdangerous
from itsdangerous.exc import BadSignature

from lilya._internal._connection import Connection
from lilya.datastructures import Header, Secret
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.types import ASGIApp, Message, Receive, Scope, Send


class SessionMiddleware(MiddlewareProtocol):
    def __init__(
        self,
        app: ASGIApp,
        secret_key: str | Secret,
        session_cookie: str = "session",
        max_age: int | None = 14 * 24 * 60 * 60,  # 14 days, in seconds
        path: str = "/",
        same_site: Literal["lax", "strict", "none"] = "lax",
        https_only: bool = False,
        domain: str | None = None,
        session_serializer: Callable[[Any], bytes | str] = json.dumps,
        session_deserializer: Callable[[bytes], Any] = json.loads,
    ) -> None:
        """
        Middleware for handling session data in ASGI applications.

        Args:
            app (ASGIApp): The ASGI application to wrap.
            secret_key (Union[str, Secret]): The secret key used for signing session data.
            session_cookie (str): The name of the session cookie.
            max_age (Optional[int]): The maximum age of the session in seconds (default is 14 days).
            path (str): The path attribute for the session cookie.
            same_site (Literal["lax", "strict", "none"]): The SameSite attribute for the session cookie.
            https_only (bool): If True, set the secure flag for the session cookie (HTTPS only).
            domain (Optional[str]): The domain attribute for the session cookie.
            session_serializer (Callable[[Any], bytes | str]): The encoder for the session. Default json.dumps.
            session_deserializer (Callable[[bytes], Any]): The decoder for the session. Default json.loads.
        """
        self.app = app
        self.signer = itsdangerous.TimestampSigner(str(secret_key))
        self.session_cookie = session_cookie
        self.max_age = max_age
        self.path = path
        self.security_flags = "httponly; samesite=" + same_site
        if https_only:
            self.security_flags += "; secure"
        if domain is not None:
            self.security_flags += f"; domain={domain}"
        self.session_serializer = session_serializer
        self.session_deserializer = session_deserializer

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        ASGI application callable.

        Args:
            scope (Scope): ASGI scope.
            receive (Receive): ASGI receive channel.
            send (Send): ASGI send channel.
        """
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        connection = Connection(scope)
        initial_session_was_empty = await self.load_session_data(scope, connection)

        async def send_wrapper(message: Message) -> None:
            await self.process_response(message, scope, initial_session_was_empty, send)

        await self.app(scope, receive, send_wrapper)

    def decode_session(self, data: bytes) -> Any:
        return self.session_deserializer(b64decode(data))

    def encode_session(self, session: Any) -> bytes:
        data = self.session_serializer(session)
        if isinstance(data, str):
            data = data.encode("utf-8")
        return b64encode(data)

    async def load_session_data(self, scope: Scope, connection: Connection) -> bool:
        """
        Load session data from the session cookie.

        Args:
            scope (Scope): ASGI scope.
            connection (Connection): HTTP connection object.

        Returns:
            bool: True if the initial session was empty, False otherwise.
        """
        if self.session_cookie in connection.cookies:
            data = connection.cookies[self.session_cookie].encode("utf-8")
            try:
                data = self.signer.unsign(data, max_age=self.max_age)
                scope["session"] = self.decode_session(data)
                return False
            except BadSignature:
                scope["session"] = {}
        else:
            scope["session"] = {}
        return True

    async def process_response(
        self,
        message: Message,
        scope: Scope,
        initial_session_was_empty: bool,
        send: Send,
    ) -> None:
        """
        Process the response and set the session cookie.

        Args:
            message (Message): ASGI message.
            scope (Scope): ASGI scope.
            initial_session_was_empty (bool): True if the initial session was empty, False otherwise.
            send (Send): ASGI send channel.
        """
        if message["type"] == "http.response.start":
            if scope["session"]:
                message = await self.set_session_cookie(scope, message)
            elif not initial_session_was_empty:
                message = await self.clear_session_cookie(scope, message)

        await send(message)

    async def set_session_cookie(self, scope: Scope, message: Message) -> Message:
        """
        Set the session cookie in the response headers.

        Args:
            scope (Scope): ASGI scope.
            message (Message): ASGI message
        """
        data = self.encode_session(scope["session"])
        data = self.signer.sign(data)
        headers = Header.from_scope(scope=scope)
        header_value = "{session_cookie}={data}; path={path}; {max_age}{security_flags}".format(
            session_cookie=self.session_cookie,
            data=data.decode("utf-8"),
            path=self.path,
            max_age=f"Max-Age={self.max_age}; " if self.max_age else "",
            security_flags=self.security_flags,
        )
        headers.add("Set-Cookie", header_value)
        message["headers"] = headers.encoded_multi_items()
        return message

    async def clear_session_cookie(self, scope: Scope, message: Message) -> Message:
        """
        Clear the session cookie in the response headers.

        Args:
            scope (Scope): ASGI scope.
        """
        headers = Header.from_scope(scope=scope)
        header_value = "{session_cookie}={data}; path={path}; {expires}{security_flags}".format(
            session_cookie=self.session_cookie,
            data="null",
            path=self.path,
            expires="expires=Thu, 01 Jan 1970 00:00:00 GMT; ",
            security_flags=self.security_flags,
        )
        headers.add("Set-Cookie", header_value)
        message["headers"] = headers.encoded_multi_items()
        return message
