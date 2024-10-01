from __future__ import annotations

from dataclasses import dataclass

from lilya.apps import Lilya
from lilya.conf.global_settings import Settings
from lilya.middleware import DefineMiddleware
from lilya.middleware.clientip import ClientIPMiddleware

routes = [...]

# Only trust unix (no client ip is set) (default)
trusted_proxies = ["unix"]
# No forwarded ip headers will be evaluated. Only the direct ip is accepted
trusted_proxies = []
# trust all client ips to provide forwarded headers
trusted_proxies = ["*"]


# Option one
middleware = [DefineMiddleware(ClientIPMiddleware, trusted_proxies=trusted_proxies)]

app = Lilya(routes=routes, middleware=middleware)


# Option two - Using the settings module
# Running the application with your custom settings -> LILYA_SETTINGS_MODULE
@dataclass
class AppSettings(Settings):

    def middleware(self) -> list[DefineMiddleware]:
        return [
            DefineMiddleware(ClientIPMiddleware, trusted_proxies=trusted_proxies),
        ]
