from lilya.contrib.openapi.config import OpenAPIConfig as BaseOpenAPIConfig

class OpenAPIConfig(BaseOpenAPIConfig):
    """
    Custom OpenAPI configuration for Lilya applications.

    This class extends the base OpenAPI configuration to provide
    additional settings specific to Lilya applications.
    """

    title: str = "My App"
