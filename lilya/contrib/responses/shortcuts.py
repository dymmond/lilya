from collections.abc import (
    Mapping,
    Sequence,
)
from typing import Any

from lilya import status
from lilya.background import Task
from lilya.datastructures import URL
from lilya.encoders import EncoderProtocol, MoldingProtocol
from lilya.exceptions import HTTPException
from lilya.responses import JSONResponse, RedirectResponse, Response, StreamingResponse

Encoder = EncoderProtocol | MoldingProtocol


def abort(
    status_code: int,
    detail: Any | None = None,
    headers: dict[str, Any] | None = None,
) -> None:
    """
    Immediately raise an :class:`~lilya.exceptions.HTTPException` to stop request processing.

    The :func:`abort` shortcut provides a clean, expressive way to interrupt the current
    request flow and return an HTTP error response without manually raising exceptions
    or returning response objects.

    Depending on the ``detail`` parameter, Lilya will automatically determine the appropriate
    response type:

    * If ``detail`` is a dictionary or list, a :class:`~lilya.responses.JSONResponse` is created.
    * If ``detail`` is a string, a :class:`~lilya.responses.Response` with plain text is created.
    * If ``detail`` is ``None``, the default HTTP status phrase (e.g., *"Not Found"*) is used.

    Example:
        ```python
        from lilya.contrib.responses.shortcuts import abort

        async def not_found(request):
            abort(404)

        async def unauthorized(request):
            abort(401, "Unauthorized access")

        async def bad_request(request):
            abort(400, {"error": "Invalid payload", "code": 400})
        ```

    Args:
        status_code: The HTTP status code to send (e.g., 400, 404, 500).
        detail: Optional content or message for the response. Can be a string, list, dict, or ``None``.
        headers: Optional dictionary of HTTP headers to include in the response.

    Raises:
        :class:`~lilya.exceptions.HTTPException`: Raised internally to trigger an immediate HTTP error response.

    Behavior:
        * Execution after :func:`abort` will never continue.
        * The raised exception is automatically caught by the
          :class:`~lilya.middleware.exceptions.ExceptionMiddleware` and transformed into a response.
    """
    response: Response

    if isinstance(detail, (dict, list)):
        response = JSONResponse(detail, status_code=status_code, headers=headers)
        raise HTTPException(status_code=status_code, headers=headers, response=response)

    if detail is None:
        raise HTTPException(status_code=status_code, headers=headers)

    response = Response(detail, status_code=status_code, headers=headers)
    raise HTTPException(status_code=status_code, detail=detail, headers=headers, response=response)


