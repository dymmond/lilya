from __future__ import annotations

import functools
import http.cookies
import json
import os
import stat
import typing
from datetime import datetime
from email.utils import format_datetime, formatdate
from mimetypes import guess_type
from typing import (
    Any,
    AsyncIterable,
    Awaitable,
    Callable,
    Dict,
    Iterator,
    List,
    Literal,
    Mapping,
    NoReturn,
    Union,
)
from urllib.parse import quote

import anyio

from lilya import status
from lilya._internal._helpers import HeaderHelper
from lilya.background import Task
from lilya.compat import md5_hexdigest
from lilya.concurrency import iterate_in_threadpool
from lilya.datastructures import URL, Header
from lilya.enums import Event, HTTPMethod, MediaType
from lilya.types import Receive, Scope, Send

Content = Union[str, bytes]
SyncContentStream = Iterator[Content]
AsyncContentStream = AsyncIterable[Content]
ContentStream = Union[AsyncContentStream, SyncContentStream]


class Response:
    media_type: Union[str, None] = None
    status_code: Union[int, None] = None
    charset: str = "utf-8"

    def __init__(
        self,
        content: Any = None,
        status_code: int = status.HTTP_200_OK,
        headers: Union[Mapping[str, str], None] = None,
        cookies: Union[Mapping[str, str], Any, None] = None,
        media_type: Union[str, None] = None,
        background: Union[Task, None] = None,
    ) -> None:
        if status_code is not None:
            self.status_code = status_code
        if media_type is not None:
            self.media_type = media_type
        self.background = background
        self.cookies = cookies
        self.body = self.make_response(content)
        self.raw_headers: List[Any] = []
        self.make_headers(headers)

    def make_response(self, content: Any) -> Union[bytes, str]:
        """
        Makes the Response object type.
        """
        if content is None or content is NoReturn:
            return b""
        if isinstance(content, bytes):
            return content
        return content.encode(self.charset)  # type: ignore

    def make_headers(
        self, content_headers: Union[Mapping[str, str], Dict[str, str], None] = None
    ) -> None:
        """
        Initialises the headers by builing the proper conditions and
        restrictions based on RFC specification.
        """
        headers: Dict[str, str] = {} if content_headers is None else content_headers  # type: ignore

        if HeaderHelper.has_entity_header_status(self.status_code):
            headers = HeaderHelper.remove_entity_headers(headers)
        if HeaderHelper.has_body_message(self.status_code):
            content_type = HeaderHelper.get_content_type(
                charset=self.charset, media_type=self.media_type
            )
            if hasattr(self, "body") and self.body is not None:
                headers.setdefault("content-length", str(len(self.body)))

            # Populates the content type if exists
            if content_type is not None:
                headers.setdefault("content-type", content_type)

        raw_headers = [
            (name.encode("latin-1"), f"{value}".encode(errors="surrogateescape"))
            for name, value in headers.items()
        ]
        self.raw_headers = raw_headers

    @property
    def headers(self) -> Header:
        if not hasattr(self, "_headers"):
            self._headers = Header(self.raw_headers)
        return self._headers

    def set_cookie(
        self,
        key: str,
        value: str = "",
        *,
        path: str = "/",
        domain: Union[str, None] = None,
        secure: bool = False,
        max_age: Union[int, None] = None,
        expires: Union[Union[datetime, str, int], None] = None,
        httponly: bool = False,
        samesite: Literal["lax", "strict", "none"] = "lax",
    ) -> None:
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
        self.headers.add("set-cookie", cookie_val.encode("latin-1"))

    def delete_cookie(
        self,
        key: str,
        path: str = "/",
        domain: Union[str, None] = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: Literal["lax", "strict", "none"] = "lax",
    ) -> None:
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
    def message(self) -> Dict[str, Any]:
        return {
            "type": "http.response.start",
            "status": self.status_code,
            "headers": list(self.headers.multi_items()),
        }

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await send(self.message)
        await send({"type": "http.response.body", "body": self.body})
        if self.background is not None:
            await self.background()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(media_type={self.media_type}, status_code={self.status_code}, charset={self.charset})"


class HTMLResponse(Response):
    media_type = MediaType.HTML


class Error(Response):
    media_type = MediaType.HTML
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class PlainText(Response):
    media_type = MediaType.TEXT


