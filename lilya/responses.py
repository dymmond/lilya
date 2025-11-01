from __future__ import annotations

import contextlib
import functools
import http.cookies
import inspect
import os
import stat
import time
import typing
import warnings
from collections.abc import (
    AsyncIterable,
    Awaitable,
    Callable,
    Coroutine,
    Generator,
    Iterable,
    Mapping,
    Sequence,
)
from contextvars import ContextVar
from datetime import datetime
from email.utils import format_datetime, formatdate
from inspect import isawaitable, isclass
from io import FileIO
from mimetypes import guess_type
from typing import IO, Any, Literal, NoReturn, cast
from urllib.parse import quote

import anyio

from lilya import status
from lilya._internal._helpers import HeaderHelper
from lilya.background import Task
from lilya.compat import md5_hexdigest
from lilya.concurrency import iterate_in_threadpool
from lilya.datastructures import URL, Header
from lilya.encoders import ENCODER_TYPES, EncoderProtocol, MoldingProtocol, json_encode
from lilya.enums import Event, HTTPMethod, MediaType
from lilya.logging import logger
from lilya.ranges import ContentRanges, Range, parse_range_value
from lilya.serializers import serializer
from lilya.types import Message, Receive, Scope, Send

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

try:
    import msgpack
except ImportError:  # pragma: no cover
    msgpack = None

try:
    import magic
except ImportError:  # pragma: no cover
    magic = None

Content = str | bytes
Encoder = EncoderProtocol | MoldingProtocol
SyncContentStream = Iterable[Content]
AsyncContentStream = AsyncIterable[Content]
ContentStream = AsyncContentStream | SyncContentStream

_empty: tuple[Any, ...] = ()

RESPONSE_TRANSFORM_KWARGS: ContextVar[dict | None] = ContextVar(
    "RESPONSE_TRANSFORM_KWARGS", default=None
)


@functools.lru_cache(1)
def require_magic() -> None:
    if magic is None:
        raise ImportError(
            "The 'python-magic' library is required to deduce the media_type from the body."
        )


