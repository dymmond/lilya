from typing import Literal

from pydantic import AnyUrl, BaseModel, ConfigDict, Field


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


class SecurityScheme(BaseModel):
    """Defines a security scheme that can be used by the operations.

    Supported schemes are HTTP authentication,
    an API key (either as a header, a cookie parameter or as a query parameter),
    mutual TLS (use of a client certificate),
    OAuth2's common flows (implicit, password, client credentials and authorization code)
    as defined in [RFC6749](https://tools.ietf.org/html/rfc6749),
    and [OpenID Connect Discovery](https://tools.ietf.org/html/draft-ietf-oauth-discovery-06).

    Please note that as of 2020, the implicit flow is about to be deprecated by
    [OAuth 2.0 Security Best Current Practice](https://tools.ietf.org/html/draft-ietf-oauth-security-topics).
    Recommended for most use case is Authorization Code Grant flow with PKCE.
    """

    type: Literal["apiKey", "http", "mutualTLS", "oauth2", "openIdConnect"]
    """
    **REQUIRED**. The type of the security scheme.
    """

    description: str | None = None
    """
    A description for security scheme.
    [CommonMark syntax](https://spec.commonmark.org/) MAY be used for rich text representation.
    """

    name: str | None = None
    """
    **REQUIRED** for `apiKey`. The name of the header, query or cookie parameter to be used.
    """

    security_scheme_in: Literal["query", "header", "cookie"] | None = Field(
        alias="in", default=None
    )
    """
    **REQUIRED** for `apiKey`. The location of the API key.
    """

    scheme: str | None = None
    """
    **REQUIRED** for `http`. The name of the HTTP Authorization scheme to be used in the
    [Authorization header as defined in RFC7235](https://tools.ietf.org/html/rfc7235#section-5.1).

    The values used SHOULD be registered in the
    [IANA Authentication Scheme registry](https://www.iana.org/assignments/http-authschemes/http-authschemes.xhtml).
    """

    bearerFormat: str | None = None
    """
    A hint to the client to identify how the bearer token is formatted.

    Bearer tokens are usually generated by an authorization server,
    so this information is primarily for documentation purposes.
    """

    flows: OAuthFlows | None = None
    """
    **REQUIRED** for `oauth2`. An object containing configuration information for the flow types supported.
    """

    openIdConnectUrl: AnyUrl | str | None = None
    """
    **REQUIRED** for `openIdConnect`. OpenId Connect URL to discover OAuth2 configuration values.
    This MUST be in the form of a URL. The OpenID Connect standard requires the use of TLS.
    """
    model: BaseModel | None = None
    """
    An optional model to be used for the security scheme.
    """

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {"type": "http", "scheme": "basic"},
                {"type": "apiKey", "name": "api_key", "in": "header"},
                {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
                {
                    "type": "oauth2",
                    "flows": {
                        "implicit": {
                            "authorizationUrl": "https://example.com/api/oauth/dialog",
                            "scopes": {
                                "write:pets": "modify pets in your account",
                                "read:pets": "read your pets",
                            },
                        }
                    },
                },
                {"type": "openIdConnect", "openIdConnectUrl": "https://example.com/openIdConnect"},
                {
                    "type": "openIdConnect",
                    "openIdConnectUrl": "openIdConnect",
                },
            ]
        },
    )


class SecurityBase(SecurityScheme):
    scheme_name: str | None = None
    """
    An optional name for the security scheme.
    """
    __auto_error__: bool = False
    """
    A flag to indicate if automatic error handling should be enabled.
    """
    __is_security__: bool = True
    """A flag to indicate that this is a security scheme. """


class HttpSecurityBase(SecurityScheme):
    scheme_name: str | None = None
    """
    An optional name for the security scheme.
    """
    realm: str | None = None
    """
    An optional realm for the security scheme.
    """
    __auto_error__: bool = False
    """
    A flag to indicate if automatic error handling should be enabled.
    """