def send_json(
    data: dict | list,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """
    Quickly return a :class:`~lilya.responses.JSONResponse`.

    This is a convenience function for endpoints that need to
    return JSON data without explicitly importing and instantiating
    :class:`~lilya.responses.JSONResponse`.

    Example:
        ```python
        from lilya.contrib.responses.shortcuts import send_json

        async def user_info(request):
            return send_json({"id": 1, "name": "Alice"})
        ```

    Args:
        data: The Python object (dict or list) to serialize into JSON.
        status_code: The HTTP status code for the response.
        headers: Optional dictionary of HTTP headers to include.

    Returns:
        :class:`~lilya.responses.JSONResponse`: A JSON response with
        the serialized payload.
    """
    return JSONResponse(data, status_code=status_code, headers=headers)


def json_error(
    message: str | dict,
    status_code: int = 400,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """
    Return a structured JSON error response without raising an exception.

    This is a lightweight alternative to :func:`abort` when you want to
    return an error payload explicitly rather than stopping execution.

    Example:
        ```python
        from lilya.contrib.responses.shortcuts import json_error

        async def invalid(request):
            return json_error("Invalid email format", status_code=422)
        ```

    Args:
        message: The error message as a string or a structured dictionary.
        status_code: The HTTP status code for the response (default: 400).
        headers: Optional dictionary of additional HTTP headers.

    Returns:
        :class:`~lilya.responses.JSONResponse`: A JSON response containing
        the error payload.
    """
    payload = {"error": message} if isinstance(message, str) else message
    return JSONResponse(payload, status_code=status_code, headers=headers)


def stream(
    content: Any,
    mimetype: str = "text/plain",
    headers: dict[str, str] | None = None,
) -> StreamingResponse:
    """
    Send a streaming response.

    This helper automatically wraps the given content in a
    :class:`~lilya.responses.StreamingResponse`, supporting both
    synchronous and asynchronous iterators or generators.

    Example:
        ```python
        from lilya.contrib.responses.shortcuts import stream
        import asyncio

        async def numbers(request):
            async def generator():
                for i in range(5):
                    yield f"{i}\\n"
                    await asyncio.sleep(1)

            return stream(generator(), mimetype="text/plain")
        ```

    Args:
        content: The iterable, async iterable, or generator yielding bytes or strings.
        mimetype: The MIME type for the response body (default: ``"text/plain"``).
        headers: Optional dictionary of additional HTTP headers.

    Returns:
        :class:`~lilya.responses.StreamingResponse`: The streaming HTTP response.
    """
    return StreamingResponse(content, media_type=mimetype, headers=headers)


def empty(
    status_code: int = 204,
    headers: dict[str, str] | None = None,
) -> Response:
    """
    Return an empty :class:`~lilya.responses.Response`.

    Useful for endpoints that need to indicate success without returning a body,
    such as DELETE or PUT requests.

    Example:
        ```python
        from lilya.contrib.responses.shortcuts import empty

        async def delete_user(request):
            # perform deletion...
            return empty()  # returns 204 No Content
        ```

    Args:
        status_code: The HTTP status code to return (default: ``204``).
        headers: Optional dictionary of HTTP headers.

    Returns:
        :class:`~lilya.responses.Response`: An empty HTTP response.
    """
    return Response(status_code=status_code, headers=headers)


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


def unauthorized(
    message: str = "Unauthorized",
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """
    Return a 401 **Unauthorized** JSON response.

    This helper is used when authentication is required but has failed
    or has not yet been provided. It returns a JSON payload with an
    `"error"` key and a 401 status code.

    Example:
        ```python
        from lilya.contrib.responses.shortcuts import unauthorized

        async def protected(request):
            if not request.user.is_authenticated:
                return unauthorized("Authentication required")
        ```

    Args:
        message: The error message to include in the response.
        headers: Optional dictionary of HTTP headers.

    Returns:
        :class:`~lilya.responses.JSONResponse`: A JSON response with
        status code 401 and the error message.
    """
    return JSONResponse({"error": message}, status_code=401, headers=headers)


def forbidden(
    message: str = "Forbidden",
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """
    Return a 403 **Forbidden** JSON response.

    This shortcut is used when the client is authenticated but does not
    have permission to access the requested resource.

    Example:
        ```python
        from lilya.contrib.responses.shortcuts import forbidden

        async def admin_only(request):
            if not request.user.is_admin:
                return forbidden("You are not allowed to access this section")
        ```

    Args:
        message: The error message to include in the response.
        headers: Optional dictionary of HTTP headers.

    Returns:
        :class:`~lilya.responses.JSONResponse`: A JSON response with
        status code 403 and the error message.
    """
    return JSONResponse({"error": message}, status_code=403, headers=headers)


def not_found(
    message: str = "Not Found",
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """
    Return a 404 **Not Found** JSON response.

    This shortcut is used when the requested resource cannot be located
    on the server. It provides a consistent error payload structure for
    missing entities or routes.

    Example:
        ```python
        from lilya.contrib.responses.shortcuts import not_found

        async def get_user(request):
            user = await db.users.get(id=42)
            if not user:
                return not_found("User not found")
        ```

    Args:
        message: The error message to include in the response.
        headers: Optional dictionary of HTTP headers.

    Returns:
        :class:`~lilya.responses.JSONResponse`: A JSON response with
        status code 404 and the error message.
    """
    return JSONResponse({"error": message}, status_code=404, headers=headers)
