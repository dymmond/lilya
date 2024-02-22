from dataclasses import dataclass
from typing import List

from lilya.apps import Lilya
from lilya.conf import Settings
from lilya.middleware import DefineMiddleware
from lilya.middleware.sessions import SessionMiddleware

routes = [...]

# Option one
middleware = [DefineMiddleware(SessionMiddleware, secret_key=...)]

app = Lilya(routes=routes, middleware=middleware)


# Option two - Using the settings module
# Running the application with your custom settings -> SETTINGS_MODULE
@dataclass
class AppSettings(Settings):
    @property
    def middleware(self) -> List[DefineMiddleware]:
        return [
            DefineMiddleware(SessionMiddleware, secret_key=...),
        ]
