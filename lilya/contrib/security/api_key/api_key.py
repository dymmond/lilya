from typing import Annotated, cast

from pydantic import BaseModel

from lilya.contrib.documentation import Doc
from lilya.contrib.openapi.enums import APIKeyIn
from lilya.contrib.openapi.models import APIKey
from lilya.contrib.security.base import SecurityBase
from lilya.contrib.security.errors import AuthenticationErrorMixin
from lilya.exceptions import HTTPException
from lilya.requests import Request


class APIKeyBase(SecurityBase, AuthenticationErrorMixin):
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

    def raise_for_authentication_error(self) -> HTTPException:
        """
        Raise an authentication error if the query parameter is missing.
        """
        return self.build_authentication_exception(headers={"WWW-Authenticate": "APIKey"})

    async def __call__(self, request: Request) -> str | None:
        api_key = request.query_params.get(self.__model__.name)
        if api_key:
            return cast(str, api_key)
        if self.__auto_error__:
            raise self.raise_for_authentication_error()
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

    def raise_for_authentication_error(self) -> HTTPException:
        """
        Raise an authentication error if the query parameter is missing.
        """
        return self.build_authentication_exception(headers={"WWW-Authenticate": "APIKey"})

    async def __call__(self, request: Request) -> str | None:
        api_key = request.headers.get(self.__model__.name)
        if api_key:
            return cast(str, api_key)
        if self.__auto_error__:
            raise self.raise_for_authentication_error()
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

    def raise_for_authentication_error(self) -> HTTPException:
        """
        Raise an authentication error if the query parameter is missing.
        """
        return self.build_authentication_exception(headers={"WWW-Authenticate": "APIKey"})

    async def __call__(self, request: Request) -> str | None:
        api_key = request.cookies.get(self.__model__.name)
        if api_key:
            return api_key
        if self.__auto_error__:
            raise self.raise_for_authentication_error()
        return None
