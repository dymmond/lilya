from __future__ import annotations

import contextlib
import functools
import http.cookies
import json
import os
import stat
import time
import typing
import warnings
from collections.abc import (
    AsyncIterable,
    Awaitable,
    Callable,
    Generator,
    Iterable,
    Mapping,
    Sequence,
)
from contextvars import ContextVar
from datetime import datetime
from email.utils import format_datetime, formatdate
from inspect import isawaitable, isclass
from mimetypes import guess_type
from typing import (
    Any,
    Literal,
    NoReturn,
    cast,
)
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
from lilya.ranges import ContentRanges, Range, parse_range_value
from lilya.types import Receive, Scope, Send

Content = str | bytes
Encoder = EncoderProtocol | MoldingProtocol
SyncContentStream = Iterable[Content]
AsyncContentStream = AsyncIterable[Content]
ContentStream = AsyncContentStream | SyncContentStream

_empty: tuple[Any, ...] = ()

RESPONSE_TRANSFORM_KWARGS: ContextVar[dict | None] = ContextVar(
    "RESPONSE_TRANSFORM_KWARGS", default=None
)


class Response:
    media_type: str | None = None
    status_code: int | None = None
    charset: str = "utf-8"
    # should be at least bytes. Ensures that no unsupported types are passed to the application server
    # uvicorn would allow also body memoryview and bytearray
    passthrough_body_types: tuple[type, ...] = (bytes,)
    headers: Header

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
    ) -> None:
        if passthrough_body_types is not None:
            self.passthrough_body_types = passthrough_body_types
        if status_code is not None:
            self.status_code = status_code
        if media_type is not None:
            self.media_type = media_type
        self.background = background
        self.cookies = cookies
        self.encoders: list[Encoder] = [
            encoder() if isclass(encoder) else encoder for encoder in encoders or _empty
        ]
        if isawaitable(content):
            self.async_content = content
        else:
            self.body = self.make_response(content)
        self.make_headers(headers)

    async def resolve_async_content(self) -> None:
        if getattr(self, "async_content", None) is not None:
            self.body = self.make_response(await self.async_content)
            self.async_content = None
            if (
                HeaderHelper.has_body_message(self.status_code)
                and "content-length" not in self.headers
            ):
                self.headers["content-length"] = str(len(self.body))

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
            content_type = HeaderHelper.get_content_type(
                charset=self.charset, media_type=self.media_type
            )
            if getattr(self, "body", None) is not None:
                headers.setdefault("content-length", str(len(self.body)))

            # Populates the content type if exists
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
        prefix = "websocket." if scope["type"] == "websocket" else ""
        await self.resolve_async_content()
        await send(self.message(prefix=prefix))
        # should be mutation free for both methods
        mutation_free = "method" in scope and scope["method"].upper() in {
            HTTPMethod.HEAD,
            HTTPMethod.OPTIONS,
        }

        # don't interfere, in case of bodyless requests like head the message is ignored.
        await send({"type": f"{prefix}http.response.body", "body": self.body})

        if self.background is not None and not mutation_free:
            await self.background()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(media_type={self.media_type}, status_code={self.status_code}, charset={self.charset})"


class HTMLResponse(Response):
    media_type = MediaType.HTML


class Error(HTMLResponse):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class PlainText(Response):
    media_type = MediaType.TEXT


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
        new_params.setdefault(
            "json_encode_fn",
            functools.partial(
                json.dumps,
                ensure_ascii=False,
                allow_nan=False,
                indent=None,
                separators=(",", ":"),
            ),
        )
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
        status_code: int = status.HTTP_307_TEMPORARY_REDIRECT,
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
        self.media_type = self.media_type if media_type is None else media_type
        self.background = background
        self.make_headers(headers)

    async def wait_for_disconnect(self, receive: Receive) -> None:
        while True:
            message = await receive()
            if message["type"] == Event.HTTP_DISCONNECT:
                break

    async def stream(self, send: Send) -> None:
        async for chunk in self.body_iterator:
            if not isinstance(chunk, bytes):
                chunk = chunk.encode(self.charset)
            await send({"type": "http.response.body", "body": chunk, "more_body": True})

        await send({"type": "http.response.body", "body": b"", "more_body": False})

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        prefix = "websocket." if scope["type"] == "websocket" else ""
        await send(self.message(prefix=prefix))
        # for options and head, we certainly don't want to execute the stream when requesting options
        send_header_only = "method" in scope and scope["method"].upper() in {
            HTTPMethod.HEAD,
            HTTPMethod.OPTIONS,
        }

        if send_header_only:
            # no background execution
            return
        async with anyio.create_task_group() as task_group:

            async def wrap(func: Callable[[], Awaitable[None]]) -> None:
                await func()
                task_group.cancel_scope.cancel()

            task_group.start_soon(wrap, functools.partial(self.stream, send))
            await wrap(functools.partial(self.wait_for_disconnect, receive))

        if self.background is not None:
            await self.background()


