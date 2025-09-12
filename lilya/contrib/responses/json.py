from __future__ import annotations

from typing import Any

from lilya import status
from lilya.enums import MediaType
from lilya.exceptions import ImproperlyConfigured
from lilya.responses import Response
from lilya.serializers import serializer


def jsonify(
    *args: Any,
    status_code: int = status.HTTP_200_OK,
    headers: dict[str, str] | None = None,
    cookies: dict[str, str] | None = None,
    **kwargs: Any,
) -> Response:
    """
    Accepts:
    - A single dict, list, etc.
    - Keyword arguments (converted into a dict).
    - Multiple args (will return them as a list).

    Ensures:
    - application/json content type
    - orjson encoding
    """
    if args and kwargs:
        raise ImproperlyConfigured("jsonify() can only take either *args or **kwargs, not both")

    if len(args) == 1:
        payload = args[0]
    elif len(args) > 1:
        payload = list(args)
    else:
        payload = kwargs

    response = Response(
        content=serializer.dumps(payload),
        media_type=MediaType.JSON,
        status_code=status_code,
        headers=headers,
    )

    if cookies:
        for k, v in cookies.items():
            response.set_cookie(k, v)

    return response
