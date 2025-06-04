# lilya/contrib/openapi/decorator.py

import inspect
from collections.abc import Callable, Sequence
from functools import wraps
from typing import Annotated, Any

from typing_extensions import Doc

from lilya.contrib.openapi.datastructures import OpenAPIResponse
from lilya.contrib.openapi.params import Query

SUCCESSFUL_RESPONSE = "Successful response"


def openapi(
    summary: Annotated[
        str | None,
        Doc(
            """
            The summary of the handler. This short summary is displayed when the OpenAPI documentation is used.
            """
        ),
    ] = None,
    description: Annotated[
        str | None,
        Doc(
            """
            A longer description for this operation. If omitted, no description is emitted.
            """
        ),
    ] = None,
    status_code: Annotated[
        int | None,
        Doc(
            """
            An integer indicating the status code of the handler. This can be achieved by passing directly the value.
            """
        ),
    ] = None,
    content_encoding: Annotated[
        str | None,
        Doc(
            """
            The string indicating the content encoding of the handler (e.g. "gzip"). Used for OpenAPI.
            """
        ),
    ] = None,
    media_type: Annotated[
        str | None,
        Doc(
            """
            The string indicating the content media type of the handler (e.g. "application/json").
            Used for OpenAPI.
            """
        ),
    ] = None,
    include_in_schema: Annotated[
        bool,
        Doc(
            """
            Boolean flag indicating if it should be added to the OpenAPI docs.
            """
        ),
    ] = True,
    tags: Annotated[
        Sequence[str] | None,
        Doc(
            """
            A list of string tags to be applied to the path operation. Will be added to the generated OpenAPI documentation.
            """
        ),
    ] = None,
    deprecated: Annotated[
        bool | None,
        Doc(
            """
            Boolean flag indicating if the handler should be marked as deprecated in the OpenAPI docs.
            """
        ),
    ] = None,
    security: Annotated[
        Sequence[Any] | None,
        Doc(
            """
            A list of security requirement objects for this operation.
            """
        ),
    ] = None,
    operation_id: Annotated[
        str | None,
        Doc(
            """
            A unique string used to identify this operation. If omitted, the function name is used.
            """
        ),
    ] = None,
    response_description: Annotated[
        str | None,
        Doc(
            """
            A description for the default response (200) if no `responses` are provided.
            """
        ),
    ] = SUCCESSFUL_RESPONSE,
    responses: Annotated[
        dict[int, OpenAPIResponse] | None,
        Doc(
            """
            A dict mapping status code (int) → OpenAPIResponse instance.
            """
        ),
    ] = None,
    query: Annotated[
        dict[str, Query] | None,
        Doc(
            """
            A dict mapping each query‐param name (str) → a Query(...) instance.
            E.g. {"limit": Query(default=10, schema={"type":"integer"}, ...), ...}
            """,
        ),
    ] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to attach OpenAPI metadata to a handler. Handles both sync and async functions.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                return await func(*args, **kwargs)

            wrapper = async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                return func(*args, **kwargs)

            wrapper = sync_wrapper

        wrapper.openapi_meta = {
            "summary": summary,
            "description": description,
            "status_code": status_code,
            "content_encoding": content_encoding,
            "media_type": media_type,
            "include_in_schema": include_in_schema,
            "tags": tags,
            "deprecated": deprecated,
            "security": security,
            "operation_id": operation_id,
            "response_description": response_description,
            "responses": responses or {},
            "query": query or {},
        }

        return wrapper

    return decorator