class FileResponse(Response):
    chunk_size = 64 * 1024

    def __init__(
        self,
        path: str | os.PathLike[str],
        status_code: int = status.HTTP_200_OK,
        headers: typing.Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: Task | None = None,
        filename: str | None = None,
        stat_result: os.stat_result | None = None,
        method: str | None = None,
        content_disposition_type: str = "attachment",
        encoders: Sequence[Encoder | type[Encoder]] | None = None,
        allow_range_requests: bool = True,
        range_multipart_boundary: bool | str = False,
    ) -> None:
        if method:
            warnings.warn(
                '"method" parameter is obsolete. It is now automatically deduced.', stacklevel=2
            )
        self.path = path
        self.status_code = status_code
        self.allow_range_requests = allow_range_requests
        if not allow_range_requests:
            range_multipart_boundary = False
        self.range_multipart_boundary = range_multipart_boundary
        self.filename = filename
        if media_type is None:
            # by default it must be octet
            media_type = guess_type(filename or path)[0] or MediaType.OCTET
        self.media_type = media_type
        self.background = background

        self.encoders: list[Encoder] = [
            encoder() if isclass(encoder) else encoder for encoder in encoders or _empty
        ]
        self.make_headers(headers)

        if self.allow_range_requests:
            self.headers["accept-ranges"] = "bytes"

        if self.filename is not None:
            content_disposition_filename = quote(self.filename)
            if content_disposition_filename != self.filename:
                content_disposition = (
                    f"{content_disposition_type}; filename*=utf-8''{content_disposition_filename}"
                )
            else:
                content_disposition = f'{content_disposition_type}; filename="{self.filename}"'
            self.headers.setdefault("content-disposition", content_disposition)
        self.stat_result = stat_result
        if stat_result is not None:
            self.set_stat_headers(stat_result)

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
        if self.background is not None:
            await self.background()


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


def make_response(
    content: Any,
    response_class: type[Response] = JSONResponse,
    status_code: int = status.HTTP_200_OK,
    headers: Mapping[str, str] | None = None,
    background: Task | None = None,
    encoders: Sequence[Encoder | type[Encoder]] | None = None,
    # passing mutables as default argument is not a good style but here is no other way
    json_encode_extra_kwargs: dict | None = {},  # noqa: B006
) -> Response:
    """
    Build JSON responses from a given content and
    providing extra parameters.
    """
    with response_class.with_transform_kwargs(json_encode_extra_kwargs):
        return response_class(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type=MediaType.JSON,
            background=background,
            encoders=encoders,
        )


def redirect(
    url: str | URL,
    status_code: int = status.HTTP_307_TEMPORARY_REDIRECT,
    headers: Mapping[str, str] | None = None,
    background: Task | None = None,
    encoders: Sequence[Encoder | type[Encoder]] | None = None,
) -> RedirectResponse:
    """
    Redirect to a different URL.

    Args:
        url (Union[str, URL]): The URL to redirect to.
        status_code (int, optional): The status code of the redirect response (default is 307).
        headers (Union[Mapping[str, str], None], optional): Additional headers to include (default is None).
        background (Union[Task, None], optional): A background task to run (default is None).
        encoders (Union[Sequence[Encoder | type[Encoder]], None], optional): A sequence of encoders to use (default is None).

    Returns:
        RedirectResponse: A response object that redirects to the given URL.
    """
    return RedirectResponse(
        url=url,
        status_code=status_code,
        headers=headers,
        background=background,
        encoders=encoders,
    )
