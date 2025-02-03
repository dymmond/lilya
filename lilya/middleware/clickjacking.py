from __future__ import annotations

from lilya.conf import settings
from lilya.datastructures import Header
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.types import ASGIApp, Message, Receive, Scope, Send


class XFrameOptionsMiddleware(MiddlewareProtocol):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Middleware entry point. Handles incoming requests and sends responses.

        Args:
            scope (Scope): The ASGI scope of the incoming request.
            receive (Receive): The ASGI receive function.
            send (Send): The ASGI send function.

        Returns:
            None
        """
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: Message) -> None:
            await self.process_response(send, scope, message)

        await self.app(scope, receive, send_wrapper)

    async def process_response(self, send: Send, scope: Scope, message: Message) -> None:
        """
        Process the response message and add the X-Frame-Options header if it is not already present.

        Args:
            scope (Scope): The ASGI scope.
            message (dict): The response message.

        Returns:
            None
        """
        if message["type"] == "http.response.start":
            # we need to update the message
            headers: Header = Header.ensure_header_instance(message)

            if headers.get("X-Frame-Options") is None:
                headers.add("X-Frame-Options", self.get_xframe_options())
        await send(message)

    def get_xframe_options(self) -> str:
        """
        Get the X-Frame-Options value from the settings.

        Returns:
            str: The X-Frame-Options value.
        """
        if getattr(settings, "x_frame_options", None) is not None:
            return settings.x_frame_options.upper()
        return "DENY"
