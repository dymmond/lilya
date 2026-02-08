from __future__ import annotations

from lilya.apps import Lilya
from lilya.conf.global_settings import Settings
from lilya.middleware import DefineMiddleware
from lilya.middleware.asyncexit import AsyncExitStackMiddleware

routes = [...]

# Option one
middleware = [DefineMiddleware(AsyncExitStackMiddleware, debug=True)]

app = Lilya(routes=routes, middleware=middleware)


# Option two - Using the settings module
# Running the application with your custom settings -> LILYA_SETTINGS_MODULE
class AppSettings(Settings):
    @property
    def middleware(self) -> list[DefineMiddleware]:
        return [
            DefineMiddleware(AsyncExitStackMiddleware, debug=True),
        ]
