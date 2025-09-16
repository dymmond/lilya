from __future__ import annotations

from lilya.contrib.mail.backends.base import BaseMailBackend
from lilya.contrib.mail.exceptions import BackendNotConfigured
from lilya.contrib.mail.mailer import Mailer
from lilya.types import ASGIApp


def setup_mail(
    app: ASGIApp,
    *,
    backend: BaseMailBackend,
    template_dir: str | None = None,
    attach_lifecycle: bool = True,
) -> None:
    """
    Attach a global Mailer to `app.state.mailer`. Optionally registers
    startup/shutdown hooks if the app exposes Starlette-like events.
    """
    if not backend:
        raise BackendNotConfigured("No mail backend provided.")

    mailer = Mailer(backend=backend, template_dir=template_dir)
    app.state.mailer = mailer

    if attach_lifecycle:
        add_event = getattr(app, "add_event_handler", None)
        if callable(add_event):
            add_event("startup", mailer.open)
            add_event("shutdown", mailer.close)
        else:
            # Fallback: do nothing (caller can manage open/close explicitly)
            ...
