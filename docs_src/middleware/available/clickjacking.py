from __future__ import annotations

from dataclasses import dataclass

from lilya.apps import Lilya
from lilya.conf import Settings
from lilya.middleware import DefineMiddleware
from lilya.middleware.clickjacking import XFrameOptionsMiddleware

routes = [...]

# Option one
middleware = [DefineMiddleware(XFrameOptionsMiddleware)]

app = Lilya(routes=routes, middleware=middleware)


# Option two - Using the settings module
# Running the application with your custom settings -> LILYA_SETTINGS_MODULE
@dataclass
class AppSettings(Settings):
    x_frame_options: str = "SAMEORIGIN"

    def middleware(self) -> list[DefineMiddleware]:
        return [
            DefineMiddleware(XFrameOptionsMiddleware),
        ]
