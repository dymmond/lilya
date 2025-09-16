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
    Configure and attach a global `Mailer` instance to the Lilya application.

    This function ensures that `app.state.mailer` is always available,
    allowing you to send emails anywhere in your application
    (handlers, dependencies, background tasks).

    Optionally, it will also hook into the application's startup
    and shutdown events to manage the backend's connection lifecycle.

    Args:
        app: The Lilya application instance.
        backend: A configured mail backend (e.g., `SMTPBackend`,
            `ConsoleBackend`, `FileBackend`, `InMemoryBackend`).
        template_dir: Optional path to a directory containing Jinja2 templates
            for rendering HTML/plain-text emails.
        attach_lifecycle: If `True`, register startup/shutdown event handlers
            to automatically open/close the mail backend connection.

    Raises:
        BackendNotConfigured: If no backend is provided.
    """
    if backend is None:
        raise BackendNotConfigured("No mail backend provided to setup_mail().")

    mailer = Mailer(backend=backend, template_dir=template_dir)
    app.state.mailer = mailer

    if attach_lifecycle:
        add_event_handler = getattr(app, "add_event_handler", None)
        if callable(add_event_handler):
            add_event_handler("startup", mailer.open)
            add_event_handler("shutdown", mailer.close)
        else:
            # If the app does not support event handlers,
            # the developer must call `mailer.open()` and `mailer.close()` manually.
            return
