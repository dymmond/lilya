from typing import Annotated, Any

from pydantic import BaseModel, field_validator

from lilya.enums import MediaType
from lilya.types import Doc


class OpenAPIResponse(BaseModel):
    """
    The OpenAPIResponse is used for [OpenAPI](https://lilya.dev/openapi/)
    documentation purposes and allows to describe in detail what alternative
    responses the API can return as well as the type of the return itself.
    """

    model: Annotated[
        type[BaseModel] | list[type[BaseModel]] | type[Any] | list[type[Any]],
        Doc(
            """
            A `pydantic.BaseModel` type of object of a `list` of
            `pydantic.BaseModel` types of objects.

            This is parsed and displayed in the [OpenAPI](https://esmerald.dev/openapi/)
            documentation.

            **Example**

            ```python
            from esmerald.openapi.datastructures import OpenAPIResponse
            from pydantic import BaseModel


            class Error(BaseModel):
                detail: str

            # Single
            OpenAPIResponse(model=Error)

            # list
            OpenAPIResponse(model=[Error])
            ```
            """
        ),
    ]
    description: Annotated[
        str,
        Doc(
            """
            Description of the response.

            This description is displayed in the [OpenAPI](https://esmerald.dev/openapi/)
            documentation.
            """
        ),
    ] = "Additional response"
    media_type: Annotated[
        MediaType | str,
        Doc("""The `media-type` of the response."""),
    ] = MediaType.JSON
    status_text: Annotated[
        str | None,
        Doc(
            """
            Description of the `status_code`. The description of the status code itself.

            This description is displayed in the [OpenAPI](https://esmerald.dev/openapi/)
            documentation.
            """
        ),
    ] = None

    @field_validator("model", mode="before")
    def validate_model(
        cls,
        model: type[BaseModel] | list[type[BaseModel]] | type[Any] | list[type[Any]],
    ) -> type[BaseModel] | list[type[BaseModel]] | type[Any] | list[type[Any]]:
        if isinstance(model, (list, tuple)) and len(model) > 1:
            raise ValueError(
                "The representation of a list or a tuple of models in OpenAPI can only be a total of one. Example: OpenAPIResponse(model=[MyModel])."
            )
        return model
