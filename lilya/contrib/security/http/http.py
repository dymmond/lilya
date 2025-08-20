import binascii
from base64 import b64decode
from typing import Annotated, Any

from pydantic import BaseModel
from typing_extensions import Doc

from lilya.contrib.openapi.models import HTTPBase as HTTPBaseModel, HTTPBearer as HTTPBearerModel
from lilya.contrib.security.base import HttpSecurityBase
from lilya.contrib.security.utils import get_authorization_scheme_param
from lilya.exceptions import HTTPException
from lilya.requests import Request
from lilya.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN


class HTTPBasicCredentials(BaseModel):
    """
    Represents HTTP Basic credentials.

    Attributes:
        username (str): The username.
        password (str): The password.
    """

    username: Annotated[str, Doc("The username for HTTP Basic authentication.")]
    password: Annotated[str, Doc("The password for HTTP Basic authentication.")]


class HTTPAuthorizationCredentials(BaseModel):
    """
    Represents HTTP authorization credentials.

    Attributes:
        scheme (str): The authorization scheme (e.g., "Bearer").
        credentials (str): The authorization credentials (e.g., token).
    """

    scheme: Annotated[str, Doc("The authorization scheme extracted from the header.")]
    credentials: Annotated[str, Doc("The authorization credentials extracted from the header.")]


class HTTPBase(HttpSecurityBase):
    def __init__(
        self,
        *,
        scheme: str,
        scheme_name: str | None = None,
        description: str | None = None,
        auto_error: bool = True,
        **kwargs: Any,
    ):
        """
        Base class for HTTP security schemes.

        Args:
            scheme (str): The security scheme (e.g., "basic", "bearer").
            scheme_name (str, optional): The name of the security scheme.
            description (str, optional): Description of the security scheme.
            auto_error (bool, optional): Whether to automatically raise an error if authentication fails.
        """
        model = HTTPBaseModel(scheme=scheme, description=description)
        model_dump = {**model.model_dump(), **kwargs}
        super().__init__(**model_dump)
        self.scheme_name = scheme_name or self.__class__.__name__
        self.__auto_error__ = auto_error

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        authorization = request.headers.get("Authorization")
        if not authorization:
            if self.__auto_error__:
                raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Not authenticated")
            return None

        scheme, credentials = get_authorization_scheme_param(authorization)
        if not (scheme and credentials):
            if self.__auto_error__:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN, detail="Invalid authentication credentials"
                )
            return None

        return HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)


class HTTPBasic(HTTPBase):
    def __init__(
        self,
        *,
        scheme_name: Annotated[str | None, Doc("The name of the security scheme.")] = None,
        realm: Annotated[str | None, Doc("The HTTP Basic authentication realm.")] = None,
        description: Annotated[str | None, Doc("Description of the security scheme.")] = None,
        auto_error: Annotated[
            bool,
            Doc(
                "Whether to automatically raise an error if authentication fails. "
                "If set to False, the dependency result will be None when authentication is not provided."
            ),
        ] = True,
    ):
        model = HTTPBaseModel(scheme="basic", description=description)
        super().__init__(**model.model_dump())
        self.scheme_name = scheme_name or self.__class__.__name__
        self.realm = realm
        self.__auto_error__ = auto_error

    async def __call__(self, request: Request) -> HTTPBasicCredentials | None:
        authorization = request.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(authorization)

        unauthorized_headers = {
            "WWW-Authenticate": f'Basic realm="{self.realm}"' if self.realm else "Basic"
        }

        if not authorization or scheme.lower() != "basic":
            if self.__auto_error__:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers=unauthorized_headers,
                )
            return None

        try:
            data = b64decode(param).decode("ascii")
            username, separator, password = data.partition(":")
            if not separator:
                raise ValueError("Invalid credentials format")
        except (ValueError, UnicodeDecodeError, binascii.Error):
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers=unauthorized_headers,
            ) from None

        return HTTPBasicCredentials(username=username, password=password)


class HTTPBearer(HTTPBase):
    def __init__(
        self,
        *,
        bearerFormat: Annotated[str | None, Doc("The format of the Bearer token.")] = None,
        scheme_name: Annotated[str | None, Doc("The name of the security scheme.")] = None,
        description: Annotated[str | None, Doc("Description of the security scheme.")] = None,
        auto_error: Annotated[
            bool,
            Doc(
                "Whether to automatically raise an error if authentication fails. "
                "If set to False, the dependency result will be None when authentication is not provided."
            ),
        ] = True,
    ):
        model = HTTPBearerModel(bearerFormat=bearerFormat, description=description)
        super().__init__(**model.model_dump())
        self.scheme_name = scheme_name or self.__class__.__name__
        self.__auto_error__ = auto_error

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        authorization = request.headers.get("Authorization")
        if not authorization:
            if self.__auto_error__:
                raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Not authenticated")
            return None

        scheme, credentials = get_authorization_scheme_param(authorization)
        if not (scheme and credentials) or scheme.lower() != "bearer":
            if self.__auto_error__:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN,
                    detail="Invalid authentication credentials",
                )
            return None

        return HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)


class HTTPDigest(HTTPBase):
    def __init__(
        self,
        *,
        scheme_name: Annotated[str | None, Doc("The name of the security scheme.")] = None,
        description: Annotated[str | None, Doc("Description of the security scheme.")] = None,
        auto_error: Annotated[
            bool,
            Doc(
                "Whether to automatically raise an error if authentication fails. "
                "If set to False, the dependency result will be None when authentication is not provided."
            ),
        ] = True,
    ):
        model = HTTPBaseModel(scheme="digest", description=description)
        super().__init__(**model.model_dump())
        self.scheme_name = scheme_name or self.__class__.__name__
        self.__auto_error__ = auto_error

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        authorization = request.headers.get("Authorization")
        scheme, credentials = get_authorization_scheme_param(authorization)
        if not (authorization and scheme and credentials):
            if self.__auto_error__:
                raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Not authenticated")
            else:
                return None
        if scheme.lower() != "digest":
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail="Invalid authentication credentials",
            )
        return HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)
