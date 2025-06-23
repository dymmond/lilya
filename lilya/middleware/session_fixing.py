from __future__ import annotations

from typing import Protocol

from lilya.enums import ScopeType
from lilya.exceptions import ImproperlyConfigured
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.types import ASGIApp, Receive, Scope, Send


class NotificationFunctionType(Protocol):
    def __call__(
        self, *, old_session: dict, old_ip: str | None, new_session: dict, new_ip: str
    ) -> None: ...


class SessionFixingMiddleware(MiddlewareProtocol):
    session_name_clientip: str = "real-clientip"
    scope_name_clientip: str = "real-clientip"

    def __init__(self, app: ASGIApp, notify_fn: NotificationFunctionType | None) -> None:
        self.app = app
        self.notify_fn = notify_fn
        self.scopes: set[str] = {ScopeType.HTTP, ScopeType.WEBSOCKET}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        ASGI application callable.
        """
        if scope["type"] not in self.scopes:
            await self.app(scope, receive, send)
            return
        try:
            session = scope["session"]
            if not isinstance(session, dict):
                raise KeyError
        except KeyError:
            raise ImproperlyConfigured(
                "'session' not set. Ensure 'SessionMiddleware' is properly installed."
            ) from None
        try:
            clientip = scope[self.scope_name_clientip]
        except KeyError:
            raise ImproperlyConfigured(
                f"'{self.scope_name_clientip}' not set. Ensure 'ClientIPMiddleware' or 'ClientIPScopeOnlyMiddleware' is properly installed."
            ) from None
        session_clientip = session.get(self.session_name_clientip)
        if session_clientip is None:
            session[self.session_name_clientip] = clientip
            self.notify_fn(
                old_session=session,
                new_session=session,
                old_ip=None,
                new_ip=clientip,
            )
        elif session_clientip != clientip:
            if self.notify_fn:
                old_session = session.copy()
                session.clear()
                session[self.session_name_clientip] = clientip
                self.notify_fn(
                    old_session=old_session,
                    new_session=session,
                    old_ip=session_clientip,
                    new_ip=clientip,
                )
            else:
                session.clear()
                session[self.session_name_clientip] = clientip
        await self.app(scope, receive, send)