class JSONResponse(Response):
    media_type = MediaType.JSON

    def __init__(
        self,
        content: Any,
        status_code: int = status.HTTP_200_OK,
        headers: Union[Mapping[str, str], None] = None,
        media_type: Union[str, None] = None,
        background: Union[Task, None] = None,
    ) -> None:
        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )

    def make_response(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode(self.charset)


class Ok(JSONResponse):
    media_type = MediaType.JSON


class RedirectResponse(Response):
    def __init__(
        self,
        url: Union[str, URL],
        status_code: int = status.HTTP_307_TEMPORARY_REDIRECT,
        headers: Union[Mapping[str, str], None] = None,
        background: Union[Task, None] = None,
    ) -> None:
        super().__init__(
            content=b"", status_code=status_code, headers=headers, background=background
        )
        self.headers["location"] = quote(str(url), safe=":/%#?=@[]!$&'()*+,;")


class StreamingResponse(Response):
    body_iterator: AsyncContentStream

    def __init__(
        self,
        content: ContentStream,
        status_code: int = status.HTTP_200_OK,
        headers: Union[Mapping[str, str], None] = None,
        media_type: Union[str, None] = None,
        background: Union[Task, None] = None,
    ) -> None:
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
        await send(self.message)

        async for chunk in self.body_iterator:
            if not isinstance(chunk, bytes):
                chunk = chunk.encode(self.charset)
            await send({"type": "http.response.body", "body": chunk, "more_body": True})

        await send({"type": "http.response.body", "body": b"", "more_body": False})

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async with anyio.create_task_group() as task_group:

            async def wrap(func: "Callable[[], Awaitable[None]]") -> None:
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
        path: typing.Union[str, os.PathLike[str]],
        status_code: int = status.HTTP_200_OK,
        headers: typing.Optional[typing.Mapping[str, str]] = None,
        media_type: typing.Optional[str] = None,
        background: typing.Optional[Task] = None,
        filename: typing.Optional[str] = None,
        stat_result: typing.Optional[os.stat_result] = None,
        method: typing.Optional[str] = None,
        content_disposition_type: str = "attachment",
    ) -> None:
        self.path = path
        self.status_code = status_code
        self.filename = filename
        self.send_header_only = method is not None and method.upper() == HTTPMethod.HEAD
        if media_type is None:
            media_type = guess_type(filename or path)[0] or MediaType.TEXT
        self.media_type = media_type
        self.background = background
        self.make_headers(headers)

        if self.filename is not None:
            content_disposition_filename = quote(self.filename)
            if content_disposition_filename != self.filename:
                content_disposition = "{}; filename*=utf-8''{}".format(
                    content_disposition_type, content_disposition_filename
                )
            else:
                content_disposition = '{}; filename="{}"'.format(
                    content_disposition_type, self.filename
                )
            self.headers.setdefault("content-disposition", content_disposition)
        self.stat_result = stat_result
        if stat_result is not None:
            self.set_stat_headers(stat_result)

    def set_stat_headers(self, stat_result: os.stat_result) -> None:
        content_length = str(stat_result.st_size)
        last_modified = formatdate(stat_result.st_mtime, usegmt=True)
        etag_base = str(stat_result.st_mtime) + "-" + str(stat_result.st_size)
        etag = md5_hexdigest(etag_base.encode(), usedforsecurity=False)

        self.headers.setdefault("content-length", content_length)
        self.headers.setdefault("last-modified", last_modified)
        self.headers.setdefault("etag", etag)

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

        await send(self.message)

        if self.send_header_only:
            await send({"type": "http.response.body", "body": b"", "more_body": False})
        else:
            async with await anyio.open_file(self.path, mode="rb") as file:
                more_body = True
                while more_body:
                    chunk = await file.read(self.chunk_size)
                    more_body = len(chunk) == self.chunk_size
                    await send(
                        {
                            "type": "http.response.body",
                            "body": chunk,
                            "more_body": more_body,
                        }
                    )
        if self.background is not None:
            await self.background()


def make_response(
    content: Any,
    status_code: int = status.HTTP_200_OK,
    headers: Union[Mapping[str, str], None] = None,
    background: Union[Task, None] = None,
) -> JSONResponse:
    """
    Helper for building JSON responses.
    """
    return JSONResponse(
        content=content,
        status_code=status_code,
        headers=headers,
        media_type=MediaType.JSON,
        background=background,
    )