class Response:
    media_type: str | None = None
    status_code: int | None = None
    charset: str = "utf-8"
    passthrough_body_types: tuple[type, ...] = (bytes,)
    headers: Header
    deduce_media_type_from_body: bool | Literal["force"] = False
    cleanup_handler: Callable[[], None | Awaitable[None]] | None = None

    def __init__(
        self,
        content: Any = None,
        status_code: int = status.HTTP_200_OK,
        headers: Mapping[str, str] | None = None,
        cookies: Mapping[str, str] | Any | None = None,
        media_type: str | None = None,
        background: Task | None = None,
        encoders: Sequence[Encoder | type[Encoder]] | None = None,
        passthrough_body_types: tuple[type, ...] | None = None,
        deduce_media_type_from_body: bool | Literal["force"] = False,
    ) -> None:
        if passthrough_body_types is not None:
            self.passthrough_body_types = passthrough_body_types
        if status_code is not None:
            self.status_code = status_code
        if media_type is not None:
            self.media_type = media_type
        self.background = background
        self.cookies = cookies
        self.deduce_media_type_from_body = deduce_media_type_from_body
        self.encoders: list[Encoder] = [
            encoder() if isclass(encoder) else encoder for encoder in encoders or _empty
        ]
        if isawaitable(content):
            self.async_content = content
        else:
            self.body = self.make_response(content)
        # deduce media type
        if self.deduce_media_type_from_body and getattr(self, "body", None) is not None:
            if self.deduce_media_type_from_body == "force" or self.media_type is None:
                self.media_type = self.find_media_type()
        self.make_headers(headers)

    async def execute_cleanup_handler(self) -> None:
        if self.cleanup_handler is None:
            return
        res = self.cleanup_handler()
        if isawaitable(res):
            await res

    async def resolve_async_content(self) -> None:
        if getattr(self, "async_content", None) is not None:
            self.body = self.make_response(await self.async_content)
            self.async_content = None
            if (
                HeaderHelper.has_body_message(self.status_code)
                and "content-length" not in self.headers
            ):
                self.headers["content-length"] = str(len(self.body))
            if self.deduce_media_type_from_body:
                if self.deduce_media_type_from_body == "force" or self.media_type is None:
                    self.media_type = self.find_media_type()
                    self.headers["content-type"] = HeaderHelper.get_content_type(
                        charset=self.charset, media_type=self.media_type
                    )

    def find_media_type(self) -> str:
        require_magic()
        return magic.from_buffer(self.body[:2048], mime=True) or self.media_type or MediaType.OCTET

    @classmethod
    @contextlib.contextmanager
    def with_transform_kwargs(cls, params: dict | None, /) -> Generator[None, None, None]:
        token = RESPONSE_TRANSFORM_KWARGS.set(params)
        try:
            yield
        finally:
            RESPONSE_TRANSFORM_KWARGS.reset(token)

    @classmethod
    def transform(cls, content: Any) -> Any:
        transform_kwargs = RESPONSE_TRANSFORM_KWARGS.get()
        if transform_kwargs is None:
            transform_kwargs = {}
        return json_encode(content, **transform_kwargs)

    def make_response(self, content: Any) -> bytes:
        """
        Makes the Response object type.
        """
        if content is None or content is NoReturn:
            return b""
        # convert them to bytes if not in passthrough_body_types
        if not isinstance(content, self.passthrough_body_types) and isinstance(
            content, (bytearray, memoryview)
        ):
            content = bytes(content)
        if isinstance(content, self.passthrough_body_types):
            return cast(bytes, content)
        transform_kwargs = RESPONSE_TRANSFORM_KWARGS.get()
        if transform_kwargs is not None:
            transform_kwargs = transform_kwargs.copy()
            if self.encoders:
                transform_kwargs["with_encoders"] = (*self.encoders, *ENCODER_TYPES.get())
            # strip " from stringified primitives
            transform_kwargs.setdefault(
                "post_transform_fn",
                lambda x: x.strip('"') if isinstance(x, str) else x.strip(b'"'),
            )
            content = json_encode(content, **transform_kwargs)

            # convert them to bytes if not in passthrough_body_types
            if not isinstance(content, self.passthrough_body_types) and isinstance(
                content, (bytearray, memoryview)
            ):
                content = bytes(content)
            if isinstance(content, self.passthrough_body_types):
                return cast(bytes, content)
        # handle empty {} or [] gracefully instead of failing
        # must be transformed before
        if not content:
            return b""
        return content.encode(self.charset)  # type: ignore

    def make_headers(
        self, content_headers: Mapping[str, str] | dict[str, str] | None = None
    ) -> None:
        """
        Initializes the headers based on RFC specifications by setting appropriate conditions and restrictions.

        Args:
            content_headers (Union[Mapping[str, str], Dict[str, str], None], optional): Additional headers to include (default is None).
        """
        headers: dict[str, str] = {} if content_headers is None else content_headers  # type: ignore

        if HeaderHelper.has_entity_header_status(self.status_code):
            headers = HeaderHelper.remove_entity_headers(headers)
        if HeaderHelper.has_body_message(self.status_code):
            if getattr(self, "body", None) is not None:
                headers.setdefault("content-length", str(len(self.body)))

            # Populates the content type if exists and either a body was found or deduce_media_type_from_body was not force
            if (
                self.deduce_media_type_from_body != "force"
                or getattr(self, "body", None) is not None
            ):
                content_type = HeaderHelper.get_content_type(
                    charset=self.charset, media_type=self.media_type
                )
                if content_type is not None:
                    headers.setdefault("content-type", content_type)
        self.headers = Header(headers)

    def set_cookie(
        self,
        key: str,
        value: str = "",
        *,
        path: str = "/",
        domain: str | None = None,
        secure: bool = False,
        max_age: int | None = None,
        expires: datetime | str | int | None = None,
        httponly: bool = False,
        samesite: Literal["lax", "strict", "none"] = "lax",
    ) -> None:
        """
        Sets a cookie in the response headers.

        Args:
            key (str): The name of the cookie.
            value (str, optional): The value of the cookie.
            path (str, optional): The path for which the cookie is valid (default is '/').
            domain (Union[str, None], optional): The domain to which the cookie belongs.
            secure (bool, optional): If True, the cookie should only be sent over HTTPS.
            max_age (Union[int, None], optional): The maximum age of the cookie in seconds.
            expires (Union[Union[datetime, str, int], None], optional): The expiration date of the cookie.
            httponly (bool, optional): If True, the cookie should only be accessible through HTTP.
            samesite (Literal["lax", "strict", "none"], optional): SameSite attribute of the cookie.

        Raises:
            AssertionError: If samesite is not one of 'strict', 'lax', or 'none'.
        """
        cookie: http.cookies.BaseCookie[str] = http.cookies.SimpleCookie()
        cookie[key] = value
        if max_age is not None:
            cookie[key]["max-age"] = max_age
        if expires is not None:
            if isinstance(expires, datetime):
                cookie[key]["expires"] = format_datetime(expires, usegmt=True)
            else:
                cookie[key]["expires"] = expires
        if path is not None:
            cookie[key]["path"] = path
        if domain is not None:
            cookie[key]["domain"] = domain
        if secure:
            cookie[key]["secure"] = True
        if httponly:
            cookie[key]["httponly"] = True
        if samesite is not None:
            assert samesite.lower() in [
                "strict",
                "lax",
                "none",
            ], "samesite must be either 'strict', 'lax' or 'none'"
            cookie[key]["samesite"] = samesite
        cookie_val = cookie.output(header="").strip()
        self.headers.add("set-cookie", cookie_val)

    def delete_cookie(
        self,
        key: str,
        path: str = "/",
        domain: str | None = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: Literal["lax", "strict", "none"] = "lax",
    ) -> None:
        """
        Deletes a cookie in the response headers by setting its max age and expiration to 0.

        Args:
            key (str): The name of the cookie to delete.
            path (str, optional): The path for which the cookie is valid (default is '/').
            domain (Union[str, None], optional): The domain to which the cookie belongs.
            secure (bool, optional): If True, the cookie should only be sent over HTTPS.
            httponly (bool, optional): If True, the cookie should only be accessible through HTTP.
            samesite (Literal["lax", "strict", "none"], optional): SameSite attribute of the cookie.
        """
        self.set_cookie(
            key,
            max_age=0,
            expires=0,
            path=path,
            domain=domain,
            secure=secure,
            httponly=httponly,
            samesite=samesite,
        )

    @property
    def encoded_headers(self) -> list[Any]:
        return self.headers.get_encoded_multi_items()

    # make raw_headers an alias for encoded_headers in case anyone ever requires it
    raw_headers = encoded_headers

    def message(self, prefix: str) -> dict[str, Any]:
        return {
            "type": prefix + "http.response.start",
            "status": self.status_code,
            # some tests add headers dirty and assume a list
            "headers": self.headers,
        }

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # should be mutation free for both methods
        mutation_free = "method" in scope and scope["method"].upper() in {
            HTTPMethod.HEAD,
            HTTPMethod.OPTIONS,
        }
        try:
            prefix = "websocket." if scope["type"] == "websocket" else ""
            await self.resolve_async_content()
            await send(self.message(prefix=prefix))

            # don't interfere, in case of bodyless requests like head the message is ignored.
            await send({"type": f"{prefix}http.response.body", "body": self.body})

        finally:
            await self.execute_cleanup_handler()
        if self.background is not None and not mutation_free:
            await self.background()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(media_type={self.media_type}, status_code={self.status_code}, charset={self.charset})"


class HTMLResponse(Response):
    media_type = MediaType.HTML


# alias
HTML = HTMLResponse


class Error(HTMLResponse):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class PlainText(Response):
    media_type = MediaType.TEXT


