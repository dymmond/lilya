from dataclasses import dataclass
from typing import List

from lilya.app import Lilya
from lilya.conf import Settings
from lilya.middleware import DefineMiddleware
from lilya.middleware.cors import CORSMiddleware

routes = [...]

# Option one
middleware = [DefineMiddleware(CORSMiddleware, allow_origins=["*"])]

app = Lilya(routes=routes, middleware=middleware)


# Option two - Using the settings module
# Running the application with your custom settings -> SETTINGS_MODULE
@dataclass
class AppSettings(Settings):
    @property
    def middleware(self) -> List[DefineMiddleware]:
        return [
            DefineMiddleware(CORSMiddleware, allow_origins=["*"]),
        ]