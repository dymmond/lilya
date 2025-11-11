from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import TYPE_CHECKING, Any, NoReturn, cast

from lilya._internal._message import Address
from lilya._internal._parsers import cookie_parser
from lilya.datastructures import URL, Header, QueryParam, State
from lilya.enums import ScopeType
from lilya.exceptions import ImproperlyConfigured
from lilya.types import Message, Receive, Scope

if TYPE_CHECKING:
    from lilya.apps import Lilya
    from lilya.routing import Router

SERVER_PUSH_HEADERS = {
    "accept",
    "accept-encoding",
    "accept-language",
    "cache-control",
    "user-agent",
}


async def empty_receive() -> NoReturn:  # pragma: no cover
    """Raise a `RuntimeError`.

    Serves as a placeholder `send` function.

    Raises:
        RuntimeError
    """
    raise RuntimeError()


async def empty_send(message: Message) -> NoReturn:  # pragma: no cover
    """Raise a `RuntimeError`.

    Serves as a placeholder `send` function.
    """
    raise RuntimeError()


class ClientDisconnect(Exception): ...


class Connection(Mapping[str, Any]):
    """
    The Base for all Connections.
    """

    def __init__(self, scope: Scope, receive: Receive | None = None) -> None:
        assert scope["type"] in (ScopeType.HTTP, ScopeType.WEBSOCKET)
        self.scope = scope
        self._url: URL | None = None
        self._base_url: URL | None = None
        self._headers: Header | None = None
        self._state: State | None = None
        self._query_params: QueryParam | None = None
        self._cookies: dict[str, str] | None = None

    def __getitem__(self, __key: str) -> Any:
        return self.scope[__key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.scope)

    def __len__(self) -> int:
        return len(self.scope)

    __eq__ = object.__eq__
    __hash__ = object.__hash__

    @property
    def app(self) -> Any:
        return self.scope.get("app")

    @property
    def url(self) -> URL:
        if self._url is None:
            self._url = URL.build_from_scope(scope=self.scope)
        return self._url

    @property
    def base_url(self) -> URL:
        if self._base_url is None:
            base_url_scope = dict(self.scope)
            app_root_path = base_url_scope.get(
                "app_root_path", base_url_scope.get("root_path", "")
            )
            path = app_root_path
            if not path.endswith("/"):
                path += "/"
            base_url_scope["path"] = path
            base_url_scope["query_string"] = b""
            base_url_scope["root_path"] = app_root_path
            self._base_url = URL.build_from_scope(scope=base_url_scope)
        return self._base_url

    @property
    def headers(self) -> Header:
        if self._headers is None:
            # otherwise underlying apps can see an exhausted generator in scope
            self._headers = Header.ensure_header_instance(scope=self.scope)
        return self._headers

    @property
    def state(self) -> State:
        if self._state is None:
            self.scope.setdefault("state", {})
            self._state = State(self.scope["state"])
        return self._state

    @property
    def query_params(self) -> QueryParam:
        if self._query_params is None:
            self._query_params = QueryParam(self.scope["query_string"])
        return self._query_params

    @property
    def path_params(self) -> dict[str, Any]:
        return cast(dict[str, Any], self.scope.get("path_params", {}))

    @property
    def cookies(self) -> dict[str, str]:
        """
        This addresses multiple cookies and duplicates as per RFC 7540.
        https://datatracker.ietf.org/doc/html/rfc7540
        """
        cookies: dict[str, str] = {}
        if self._cookies is None:
            cookie_headers = self.headers.getlist("cookie")
            for header in cookie_headers:
                cookies.update(cookie_parser(header))
            self._cookies = cookies
        return self._cookies

    @property
    def client(self) -> Address | None:
        client = self.scope.get("client")
        return Address(*client) if client else None

    @property
    def server(self) -> Address | None:
        server = self.scope.get("server")
        return Address(*server) if server else None

    @property
    def auth(self) -> Any:
        if "auth" not in self.scope:
            raise ImproperlyConfigured(
                "AuthenticationMiddleware must be installed to access request.auth"
            )
        return self.scope["auth"]

    @property
    def user(self) -> Any:
        if "user" not in self.scope:
            raise ImproperlyConfigured(
                "AuthenticationMiddleware must be installed to access request.user"
            )

        return self.scope["user"]

    @property
    def session(self) -> dict[str, Any]:
        if "session" not in self.scope:
            raise ImproperlyConfigured(
                "SessionMiddleware must be installed to access request.session"
            )
        return cast(dict[str, Any], self.scope["session"])

    @property
    def is_server_push(self) -> bool:
        return cast(bool, self.scope.get("server_push", False))

    @property
    def is_server_pull(self) -> bool:
        return cast(bool, self.scope.get("server_pull", False))

    def set_session(self, value: Any) -> None:
        """
        Sets the value of a request session by passing a dictionary.
        """
        self.scope["session"] = value

    def clear_session(self) -> None:
        """
        Clears the scope session.
        """
        self.scope["session"] = None

    def is_secure(self) -> bool:
        """
        Check if the connection is secure (HTTPS).

        Returns:
            bool: True if the connection is secure (HTTPS), False otherwise.
        """
        return self.url.is_secure

    def path_for(self, name: str, /, **path_params: Any) -> URL:
        return self.url_path_for(name, **path_params)

    def url_path_for(self, name: str, /, **path_params: Any) -> URL:
        router: Router | Lilya | None = self.scope.get("router") or self.scope.get("app")

        if router is None:
            raise RuntimeError(
                "The `url_for` method can only be used inside a Lilya application or with a router."
            )

        url_path = router.url_path_for(name, **path_params)
        return cast(URL, url_path.make_absolute_url(base_url=self.base_url))