TextResponse = PlainText


class DispositionResponse(Response):
    def __init__(
        self,
        *,
        filename: str | None = None,
        content_disposition_type: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.filename = filename
        self.content_disposition_type = content_disposition_type
        super().__init__(**kwargs)

    @staticmethod
    def make_content_disposition_header(
        *, content_disposition_type: str | None, filename: str | None
    ) -> str | None:
        if content_disposition_type == "inline":
            return "inline"
        elif content_disposition_type == "attachment":
            if filename is not None:
                content_disposition_filename = quote(filename)
                if content_disposition_filename != filename:
                    content_disposition = f"{content_disposition_type}; filename*=utf-8''{content_disposition_filename}"
                else:
                    content_disposition = f'{content_disposition_type}; filename="{filename}"'
            else:
                content_disposition = content_disposition_type
            return content_disposition
        elif content_disposition_type is None:
            if filename is not None:
                content_disposition_filename = quote(filename)
                if content_disposition_filename != filename:
                    content_disposition = (
                        f"attachment; filename*=utf-8''{content_disposition_filename}"
                    )
                else:
                    content_disposition = f'attachment; filename="{filename}"'
                return content_disposition
        return None

    def make_headers(
        self, content_headers: Mapping[str, str] | dict[str, str] | None = None
    ) -> None:
        super().make_headers(content_headers)
        content_disposition = self.make_content_disposition_header(
            content_disposition_type=self.content_disposition_type,
            filename=self.filename,
        )
        if content_disposition is not None:
            self.headers.setdefault("content-disposition", content_disposition)


class JSONResponse(Response):
    media_type = MediaType.JSON

    def __init__(
        self,
        content: Any,
        status_code: int = status.HTTP_200_OK,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: Task | None = None,
        encoders: Sequence[Encoder | type[Encoder]] | None = None,
        passthrough_body_types: tuple[type, ...] | None = None,
    ) -> None:
        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
            encoders=encoders,
            passthrough_body_types=passthrough_body_types,
        )

    def make_response(self, content: Any) -> bytes:
        if content is NoReturn:
            return b""
        new_params = RESPONSE_TRANSFORM_KWARGS.get()
        if new_params:
            new_params = new_params.copy()
        else:
            new_params = {}
        new_params["post_transform_fn"] = None
        if self.encoders:
            new_params["with_encoders"] = (*self.encoders, *ENCODER_TYPES.get())
        content = json_encode(content, **new_params)

        # convert them to bytes if not in passthrough_body_types
        if not isinstance(content, self.passthrough_body_types) and isinstance(
            content, (bytearray, memoryview)
        ):
            content = bytes(content)
        if isinstance(content, self.passthrough_body_types):
            return cast(bytes, content)
        return cast(bytes, content.encode(self.charset))


class Ok(JSONResponse):
    media_type = MediaType.JSON


class RedirectResponse(Response):
    # make sure bytes are always passed through here
    passthrough_body_types: tuple[type, ...] = (bytes,)

    def __init__(
        self,
        url: str | URL,
        status_code: int = status.HTTP_303_SEE_OTHER,
        headers: Mapping[str, str] | None = None,
        background: Task | None = None,
        encoders: Sequence[Encoder | type[Encoder]] | None = None,
    ) -> None:
        super().__init__(
            content=b"",
            status_code=status_code,
            headers=headers,
            background=background,
            encoders=encoders,
        )
        self.headers["location"] = quote(str(url), safe=":/%#?=@[]!$&'()*+,;")


class StreamingResponse(Response):
    body_iterator: AsyncContentStream
    deduce_media_type_from_body: bool = False

    def __init__(
        self,
        content: ContentStream,
        status_code: int = status.HTTP_200_OK,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: Task | None = None,
        encoders: Sequence[Encoder | type[Encoder]] | None = None,
    ) -> None:
        self.encoders: list[Encoder] = [
            encoder() if isclass(encoder) else encoder for encoder in encoders or _empty
        ]

        if isinstance(content, AsyncIterable):
            self.body_iterator = content
        else:
            self.body_iterator = iterate_in_threadpool(content)
        self.status_code = status_code
        if media_type is not None:
            self.media_type = media_type
        self.background = background
        self.make_headers(headers)

    async def wait_for_disconnect(self, receive: Receive) -> None:
        while True:
            message = await receive()
            if message["type"] == Event.HTTP_DISCONNECT:
                break

    async def stream(self, send: Send) -> None:
        last_chunk: bytes | None = None
        # save one round-trip by delaying sending of chunk
        async for chunk in self.body_iterator:
            if last_chunk is not None:
                await send({"type": "http.response.body", "body": last_chunk, "more_body": True})
            if not isinstance(chunk, bytes):
                chunk = chunk.encode(self.charset)
            last_chunk = chunk

        await send({"type": "http.response.body", "body": last_chunk or b"", "more_body": False})

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        prefix = "websocket." if scope["type"] == "websocket" else ""
        await send(self.message(prefix=prefix))
        # for options and head, we certainly don't want to execute the stream when requesting options
        send_header_only = "method" in scope and scope["method"].upper() in {
            HTTPMethod.HEAD,
            HTTPMethod.OPTIONS,
        }
        try:
            if send_header_only:
                # no background execution
                return
            async with anyio.create_task_group() as task_group:

                async def wrap(func: Callable[[], Awaitable[None]]) -> None:
                    await func()
                    task_group.cancel_scope.cancel()

                task_group.start_soon(wrap, functools.partial(self.stream, send))
                await wrap(functools.partial(self.wait_for_disconnect, receive))
        finally:
            await self.execute_cleanup_handler()

        if self.background is not None:
            await self.background()

    def make_response(self, content: Any) -> bytes:
        """
        This function is not implemented here
        """
        raise NotImplementedError(
            "`StreamingResponse` doesn't implement `make_response` use stream instead"
        )


