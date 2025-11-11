from __future__ import annotations

import functools
import inspect
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from typing import Any, ParamSpec, Protocol, runtime_checkable
from urllib.parse import urlencode

from lilya.compat import is_async_callable
from lilya.exceptions import HTTPException
from lilya.requests import Connection, Request
from lilya.responses import RedirectResponse
from lilya.websockets import WebSocket

P = ParamSpec("P")

AuthResult = tuple["AuthCredentials", "UserInterface"]


def has_required_scope(conn: Connection, scopes: Sequence[str]) -> bool:
    """
    Check if the connection has all the required scopes.

    Args:
        conn (Connection): The connection object containing authentication details.
        scopes (Sequence[str]): A sequence of required scope strings.

    Returns:
        bool: True if all required scopes are present in the connection's scopes, False otherwise.
    """
    conn_scopes = set(conn.auth.scopes)
    return all(scope in conn_scopes for scope in scopes)


def requires(
    scopes: str | Sequence[str],
    status_code: int = 403,
    redirect: str | None = None,
    raise_for_missing_conn: bool = True,
    conn_param: str | None = None,
) -> Callable[[Callable[P, Any]], Callable[P, Any]]:
    """
    Decorator to enforce required scopes on a function.

    Args:
        scopes (str | Sequence[str]): A single scope or a sequence of required scopes.
        status_code (int, optional): The HTTP status code to return if the scope check fails. Defaults to 403.
        redirect (str | None, optional): The URL to redirect to if the scope check fails. Defaults to None.
        raise_for_missing_conn (bool, optional): If True, raise an exception if the scope check fails. Defaults to False.
        conn_param (str | None, optional): The name of the connection parameter
        (e.g., "request" or "websocket"). If None, it will be auto-detected. Defaults to None.

    Returns:
        Callable[[Callable[P, Any]], Callable[P, Any]]: The decorated function.
    """
    # Normalize the input scopes into a list of strings
    scopes_list: list[str] = [scopes] if isinstance(scopes, str) else list(scopes)

    def decorator(func: Callable[P, Any]) -> Callable[P, Any]:
        """The actual decorator applied to the route handler."""
        sig = inspect.signature(func)
        nonlocal conn_param
        connection_param: str | None = conn_param

        # Try to locate a connection-like parameter (request/websocket/conn)
        for name, _ in sig.parameters.items():
            if name in {"request", "websocket", conn_param}:
                connection_param = name
                break

        # If the parameter wasn't found and we must enforce the check
        if connection_param is None and raise_for_missing_conn:
            raise Exception(f'No "request" or "websocket" argument on function "{func.__name__}"')

        async def _check_scopes(conn: Connection) -> bool:
            """
            Asynchronously checks the required scopes on the connection.
            """
            if not hasattr(conn, "auth") or conn.auth is None:
                return False
            # Call the external utility function
            return has_required_scope(conn, scopes_list)

        async def _handle_redirect_or_error(conn: Request) -> Any:
            """
            Handles failed authorization for an HTTP Request, either redirecting
            or raising an HTTP exception.
            """
            if redirect is not None:
                # Store the original request URL as a 'next' query parameter
                orig_request_qparam: str = urlencode({"next": str(conn.url)})

                try:
                    next_url: str = f"{conn.url_path_for(redirect)}?{orig_request_qparam}"
                except RuntimeError:
                    # Fallback if path_for fails (e.g., redirect is not a route name)
                    next_url: str = f"{redirect}?{orig_request_qparam}"  # type: ignore

                return RedirectResponse(url=next_url, status_code=303)

            # If no redirect, raise the configured HTTPException
            raise HTTPException(status_code=status_code)

        if is_async_callable(func):
            # --- Async Handler Wrapper ---
            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
                """The wrapper for an async route handler."""
                conn: Connection | None = (
                    kwargs.get(connection_param) if connection_param else None  # type: ignore
                )

                if conn is not None:
                    # Type narrowing for WebSocket
                    if isinstance(conn, WebSocket):
                        if not await _check_scopes(conn):
                            await conn.close(code=1000)  # Close with normal status
                            return

                    # Type narrowing for Request
                    elif isinstance(conn, Request):
                        if not await _check_scopes(conn):
                            return await _handle_redirect_or_error(conn)

                # No connection param or all good: proceed to the original function
                return await func(*args, **kwargs)

            return async_wrapper

        else:
            # --- Sync Handler Wrapper ---
            @functools.wraps(func)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
                """The wrapper for a sync route handler."""
                conn: Connection | None = (
                    kwargs.get(connection_param) if connection_param else None  # type: ignore
                )

                if conn is not None:
                    # Type narrowing for Request (handled sync)
                    if isinstance(conn, Request):
                        if not has_required_scope(conn, scopes_list):
                            # Sync error handling for Request
                            if redirect is not None:
                                orig_request_qparam: str = urlencode({"next": str(conn.url)})
                                try:
                                    next_url: str = (
                                        f"{conn.url_path_for(redirect)}?{orig_request_qparam}"
                                    )
                                except RuntimeError:
                                    next_url: str = f"{redirect}?{orig_request_qparam}"  # type: ignore

                                return RedirectResponse(url=next_url, status_code=303)

                            raise HTTPException(status_code=status_code)

                    # Type narrowing for WebSocket (handled sync)
                    elif isinstance(conn, WebSocket):
                        if not has_required_scope(conn, scopes_list):
                            # Sync error handling for WebSocket: attempt to close
                            try:
                                conn.close(code=1000)  # type: ignore
                            except Exception:
                                pass  # Ignore exceptions if connection is already closed
                            return

                # No connection param or all good: proceed to the original function
                return func(*args, **kwargs)

            return sync_wrapper

    return decorator


class AuthenticationBackend(ABC):
    @abstractmethod
    async def authenticate(self, connection: Connection, **kwargs: Any) -> AuthResult | None: ...


class AuthCredentials:
    def __init__(self, scopes: Sequence[str] | None = None):
        self.scopes = [] if scopes is None else list(scopes)


@runtime_checkable
class UserInterface(Protocol):
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
        self._username = username

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def display_name(self) -> str:
        return self._username


class AnonymousUser(UserInterface):
    """
    Represents a user who is not authenticated.

    This class implements the `UserInterface` protocol and provides default
    values for an anonymous user.
    """

    @property
    def is_authenticated(self) -> bool:
        return False

    @property
    def display_name(self) -> str:
        return ""
