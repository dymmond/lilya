import inspect
from collections.abc import Callable, Sequence
from functools import lru_cache, wraps
from typing import Annotated, Any, cast, get_origin

from pydantic import TypeAdapter

from lilya._internal._responses import BaseHandler
from lilya._utils import is_function
from lilya.contrib.documentation import Doc
from lilya.contrib.openapi.datastructures import OpenAPIResponse
from lilya.contrib.openapi.helpers import convert_annotation_to_pydantic_model
from lilya.contrib.openapi.params import Query, ResponseParam
from lilya.contrib.security.base import SecurityBase, SecurityScheme

SUCCESSFUL_RESPONSE = "Successful response"
DEFAULT_REQUEST_MEDIA_TYPE = "application/json"
MULTIPART_REQUEST_MEDIA_TYPE = "multipart/form-data"
REQUEST_BODY_SCHEMA_KEYS = {
    "$ref",
    "allOf",
    "anyOf",
    "format",
    "items",
    "oneOf",
    "properties",
    "required",
    "type",
}


def _is_openapi_request_body_dict(value: Any) -> bool:
    """
    Determine whether a value is already an OpenAPI ``requestBody`` object.
    """
    return isinstance(value, dict) and "content" in value and isinstance(value["content"], dict)


def _is_json_schema_dict(value: Any) -> bool:
    """
    Determine whether a dictionary looks like a JSON Schema object.
    """
    return isinstance(value, dict) and any(key in value for key in REQUEST_BODY_SCHEMA_KEYS)


def _schema_contains_binary_format(schema: Any) -> bool:
    """
    Recursively detect whether a JSON Schema contains ``format: binary``.
    """
    if isinstance(schema, dict):
        if schema.get("format") == "binary":
            return True
        return any(_schema_contains_binary_format(value) for value in schema.values())
    if isinstance(schema, list):
        return any(_schema_contains_binary_format(value) for value in schema)
    return False


def _build_request_body_metadata(
    request_body: Any | None,
    media_type: str | None,
) -> dict[str, Any]:
    """
    Normalize the ``request_body`` decorator input into an OpenAPI ``requestBody`` object.

    Supported forms are:
    - A Python annotation or model (e.g. ``MyModel`` or ``list[MyModel]``).
    - A single-item list/tuple shorthand (e.g. ``[MyModel]``).
    - A JSON Schema dictionary.
    - A complete OpenAPI ``requestBody`` dictionary containing ``content``.
    """
    if request_body is None:
        return {}

    if _is_openapi_request_body_dict(request_body):
        return request_body  # type: ignore

    if _is_json_schema_dict(request_body):
        schema = request_body
    else:
        if isinstance(request_body, (list, tuple)):
            if len(request_body) != 1:
                raise ValueError(
                    "Request body list/tuple representation accepts a single model only. "
                    "Example: request_body=[MyModel]."
                )
            annotation: Any = list[request_body[0]]  # type: ignore
        elif get_origin(request_body) in (list, tuple, Sequence):
            annotation = request_body
        else:
            annotation = request_body

        converted_annotation = convert_annotation_to_pydantic_model(annotation)
        schema = TypeAdapter(converted_annotation).json_schema()

    selected_media_type = media_type or (
        MULTIPART_REQUEST_MEDIA_TYPE
        if _schema_contains_binary_format(schema)
        else DEFAULT_REQUEST_MEDIA_TYPE
    )
    return {"content": {selected_media_type: {"schema": schema}}}