class EventStreamResponse(Response):
    """
    A fully AnyIO-native Server-Sent Events (SSE) streaming response for Lilya.

    This response allows an application to stream real-time events over
    HTTP using the standard `text/event-stream` format. It supports both
    synchronous and asynchronous iterables as content sources, automatic
    keep-alive pings, per-event timeouts, graceful shutdown, and client
    disconnect detection.

    Typical usage:
        ```python
        async def event_source():
            for i in range(3):
                yield {"event": "tick", "data": i}
                await anyio.sleep(1)

        return EventStreamResponse(event_source(), ping_interval=15)
        ```

    Features:
        * Works with async and sync iterables
        * Sends periodic ping comments to keep connections alive
        * Supports per-event send timeouts (in seconds)
        * Detects and handles client disconnects
        * Gracefully shuts down the stream when complete
    """

    DEFAULT_PING_INTERVAL = 15
    DEFAULT_SEPARATOR = "\n"
    media_type = "text/event-stream"
    deduce_media_type_from_body: bool = False

    def __init__(
        self,
        content: AsyncIterable[dict[str, Any]] | Iterable[dict[str, Any]],
        *,
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        media_type: str = "text/event-stream",
        background: Task | None = None,
        retry: int | None = None,
        ping_interval: float | None = None,
        separator: str | None = None,
        ping_message_factory: Callable[[], dict[str, Any]] | None = None,
        send_timeout: float | None = None,
        data_sender_callable: Callable[[], Coroutine[None, None, None]] | None = None,
        client_close_handler: Callable[[Message], Awaitable[None]] | None = None,
    ) -> None:
        """
        Initialize a new EventStreamResponse.

        Args:
            content: An async or sync iterable yielding event dictionaries.
            status_code: HTTP status code (defaults to 200).
            headers: Optional mapping of additional response headers.
            media_type: MIME type of the response (always `text/event-stream`).
            background: Optional background task to execute after completion.
            retry: Default reconnect interval in milliseconds for the client.
            ping_interval: Interval (in seconds) between keep-alive pings.
            separator: Line separator used between event fields.
            ping_message_factory: Optional callable that returns a custom ping event.
            send_timeout: Maximum time (in seconds) allowed to send each event.
            data_sender_callable: Optional coroutine started in the same task group.
            client_close_handler: Async callable invoked when the client disconnects.

        Raises:
            ValueError: If `separator` is not one of ``\\n``, ``\\r``, or ``\\r\\n``.
        """
        if separator not in (None, "\r\n", "\r", "\n"):
            raise ValueError(f"sep must be one of: \\r\\n, \\r, \\n, got: {separator}")
        self.sep = separator or self.DEFAULT_SEPARATOR
        self.retry = retry

        # Normalize the content generator
        if inspect.isasyncgen(content) or isinstance(content, AsyncIterable):

            async def async_bytes_gen() -> AsyncIterable[bytes]:
                async for event in content:
                    yield self._encode_event(event)

            self.body_iterator = async_bytes_gen()
        else:

            async def sync_bytes_gen() -> AsyncIterable[bytes]:
                for event in content:
                    yield self._encode_event(event)

            self.body_iterator = sync_bytes_gen()

        self.status_code = status_code
        self.media_type = media_type or self.media_type
        self.background = background
        self.ping_message_factory = ping_message_factory
        self.ping_interval = (
            ping_interval if ping_interval is not None else self.DEFAULT_PING_INTERVAL
        )
        self.send_timeout = send_timeout  # seconds
        self._timeout_for_log = send_timeout
        self.data_sender_callable = data_sender_callable
        self.client_close_handler = client_close_handler
        self.active = True
        self._send_lock = anyio.Lock()

        # Nginx/Proxy-safe headers
        default_headers = {
            "cache-control": "no-cache",
            "connection": "keep-alive",
            "content-type": "text/event-stream",
            "x-accel-buffering": "no",
            "transfer-encoding": "chunked",
        }
        if headers:
            default_headers.update(headers)

        default_headers.pop("content-length", None)

        super().__init__(
            content=None,
            status_code=status_code,
            headers=default_headers,
            media_type=self.media_type,
            background=background,
        )
        self.headers["content-type"] = "text/event-stream"
        self.headers.pop("content-length", None)

    async def _send_chunk(self, send: Send, data: str | bytes) -> None:
        """
        Send a single SSE chunk to the client, respecting the send timeout.

        Args:
            send: ASGI send callable.
            data: The already-encoded event string or bytes.

        Raises:
            TimeoutError: If sending the chunk exceeds the configured timeout.
        """
        if isinstance(data, bytes):
            payload = data
        else:
            if not data.endswith("\n\n"):
                data += "\n\n"
            payload = data.encode("utf-8")

        try:
            if self.send_timeout is not None:
                with anyio.fail_after(self.send_timeout):
                    await send({"type": "http.response.body", "body": payload, "more_body": True})
            else:
                await send({"type": "http.response.body", "body": payload, "more_body": True})
        except TimeoutError as exc:
            raise TimeoutError("SSE send timed out") from exc

    async def _stream_response(self, send: Send) -> None:
        """
        Stream encoded events from the source iterable to the client.

        This coroutine drives the main SSE data flow:
        it encodes events, enforces per-event timeouts,
        and stops cleanly when iteration ends or a timeout occurs.

        Args:
            send: ASGI send callable.

        Raises:
            TimeoutError: If event emission or transmission times out.
        """
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": self.raw_headers,
            }
        )

        aiter_obj = self.body_iterator.__aiter__()

        try:
            while True:
                try:
                    if self.send_timeout is not None:
                        with anyio.fail_after(self.send_timeout):
                            event_bytes = await aiter_obj.__anext__()
                    else:
                        event_bytes = await aiter_obj.__anext__()
                except StopAsyncIteration:
                    break
                except TimeoutError:
                    msg = (
                        f"SSE send timed out after {self._timeout_for_log:.3f}s"
                        if self._timeout_for_log
                        else "SSE send timed out"
                    )
                    logger.warning(msg)
                    self.active = False
                    async with self._send_lock:
                        await send(
                            {
                                "type": "http.response.body",
                                "body": b"",
                                "more_body": False,
                            }
                        )
                    raise TimeoutError("SSE send timed out") from None
                except anyio.get_cancelled_exc_class():
                    self.active = False
                    async with self._send_lock:
                        await send(
                            {
                                "type": "http.response.body",
                                "body": b"",
                                "more_body": False,
                            }
                        )
                    raise TimeoutError("SSE send timed out") from None

                # Send the encoded event as a body chunk
                await self._send_chunk(send, event_bytes)

        finally:
            # Always end cleanly for proxies
            async with self._send_lock:
                await send(
                    {
                        "type": "http.response.body",
                        "body": b"",
                        "more_body": False,
                    }
                )
            self.active = False

    async def _ping(self, send: Send) -> None:
        """
        Periodically send SSE ping comments to maintain the connection.

        Runs concurrently with the main streaming loop.
        Automatically stops when the stream becomes inactive.

        Args:
            send: ASGI send callable.
        """
        if not self.ping_interval:
            return

        try:
            ping_event = (
                self.ping_message_factory() if self.ping_message_factory else {":": "ping"}
            )
            await self._send_chunk(send, self._encode_event(ping_event))
            await anyio.sleep(0)

            while self.active:
                await anyio.sleep(self.ping_interval)
                if not self.active:
                    break
                ping_event = (
                    self.ping_message_factory() if self.ping_message_factory else {":": "ping"}
                )
                await self._send_chunk(send, self._encode_event(ping_event))
        except Exception:
            ...

    async def _listen_for_disconnect(
        self, receive: Receive, cancel_scope: anyio.CancelScope | None = None
    ) -> None:
        """
        Listen for client disconnect messages and trigger cancellation.

        If a message with ``type == "http.disconnect"`` is received,
        the stream is marked inactive, the optional
        ``client_close_handler`` is invoked, and all running tasks
        in the current AnyIO task group are cancelled.

        Args:
            receive: ASGI receive callable.
            cancel_scope: Optional AnyIO cancel scope controlling this group.
        """
        try:
            while self.active:
                message = await receive()
                if message.get("type") == "http.disconnect":
                    self.active = False
                    if self.client_close_handler:
                        try:
                            await self.client_close_handler(message)
                        except Exception:
                            logger.exception("Error in client_close_handler()")
                    if cancel_scope:
                        cancel_scope.cancel()
                    return
        except anyio.get_cancelled_exc_class():
            return

    async def _listen_for_exit_signal(self) -> None:
        """
        ASGI entrypoint.

        Runs the SSE streaming loop, ping task, and disconnect listener
        concurrently in an AnyIO task group. Ensures that all tasks
        are cancelled together on completion, timeout, or disconnect.

        Args:
            scope: ASGI scope dictionary.
            receive: ASGI receive callable.
            send: ASGI send callable.
        """
        try:
            await anyio.sleep_forever()
        except anyio.get_cancelled_exc_class():
            return

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Entrypoint for Lilya's ASGI contract.
        Runs the SSE stream, listens for disconnects, and ensures graceful teardown.
        """
        async with anyio.create_task_group() as tg:

            async def run_stream() -> None:
                try:
                    await self._stream_response(send)
                    # Short grace window for final disconnects
                    with anyio.move_on_after(0.05):
                        await anyio.sleep(0.05)
                finally:
                    tg.cancel_scope.cancel()

            tg.start_soon(run_stream)

            tg.start_soon(self._ping, send)
            tg.start_soon(self._listen_for_disconnect, receive, tg.cancel_scope)
            tg.start_soon(self._listen_for_exit_signal)

            if self.data_sender_callable:
                tg.start_soon(self.data_sender_callable)

        if self.background:
            await self.background()

    def _encode_event(self, event: dict[str, Any] | bytes) -> bytes:
        """
        Encode a single event dictionary into the text/event-stream format.

        Args:
            event: A mapping containing optional fields:
                ``id``, ``event``, ``data``, ``retry``, or ``:`` for comments.

        Returns:
            Encoded UTF-8 bytes ready to send to the client.
        """
        if isinstance(event, bytes):
            return event

        lines: list[str] = []

        if ":" in event:
            lines.append(f": {event[':']}")

        if "id" in event:
            lines.append(f"id: {event['id']}")
        if "event" in event:
            lines.append(f"event: {event['event']}")
        if "data" in event:
            data = event["data"]
            if isinstance(data, (dict, list)):
                data = serializer.dumps(data, separators=(", ", ": "))
            lines.append(f"data: {data}")
        if "retry" in event or self.retry:
            retry = event.get("retry", self.retry)
            if retry is not None:
                lines.append(f"retry: {retry}")

        return (self.sep.join(lines) + self.sep * 2).encode("utf-8")


class FileResponse(DispositionResponse):
    chunk_size = 64 * 1024
    deduce_media_type_from_body: bool = False

    def __init__(
        self,
        path: str | os.PathLike[str] | FileIO,
        status_code: int = status.HTTP_200_OK,
        headers: typing.Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: Task | None = None,
        filename: str | None = None,
        stat_result: os.stat_result | None = None,
        method: str | None = None,
        content_disposition_type: str | None = None,
        encoders: Sequence[Encoder | type[Encoder]] | None = None,
        deduce_media_type_from_body: bool = False,
        allow_range_requests: bool = True,
        range_multipart_boundary: bool | str = False,
    ) -> None:
        if method:
            warnings.warn(
                '"method" parameter is obsolete. It is now automatically deduced.', stacklevel=2
            )
        try:
            self.path = os.fspath(cast(Any, path))
        except TypeError:
            if getattr(cast(Any, path), "name", None):
                self.path = cast(FileIO, path).name
        # use path not self.path which is a string
        if hasattr(path, "aclose"):
            self.cleanup_handler = path.aclose
        elif hasattr(path, "close"):
            self.cleanup_handler = path.close
        self.deduce_media_type_from_body = deduce_media_type_from_body
        self.status_code = status_code
        self.allow_range_requests = allow_range_requests
        if not allow_range_requests:
            range_multipart_boundary = False
        self.range_multipart_boundary = range_multipart_boundary
        self.content_disposition_type = content_disposition_type
        self.filename = filename
        if media_type is None:
            # by default it must be octet
            media_type = self.find_media_type()
        self.media_type = media_type
        self.background = background

        self.encoders: list[Encoder] = [
            encoder() if isclass(encoder) else encoder for encoder in encoders or _empty
        ]
        self.make_headers(headers)

        if self.allow_range_requests:
            self.headers["accept-ranges"] = "bytes"

        self.stat_result = stat_result
        if stat_result is not None:
            self.set_stat_headers(stat_result)

    def find_media_type(self) -> str:
        if self.deduce_media_type_from_body:
            require_magic()
            return magic.from_file(self.path, mime=True)
        return guess_type(self.filename or self.path)[0] or MediaType.OCTET

    def make_boundary(self) -> str:
        return f"{time.time()}-{self.headers['etag']}"

    def set_stat_headers(self, stat_result: os.stat_result) -> None:
        content_length = str(stat_result.st_size)
        last_modified = formatdate(stat_result.st_mtime, usegmt=True)
        etag_base = str(stat_result.st_mtime) + "-" + str(stat_result.st_size)
        etag = md5_hexdigest(etag_base.encode(), usedforsecurity=False)

        self.headers.setdefault("content-length", content_length)
        self.headers.setdefault("last-modified", last_modified)
        self.headers.setdefault("etag", etag)

    def check_if_range(self, scope: Scope) -> bool:
        """Is the if-range matching and the byte ranges are valid?"""
        received_headers = Header.ensure_header_instance(scope)
        if_range: str = received_headers.get("if-range", "")
        # succeeds if_range is matching or empty
        return not if_range or if_range == cast(str, self.headers["etag"])

    def get_content_ranges_and_multipart(
        self, scope: Scope, /, **kwargs: Any
    ) -> tuple[ContentRanges | None, bool]:
        received_headers = Header.ensure_header_instance(scope)
        range_header = received_headers.get("range", "")
        kwargs.setdefault("max_values", int(self.headers["content-length"]) - 1)
        # limit to maximal 5 requested ranges for security reasons
        kwargs.setdefault("max_ranges", 5 if self.range_multipart_boundary else 1)
        content_ranges = parse_range_value(range_header, **kwargs)
        if content_ranges is None or not content_ranges.ranges:
            return None, False
        # comma counting ensures no single range response is send for a multirange request
        # overwrites are free to use a different logic or enforcing multipart/single range responses
        return content_ranges, "," in range_header

    def set_range_headers(
        self,
        scope: Scope,
        *,
        provided_ranges_and_multipart: tuple[ContentRanges | None, bool] | None = None,
    ) -> ContentRanges | None:
        if provided_ranges_and_multipart:
            content_ranges, use_multipart_response = provided_ranges_and_multipart
        else:
            content_ranges, use_multipart_response = self.get_content_ranges_and_multipart(scope)
        if content_ranges is None:
            return None
        if use_multipart_response and not self.range_multipart_boundary:
            return None

        if use_multipart_response:
            if self.range_multipart_boundary is True:
                self.range_multipart_boundary = self.make_boundary()
            self.headers["content-type"] = (
                f"multipart/byteranges; boundary={self.range_multipart_boundary}"
            )
        else:
            assert content_ranges.ranges, (
                "Empty content ranges are not supported for single range responses."
            )
            # allow conversion in a single range, when the client supports this.
            if len(content_ranges.ranges) > 1:
                new_range = Range(
                    start=content_ranges.ranges[0].start, stop=content_ranges.ranges[-1].stop
                )
                new_size = new_range.stop - new_range.start + 1
                content_ranges.ranges = [new_range]
                content_ranges.size = new_size
            self.headers["content-range"] = (
                f"bytes {content_ranges.ranges[0].start}-{content_ranges.ranges[0].stop}/{content_ranges.max_value + 1}"
            )
        self.headers["content-length"] = f"{content_ranges.size}"
        self.status_code = status.HTTP_206_PARTIAL_CONTENT
        return content_ranges

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self.stat_result is None:
            try:
                stat_result = await anyio.to_thread.run_sync(os.stat, self.path)
                self.set_stat_headers(stat_result)
            except FileNotFoundError:
                raise RuntimeError(f"File at path {self.path} does not exist.") from None
            else:
                mode = stat_result.st_mode
                if not stat.S_ISREG(mode):
                    raise RuntimeError(f"File at path {self.path} is not a file.") from None

        # for options and head, we certainly don't want to send the file when requesting options
        send_header_only = "method" in scope and scope["method"].upper() in {
            HTTPMethod.HEAD,
            HTTPMethod.OPTIONS,
        }
        prefix = "websocket." if scope["type"] == "websocket" else ""
        content_ranges: ContentRanges | None = None
        if not send_header_only and self.allow_range_requests and self.check_if_range(scope):
            content_ranges = self.set_range_headers(scope)
        await send(self.message(prefix=prefix))

        try:
            if send_header_only:
                # no background execution
                return

            ranges = (
                [Range(start=0, stop=int(self.headers["content-length"]) - 1)]
                if content_ranges is None
                else content_ranges.ranges
            )
            subheader: str = ""
            if content_ranges and "content-range" not in self.headers:
                # TODO: check if there is a better way to escape media_type
                media_type = self.media_type.replace(" ", "").replace("\n", "")
                subheader = (
                    f"--{self.range_multipart_boundary}\ncontent-type: {media_type}\n"
                    "content-range: bytes {start}-{stop}/{fullsize}\n\n"
                )

            extensions = scope.get("extensions", {})
            if content_ranges is None and "http.response.pathsend" in extensions:
                await send({"type": "http.response.pathsend", "path": self.path})
            elif "http.response.zerocopysend" in extensions:
                async with await anyio.open_file(self.path, mode="rb") as file:
                    last_stop = 0
                    for rangedef in ranges:
                        if last_stop != rangedef.start:
                            await file.seek(rangedef.start, os.SEEK_SET)
                        size = rangedef.stop - rangedef.start + 1
                        if subheader:
                            await send(
                                {
                                    "type": "http.response.body",
                                    "body": subheader.format(
                                        start=rangedef.start,
                                        stop=rangedef.stop,
                                        fullsize=content_ranges.max_value + 1,
                                    ).encode(),
                                    "more_body": True,
                                }
                            )
                        more_chunks = True
                        while more_chunks:
                            more_chunks = size > self.chunk_size
                            count = self.chunk_size
                            if not more_chunks:
                                count = size
                            await send(
                                {
                                    "type": "http.response.zerocopysend",
                                    "file": file.fileno(),  # type: ignore
                                    "count": count,
                                    "more_body": bool(more_chunks or subheader),
                                }
                            )
                            size -= count
                        last_stop = rangedef.stop
                # subheader = more than 1 range
                if subheader:
                    await send(
                        {
                            "type": "http.response.body",
                            "body": b"",
                            "more_body": False,
                        }
                    )
            else:
                async with await anyio.open_file(self.path, mode="rb") as file:
                    last_stop = 0
                    for rangedef in ranges:
                        if last_stop != rangedef.start:
                            await file.seek(rangedef.start, os.SEEK_SET)
                        size = rangedef.stop - rangedef.start + 1
                        if subheader:
                            await send(
                                {
                                    "type": "http.response.body",
                                    "body": subheader.format(
                                        start=rangedef.start,
                                        stop=rangedef.stop,
                                        fullsize=content_ranges.max_value + 1,
                                    ).encode(),
                                    "more_body": True,
                                }
                            )
                        more_chunks = True
                        while more_chunks:
                            more_chunks = size > self.chunk_size
                            count = self.chunk_size
                            if not more_chunks:
                                count = size
                            await send(
                                {
                                    "type": "http.response.body",
                                    "body": await file.read(count),
                                    "more_body": bool(more_chunks or subheader),
                                }
                            )
                            size -= count
                        last_stop = rangedef.stop
                    # subheader = more than 1 range
                    if subheader:
                        await send(
                            {
                                "type": "http.response.body",
                                "body": b"",
                                "more_body": False,
                            }
                        )
        finally:
            await self.execute_cleanup_handler()

        if self.background is not None:
            await self.background()


class SimpleFileResponse(Response):
    """A simplified FileResponse which allows sending arbitary data formats as file."""

    def __new__(
        cls,
        content: bytes | memoryview | os.PathLike | str | IO[bytes] | FileIO,
        *,
        filename: str | None = None,
        status_code: int = status.HTTP_200_OK,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: Task | None = None,
        content_disposition_type: str = "inline",
        deduce_media_type_from_body: bool | None = None,
        allow_range_requests: bool = True,
        range_multipart_boundary: bool | str = False,
    ) -> Response:
        if (
            isinstance(content, str)
            or hasattr(content, "__fspath__")
            or getattr(content, "name", None)
        ):
            return FileResponse(
                path=cast("str | os.PathLike | FileIO", content),
                filename=filename,
                status_code=status_code,
                headers=headers,
                media_type=media_type,
                background=background,
                content_disposition_type=content_disposition_type,
                deduce_media_type_from_body=deduce_media_type_from_body
                if deduce_media_type_from_body is not None
                else False,
                allow_range_requests=allow_range_requests,
                range_multipart_boundary=range_multipart_boundary,
            )
        elif isinstance(content, bytes | memoryview):
            return DispositionResponse(
                content=content,
                filename=filename,
                status_code=status_code,
                headers=headers,
                media_type=media_type,
                background=background,
                content_disposition_type=content_disposition_type,
                deduce_media_type_from_body=deduce_media_type_from_body
                if deduce_media_type_from_body is not None
                else True,
            )
        else:
            # close filedescriptors in case of anonymous, nameless files
            cleanup_handler = None
            if hasattr(content, "aclose"):
                cleanup_handler = content.aclose
            elif hasattr(content, "close"):
                cleanup_handler = content.close
            content_disposition = DispositionResponse.make_content_disposition_header(
                content_disposition_type=content_disposition_type,
                filename=filename,
            )
            if content_disposition is not None:
                headers = {} if headers is None else headers.copy()
                headers.setdefault("content-disposition", content_disposition)

            response = StreamingResponse(
                content=content,
                status_code=status_code,
                headers=headers,
                media_type=media_type,
                background=background,
            )
            response.cleanup_handler = cleanup_handler
            return response


ImageResponse = SimpleFileResponse


class TemplateResponse(HTMLResponse):
    render_function_name: str = "render"

    def __init__(
        self,
        template: Any,
        status_code: int = status.HTTP_200_OK,
        context: dict[str, Any] | None = None,
        background: Task | None = None,
        headers: dict[str, Any] | None = None,
        media_type: MediaType | str = MediaType.HTML,
        encoders: Sequence[Encoder | type[Encoder]] | None = None,
        passthrough_body_types: tuple[type, ...] | None = None,
        render_function_name: str | None = None,
    ):
        if render_function_name:
            self.render_function_name = render_function_name
        self.template = template
        self.context = context or {}
        content = getattr(self.template, self.render_function_name)(context)
        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
            encoders=encoders,
            passthrough_body_types=passthrough_body_types,
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        request = self.context.get("request", {})
        extensions = request.get("extensions", {})
        if "http.response.debug" in extensions:
            await send(
                {
                    "type": "http.response.debug",
                    "info": {"template": self.template, "context": self.context},
                }
            )
        await super().__call__(scope, receive, send)


class CSVResponse(StreamingResponse):
    media_type = "text/csv"
    body_iterator: AsyncIterable[Mapping[str, Any]]  # type: ignore

    def __init__(
        self,
        content: AsyncIterable[Mapping[str, Any]] | Iterable[Mapping[str, Any]] | None = None,
        status_code: int = status.HTTP_200_OK,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: Task | None = None,
        encoders: Sequence[Encoder | type[Encoder]] | None = None,
    ) -> None:
        if content is None:
            content = _empty
        super().__init__(
            content=cast(Any, content),
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
            encoders=encoders,
        )

    async def stream(self, send: Send) -> None:
        try:
            row1 = await self.body_iterator.__anext__()
        except StopAsyncIteration:
            await send({"type": "http.response.body", "body": b"", "more_body": False})
            return
        headers = row1.keys()
        await send(
            {
                "type": "http.response.body",
                "body": f"{','.join(headers)}\n".encode(self.charset),
                "more_body": True,
            }
        )
        # send content
        last_row = row1
        async for row in self.body_iterator:
            # send last_row with \n
            await send(
                {
                    "type": "http.response.body",
                    "body": f"{','.join(str(last_row.get(h, '')) for h in headers)}\n".encode(
                        self.charset
                    ),
                    "more_body": True,
                }
            )
            last_row = row
        # send really last row without newline
        await send(
            {
                "type": "http.response.body",
                "body": f"{','.join(str(last_row.get(h, '')) for h in headers)}".encode(
                    self.charset
                ),
                "more_body": False,
            }
        )


class XMLResponse(Response):
    media_type = "application/xml"

    def make_response(self, content: Any) -> bytes:
        """
        Converts a Python object (dict, list, str, bytes) to an XML formatted byte string.

        Args:
            content (Any): The content to be converted to XML.
        """
        if content is None:
            return b""

        if isinstance(content, (bytes, bytearray)):
            return bytes(content)

        if isinstance(content, str):
            return content.encode(self.charset)

        def to_xml(value: Any, tag: str) -> Any:
            # For dict: recurse into children
            if isinstance(value, dict):
                inner = "".join(to_xml(v, k) for k, v in value.items())
                return f"<{tag}>{inner}</{tag}>"

            # For list: repeat same tag for each element
            elif isinstance(value, list):
                return "".join(to_xml(item, tag) for item in value)
            else:
                return f"<{tag}>{value}</{tag}>"

        # When top-level is a dict, wrap each key directly
        if isinstance(content, dict):
            xml_str = "".join(to_xml(v, k) for k, v in content.items())
            xml_str = f"<root>{xml_str}</root>"

        # When top-level is a list, wrap each item in <root>
        elif isinstance(content, list):
            xml_str = "".join(to_xml(item, "root") for item in content)
        else:
            xml_str = f"<root>{content}</root>"

        return xml_str.encode(self.charset)


class YAMLResponse(Response):
    media_type = "application/x-yaml"

    def make_response(self, content: Any) -> bytes:
        """
        Converts a Python object to a YAML formatted byte string.

        Args:
            content (Any): The content to be converted to YAML.
        """
        if content is None:
            return b""
        return cast(bytes, yaml.safe_dump(content, sort_keys=False).encode(self.charset))


class MessagePackResponse(Response):
    media_type = "application/x-msgpack"

    def make_response(self, content: Any) -> bytes:
        """
        Converts a Python object to a MessagePack formatted byte string.
        """
        if content is None:
            return b""
        return cast(bytes, msgpack.packb(content, use_bin_type=True))


class NDJSONResponse(StreamingResponse):
    media_type = "application/x-ndjson"
    body_iterator: AsyncIterable[Any]

    def __init__(
        self,
        content: AsyncIterable[Any] | Iterable[Any] | None = None,
        status_code: int = status.HTTP_200_OK,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: Task | None = None,
        encoders: Sequence[Encoder | type[Encoder]] | None = None,
    ) -> None:
        if content is None:
            content = _empty
        super().__init__(
            content=cast(Any, content),
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
            encoders=encoders,
        )

    async def stream(self, send: Send) -> None:
        """
        Converts an iterable of dictionaries to a NDJSON formatted byte string.
        """
        last_row: bytes | None = None

        new_params = RESPONSE_TRANSFORM_KWARGS.get()
        if new_params:
            new_params = new_params.copy()
        else:
            new_params = {}
        new_params["post_transform_fn"] = None
        if self.encoders:
            new_params["with_encoders"] = (*self.encoders, *ENCODER_TYPES.get())
        async for row in self.body_iterator:
            if last_row is not None:
                await send(
                    {
                        "type": "http.response.body",
                        "body": b"%b\n" % last_row,
                        "more_body": True,
                    }
                )
            content = json_encode(row, **new_params)
            if isinstance(content, (bytearray, memoryview)):
                content = bytes(content)
            elif isinstance(content, str):
                content = content.encode(self.charset)
            last_row = content
        if last_row is not None:
            await send(
                {
                    "type": "http.response.body",
                    "body": last_row,
                    "more_body": False,
                }
            )
        else:
            await send({"type": "http.response.body", "body": b"", "more_body": False})


def make_response(
    content: Any,
    response_class: type[Response] = JSONResponse,
    status_code: int = status.HTTP_200_OK,
    headers: Mapping[str, str] | None = None,
    background: Task | None = None,
    encoders: Sequence[Encoder | type[Encoder]] | None = None,
    json_encode_extra_kwargs: dict | None = None,  # noqa: B006
) -> Response:
    """
    Build JSON responses from a given content and
    providing extra parameters.
    """
    if json_encode_extra_kwargs is None:
        json_encode_extra_kwargs = {}

    with response_class.with_transform_kwargs(json_encode_extra_kwargs):
        return response_class(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type=MediaType.JSON,
            background=background,
            encoders=encoders,
        )
