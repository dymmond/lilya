from lilya.apps import Lilya
from lilya.contrib.openapi.config import OpenAPIConfig as BaseOpenAPIConfig

class OpenAPIConfig(BaseOpenAPIConfig):
    """
    Custom OpenAPI configuration for Lilya applications.

    This class extends the base OpenAPI configuration to provide
    additional settings specific to Lilya applications.
    """

    title = "My Lilya App",
    version = "1.0.0",
    description = "This is a Lilya application with OpenAPI support.",
    contact = {
        "name": "Support Team",
        "email": "myapp@test.com"
    }

openapi_config = OpenAPIConfig()

app = Lilya(
    routes=[],
    openapi_config=openapi_config,
    enable_openapi=True
)
