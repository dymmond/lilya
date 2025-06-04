from typing import Any

from pydantic.fields import FieldInfo


class Query(FieldInfo):
    """
    Use this in `@openapi(query=...)` to declare one or more query parameters.
    Inherits from pydantic.FieldInfo so you can pass the same arguments you’d pass to `Field(...)`.
    """

    def __init__(
        self,
        *,
        default: Any = ...,
        description: str | None = None,
        required: bool = False,
        schema: dict[str, Any] | None = None,
        style: str | None = "form",
        explode: bool | None = True,
    ):
        """
        - default: the default value (if any) for this query parameter.
                   If you want to force it to be required, set `required=True`.
        - description: a human‐readable description of what this query param does.
        - required: whether this parameter is required. (By default False.)
        - schema: a JSON‐schema dict, e.g. {"type": "string"} or
                  {"type": "array", "items": {"type": "string"}} etc.
        - style / explode: OpenAPI 3.x “style” / “explode” for query‐params. Usually
                           “form” + explode=True works for arrays like ?tags=a&tags=b;
                           use “deepObject” + explode=True for nested objects like
                           ?filter[name]=alice&filter[age]=30, etc.
        """
        super().__init__(default=default, description=description)

        # Required vs optional
        self.required = required

        # The JSON schema for this parameter (must be a dict with “type”, etc.)
        self.schema = schema or {}

        # style/explode for array/object serialization
        self.style = style
        self.explode = explode

    def as_openapi_dict(self, name: str) -> dict[str, Any]:
        """
        Return a properly formatted OpenAPI parameter-object (dict) for this query param.
        """
        param: dict[str, Any] = {
            "name": name,
            "in": "query",
            "required": self.required,
            "schema": self.schema or {"type": "string"},
        }
        if self.description is not None:
            param["description"] = self.description
        if self.style is not None:
            param["style"] = self.style
        if self.explode is not None:
            param["explode"] = self.explode
        return param


class ResponseParam(FieldInfo): ...
