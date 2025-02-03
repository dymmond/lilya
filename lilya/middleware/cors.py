from __future__ import annotations

import functools
import re
from collections.abc import Sequence
from typing import Any

from lilya.datastructures import Header
from lilya.enums import HeaderEnum, HTTPCorsEnum
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.responses import PlainText, Response
from lilya.types import ASGIApp, Message, Receive, Scope, Send


class CORSMiddleware(MiddlewareProtocol):
    def __init__(
        self,
        app: ASGIApp,
        allow_origins: Sequence[str] | None = None,
        allow_methods: Sequence[str] | None = None,
        allow_headers: Sequence[str] | None = None,
        allow_credentials: bool = False,
        allow_origin_regex: str | None = None,
        allow_private_networks: bool = False,
        expose_headers: Sequence[str] | None = None,
        max_age: int = 600,
    ) -> None:
        """
        Middleware for handling Cross-Origin Resource Sharing (CORS) headers.

        Args:
            app (ASGIApp): The ASGI application to wrap.
            allow_origins (Sequence[str]): List of allowed origin patterns.
            allow_methods (Sequence[str]): List of allowed HTTP methods.
            allow_headers (Sequence[str]): List of allowed HTTP headers.
            allow_credentials (bool): Whether credentials such as cookies are allowed.
            allow_origin_regex (Optional[str]): Regular expression for allowed origins.
            expose_headers (Sequence[str]): List of headers exposed to the browser.
            max_age (int): Maximum age (in seconds) for caching preflight requests.
        """
        allow_origins = allow_origins or ()
        allow_methods = allow_methods or ("GET",)
        allow_headers = allow_headers or ()
        expose_headers = expose_headers or ()

        if "*" in allow_methods:
            allow_methods = HTTPCorsEnum.to_tuple()

        compiled_allow_origin_regex = None
        if allow_origin_regex is not None:
            compiled_allow_origin_regex = re.compile(allow_origin_regex)

        allow_all_origins = "*" in allow_origins
        allow_all_headers = "*" in allow_headers
        preflight_explicit_allow_origin = not allow_all_origins or allow_credentials

        simple_headers = self.get_simple_headers(
            allow_all_origins, allow_credentials, expose_headers, allow_private_networks
        )

        allow_headers = sorted(HeaderEnum.to_set() | set(allow_headers))
        preflight_headers = self.get_preflight_headers(
            allow_all_origins,
            allow_methods,
            max_age,
            allow_all_headers,
            allow_headers,
            allow_credentials,
            allow_private_networks,
        )

        self.app = app
        self.allow_origins = allow_origins
        self.allow_methods = allow_methods
        self.allow_headers = [h.lower() for h in allow_headers]
        self.allow_all_origins = allow_all_origins
        self.allow_all_headers = allow_all_headers
        self.preflight_explicit_allow_origin = preflight_explicit_allow_origin
        self.allow_origin_regex = compiled_allow_origin_regex
        self.simple_headers = simple_headers
        self.preflight_headers = preflight_headers
        self.allow_private_networks = allow_private_networks

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        ASGI application callable.

        Args:
            scope (Scope): ASGI scope.
            receive (Receive): ASGI receive channel.
            send (Send): ASGI send channel.
        """
        if scope["type"] != "http":  # pragma: no cover
            await self.app(scope, receive, send)
            return

        method = scope["method"]
        headers = Header.ensure_header_instance(scope=scope)
        origin = headers.get("origin")

        if origin is None:
            await self.app(scope, receive, send)
            return

        if method == "OPTIONS" and "access-control-request-method" in headers:
            response = self.preflight_response(request_headers=headers)
            await response(scope, receive, send)
            return

        if method == "OPTIONS" and "access-control-request-private-network" in headers:
            response = self.preflight_private_network_response(request_headers=headers)
            await response(scope, receive, send)
            return

        await self.simple_response(scope, receive, send, request_headers=headers)

    def validate_origin(self, origin: str) -> bool:
        """
        Validate if the origin is allowed.

        Args:
            origin (str): Origin header value.

        Returns:
            bool: True if the origin is allowed, False otherwise.
        """
        if self.allow_all_origins:
            return True

        if self.allow_origin_regex is not None and self.allow_origin_regex.fullmatch(origin):
            return True

        return origin in self.allow_origins

    def preflight_response(self, request_headers: Header) -> Response:
        """
        Generate a preflight response.

        Args:
            request_headers (Header): Header from the incoming preflight request.

        Returns:
            Response: Preflight response.
        """
        requested_origin = request_headers["origin"]
        requested_method = request_headers["access-control-request-method"]
        requested_headers = request_headers.get("access-control-request-headers")

        headers = dict(self.preflight_headers)
        failures = []

        if self.validate_origin(origin=requested_origin):
            if self.preflight_explicit_allow_origin:
                headers["Access-Control-Allow-Origin"] = requested_origin
        else:
            failures.append("origin")

        if requested_method not in self.allow_methods:
            failures.append("method")

        if self.allow_all_headers and requested_headers is not None:
            headers["Access-Control-Allow-Headers"] = requested_headers
        elif requested_headers is not None:
            for header in [h.lower() for h in requested_headers.split(",")]:
                if header.strip() not in self.allow_headers:
                    failures.append("headers")
                    break

        if failures:
            failure_text = "Disallowed CORS " + ", ".join(failures)
            return PlainText(failure_text, status_code=400, headers=headers)

        return PlainText("OK", status_code=200, headers=headers)

    def preflight_private_network_response(self, request_headers: Header) -> Response:
        """
        Process the preflight request for private network access.
        This feature is not part of the CORS specification but is useful for the new browsers
        that enforce the private network access policy.

        By the time of this implementation, this specific functionality got inspired by great
        developers thinking about the future of the web and the security of the users.

        More information about the private network access policy can be found at:

            1. https://developer.chrome.com/blog/private-network-access-preflight/
            2. https://documentation.alphasoftware.com/documentation/pages/Guides/Mobile%20and%20Web%20Components/UX/Properties/Advanced/CORS%20allow%20private%20network.xml#:~:text=Enables%20cross%20origin%20requests%20from,(e.g.%20behind%20a%20firewall).

        This will be rolled out on Chromium based browsers such as Google Chrome, Microsoft Edge, Brave and others.

        Args:
            request_headers (Header): The headers of the request.

        Returns:
            Response: The response to the preflight request.
        """
        requested_origin = request_headers["origin"]
        requested_private_network = request_headers["access-control-request-private-network"]

        headers = dict(self.preflight_headers)
        errors = []

        if not self.validate_origin(origin=requested_origin):
            errors.append("origin")

        if requested_private_network == "true" and not self.allow_private_networks:
            errors.append("private-network")

        if errors:
            message = "Disallowed Private Network Access " + ", ".join(errors)
            return PlainText(message, status_code=400, headers=headers)

        headers["Access-Control-Allow-Origin"] = requested_origin
        return PlainText("Allowed", status_code=200, headers=headers)

    async def simple_response(
        self, scope: Scope, receive: Receive, send: Send, request_headers: Header
    ) -> None:
        """
        Handle the simple response.

        Args:
            scope (Scope): ASGI scope.
            receive (Receive): ASGI receive channel.
            send (Send): ASGI send channel.
            request_headers (Header): Header from the incoming request.
        """
        send = functools.partial(self.send, send=send, request_headers=request_headers)
        await self.app(scope, receive, send)

    async def send(self, message: Message, send: Send, request_headers: Header) -> None:
        """
        Send the message and apply CORS headers.

        Args:
            message (Message): ASGI message.
            send (Send): ASGI send channel.
            request_headers (Header): Header from the incoming request.
        """
        if message["type"] != "http.response.start":
            await send(message)
            return

        # we need to update the message
        headers = Header.ensure_header_instance(scope=message)
        headers.update(self.simple_headers)
        origin = request_headers["Origin"]
        has_cookie = "cookie" in request_headers

        if self.allow_all_origins and has_cookie:
            self.set_explicit_origin(headers, origin)
        elif not self.allow_all_origins and self.validate_origin(origin=origin):
            self.set_explicit_origin(headers, origin)

        await send(message)

    @staticmethod
    def set_explicit_origin(headers: Header, origin: str) -> None:
        """
        Set explicit origin in headers.

        Args:
            headers (MutableHeaders): MutableHeaders instance.
            origin (str): Origin header value.
        """
        headers["Access-Control-Allow-Origin"] = origin
        headers.add_vary_header("Origin")

        expose_headers = headers.get("Access-Control-Expose-Headers")
        if expose_headers:
            headers.add_vary_header("Access-Control-Expose-Headers")

    @staticmethod
    def get_simple_headers(
        allow_all_origins: bool,
        allow_credentials: bool,
        expose_headers: Sequence[str],
        allow_private_networks: bool,
    ) -> dict:
        """
        Get headers for simple (non-preflight) responses.

        Args:
            allow_all_origins (bool): Whether all origins are allowed.
            allow_credentials (bool): Whether credentials such as cookies are allowed.
            expose_headers (Sequence[str]): List of headers exposed to the browser.

        Returns:
            dict: Dictionary of simple response headers.
        """
        simple_headers = {}

        if allow_all_origins:
            simple_headers["Access-Control-Allow-Origin"] = "*"
        if allow_credentials:
            simple_headers["Access-Control-Allow-Credentials"] = "true"
        if expose_headers:
            simple_headers["Access-Control-Expose-Headers"] = ", ".join(expose_headers)
        if allow_private_networks:
            simple_headers["Access-Control-Allow-Private-Network"] = "true"

        return simple_headers

    @staticmethod
    def get_preflight_headers(
        allow_all_origins: bool,
        allow_methods: Sequence[str],
        max_age: int,
        allow_all_headers: bool,
        allow_headers: Sequence[str],
        allow_credentials: bool,
        allow_private_networks: bool,
    ) -> dict[str, Any]:
        """
        Get headers for preflight responses.

        Args:
            allow_all_origins (bool): Whether all origins are allowed.
            allow_methods (Sequence[str]): List of allowed HTTP methods.
            max_age (int): Maximum age (in seconds) for caching preflight requests.
            allow_all_headers (bool): Whether all headers are allowed.
            allow_headers (Sequence[str]): List of allowed HTTP headers.
            allow_credentials (bool): Whether credentials such as cookies are allowed.

        Returns:
            dict: Dictionary of preflight response headers.
        """
        preflight_headers = {}
        explicit_allow_origin = not allow_all_origins or allow_credentials

        if allow_all_origins:
            preflight_headers["Access-Control-Allow-Origin"] = "*"
        if allow_credentials:
            preflight_headers["Access-Control-Allow-Credentials"] = "true"
        if allow_private_networks:
            preflight_headers["Access-Control-Allow-Private-Network"] = "true"
        if allow_all_headers:
            preflight_headers["Access-Control-Allow-Headers"] = "*"
        elif allow_headers:
            preflight_headers["Access-Control-Allow-Headers"] = ", ".join(allow_headers)

        if explicit_allow_origin:
            preflight_headers["Vary"] = "Origin"

        preflight_headers.update(
            {
                "Access-Control-Allow-Methods": ", ".join(allow_methods),
                "Access-Control-Max-Age": str(max_age),
            }
        )

        return preflight_headers
