from __future__ import annotations

from typing import Any

from lilya.contrib.mail.mailer import Mailer
from lilya.dependencies import Provide
from lilya.requests import Request


async def _resolve_mailer(request: Request, **kwargs: Any) -> Mailer:
    """
    Dependency resolver for the global `Mailer` instance.

    This function is used internally by the ``Mail`` dependency
    (a :class:`Provide` wrapper) to inject a configured mailer into
    your endpoints, background tasks, or WebSocket handlers.

    It looks up ``request.app.state.mailer`` – which is set when you
    call :func:`setup_mail` during application startup – and returns
    that instance.

    Args:
        request: The current Lilya request.
        **kwargs: Extra keyword arguments passed by the dependency
            system (unused here, but accepted for compatibility).

    Returns:
        The configured global :class:`Mailer` instance.

    Raises:
        RuntimeError: If no mailer has been configured or if
            ``app.state.mailer`` is not a valid :class:`Mailer`.
            This usually means you forgot to call
            ``setup_mail(app, backend=...)`` in your ``main.py``.

    Example:
        ```python
        from lilya.apps import Lilya
        from lilya.contrib.mail import setup_mail
        from lilya.contrib.mail.backends.console import ConsoleBackend
        from lilya.contrib.mail.dependencies import Mail

        app = Lilya()
        setup_mail(app, backend=ConsoleBackend())

        @app.post("/contact", dependencies={"mailer": Mail})
        async def contact(mailer: Mail):
            await mailer.send_template(
                subject="Hello",
                to=["admin@myapp.com"],
                template_html="contact.html",
                context={"name": "John"},
            )
            return {"ok": True}
        ```
    """
    mailer = getattr(request.app.state, "mailer", None)
    if not isinstance(mailer, Mailer):
        raise RuntimeError(
            "No Mailer configured. Did you forget to call `setup_mail(app, backend=...)`?"
        )
    return mailer


Mail = Provide(_resolve_mailer)
