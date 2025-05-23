from __future__ import annotations

import orjson
from dataclasses import dataclass

from lilya.apps import Lilya
from lilya.conf.global_settings import Settings
from lilya.middleware import DefineMiddleware
from lilya.middleware.sessions import SessionMiddleware



routes = [...]

# Option one
middleware = [DefineMiddleware(SessionMiddleware, session_serializer=orjson.dumps, session_deserializer=orjson.loads, secret_key=...)]

app = Lilya(routes=routes, middleware=middleware)


# Option two - Using the settings module
# Running the application with your custom settings -> LILYA_SETTINGS_MODULE
@dataclass
class AppSettings(Settings):
    @property
    def middleware(self) -> list[DefineMiddleware]:
        return [
            DefineMiddleware(SessionMiddleware, session_serializer=orjson.dumps, session_deserializer=orjson.loads, secret_key=...),
        ]
