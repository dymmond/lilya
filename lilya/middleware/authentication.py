from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from typing_extensions import Annotated, Doc

from lilya._internal._connection import Connection
from lilya.enums import ScopeType
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.types import ASGIApp, Receive, Scope, Send


@dataclass
class AuthResult:
    user: Annotated[
        Any,
        Doc(
            """
            Arbitrary user coming from the `authenticate` of the `BaseAuthMiddleware`
            and can be assigned to the `request.user`.
            """
        ),
    ]


class BaseAuthMiddleware(ABC, MiddlewareProtocol):  # pragma: no cover
    """
    `BaseAuthMiddleware` is the object that you can implement if you
    want to implement any `authentication` middleware with Lilya.

    It is not mandatory to use it and you are free to implement your.

    Once you have installed the `AuthenticationMiddleware` and implemented the
    `authenticate`, the `request.user` will be available in any of your
    endpoints.

    When implementing the `authenticate`, you must assign the result into the
    `AuthResult` object in order for the middleware to assign the `request.user`
    properly.

    The `AuthResult` is of type `lilya.middleware.authentication.AuthResult`.
    """

    def __init__(
        self,
        app: Annotated[
            ASGIApp,
            Doc(
                """
                An ASGI type callable.
                """
            ),
        ],
    ):
        super().__init__(app)
        self.app = app
        self.scopes: set[str] = {ScopeType.HTTP, ScopeType.WEBSOCKET}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Function callable that automatically will call the `authenticate` function
        from any middleware subclassing the `BaseAuthMiddleware` and assign the `AuthUser` user
        to the `request.user`.
        """
        if scope["type"] not in self.scopes:
            await self.app(scope, receive, send)
            return

        auth_result = await self.authenticate(Connection(scope))
        scope["user"] = auth_result.user
        await self.app(scope, receive, send)

    @abstractmethod
    async def authenticate(self, request: Connection) -> AuthResult:
        """
        The abstract method that needs to be implemented for any authentication middleware.
        """
        raise NotImplementedError("authenticate must be implemented.")
