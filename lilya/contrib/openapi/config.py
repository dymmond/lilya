from collections.abc import Sequence
from typing import Annotated, Any

from pydantic import AnyUrl, BaseModel

from lilya import __version__
from lilya.contrib.openapi.docs import (
    get_rapidoc_ui_html,
    get_redoc_html,
    get_stoplight_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from lilya.contrib.openapi.utils import get_openapi
from lilya.requests import Request
from lilya.responses import HTMLResponse, JSONResponse
from lilya.types import Doc


class OpenAPIConfig(BaseModel):
    """
    An instance of [OpenAPIConfig](https://lilya.dev/openapi/#openapiconfig).

    This object is then used by Lilya to create the [OpenAPI](https://lilya.dev/openapi/) documentation.

    **Note**: Here is where the defaults for Lilya OpenAPI are overriden and if
    this object is passed, then the previous defaults of the settings are ignored.

    !!! Tip
        This is the way you could override the defaults all in one go
        instead of doing attribute by attribute.

    **Example**

    ```python
    from lilya.contrib.openapi.config import OpenAPIConfig

    openapi_config = OpenAPIConfig(
        title="Black Window",
        openapi_url="/openapi.json",
        docs_url="/docs/swagger",
        redoc_url="/docs/redoc",
    )

    app = Lilya(openapi_config=openapi_config)
    ```

    !!! Important
        Lilya when starting an application, checks the attributes and looks for an
        `openapi_config` parameter.

        If the parameter is not specified, `Lilya` will automatically use the internal
        settings system to generate the default OpenAPIConfig and populate the values.
    """

    title: Annotated[
        str | None,
        Doc(
            """
            Title of the application/API documentation.
            """
        ),
    ] = "Lilya"
    version: Annotated[
        str | None,
        Doc(
            """
            The version of the API documentation.
            """
        ),
    ] = __version__
    summary: Annotated[
        str | None,
        Doc(
            """
            Simple and short summary text of the application/API.
            """
        ),
    ] = "Lilya application"
    description: Annotated[
        str | None,
        Doc(
            """
            A longer and more descriptive explanation of the application/API documentation.
            """
        ),
    ] = "Yet another framework/toolkit that delivers."
    contact: Annotated[
        dict[str, str | Any] | None,
        Doc(
            """
            API contact information. This is an OpenAPI schema contact, meaning, in a dictionary format compatible with OpenAPI or an instance of `lilya.openapi.schemas.v3_1_0.contact.Contact`.
            """
        ),
    ] = {"name": "Lilya", "url": "https://lilya.dev", "email": "admin@myapp.com"}
    terms_of_service: Annotated[
        AnyUrl | None,
        Doc(
            """
            URL to a page that contains terms of service.
            """
        ),
    ] = None
    license: Annotated[
        dict[str, str | Any] | None,
        Doc(
            """
            API Licensing information. This is an OpenAPI schema licence, meaning, in a dictionary format compatible with OpenAPI or an instance of `lilya.openapi.schemas.v3_1_0.license.License`.
            """
        ),
    ] = None
    security: Annotated[
        Any | None,
        Doc(
            """
            API Security requirements information. This is an OpenAPI schema security, meaning, in a dictionary format compatible with OpenAPI or an instance of `lilya.openapi.schemas.v3_1_0.security_requirement.SecurityScheme`.
            """
        ),
    ] = None
    servers: Annotated[
        list[dict[str, str | Any]] | None,
        Doc(
            """
            A python list with dictionary compatible with OpenAPI specification.
            """
        ),
    ] = [{"url": "/"}]
    tags: Annotated[
        list[str] | None,
        Doc(
            """
            A list of OpenAPI compatible tag (string) information.
            """
        ),
    ] = None
    openapi_version: Annotated[
        str | None,
        Doc(
            """
            The version of the OpenAPI being used. Lilya uses the version 3.1.0 by
            default and tis can be useful if you want to trick some of the existing tools
            that require a lower version.
            """
        ),
    ] = "3.1.0"
    openapi_url: Annotated[
        str | None,
        Doc(
            """
            URL of the `openapi.json` in the format of a path.

            Example: `/openapi.json.`
            """
        ),
    ] = "/openapi.json"
    root_path_in_servers: Annotated[
        bool,
        Doc(
            """
            A `boolean` flag indicating if the root path should be included in the servers.
            """
        ),
    ] = True
    docs_url: Annotated[
        str | None,
        Doc(
            """
            String default relative URL where the Swagger documentation
            shall be accessed in the application.

            Example: '/docs/swagger`.
            """
        ),
    ] = "/docs/swagger"
    redoc_url: Annotated[
        str | None,
        Doc(
            """
            String default relative URL where the ReDoc documentation
            shall be accessed in the application.

            Example: '/docs/swagger`.
            """
        ),
    ] = "/docs/redoc"
    swagger_ui_oauth2_redirect_url: Annotated[
        str | None,
        Doc(
            """
            String default relative URL where the Swagger UI OAuth Redirect URL
            shall be accessed in the application.

            Example: `/docs/oauth2-redirect`.
            """
        ),
    ] = "/docs/oauth2-redirect"
    redoc_js_url: Annotated[
        str | None,
        Doc(
            """
            String default URL where the ReDoc Javascript is located
            and used within OpenAPI documentation,

            Example: `https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js`.
            """
        ),
    ] = "https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"
    redoc_favicon_url: Annotated[
        str | None,
        Doc(
            """
            String default URL where the ReDoc favicon is located
            and used within OpenAPI documentation,

            Example: `https://lilya.dev/statics/images/favicon.ico`.
            """
        ),
    ] = "https://www.lilya.dev/statics/images/favicon.ico"
    swagger_ui_init_oauth: Annotated[
        dict[str, Any] | None,
        Doc(
            """
            String default relative URL where the Swagger Init Auth documentation
            shall be accessed in the application.
            """
        ),
    ] = None
    swagger_ui_parameters: Annotated[
        dict[str, Any] | None,
        Doc(
            """
            A mapping with parameters to be passed onto Swagger.
            """
        ),
    ] = None
    swagger_js_url: Annotated[
        str | None,
        Doc(
            """
            Boolean flag indicating if the google fonts shall be used
            in the ReDoc OpenAPI Documentation.
            """
        ),
    ] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.4/swagger-ui-bundle.min.js"
    swagger_css_url: Annotated[
        str | None,
        Doc(
            """
            String default URL where the Swagger Javascript is located
            and used within OpenAPI documentation,

            Example: `https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.1.3/swagger-ui-bundle.min.js`.
            """
        ),
    ] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.4/swagger-ui.min.css"
    swagger_favicon_url: Annotated[
        str | None,
        Doc(
            """
            String default URL where the Swagger favicon is located
            and used within OpenAPI documentation,

            Example: `https://lilya.dev/statics/images/favicon.ico`.
            """
        ),
    ] = "https://lilya.dev/statics/images/favicon.ico"
    with_google_fonts: Annotated[
        bool,
        Doc(
            """
            Boolean flag indicating if the google fonts shall be used
            in the ReDoc OpenAPI Documentation.
            """
        ),
    ] = True
    stoplight_js_url: Annotated[
        str | None,
        Doc(
            """
            Boolean flag indicating if the google fonts shall be used
            in the ReDoc OpenAPI Documentation.
            """
        ),
    ] = "https://unpkg.com/@stoplight/elements/web-components.min.js"
    stoplight_css_url: Annotated[
        str | None,
        Doc(
            """
            String default URL where the Stoplight CSS is located
            and used within OpenAPI documentation,

            Example: `https://unpkg.com/@stoplight/elements/styles.min.css`.
            """
        ),
    ] = "https://unpkg.com/@stoplight/elements/styles.min.css"
    stoplight_url: Annotated[
        str | None,
        Doc(
            """
            String default relative URL where the Stoplight documentation
            shall be accessed in the application.

            Example: `/docs/elements`.
            """
        ),
    ] = "/docs/elements"
    stoplight_favicon_url: Annotated[
        str | None,
        Doc(
            """
            String default URL where the Stoplight favicon is located
            and used within OpenAPI documentation,

            Example: `https://lilya.dev/statics/images/favicon.ico`.
            """
        ),
    ] = None
    rapidoc_url: Annotated[
        str | None,
        Doc(
            """
            String default relative URL where the Rapidoc documentation
            shall be accessed in the application.

            Example: `/docs/rapidoc`.
            """
        ),
    ] = "/docs/rapidoc"
    rapidoc_js_url: Annotated[
        str | None,
        Doc(
            """
            String default URL where the Stoplight Javascript is located
            and used within OpenAPI documentation,
            """
        ),
    ] = "https://unpkg.com/rapidoc@9.3.4/dist/rapidoc-min.js"
    rapidoc_favicon_url: Annotated[
        str | None,
        Doc(
            """
            String default URL where the RapiDoc favicon is located
            and used within OpenAPI documentation,

            Example: `https://lilya.dev/statics/images/favicon.ico`.
            """
        ),
    ] = "https://lilya.dev/statics/images/favicon.ico"
    webhooks: Annotated[
        Sequence[Any] | None,
        Doc(
            """
            This is the same principle of the `routes` but for OpenAPI webhooks.

            When a webhook is added, it will automatically add them into the
            OpenAPI documentation.
            """
        ),
    ] = None

    def openapi(self, app: Any) -> dict[str, Any]:
        """Loads the OpenAPI routing schema"""
        openapi_schema = get_openapi(
            app=app,
            title=self.title,
            version=self.version,
            openapi_version=self.openapi_version,
            summary=self.summary,
            description=self.description,
            routes=app.routes,
            tags=self.tags,
            servers=self.servers,
            terms_of_service=self.terms_of_service,  # type: ignore
            contact=self.contact,
            license=self.license,
            webhooks=self.webhooks,
        )
        app.openapi_schema = openapi_schema
        return openapi_schema

    def enable(self, app: Any) -> None:
        """Enables the OpenAPI documentation"""
        if self.openapi_url:
            urls = {server.get("url") for server in self.servers}
            server_urls = set(urls)

            async def _openapi(request: Request) -> JSONResponse:
                root_path = request.scope.get("root_path", "").rstrip("/")

                if root_path not in server_urls:
                    if root_path and self.root_path_in_servers:
                        self.servers.insert(0, {"url": root_path})
                        server_urls.add(root_path)
                return JSONResponse(self.openapi(app))

            app.add_route(
                path=self.openapi_url,
                handler=_openapi,
                include_in_schema=False,
            )

        if self.openapi_url and self.docs_url:

            async def swagger_ui_html(
                request: Request,
            ) -> HTMLResponse:  # pragma: no cover
                root_path = request.scope.get("root_path", "").rstrip("/")
                openapi_url = root_path + self.openapi_url
                oauth2_redirect_url = self.swagger_ui_oauth2_redirect_url
                if oauth2_redirect_url:
                    oauth2_redirect_url = root_path + oauth2_redirect_url
                return get_swagger_ui_html(
                    openapi_url=openapi_url,
                    title=self.title + " - Swagger UI",
                    oauth2_redirect_url=oauth2_redirect_url,
                    init_oauth=self.swagger_ui_init_oauth,
                    swagger_ui_parameters=self.swagger_ui_parameters,
                    swagger_js_url=self.swagger_js_url,
                    swagger_favicon_url=self.swagger_favicon_url,
                    swagger_css_url=self.swagger_css_url,
                )

            app.add_route(
                path=self.docs_url,
                handler=swagger_ui_html,
                include_in_schema=False,
            )

        if self.swagger_ui_oauth2_redirect_url:

            async def swagger_ui_redirect(
                request: Request,
            ) -> HTMLResponse:  # pragma: no cover
                return get_swagger_ui_oauth2_redirect_html()

            app.add_route(
                path=self.swagger_ui_oauth2_redirect_url,
                handler=swagger_ui_redirect,
                include_in_schema=False,
            )

        if self.openapi_url and self.redoc_url:

            async def redoc_html(request: Request) -> HTMLResponse:  # pragma: no cover
                root_path = request.scope.get("root_path", "").rstrip("/")
                openapi_url = root_path + self.openapi_url
                return get_redoc_html(
                    openapi_url=openapi_url,
                    title=self.title + " - ReDoc",
                    redoc_js_url=self.redoc_js_url,
                    redoc_favicon_url=self.redoc_favicon_url,
                    with_google_fonts=self.with_google_fonts,
                )

            app.add_route(
                path=self.redoc_url,
                handler=redoc_html,
                include_in_schema=False,
            )

        if self.openapi_url and self.stoplight_url:

            async def stoplight_html(
                request: Request,
            ) -> HTMLResponse:  # pragma: no cover
                root_path = request.scope.get("root_path", "").rstrip("/")
                openapi_url = root_path + self.openapi_url
                return get_stoplight_html(
                    openapi_url=openapi_url,
                    title=self.title + " - Stoplight Elements",
                    stoplight_js=self.stoplight_js_url,
                    stoplight_css=self.stoplight_css_url,
                    stoplight_favicon_url=self.stoplight_favicon_url,
                )

            app.add_route(
                path=self.stoplight_url,
                handler=stoplight_html,
                include_in_schema=False,
            )

        if self.openapi_url and self.rapidoc_url:

            async def rapidoc_html(
                request: Request,
            ) -> HTMLResponse:  # pragma: no cover
                root_path = request.scope.get("root_path", "").rstrip("/")
                openapi_url = root_path + self.openapi_url

                return get_rapidoc_ui_html(
                    openapi_url=openapi_url,
                    title=self.title + " - RapiDoc",
                    rapidoc_js_url=self.rapidoc_js_url,
                    rapidoc_favicon_url=self.rapidoc_favicon_url,
                )

            app.add_route(
                path=self.rapidoc_url,
                handler=rapidoc_html,
                include_in_schema=False,
            )
