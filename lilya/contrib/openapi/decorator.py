from collections.abc import Sequence
from functools import wraps
from typing import Annotated, Any

from typing_extensions import Doc

from lilya.contrib.openapi.datastructures import OpenAPIResponse

SUCCESSFUL_RESPONSE = "Successful response"

def openapi(
    summary: Annotated[
        str | None,
        Doc(
            """
            The summary of the handler. This short summary is displayed when the [OpenAPI](https://esmerald.dev/openapi/) documentation is used.

            **Example**

            ```python
            from esmerald import get


            @get(summary="Black Window joining Pretenders")
            async def get_joiners() -> None:
                ...
            ```
            """
        ),
    ] = None,
    description: Annotated[
        str | None,
        Doc(
            """
            The description of the Esmerald application/API. This description is displayed when the [OpenAPI](https://esmerald.dev/openapi/) documentation is used.

            **Example**

            ```python
            from esmerald import get


            @get(description=...)
            async def get_joiners() -> None:
                ...
            """
        ),
    ] = None,
    status_code: Annotated[
        int | None,
        Doc(
            """
            An integer indicating the status code of the handler.

            This can be achieved by passing directly the value or
            by using the `esmerald.status` or even the `lilya.status`.
            """
        ),
    ] = None,
    content_encoding: Annotated[
        str | None,
        Doc(
            """
            The string indicating the content encoding of the handler.

            This is used for the generation of the [OpenAPI](https://esmerald.dev/openapi/)
            documentation.
            """
        ),
    ] = None,
    media_type: Annotated[
        str | None,
        Doc(
            """
            The string indicating the content media type of the handler.

            This is used for the generation of the [OpenAPI](https://esmerald.dev/openapi/)
            documentation.
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
            A list of strings tags to be applied to the *path operation*.

            It will be added to the generated OpenAPI documentation.

            **Note** almost everything in Esmerald can be done in [levels](https://esmerald.dev/application/levels/), which means
            these tags on a Esmerald instance, means it will be added to every route even
            if those routes also contain tags.

            **Example**

            ```python
            from esmerald import get

            @get(tags=["application"])
            ```
            """
        ),
    ] = None,
    deprecated: Annotated[
        bool | None,
        Doc(
            """
            Boolean flag indicating if the handler
            should be deprecated in the OpenAPI documentation.

            **Example**

            ```python
            from esmerald import get

            @get(deprecated=True)
            ```
            """
        ),
    ] = None,
    security: Annotated[
        list[Any] | None,
        Doc(
            """
            Used by OpenAPI definition, the security must be compliant with the norms.
            Esmerald offers some out of the box solutions where this is implemented.

            The [Esmerald security](https://esmerald.dev/openapi/) is available to automatically used.

            The security can be applied also on a [level basis](https://esmerald.dev/application/levels/).

            For custom security objects, you **must** subclass
            `esmerald.openapi.security.base.HTTPBase` object.

            **Example**

            ```python
            from esmerald import get
            from esmerald.openapi.security.http import Bearer

            @get(security=[Bearer()])
            ```
            """
        ),
    ] = None,
    operation_id: Annotated[
        str | None,
        Doc(
            """
            The unique identifier of the `handler`. This acts as a unique ID
            for the OpenAPI documentation.

            !!! Tip
                Usually you don't need this as Esmerald handles it automatically
                but it is here if you want to add your own.
            """
        ),
    ] = None,
    response_description: Annotated[
        str | None,
        Doc(
            """
                A description of the response. This is used for OpenAPI documentation
                purposes only and accepts all the docstrings including `markdown` format.
                """
        ),
    ] = SUCCESSFUL_RESPONSE,
    responses: Annotated[
        dict[int, OpenAPIResponse] | None,
        Doc(
            """
            Additional responses that are handled by the handler and need to be described
            in the OpenAPI documentation.

            The `responses` is a dictionary like object where the first parameter is an
            `integer` and the second is an instance of an [OpenAPIResponse](https://esmerald.dev/responses/#openapi-responses) object.


            Read more about [OpenAPIResponse](https://esmerald.dev/responses/#openapi-responses) object and how to use it.


            **Example**

            ```python
            from esmerald import get
            from esmerald.openapi.datastructures import OpenAPIResponse
            from pydantic import BaseModel

            class Power(BaseModel):
                name: str
                description: str


            class Error(BaseModel):
                detail: str


            @get(path='/read', responses={
                    200: OpenAPIResponse(model=Power, description=...)
                    400: OpenAPIResponse(model=Error, description=...)
                }
            )
            async def create() -> Union[None, ItemOut]:
                ...
            ```
            """
        ),
    ] = None,
) -> Any:
    def decorator(func: Any) -> Any:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)
        wrapper.__openapi__ = {
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
            "responses": responses,
        }
        return wrapper
    return decorator
