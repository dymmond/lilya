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
    Iterable,
    Literal,
    Mapping,
    NoReturn,
    Union,
)
from urllib.parse import quote

import anyio

from lilya import status
from lilya._internal._encoders import json_encoder
from lilya._internal._helpers import HeaderHelper
from lilya.background import Task
from lilya.compat import md5_hexdigest
from lilya.concurrency import iterate_in_threadpool
from lilya.datastructures import URL, Header
from lilya.enums import Event, HTTPMethod, MediaType
from lilya.types import Receive, Scope, Send

Content = Union[str, bytes]
SyncContentStream = Iterable[Content]
AsyncContentStream = AsyncIterable[Content]
ContentStream = Union[AsyncContentStream, SyncContentStream]


class Response:
    media_type: str | None = None
    status_code: int | None = None
    charset: str = "utf-8"

    def __init__(
        self,
        content: Any = None,
        status_code: int = status.HTTP_200_OK,
        headers: Mapping[str, str] | None = None,
        cookies: Mapping[str, str] | Any | None = None,
        media_type: str | None = None,
        background: Task | None = None,
    ) -> None:
        if status_code is not None:
            self.status_code = status_code
        if media_type is not None:
            self.media_type = media_type
        self.background = background
        self.cookies = cookies
        self.body = self.make_response(content)
        self.raw_headers: list[Any] = []
        self.make_headers(headers)

    def make_response(self, content: Any) -> bytes | str:
        """
        Makes the Response object type.
        """
        if content is None or content is NoReturn or not content:
            return b""
        if isinstance(content, bytes):
            return content
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
        self.headers.add("set-cookie", cookie_val.encode("latin-1"))

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
        headers: list[tuple[Any, Any]] = []

        for name, value in list(self.headers.multi_items()):
            if not isinstance(value, bytes):
                headers.append(
                    (name.encode("latin-1"), f"{value}".encode(errors="surrogateescape"))
                )
            else:
                headers.append((name.encode("latin-1"), value))
        return headers

    def message(self, prefix: str) -> dict[str, Any]:
        return {
            "type": prefix + "http.response.start",
            "status": self.status_code,
            "headers": self.encoded_headers,
        }

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        prefix = "websocket." if scope["type"] == "websocket" else ""
        await send(self.message(prefix=prefix))
        await send({"type": prefix + "http.response.body", "body": self.body})

        if self.background is not None:
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
        url: str | URL,
        status_code: int = status.HTTP_307_TEMPORARY_REDIRECT,
        headers: Mapping[str, str] | None = None,
        background: Task | None = None,
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
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: Task | None = None,
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
        await send(self.message(prefix=""))

        async for chunk in self.body_iterator:
            if not isinstance(chunk, bytes):
                chunk = chunk.encode(self.charset)
            await send({"type": "http.response.body", "body": chunk, "more_body": True})

        await send({"type": "http.response.body", "body": b"", "more_body": False})

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
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
                content_disposition = (
                    f"{content_disposition_type}; filename*=utf-8''{content_disposition_filename}"
                )
            else:
                content_disposition = f'{content_disposition_type}; filename="{self.filename}"'
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

        prefix = "websocket." if scope["type"] == "websocket" else ""
        await send(self.message(prefix=prefix))

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


class TemplateResponse(HTMLResponse):
    def __init__(
        self,
        template: Any,
        status_code: int = status.HTTP_200_OK,
        context: dict[str, Any] | None = None,
        background: Task | None = None,
        headers: dict[str, Any] | None = None,
        media_type: MediaType | str = MediaType.HTML,
    ):
        self.template = template
        self.context = context or {}
        content = self.template.render(context)
        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
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
) -> Response:
    """
    Build JSON responses from a given content and
    providing extra parameters.
    """
    app = json_encoder(content) if content is not None else None

    return response_class(
        content=app,
        status_code=status_code,
        headers=headers,
        media_type=MediaType.JSON,
        background=background,
    )
