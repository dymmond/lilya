from typing import Literal

from pydantic import Field

from lilya.contrib.openapi.enums import APIKeyIn, SecuritySchemeType
from lilya.contrib.security.base import OAuthFlows, SecurityScheme


class APIKey(SecurityScheme):
    type: Literal["apiKey", "http", "mutualTLS", "oauth2", "openIdConnect"] = Field(
        default=SecuritySchemeType.apiKey.value,
        alias="type",
    )
    param_in: APIKeyIn = Field(alias="in")
    name: str


class HTTPBase(SecurityScheme):
    type: Literal["apiKey", "http", "mutualTLS", "oauth2", "openIdConnect"] = Field(
        default=SecuritySchemeType.http.value,
        alias="type",
    )
    scheme: str


class HTTPBearer(HTTPBase):
    scheme: Literal["bearer"] = "bearer"
    bearerFormat: str | None = None


class OAuth2(SecurityScheme):
    type: Literal["apiKey", "http", "mutualTLS", "oauth2", "openIdConnect"] = Field(
        default=SecuritySchemeType.oauth2.value, alias="type"
    )
    flows: OAuthFlows


class OpenIdConnect(SecurityScheme):
    type: Literal["apiKey", "http", "mutualTLS", "oauth2", "openIdConnect"] = Field(
        default=SecuritySchemeType.openIdConnect.value, alias="type"
    )
    openIdConnectUrl: str
