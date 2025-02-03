from __future__ import annotations

from collections import OrderedDict
from typing import cast

from lilya.datastructures import Header
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.types import ASGIApp, Message, Receive, Scope, Send


def parse_content_policy(policy: dict[str, str | list[str]] | str) -> str:
    """
    Parse a given policy from a dictionary or string format to a standardized string representation.

    Args:
        policy (Union[Dict[str, Union[str, List[str]]], str]): The policy to parse. It can be either a dictionary
        where the keys are policy sections and the values are either strings or lists of strings, or a string
        representing the policy.

    Returns:
        str: A standardized string representation of the policy.

    Examples:
        >>> parse_policy("default-src 'self'; img-src https://example.com")
        "default-src 'self'; img-src https://example.com"

        >>> parse_policy(
        ...     {
        ...         "default-src": "'self'",
        ...         "img-src": ["https://example.com", "https://another.com"],
        ...     }
        ... )
        "default-src 'self'; img-src https://example.com https://another.com"
    """
    # If the input policy is a string, parse it into a dictionary
    if isinstance(policy, str):
        parsed_policy_dict = OrderedDict()
        for policy_part in policy.split(";"):
            policy_parts = policy_part.strip().split()
            if policy_parts:
                section = policy_parts[0]
                content = " ".join(policy_parts[1:])
                parsed_policy_dict[section] = content
        policy = cast(dict[str, str | list[str]], parsed_policy_dict)

    # If the policy is already a dictionary, process it directly
    policies = []
    for section, content in policy.items():  # type: ignore
        if isinstance(content, list):  # type: ignore
            content = " ".join(content)  # type: ignore
        policies.append(f"{section} {content}")

    # Join all policy parts into a single string with proper formatting
    return "; ".join(policies)


class SecurityMiddleware(MiddlewareProtocol):
    """
    Middleware for handling security-related tasks.
    """

    def __init__(
        self,
        app: ASGIApp,
        content_policy: dict[str, str | list[str]] | str,
        cross_origin_opener_policy: str = "same-origin",
        referrer_policy: str = "same-origin",
        strict_transport_security: str = "max-age=31556926; includeSubDomains",
        content_type_options: str = "nosniff",
        frame_options: str = "DENY",
        xss_protection: str = "1; mode=block",
    ) -> None:
        """
        Initialize the SecurityMiddleware.

        Args:
            app (ASGIApp): The ASGI application to wrap.
            content_policy (Union[dict[str, Union[str, List[str]]], str]): The content security policy.
            cross_origin_opener_policy (str, optional): The cross-origin opener policy. Defaults to "same-origin".
            referrer_policy (str, optional): The referrer policy. Defaults to "same-origin".
            strict_transport_security (str, optional): The strict transport security policy. Defaults to "max-age=31556926; includeSubDomains".
            content_type_options (str, optional): The X-Content-Type-Options policy. Defaults to "nosniff".
            frame_options (str, optional): The X-Frame-Options policy. Defaults to "DENY".
            xss_protection (str, optional): The X-XSS-Protection policy. Defaults to "1; mode=block".
        """
        super().__init__(app)
        self.app = app
        self.content_policy = parse_content_policy(content_policy)
        self.cross_origin_opener_policy = cross_origin_opener_policy
        self.referrer_policy = referrer_policy
        self.strict_transport_security = strict_transport_security
        self.content_type_options = content_type_options
        self.frame_options = frame_options
        self.xss_protection = xss_protection

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Process the incoming request and perform HTTPS redirection if necessary.

        Args:
            scope (Scope): The ASGI scope.
            receive (Receive): The receive channel.
            send (Send): The send channel.
        """
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: Message) -> None:
            await self.process_response(send, scope, message)

        await self.app(scope, receive, send_wrapper)

    async def process_response(self, send: Send, scope: Scope, message: Message) -> None:
        """
        Process the response message and add security-related headers to the message headers.

        Args:
            scope (Scope): The ASGI scope.
            message (Message): The response message.

        Returns:
            None
        """
        if message["type"] == "http.response.start":
            # we need to update the headers of message
            headers: Header = Header.ensure_header_instance(message)
            headers.add(
                "Content-Security-Policy", "" if not self.content_policy else self.content_policy
            )
            headers.add("Cross-Origin-Opener-Policy", self.cross_origin_opener_policy)
            headers.add("Referrer-Policy", self.referrer_policy)
            headers.add("Strict-Transport-Security", self.strict_transport_security)
            headers.add("X-Content-Type-Options", self.content_type_options)
            headers.add("X-Frame-Options", self.frame_options)
            headers.add("X-XSS-Protection", self.xss_protection)

        await send(message)
