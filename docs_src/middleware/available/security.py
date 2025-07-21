from __future__ import annotations

from lilya.apps import Lilya
from lilya.conf.global_settings import Settings
from lilya.middleware import DefineMiddleware
from lilya.middleware.security import SecurityMiddleware

routes = [...]

content_policy_dict = {
    "default-src": "'self'",
    "img-src": [
        "*",
        "data:",
    ],
    "connect-src": "'self'",
    "script-src": "'self'",
    "style-src": ["'self'", "'unsafe-inline'"],
    "script-src-elem": [
        "https://unpkg.com/@stoplight/elements/web-components.min.jss",
    ],
    "style-src-elem": [
        "https://unpkg.com/@stoplight/elements/styles.min.css",
    ],
}

# Option one
middleware = [DefineMiddleware(SecurityMiddleware, content_policy=content_policy_dict)]

app = Lilya(routes=routes, middleware=middleware)


# Option two - Using the settings module
# Running the application with your custom settings -> LILYA_SETTINGS_MODULE
class AppSettings(Settings):

    def middleware(self) -> list[DefineMiddleware]:
        return [
            DefineMiddleware(SecurityMiddleware, content_policy=content_policy_dict),
        ]
