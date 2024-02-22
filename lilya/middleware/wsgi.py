from __future__ import annotations

from typing import cast

from lilya._internal._module_loading import import_string

try:
    from a2wsgi.wsgi import WSGIMiddleware as A2WSGIMiddleware  # noqa
    from a2wsgi.wsgi_typing import WSGIApp
except ModuleNotFoundError:
    raise RuntimeError(
        "You need to install the package `a2wsgi` to be able to use this middleware. "
        "Simply run `pip install a2wsgi`."
    ) from None


class WSGIMiddleware(A2WSGIMiddleware):
    def __init__(self, app: WSGIApp | str, workers: int = 10) -> None:
        if isinstance(app, str):
            app = cast(WSGIApp, import_string(app))
        super().__init__(app, workers)
