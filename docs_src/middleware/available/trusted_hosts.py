from __future__ import annotations

from dataclasses import dataclass

from lilya.apps import Lilya
from lilya.conf import Settings
from lilya.middleware import DefineMiddleware
from lilya.middleware.trustedhost import TrustedHostMiddleware

routes = [...]

# Option one
middleware = [
    DefineMiddleware(TrustedHostMiddleware, allowed_hosts=["www.example.com", "*.example.com"])
]

app = Lilya(routes=routes, middleware=middleware)


# Option two - Using the settings module
# Running the application with your custom settings -> LILYA_SETTINGS_MODULE
@dataclass
class AppSettings(Settings):
    @property
    def middleware(self) -> list[DefineMiddleware]:
        return [
            DefineMiddleware(
                TrustedHostMiddleware, allowed_hosts=["www.example.com", "*.example.com"]
            ),
        ]
