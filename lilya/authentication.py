from __future__ import annotations

import sys
from abc import ABC
from typing import Any

from lilya._internal._connection import Connection
from lilya.protocols.authentication import AuthenticationProtocol
from lilya.types import Receive, Scope, Send

if sys.version_info >= (3, 10):  # pragma: no cover
    from typing import ParamSpec
else:  # pragma: no cover
    from typing_extensions import ParamSpec

P = ParamSpec("P")


class AuthenticationBackend(ABC, AuthenticationProtocol):
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        raise NotImplementedError("All backends must implement the `__call__()`")

    async def authenticate(self, connection: Connection) -> Any:
        raise NotImplementedError("All backends must implement the `authenticate()`")


class BaseUser:
    @property
    def is_authenticated(self) -> bool:
        raise NotImplementedError()  # pragma: no cover

    @property
    def display_name(self) -> str:
        raise NotImplementedError()  # pragma: no cover


class User(BaseUser):
    def __init__(self, username: str) -> None:
        self.username = username

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def display_name(self) -> str:
        return self.username
