from __future__ import annotations

import gzip
import io
from functools import cached_property
from typing import NoReturn

from lilya.datastructures import Header
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.types import ASGIApp, Message, Receive, Scope, Send


class GZipMiddleware(MiddlewareProtocol):
    """
    Middleware to compress responses with GZip.

    Args:
        app: The 'next' ASGI app to call.
        minimum_size: Minimum response size to trigger compression.
        compresslevel: GZip compression level (0 to 9).
    """

    def __init__(self, app: ASGIApp, minimum_size: int = 500, compresslevel: int = 9) -> None:
        """
        Initialize GZipMiddleware.

        Args:
            app: The 'next' ASGI app to call.
            minimum_size: Minimum response size to trigger compression.
            compresslevel: GZip compression level (0 to 9).
        """
        self.app = app
        self.minimum_size = minimum_size
        self.compresslevel = compresslevel

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handles incoming requests, checks for GZip support, and processes the response accordingly.

        Args:
            scope: The ASGI scope.
            receive: The ASGI receive function.
            send: The ASGI send function.
        """
        if scope["type"] == "http":
            headers = Header.ensure_header_instance(scope=scope)
            if "gzip" in headers.get("Accept-Encoding", ""):
                responder = GZipResponder(
                    self.app, self.minimum_size, compresslevel=self.compresslevel
                )
                await responder(scope, receive, send)
                return
        await self.app(scope, receive, send)


class GZipResponder:
    """
    ASGI middleware for compressing response bodies using GZip.

    Args:
        app (ASGIApp): The ASGI application to wrap.
        minimum_size (int): The minimum size of the response body to apply GZip compression.
        compresslevel (int, optional): The compression level for GZip (default is 9).
    """

    def __init__(self, app: ASGIApp, minimum_size: int, compresslevel: int = 9) -> None:
        """
        Initializes the GZipResponder.

        Args:
            app (ASGIApp): The ASGI application to wrap.
            minimum_size (int): The minimum size of the response body to apply GZip compression.
            compresslevel (int, optional): The compression level for GZip (default is 9).
        """
        self.app = app
        self.minimum_size = minimum_size
        self.compresslevel = compresslevel
        self.send: Send = self.unattached_send
        self.initial_message: Message = {}
        self.started = False
        self.content_encoding_set = False
        self.gzip_buffer = io.BytesIO()

    @cached_property
    def gzip_file(self) -> gzip.GzipFile:
        return gzip.GzipFile(mode="wb", fileobj=self.gzip_buffer, compresslevel=self.compresslevel)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        ASGI interface method to handle incoming requests.

        Args:
            scope (Scope): The ASGI scope.
            receive (Receive): The receive channel.
            send (Send): The send channel.
        """
        self.send = send
        try:
            await self.app(scope, receive, self.send_with_gzip)
        finally:
            # ensure cleanup if file is initialized
            if "gzip_file" in self.__dict__ and not self.gzip_file.closed:
                self.gzip_file.close()

    async def send_with_gzip(self, message: Message) -> None:
        """
        ASGI interface method to handle outgoing responses with GZip compression.

        Args:
            message (Message): The outgoing message.
        """
        message_type = message["type"]

        if message_type == "http.response.start":
            await self.handle_message_start(message)
        elif message_type == "http.response.body" and self.content_encoding_set:
            await self.handle_response_body_with_encoding(message)
        elif message_type == "http.response.body" and not self.started:
            await self.handle_response_body_without_encoding(message)
        elif message_type == "http.response.body":
            await self.handle_body(message)

    async def handle_message_start(self, message: Message) -> None:
        """
        Handles the 'http.response.start' message type.

        Args:
            message (Message): The outgoing message.
        """
        self.initial_message = message
        headers = Header.ensure_header_instance(self.initial_message)
        self.content_encoding_set = "content-encoding" in headers

    async def handle_response_body_with_encoding(self, message: Message) -> None:
        """
        Handles 'http.response.body' when content encoding is set.

        Args:
            message (Message): The outgoing message.
        """
        if not self.started:
            self.started = True
            await self.send(self.initial_message)
        await self.send(message)

    async def handle_response_body_without_encoding(self, message: Message) -> None:
        """
        Handles 'http.response.body' when content encoding is not set.

        Args:
            message (Message): The outgoing message.
        """
        self.started = True
        body = message.get("body", b"")
        more_body = message.get("more_body", False)

        if len(body) < self.minimum_size and not more_body:
            await self.send(self.initial_message)
            await self.send(message)
        elif not more_body:
            await self.handle_standard_gzip_response(body, message)
        else:
            await self.handle_streaming_gzip_response(body, message)

    async def handle_standard_gzip_response(self, body: bytes, message: Message) -> None:
        """
        Handles standard GZip response.

        Args:
            body (bytes): The response body.
            message (Message): The outgoing message.
        """
        self.gzip_file.write(body)
        self.gzip_file.close()
        body = self.gzip_buffer.getvalue()

        headers = Header.ensure_header_instance(self.initial_message)
        headers["Content-Encoding"] = "gzip"
        headers["Content-Length"] = str(len(body))
        headers.add_vary_header("Accept-Encoding")
        message["body"] = body

        await self.send(self.initial_message)
        await self.send(message)

    async def handle_streaming_gzip_response(self, body: bytes, message: Message) -> None:
        """
        Handles streaming GZip response.

        Args:
            body (bytes): The response body.
            message (Message): The outgoing message.
        """
        headers = Header.ensure_header_instance(self.initial_message)
        headers["Content-Encoding"] = "gzip"
        headers.add_vary_header("Accept-Encoding")

        headers.pop("Content-Length", None)

        self.gzip_file.write(body)
        message["body"] = self.gzip_buffer.getvalue()
        self.gzip_buffer.seek(0)
        self.gzip_buffer.truncate()

        await self.send(self.initial_message)
        await self.send(message)

    async def handle_body(self, message: Message) -> None:
        """
        Handles remaining body in streaming GZip response.

        Args:
            message (Message): The outgoing message.
        """
        body = message.get("body", b"")
        more_body = message.get("more_body", False)

        self.gzip_file.write(body)
        if not more_body:
            self.gzip_file.close()

        message["body"] = self.gzip_buffer.getvalue()
        self.gzip_buffer.seek(0)
        self.gzip_buffer.truncate()

        await self.send(message)

    async def unattached_send(self, message: Message) -> NoReturn:
        """
        Raises a RuntimeError if the send awaitable is not set.

        Args:
            message (Message): The outgoing message.
        """
        raise RuntimeError("send awaitable not set")
