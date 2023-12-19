from __future__ import annotations

import http.cookies
import json
from datetime import datetime
from email.utils import format_datetime
from typing import Any, Dict, List, Literal, Mapping, NoReturn, Union
from urllib.parse import quote

from lilya import status
from lilya._internal._helpers import HeaderHelper
from lilya.background import Task
from lilya.datastructures import URL, Headers
from lilya.enums import MediaType
from lilya.types import Receive, Scope, Send


class Response:
    media_type = None
    status_code = None
    charset = "utf-8"

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
        self._headers: Union[Headers, List[Headers]] = []
        self.make_headers(headers)

    def make_response(self, content: Any) -> Union[bytes, str]:
        """
        Makes the Response object type.
        """
        if content is None or content is NoReturn:
            return b""
        if isinstance(content, bytes):
            return content
        if self.media_type == MediaType.JSON:
            return json.dumps(content)
        return content.encode(self.charset)  # type: ignore

    def make_headers(self, content_headers: Union[Mapping[str, str], None] = None) -> None:
        """
        Initialises the headers by builing the proper conditions and
        restrictions based on RFC specification.
        """
        if content_headers is None:
            headers: Dict[str, str] = {}

        if HeaderHelper.has_entity_header_status(self.status_code):
            headers = HeaderHelper.remove_entity_headers(headers)
        if HeaderHelper.has_body_message(self.status_code):
            content_type = HeaderHelper.get_content_type(
                charset=self.charset, media_type=self.media_type
            )
            headers.setdefault("content-type", content_type)

        raw_headers = [  # type: ignore
            (name.encode("latin-1"), f"{value}".encode(errors="surrogateescape"))
            for name, value in headers.items()
        ]
        self._headers = raw_headers  # type: ignore

    @property
    def headers(self) -> Headers:
        if self._headers is not None:
            self._headers = Headers(self._headers)  # type: ignore
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
        self._headers.append((b"set-cookie", cookie_val.encode("latin-1")))  # type: ignore

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
            "headers": self._headers,
        }

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await send(self.message)
        await send({"type": "http.response.body", "body": self.body})
        if self.background is not None:
            await self.background()


class HTMLResponse(Response):
    media_type = MediaType.HTML


class Ok(Response):
    media_type = MediaType.JSON


class Error(Response):
    media_type = MediaType.HTML
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class PlainTextResponse(Response):
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

    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")


class Redirect(Response):
    def __init__(
        self,
        url: Union[str, URL],
        status_code: int = 307,
        headers: Union[Mapping[str, str], None] = None,
        background: Union[Task, None] = None,
    ) -> None:
        super().__init__(
            content=b"", status_code=status_code, headers=headers, background=background
        )
        self.headers["location"] = quote(str(url), safe=":/%#?=@[]!$&'()*+,;")


def make_response(
    content: Any,
    status_code: int = status.HTTP_200_OK,
    headers: Union[Mapping[str, str], None] = None,
    background: Union[Task, None] = None,
) -> JSONResponse:
    """
    Helper for building JSONResponses.
    """
    return JSONResponse(
        content=content,
        status_code=status_code,
        headers=headers,
        media_type=MediaType.JSON,
        background=background,
    )
