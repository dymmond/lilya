from typing import Annotated, cast

from pydantic import BaseModel
from typing_extensions import Doc

from lilya.contrib.openapi.enums import APIKeyIn
from lilya.contrib.openapi.models import APIKey
from lilya.contrib.security.base import SecurityBase
from lilya.exceptions import HTTPException
from lilya.requests import Request
from lilya.status import HTTP_403_FORBIDDEN


class APIKeyBase(SecurityBase):
    __model__: BaseModel | None = None


class APIKeyInQuery(APIKeyBase):
    def __init__(
        self,
        *,
        name: Annotated[str, Doc("Name of the query parameter.")],
        scheme_name: Annotated[
            str | None,
            Doc("Name of the security scheme, shown in OpenAPI documentation."),
        ] = None,
        description: Annotated[
            str | None,
            Doc("Description of the security scheme, shown in OpenAPI documentation."),
        ] = None,
        auto_error: Annotated[
            bool,
            Doc(
                "If True, raises an error if the query parameter is missing. "
                "If False, returns None when the query parameter is missing."
            ),
        ] = True,
    ):
        model: APIKey = APIKey(
            **{"in": APIKeyIn.query.value},  # type: ignore[arg-type]
            name=name,
            description=description,
        )
        super().__init__(**model.model_dump())
        self.__model__ = model
        self.scheme_name = scheme_name or self.__class__.__name__
        self.__auto_error__ = auto_error

    async def __call__(self, request: Request) -> str | None:
        api_key = request.query_params.get(self.__model__.name)
        if api_key:
            return cast(str, api_key)
        if self.__auto_error__:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Not authenticated")
        return None


class APIKeyInHeader(APIKeyBase):
    def __init__(
        self,
        *,
        name: Annotated[str, Doc("The name of the header parameter.")],
        scheme_name: Annotated[
            str | None,
            Doc("The name of the security scheme to be shown in the OpenAPI documentation."),
        ] = None,
        description: Annotated[
            str | None,
            Doc("A description of the security scheme to be shown in the OpenAPI documentation."),
        ] = None,
        auto_error: Annotated[
            bool,
            Doc(
                "If True, an error is raised if the header is missing. "
                "If False, None is returned when the header is missing."
            ),
        ] = True,
    ):
        model: APIKey = APIKey(
            **{"in": APIKeyIn.header.value},  # type: ignore[arg-type]
            name=name,
            description=description,
        )
        super().__init__(**model.model_dump())
        self.__model__ = model
        self.scheme_name = scheme_name or self.__class__.__name__
        self.__auto_error__ = auto_error

    async def __call__(self, request: Request) -> str | None:
        api_key = request.headers.get(self.__model__.name)
        if api_key:
            return cast(str, api_key)
        if self.__auto_error__:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Not authenticated")
        return None


class APIKeyInCookie(APIKeyBase):
    def __init__(
        self,
        *,
        name: Annotated[str, Doc("The name of the cookie parameter.")],
        scheme_name: Annotated[
            str | None,
            Doc("The name of the security scheme to be shown in the OpenAPI documentation."),
        ] = None,
        description: Annotated[
            str | None,
            Doc("A description of the security scheme to be shown in the OpenAPI documentation."),
        ] = None,
        auto_error: Annotated[
            bool,
            Doc(
                "If True, an error is raised if the cookie is missing. "
                "If False, None is returned when the cookie is missing."
            ),
        ] = True,
    ):
        model: APIKey = APIKey(
            **{"in": APIKeyIn.cookie.value},  # type: ignore[arg-type]
            name=name,
            description=description,
        )
        super().__init__(**model.model_dump())
        self.__model__ = model
        self.scheme_name = scheme_name or self.__class__.__name__
        self.__auto_error__ = auto_error

    async def __call__(self, request: Request) -> str | None:
        api_key = request.cookies.get(self.__model__.name)
        if api_key:
            return api_key
        if self.__auto_error__:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Not authenticated")
        return None
