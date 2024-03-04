from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Dict, Tuple, cast

import anyio

from lilya._internal._connection import (
    SERVER_PUSH_HEADERS,
    ClientDisconnect,
    Connection,
    empty_receive,
    empty_send,
)
from lilya._internal._parsers import FormParser, MultiPartException, MultiPartParser
from lilya.compat import AsyncResourceHandler
from lilya.datastructures import FormData
from lilya.enums import Event, ScopeType
from lilya.exceptions import HTTPException
from lilya.types import Empty, Message, Receive, Scope, Send

try:
    from multipart.multipart import parse_options_header
except ModuleNotFoundError:  # pragma: nocover
    parse_options_header = None


class Request(Connection):
    """
    The `Request` object of Lilya.

    This class represents an HTTP request in the Lilya web framework. It provides methods
    for accessing various aspects of the request, such as headers, body, and form data.
    """

    _form: FormData | None = None

    def __init__(
        self, scope: Scope, receive: Receive = empty_receive, send: Send = empty_send
    ) -> None:
        """
        Initialize a new instance of the Request class.

        Args:
            scope (Scope): The ASGI scope of the request.
            receive (Receive): The receive channel for the request.
            send (Send): The send channel for the request.
        """
        super().__init__(scope)
        assert scope["type"] == ScopeType.HTTP
        self._receive = receive
        self._send = send
        self._stream_consumed = False
        self._is_disconnected = False
        self._json = Empty
        self._content_type = Empty
        self._body = Empty

    @property
    def method(self) -> str:
        """
        Get the HTTP method of the request.

        Returns:
            str: The HTTP method (e.g., "GET", "POST").
        """
        return cast(str, self.scope["method"])

    @property
    def receive(self) -> Receive:
        """
        Get the receive channel of the request.

        Returns:
            Receive: The receive channel.
        """
        return self._receive

    @property
    def send(self) -> Send:
        """
        Get the send of the request.

        Returns:
            Receive: The send.
        """
        return self._send

    @property
    def content_type(self) -> tuple[str, dict[str, str]]:
        """
        Get the content type of the request.

        Returns:
            Tuple[str, Dict[str, str]]: The content type as a tuple containing a string
            and a dictionary of parameters.
        """
        if self._content_type is Empty:
            self._content_type = self.headers.get("Content-Type", "")
        return cast(Tuple[str, Dict[str, str]], self._content_type)

    async def stream(self) -> AsyncGenerator[bytes, None]:
        """
        Stream the request body in asynchronous chunks.

        Yields:
            AsyncGenerator[bytes, None]: Bytes representing chunks of the request body.
        """
        if self._body is Empty:
            if self._stream_consumed:
                raise RuntimeError("Stream consumed")
            while not self._stream_consumed:
                event = await self._receive()
                if event["type"] == Event.HTTP_REQUEST:
                    if not event.get("more_body", False):
                        self._stream_consumed = True
                    if event["body"]:
                        yield event["body"]

                elif event["type"] == Event.HTTP_DISCONNECT:
                    self._is_disconnected = True
                    raise ClientDisconnect()
            yield b""

        else:
            yield cast(bytes, self._body)
            yield b""
            return

    async def body(self) -> bytes:
        """
        Read the entire request body.

        Returns:
            bytes: The request body as bytes.
        """
        if self._body is Empty:
            chunks: list[bytes] = []
            async for chunk in self.stream():
                chunks.append(chunk)
            self._body = b"".join(chunks)  # type: ignore
        return cast(bytes, self._body)

    async def json(self) -> Any:
        """
        Parse the request body as JSON.

        Returns:
            Any: The parsed JSON data.
        """
        if self._json is Empty:
            if "_body" in self.scope:
                body = self.scope["_body"]
            else:
                body = self.scope["_body"] = await self.body() or b"null"
            self._json = json.loads(body)
        return self._json

    async def _get_form(
        self,
        *,
        max_files: int | float = 1000,
        max_fields: int | float = 1000,
    ) -> FormData:
        """
        Parse and return form data from the request.

        Args:
            max_files (Union[int, float]): Maximum number of files allowed
                in the form data.
            max_fields (Union[int, float]): Maximum number of fields allowed
                in the form data.

        Returns:
            FormData: The parsed form data.
        """
        if self._form is None:
            assert (
                parse_options_header is not None
            ), "The `python-multipart` library must be installed to use form parsing."
            content_type_header = self.headers.get("Content-Type")
            content_type: bytes
            content_type, _ = parse_options_header(content_type_header)
            if content_type == b"multipart/form-data":
                try:
                    multipart_parser = MultiPartParser(
                        self.headers,
                        self.stream(),
                        max_files=max_files,
                        max_fields=max_fields,
                    )
                    self._form = await multipart_parser.parse()
                except MultiPartException as exc:
                    if "app" in self.scope:
                        raise HTTPException(status_code=400, detail=exc.message) from exc
                    raise exc
            elif content_type == b"application/x-www-form-urlencoded":
                form_parser = FormParser(self.headers, self.stream())
                self._form = await form_parser.parse()
            else:
                self._form = FormData()
        return self._form

    def form(
        self,
        *,
        max_files: int | float = 1000,
        max_fields: int | float = 1000,
    ) -> AsyncResourceHandler[FormData]:
        """
        Get the form data from the request.

        Args:
            max_files (Union[int, float]): Maximum number of files allowed
                in the form data.
            max_fields (Union[int, float]): Maximum number of fields allowed
                in the form data.

        Returns:
            AsyncResourceHandler[FormData]: Awaiting or using this object will
            return the parsed form data.
        """
        return AsyncResourceHandler(self._get_form(max_files=max_files, max_fields=max_fields))

    async def close(self) -> None:
        """
        Close the request and associated resources.

        This includes closing the form data, if any.
        """
        if self._form is not None:
            await self._form.close()

    async def is_disconnected(self) -> bool:
        """
        Check if the client is disconnected.

        Returns:
            bool: True if the client is disconnected, False otherwise.
        """
        if not self._is_disconnected:
            message: Message = {}

            # If message isn't immediately available, move on
            with anyio.CancelScope() as cs:
                cs.cancel()
                message = await self._receive()

            if message.get("type") == "http.disconnect":
                self._is_disconnected = True

        return self._is_disconnected

    async def send_push_promise(self, path: str) -> None:
        """
        Send a push promise for the specified path.

        Args:
            path (str): The path for which to send the push promise.
        """
        if "http.response.push" in self.scope.get("extensions", {}):
            raw_headers: list[tuple[bytes, bytes]] = []
            for name in SERVER_PUSH_HEADERS:
                for value in self.headers.getlist(name):
                    raw_headers.append((name.encode("latin-1"), value.encode("latin-1")))
            await self._send({"type": "http.response.push", "path": path, "headers": raw_headers})

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
