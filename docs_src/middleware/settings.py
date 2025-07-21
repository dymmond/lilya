from __future__ import annotations

from lilya.conf.global_settings import Settings
from lilya.middleware import DefineMiddleware
from lilya.middleware.compression import GZipMiddleware
from lilya.middleware.httpsredirect import HTTPSRedirectMiddleware


class AppSettings(Settings):
    @property
    def middleware(self) -> list[DefineMiddleware]:
        """
        All the middlewares to be added when the application starts.
        """
        return [
            DefineMiddleware(HTTPSRedirectMiddleware),
            DefineMiddleware(GZipMiddleware, minimum_size=500, compresslevel=9),
        ]
