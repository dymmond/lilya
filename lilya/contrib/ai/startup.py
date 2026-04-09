from __future__ import annotations

from lilya.contrib.ai.client import AIClient
from lilya.contrib.ai.exceptions import ProviderNotConfigured
from lilya.types import ASGIApp


def setup_ai(
    app: ASGIApp,
    *,
    client: AIClient,
    attach_lifecycle: bool = True,
    state_attribute: str = "ai",
) -> None:
    """
    Attach a configured AI client to a Lilya application.

    The client becomes available through `app.state.<state_attribute>` and
    can also be injected into handlers via `lilya.contrib.ai.dependencies.AI`.
    When lifecycle hooks are enabled, the provider is started on application
    startup and shut down on application shutdown.
    """
    if client is None:
        raise ProviderNotConfigured("No AI client provided to setup_ai().")

    setattr(app.state, state_attribute, client)

    if attach_lifecycle:
        add_event_handler = getattr(app, "add_event_handler", None)
        if callable(add_event_handler):
            add_event_handler("startup", client.startup)
            add_event_handler("shutdown", client.shutdown)
