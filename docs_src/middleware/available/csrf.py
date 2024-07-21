from __future__ import annotations

from dataclasses import dataclass

from lilya.apps import Lilya
from lilya.conf.global_settings import Settings
from lilya.middleware import DefineMiddleware
from lilya.middleware.csrf import CSRFMiddleware

routes = [...]

# Option one
middleware = [DefineMiddleware(CSRFMiddleware, secret="your-long-unique-secret")]

app = Lilya(routes=routes, middleware=middleware)


# Option two - Using the settings module
# Running the application with your custom settings -> LILYA_SETTINGS_MODULE
@dataclass
class AppSettings(Settings):
    @property
    def middleware(self) -> list[DefineMiddleware]:
        return [
            DefineMiddleware(CSRFMiddleware, secret="your-long-unique-secret"),
        ]
