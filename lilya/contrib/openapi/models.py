from typing import Literal

from pydantic import AnyUrl, BaseModel, ConfigDict, Field

from lilya.contrib.openapi.enums import APIKeyIn, SecuritySchemeType
from lilya.contrib.security.base import SecurityScheme


class OAuthFlow(BaseModel):
    """Configuration details for a supported OAuth Flow."""

    authorizationUrl: AnyUrl | str | None = None
    """
    **REQUIRED** for `oauth2 ("implicit", "authorizationCode")`.
    The authorization URL to be used for this flow.
    This MUST be in the form of a URL.
    The OAuth2 standard requires the use of TLS.
    """

    tokenUrl: AnyUrl | str | None = None
    """
    **REQUIRED** for `oauth2 ("password", "clientCredentials", "authorizationCode")`.
    The token URL to be used for this flow.
    This MUST be in the form of a URL.
    The OAuth2 standard requires the use of TLS.
    """

    refreshUrl: AnyUrl | str | None = None
    """
    The URL to be used for obtaining refresh tokens.
    This MUST be in the form of a URL.
    The OAuth2 standard requires the use of TLS.
    """

    scopes: dict[str, str] | None = None
    """
    **REQUIRED** for `oauth2`. The available scopes for the OAuth2 security scheme.
    A map between the scope name and a short description for it.
    The map MAY be empty.
    """

    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "examples": [
                {
                    "authorizationUrl": "https://example.com/api/oauth/dialog",
                    "scopes": {
                        "write:pets": "modify pets in your account",
                        "read:pets": "read your pets",
                    },
                },
                {
                    "authorizationUrl": "https://example.com/api/oauth/dialog",
                    "tokenUrl": "https://example.com/api/oauth/token",
                    "scopes": {
                        "write:pets": "modify pets in your account",
                        "read:pets": "read your pets",
                    },
                },
                {
                    "authorizationUrl": "/api/oauth/dialog",  # issue #5: allow relative path
                    "tokenUrl": "/api/oauth/token",  # issue #5: allow relative path
                    "refreshUrl": "/api/oauth/token",  # issue #5: allow relative path
                    "scopes": {
                        "write:pets": "modify pets in your account",
                        "read:pets": "read your pets",
                    },
                },
            ]
        },
    )


class OAuthFlows(BaseModel):
    """Allows configuration of the supported OAuth Flows."""

    implicit: OAuthFlow | None = None
    """
    Configuration for the OAuth Implicit flow
    """

    password: OAuthFlow | None = None
    """
    Configuration for the OAuth Resource Owner Password flow
    """

    clientCredentials: OAuthFlow | None = None
    """
    Configuration for the OAuth Client Credentials flow.

    Previously called `application` in OpenAPI 2.0.
    """

    authorizationCode: OAuthFlow | None = None
    """
    Configuration for the OAuth Authorization Code flow.

    Previously called `accessCode` in OpenAPI 2.0.
    """

    model_config = ConfigDict(extra="ignore")


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
