from dataclasses import dataclass
from typing import List

from lilya.conf import Settings
from lilya.middleware import DefineMiddleware
from lilya.middleware.compression import GZipMiddleware
from lilya.middleware.httpsredirect import HTTPSRedirectMiddleware


@dataclass
class AppSettings(Settings):
    @property
    def middleware(self) -> List[DefineMiddleware]:
        """
        All the middlewares to be added when the application starts.
        """
        return [
            DefineMiddleware(HTTPSRedirectMiddleware),
            DefineMiddleware(GZipMiddleware, minimum_size=500, compresslevel=9),
        ]
