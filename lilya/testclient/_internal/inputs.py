from __future__ import annotations

from typing import Any, TypedDict

import httpx
from httpx._types import (
    AuthTypes,
    CookieTypes,
    HeaderTypes,
    QueryParamTypes,
    RequestContent,
    RequestFiles,
    TimeoutTypes,
)

from lilya.testclient._internal.types import RequestData


class RequestInputs(TypedDict, total=False):
    content: RequestContent | None = None
    data: RequestData | None = None
    files: RequestFiles | None = None
    json: Any = None
    params: QueryParamTypes | None = None
    headers: HeaderTypes | None = None
    cookies: CookieTypes | None = None
    follow_redirects: bool | None = None
    auth: AuthTypes | httpx._client.UseClientDefault
    timeout: TimeoutTypes | httpx._client.UseClientDefault
    extensions: dict[str, Any] | None = None


RequestInputsDefaultValues = {
    "content": None,
    "data": None,
    "files": None,
    "json": None,
    "params": None,
    "headers": None,
    "cookies": None,
    "follow_redirects": None,
    "auth": httpx._client.USE_CLIENT_DEFAULT,
    "timeout": httpx._client.USE_CLIENT_DEFAULT,
    "extensions": None,
}