class OpenAPIMethod:
    def __init__(self, func: Callable[..., Any], metadata: dict[str, Any]) -> None:
        """
        Initialize OpenAPIMethod with a function and its metadata.
        """
        self.func = func
        self.metadata = metadata

    def __get__(self, instance: Any, owner: Any) -> Callable[..., Any]:
        bound_func = self.func.__get__(instance, owner)

        @wraps(bound_func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            handler = instance if isinstance(instance, BaseHandler) else BaseHandler()
            signature = get_signature(bound_func)
            return handler.handle_response(bound_func, other_signature=signature)

        wrapper.openapi_meta = self.metadata  # type: ignore[attr-defined]
        return wrapper


@lru_cache
def get_signature(func: Callable[..., Any]) -> inspect.Signature:
    """
    Cache and return the function signature used by the response handler wrapper.
    """
    return inspect.Signature.from_callable(func)


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
            The media type used for the OpenAPI request body when `request_body` is provided
            (e.g. "application/json" or "multipart/form-data").
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
        dict[str, Query] | dict[str, Any] | set[str],
        None,
        Doc(
            """
            A dict mapping each query‐param name (str) → a Query(...) instance.
            E.g. {"limit": Query(default=10, schema={"type":"integer"}, ...), ...}
            """,
        ),
    ] = None,
    request_body: Annotated[
        Any | None,
        Doc(
            """
            Overridable request body definition.
            It accepts a model annotation, a JSON Schema object, or a complete OpenAPI
            requestBody object (with `content`).
            """
        ),
    ] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to attach OpenAPI metadata to a handler. Handles both sync and async functions.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            handler = BaseHandler()
            signature = get_signature(func)
            return handler.handle_response(func, other_signature=signature)

        def response_models(responses: dict[int, OpenAPIResponse] | None = None) -> Any:
            """
            Convert OpenAPI response model declarations into internal response metadata.
            """
            responses: dict[int, ResponseParam] = {} if responses is None else responses  # type: ignore

            if responses:
                for status_code, response in responses.items():
                    model = (
                        response.model if isinstance(response, (list, tuple)) else response.model  # type: ignore
                    )
                    annotation = (
                        list[model[0]] if isinstance(response.model, list) else model  # type: ignore
                    )

                    alias = model.__name__ if not isinstance(model, list) else model[0].__name__
                    responses[status_code] = ResponseParam(  # type: ignore
                        annotation=convert_annotation_to_pydantic_model(annotation),
                        description=response.description,
                        alias=alias,
                    )
            return responses

        def query_strings(
            query_dict: dict[str, Query] | dict[str, Any] | set[str] | None = None,
        ) -> dict[str, Query]:
            """
            Normalize query parameter declarations into ``Query`` instances.
            """
            if query_dict is None:
                return {}

            if isinstance(query_dict, set):
                return {q: Query() for q in query_dict}

            if isinstance(query_dict, dict):
                data: dict[str, Query] = {}
                for k, v in query_dict.items():
                    if isinstance(v, Query):
                        data[k] = v
                    elif isinstance(v, (list, tuple)):
                        raise ValueError("Query cannot be a list or tuple, use Query(...) instead")
                    elif isinstance(v, dict):
                        data[k] = Query(**v)
                return data
            raise TypeError(
                "Query must be a dict or set or a dict of key-pair value of str and Query"
            )

        def handle_security_requirement(
            security_requirements: Sequence[Any] | None,
        ) -> list[dict[str, Any]] | None:
            """
            Normalize security requirements into OpenAPI security scheme declarations.
            """
            security_schemes = []
            security_definitions: dict[str, dict[str, Any]] = {}

            for security_requirement in security_requirements or []:
                if isinstance(security_requirement, dict):
                    for name, scheme in security_requirement.items():
                        security_definitions[name] = scheme
                    continue

                if inspect.isclass(security_requirement):
                    security_requirement = security_requirement()

                if not isinstance(security_requirement, (SecurityBase, SecurityScheme)):
                    raise ValueError(
                        "Security schemes must subclass from `lilya.contrib.security.base.SecurityScheme`"
                    )

                # Means it uses the security scheme directly
                security_definition = security_requirement.model_dump(
                    by_alias=True,
                    exclude_none=True,
                )
                security_name = security_requirement.scheme_name  # type: ignore[attr-defined]
                security_definitions[security_name] = security_definition

            if security_definitions:
                security_schemes.append(security_definitions)
                return security_schemes
            return None

        wrapper.openapi_meta = {  # type: ignore[attr-defined]
            "summary": summary,
            "description": description,
            "status_code": status_code,
            "content_encoding": content_encoding,
            "media_type": media_type,
            "include_in_schema": include_in_schema,
            "tags": tags,
            "deprecated": deprecated,
            "security": handle_security_requirement(security),
            "operation_id": operation_id,
            "response_description": response_description,
            "responses": response_models(responses) or {},
            "query": query_strings(query) or {},
        }

        body_fields = _build_request_body_metadata(request_body, media_type)
        wrapper.openapi_meta["request_body"] = body_fields  # type: ignore[attr-defined]

        if is_function(func) and not inspect.ismethod(func):
            return wrapper
        return cast(Callable[..., Any], OpenAPIMethod(func, wrapper.openapi_meta))  # type: ignore[attr-defined]

    return decorator
