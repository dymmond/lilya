from __future__ import annotations

import json
from base64 import b64decode, b64encode
from collections.abc import Awaitable, Callable
from inspect import isawaitable
from typing import Any, Literal

import itsdangerous
from itsdangerous.exc import BadSignature

from lilya._internal._connection import Connection
from lilya.datastructures import Header, Secret
from lilya.enums import ScopeType
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
        populate_session: Callable[[Connection], dict[str, Any] | Awaitable[dict[str, Any]]]
        | None = None,
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
            populate_session: (Callable[[Scope], dict[str, Any] | Awaitable[dict[str, Any]]]): An optional function for providing initial data to session.
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
        self.populate_session = populate_session
        self.scopes: set[str] = {ScopeType.HTTP, ScopeType.WEBSOCKET}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        ASGI application callable.
        """
        if scope["type"] not in self.scopes:
            await self.app(scope, receive, send)
            return

        connection = Connection(scope)
        initial_session_was_empty = await self.load_session_data(scope, connection)
        if initial_session_was_empty and self.populate_session is not None:
            initial_session_data: dict[str, Any] | Awaitable[dict[str, Any]] = (
                self.populate_session(connection)
            )
            if isawaitable(initial_session_data):
                initial_session_data = await initial_session_data
            scope["session"].update(initial_session_data)

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

        Returns:
            bool: Was the session empty or invalid? If yes skip the deletion.
        """
        if self.session_cookie in connection.cookies:
            data = connection.cookies[self.session_cookie].encode("utf-8")
            try:
                data = self.signer.unsign(data, max_age=self.max_age)
                scope["session"] = self.decode_session(data)
                return False
            except BadSignature:
                # could be a conflicting session cookie. Ignore if session is not updated.
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
        Process the response and set the session cookie. Handles multiple messages.
        """
        if message["type"] == "http.response.start":
            headers = Header.ensure_header_instance(scope=message)
            if all(
                not h.startswith(f"{self.session_cookie}=") for h in headers.get_all("set-cookie")
            ):  # Check if already set
                if scope["session"]:
                    data = self.encode_session(scope["session"])
                    data = self.signer.sign(data)
                    header_value = (
                        '{session_cookie}="{data}"; path={path}; {max_age}{security_flags}'.format(
                            session_cookie=self.session_cookie,
                            data=data.decode("utf-8"),
                            path=self.path,
                            max_age=f"Max-Age={self.max_age}; " if self.max_age else "",
                            security_flags=self.security_flags,
                        )
                    )
                    headers.add("set-cookie", header_value)
                elif not initial_session_was_empty:
                    header_value = (
                        "{session_cookie}={data}; path={path}; {expires}{security_flags}".format(
                            session_cookie=self.session_cookie,
                            data="null",
                            path=self.path,
                            expires="expires=Thu, 01 Jan 1970 00:00:00 GMT; ",
                            security_flags=self.security_flags,
                        )
                    )
                    headers.add("set-cookie", header_value)

        await send(message)
