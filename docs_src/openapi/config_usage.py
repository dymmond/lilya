from lilya.apps import Lilya
from lilya.contrib.openapi.config import OpenAPIConfig

config = OpenAPIConfig(
    title="My Cool API",
    openapi_url="/api/schema",
    docs_url="/docs/swaggerui",
    redoc_url="/docs/redocpage",
    servers=[{"url": "https://api.mycompany.com"}],
    tags=["users", "items"],
    security=[{"BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}}],
    # … override any other fields as needed …
)

app = Lilya(
    routes=[...],
    openapi_config=config
)
