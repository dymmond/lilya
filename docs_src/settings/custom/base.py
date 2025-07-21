from __future__ import annotations

from lilya.conf.global_settings import Settings
from lilya.middleware import DefineMiddleware
from lilya.middleware.httpsredirect import HTTPSRedirectMiddleware


class AppSettings(Settings):
    # The default is already production but for this example
    # we set again the variable
    environment: bool = "production"
    debug: bool = False
    reload: bool = False

    @property
    def middleware(self) -> list[DefineMiddleware]:
        return [DefineMiddleware(HTTPSRedirectMiddleware)]
