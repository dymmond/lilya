from __future__ import annotations

import functools
import inspect
import typing
from abc import ABC, abstractmethod
from typing import ParamSpec
from urllib.parse import urlencode

from lilya.compat import is_async_callable
from lilya.exceptions import HTTPException
from lilya.requests import Connection, Request
from lilya.responses import RedirectResponse
from lilya.websockets import WebSocket

P = ParamSpec("P")

AuthResult = tuple["AuthCredentials", "UserInterface"]


def has_required_scope(conn: Connection, scopes: typing.Sequence[str]) -> bool:
    """
    Check if the connection has all the required scopes.

    Args:
        conn (Connection): The connection object containing authentication details.
        scopes (typing.Sequence[str]): A sequence of required scope strings.

    Returns:
        bool: True if all required scopes are present in the connection's scopes, False otherwise.
    """
    conn_scopes = set(conn.auth.scopes)
    return all(scope in conn_scopes for scope in scopes)


def requires(
    scopes: str | typing.Sequence[str],
    status_code: int = 403,
    redirect: str | None = None,
) -> typing.Callable[[typing.Callable[P, typing.Any]], typing.Callable[P, typing.Any]]:
    """
    Decorator to enforce required scopes on a function.

    Args:
        scopes (str | typing.Sequence[str]): A single scope or a sequence of required scopes.
        status_code (int, optional): The HTTP status code to return if the scope check fails. Defaults to 403.
        redirect (str | None, optional): The URL to redirect to if the scope check fails. Defaults to None.

    Returns:
        typing.Callable[[typing.Callable[P, typing.Any]], typing.Callable[P, typing.Any]]: The decorated function.
    """
    scopes_list = [scopes] if isinstance(scopes, str) else list(scopes)

    def decorator(
        func: typing.Callable[P, typing.Any],
    ) -> typing.Callable[P, typing.Any]:
        """
        Inner decorator function to wrap the original function.

        Args:
            func (typing.Callable[P, typing.Any]): The original function to be decorated.

        Returns:
            typing.Callable[P, typing.Any]: The wrapped function.
        """
        sig = inspect.signature(func)
        __type__ = None
        for idx, parameter in enumerate(sig.parameters.values()):  # noqa B007
            if parameter.name in {"request", "websocket"}:
                __type__ = parameter.name
                break

        if __type__ is None:
            raise Exception(f'No "request" or "websocket" argument on function "{func}"')

        if __type__ == "websocket":

            @functools.wraps(func)
            async def websocket_wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
                """
                Wrapper for websocket functions to enforce scope checks.

                Args:
                    *args: Positional arguments for the original function.
                    **kwargs: Keyword arguments for the original function.
                """
                websocket = kwargs.get("websocket", args[idx] if idx < len(args) else None)
                assert isinstance(websocket, WebSocket)

                if not has_required_scope(websocket, scopes_list):
                    await websocket.close()
                else:
                    await func(*args, **kwargs)

            return websocket_wrapper

        elif is_async_callable(func):

            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> typing.Any:
                """
                Wrapper for async request/response functions to enforce scope checks.

                Args:
                    *args: Positional arguments for the original function.
                    **kwargs: Keyword arguments for the original function.

                Returns:
                    typing.Any: The result of the original function or a redirect/exception.
                """
                request = kwargs.get("request", args[idx] if idx < len(args) else None)
                assert isinstance(request, Request)

                if not has_required_scope(request, scopes_list):
                    if redirect is not None:
                        orig_request_qparam = urlencode({"next": str(request.url)})
                        next_url = f"{request.path_for(redirect)}?{orig_request_qparam}"
                        return RedirectResponse(url=next_url, status_code=303)
                    raise HTTPException(status_code=status_code)
                return await func(*args, **kwargs)

            return async_wrapper

        else:

            @functools.wraps(func)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> typing.Any:
                """
                Wrapper for sync request/response functions to enforce scope checks.

                Args:
                    *args: Positional arguments for the original function.
                    **kwargs: Keyword arguments for the original function.

                Returns:
                    typing.Any: The result of the original function or a redirect/exception.
                """
                request = kwargs.get("request", args[idx] if idx < len(args) else None)
                assert isinstance(request, Request)

                if not has_required_scope(request, scopes_list):
                    if redirect is not None:
                        orig_request_qparam = urlencode({"next": str(request.url)})
                        next_url = f"{request.path_for(redirect)}?{orig_request_qparam}"
                        return RedirectResponse(url=next_url, status_code=303)
                    raise HTTPException(status_code=status_code)
                return func(*args, **kwargs)

            return sync_wrapper

    return decorator


class AuthenticationError(Exception): ...


class AuthenticationBackend(ABC):
    @abstractmethod
    async def authenticate(self, connection: Connection) -> AuthResult | None: ...


class AuthCredentials:
    def __init__(self, scopes: typing.Sequence[str] | None = None):
        self.scopes = [] if scopes is None else list(scopes)


@typing.runtime_checkable
class UserInterface(typing.Protocol):
    @property
    def is_authenticated(self) -> bool:
        raise NotImplementedError()

    @property
    def display_name(self) -> str:
        raise NotImplementedError()


# bw compatibility alias
BaseUser = UserInterface


class BasicUser(UserInterface):
    def __init__(self, username: str) -> None:
        self.username = username

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def display_name(self) -> str:
        return self.username


class AnonymousUser(UserInterface):
    @property
    def is_authenticated(self) -> bool:
        return False

    @property
    def display_name(self) -> str:
        return ""
