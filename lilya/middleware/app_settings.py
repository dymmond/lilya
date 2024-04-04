from __future__ import annotations

from typing import TYPE_CHECKING

from lilya.conf import reload_settings, settings
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.types import ASGIApp, Receive, Scope, Send

if TYPE_CHECKING:
    from lilya.apps import Lilya


class ApplicationSettingsMiddleware(MiddlewareProtocol):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        app: Lilya = scope["app"]

        if getattr(app, "settings_module", None) is not None:
            settings.configure(app.settings)
        else:
            app_settings = reload_settings()
            settings.configure(app_settings())
        await self.app(scope, receive, send)
