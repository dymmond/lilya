from __future__ import annotations

from abc import ABC
from collections.abc import Generator, Iterable, Mapping, Sequence
from copy import copy
from http.cookies import SimpleCookie
from typing import Any, Final, Generic, Literal, TypeVar, cast
from urllib.parse import SplitResult, parse_qsl, urlencode, urlsplit, urlunsplit

import anyio
from multidict import CIMultiDict, MultiDict as BaseMultiDict, MultiDictProxy, MultiMapping

from lilya.enums import DefaultPort, HTTPType, ScopeType, WebsocketType
from lilya.types import Message, Receive, Scope, Send

T = TypeVar("T")


class invertedset(frozenset):
    """
    Inverts a collection
    """

    def __contains__(self, item: Any) -> bool:
        return not super().__contains__(item)


ALL: Final = invertedset()


class MultiMixin(Generic[T], MultiMapping[T], ABC):
    """Mixin providing common methods for multi dicts"""

    def dump(self) -> dict[str, Any]:
        """
        Returns the dictionary without duplicates.
        """
        return dict(self.items())

    def dump_list(self) -> list[Any]:
        """
        Returns the dictionary without duplicates.
        """
        return list(self.dump().items())

    def dict(self) -> dict[str, list[Any]]:
        """Return the multi-dict as a dict of lists."""
        return {k: self.getall(k) for k in set(self.keys())}

    def multi_items(self) -> Generator[tuple[str, T], None, None]:
        """Get all keys and values, including duplicates."""
        for key in set(self.keys()):
            for value in self.getall(key):
                yield key, value

    def get_multi_items(self) -> list[tuple[str, T]]:
        """
        Returns a list of values from the multi items
        """
        return list(self.multi_items())


class MultiDict(BaseMultiDict, MultiMixin[T], Generic[T]):
    def __init__(
        self,
        args: MultiMapping | Mapping[str, T] | Iterable[tuple[str, T]] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(args or {})

    def to_immutable(self) -> ImmutableMultiDict[T]:
        """Create an immutable dictionary view."""
        return ImmutableMultiDict[T](self)

    def getlist(self, key: Any) -> list[Any]:
        return [item_value for item_key, item_value in list(self.multi_items()) if item_key == key]

    def poplist(self, key: Any) -> list[Any]:
        values = [v for k, v in list(self.multi_items()) if k == key]
        self.pop(key)
        return values

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return sorted(self.multi_items()) == sorted(other.multi_items())

    def __repr__(self) -> str:
        """
        Visual representation of the object sorted by keys.
        """
        items = sorted(self.items())
        return f"{self.__class__.__name__}({items!r})"


class ImmutableMultiDict(MultiDictProxy[T], MultiMixin[T], Generic[T]):
    def __init__(
        self,
        args: MultiMapping | Mapping[str, Any] | Iterable[tuple[str, Any]] | Any | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(BaseMultiDict(args or {}))

    def mutablecopy(self) -> MultiDict[T]:
        """Create a mutable copy as a.

        Returns:
            A mutable MultiDict.
        """
        return MultiDict(list(self.multi_items()))

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return sorted(self.multi_items()) == sorted(other.multi_items())

    def __repr__(self) -> str:
        """
        Visual representation of the object sorted by keys.
        """
        items = sorted(self.items())
        return f"{self.__class__.__name__}({items!r})"


class FormMultiDict(ImmutableMultiDict[Any]):
    """MultiDict for form data."""

    async def close(self) -> None:
        """Close all files in the FormMultiDict."""
        for _, value in self.multi_items():
            if isinstance(value, DataUpload):
                await value.close()


class Header(MultiDict, CIMultiDict):
    """Container used for both request and response headers.
    It is a subclass of  [CIMultiDict](https://multidict.readthedocs.io/en/stable/multidict.html#cimultidictproxy)

    Please checkout [the MultiDict documentation](https://multidict.readthedocs.io/en/stable/multidict.html#multidict) for more details.
    """

    def __init__(
        self,
        value: MultiMapping
        | Mapping[str, Any]
        | Iterable[tuple[bytes | str, bytes | str]]
        | None = None,
    ) -> None:
        # this way we can handle None, like specified
        if not value:
            value = []

        assert isinstance(value, (dict, Iterable)), (
            "The headers must be in the format of a Iterable of tuples or dictionary."
        )

        headers: list[tuple[str, Any]] = self.parse_headers(value)
        super().__init__(headers)

    def parse_headers(self, value: Any) -> list[tuple[str, Any]]:
        """
        Parses the headers and validates if its bytes or str.
        """
        headers: list[tuple[str, Any]] = []

        if isinstance(value, dict):
            for k, v in value.items():
                key = k.decode("utf-8") if isinstance(k, bytes) else k
                if not isinstance(v, (list, tuple)):
                    v = [v]
                for header_value in v:
                    header_value = (
                        header_value.decode("utf-8")
                        if isinstance(header_value, bytes)
                        else header_value
                    )
                    assert isinstance(header_value, str)
                    headers.append((key, header_value))
        elif isinstance(value, Iterable):
            for k, v in value:
                key = k.decode("utf-8") if isinstance(k, bytes) else k
                header_value = v.decode("utf-8") if isinstance(v, bytes) else v
                assert isinstance(header_value, str)
                headers.append((key, header_value))

        return headers

    def __getattr__(self, key: str) -> str:
        if key.startswith("_"):
            return cast(str, self.__getattribute__(key))
        key = key.rstrip("_").replace("_", "-")
        return ",".join(self.getall(key, default=[]))

    def get_all(self, key: str) -> list[Any]:
        """Convenience method mapped to getall()."""
        return self.getall(key, default=[])

    @classmethod
    def from_scope(cls, scope: Any) -> Header:
        """
        Builds the headers from the scope or message.
        """
        return cls(scope["headers"])

    @classmethod
    def ensure_header_instance(cls, scope: Any) -> Header:
        """
        Ensure the headers are an instance of Header.
        This way reparsing can be prevented.
        It is applicable on scope or messages.
        """
        headers = scope.get("headers", ())
        if not isinstance(headers, Header):
            scope["headers"] = cls(headers)
        return cast(Header, scope["headers"])

    def add_vary_header(self, vary: str) -> None:
        existing = self.get("vary")
        if existing is not None:
            vary = ", ".join([existing, vary])
        self["vary"] = vary

    def encoded_multi_items(self) -> Generator[tuple[bytes, bytes], None, None]:
        """Get all keys and values, including duplicates, bytes encoded for ASGI."""
        return (
            (key.encode("utf-8"), value.encode("utf-8", errors="surrogateescape"))
            for key, value in self.multi_items()
        )

    def __iter__(self) -> Generator[tuple[bytes, bytes], None, None]:
        """For compatibility with ASGI."""
        return self.encoded_multi_items()

    def __contains__(self, item: str | bytes | tuple[bytes | str, bytes | str]) -> bool:
        # required by uvicorn which assumes the headers are a container like list.
        # elaborate for generic use
        if isinstance(item, bytes):
            item = item.decode("utf-8", errors="surrogateescape")
        if isinstance(item, str):
            return super().__contains__(item)
        try:
            k, v = (
                x if isinstance(x, str) else x.decode("utf8", errors="surrogateescape")
                for x in item
            )
        except (ValueError, AttributeError):
            return False
        # required for handling case insensitivity
        return any(v == val for val in self.get_all(k))

    def get_encoded_multi_items(self) -> list[tuple[bytes, bytes]]:
        """
        Returns a list of values from the bytes encoded multi items for ASGI
        """
        return list(self.encoded_multi_items())

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        as_dict = dict(self.items())
        if len(as_dict) == len(self):
            return f"{class_name}({as_dict!r})"
        return class_name


class State:
    """
    An object that can be used to store arbitrary state.

    Used for `request.state` and `app.state`.
    """

    _state: dict[str, Any]

    def __init__(self, state: dict[str, Any] | None = None):
        if state is None:
            state = {}
        super().__setattr__("_state", state)

    def __setattr__(self, key: Any, value: Any) -> None:
        object.__getattribute__(self, "_state")[key] = value

    def __getattribute__(self, key: Any) -> Any:
        state = object.__getattribute__(self, "_state")

        if key in state:
            return state[key]

        return object.__getattribute__(self, key)

    def __delattr__(self, key: Any) -> None:
        del self._state[key]

    def __copy__(self) -> State:
        return self.__class__(copy(self._state))

    def __len__(self) -> int:
        return len(self._state)

    def __getitem__(self, key: str) -> Any:
        return self._state[key]

    def copy(self) -> State:
        return copy(self)


class URL:
    """
    Represents a URL and provides methods for manipulating it.
    """

    url: str
    scheme: str | None = None
    netloc: str | None = None
    path: str | None = None
    fragment: str | None = None
    query: str | None = None
    username: str | None = None
    password: str | None = None
    port: int | None = None
    hostname: str | None = None

    def __new__(cls, url: str | SplitResult | None = None, **kwargs: Any) -> URL:
        """
        Overrides the new base class to create a new structure for the URL.

        Args:
            url (str | SplitResult | None): The URL to create.

        Returns:
            URL: The created URL instance.
        """
        instance = cls.__create__(url) if url is not None else cls.__create_from_kwargs__(**kwargs)
        return instance

    @classmethod
    def __create_from_kwargs__(cls, **kwargs: Any) -> URL:
        """
        Creates a new URL instance from keyword arguments.

        Args:
            **kwargs: Keyword arguments representing URL components.

        Returns:
            URL: The created URL instance.
        """
        instance: URL = super().__new__(cls)

        for k, _ in instance.__annotations__.items():
            if k in kwargs:
                setattr(instance, k, kwargs[k])
        instance.url = instance.base_url
        return instance

    @classmethod
    def __create__(cls, url: str | SplitResult | None = None) -> URL:
        """
        Creates a new URL instance.

        Args:
            url (str | SplitResult | None): The URL to create.

        Returns:
            URL: The created URL instance.
        """
        instance: URL = super().__new__(cls)

        assert isinstance(url, (str, SplitResult)), (
            "The url must be a string or a SplitResult instance."
        )

        if isinstance(url, str):
            result: SplitResult = urlsplit(url)
            instance.parsed_url = result
        else:
            instance.parsed_url = url

        instance.url = instance.base_url if isinstance(url, SplitResult) else url
        instance.scheme = instance.parsed_url.scheme
        instance.netloc = instance.parsed_url.netloc
        instance.path = instance.parsed_url.path
        instance.fragment = instance.parsed_url.fragment
        instance.query = instance.parsed_url.query
        instance.username = instance.parsed_url.username
        instance.password = instance.parsed_url.password
        instance.port = instance.parsed_url.port
        instance.hostname = instance.parsed_url.hostname
        return instance

    @classmethod
    def build_from_scope(cls, scope: Scope) -> URL:
        """
        Builds the URL from the Scope.

        Args:
            scope (Scope): The scope object.

        Returns:
            URL: The URL built from the scope.
        """
        scheme = scope.get("scheme", HTTPType.HTTP.value)
        server = scope.get("server")
        path = scope["path"]
        query_string = scope.get("query_string", b"")

        host_header = None
        for key, value in scope["headers"]:
            if key == b"host":
                host_header = value.decode("utf-8")
                break

        if host_header is not None:
            url = f"{scheme}://{host_header}{path}"
        elif server is None:
            url = path
        else:
            host, port = server
            default_port = DefaultPort.to_dict()[scheme]
            if port == default_port:
                url = f"{scheme}://{host}{path}"
            else:
                url = f"{scheme}://{host}:{port}{path}"

        if query_string:
            url += "?" + query_string.decode()
        return cls(url)

    @property
    def parsed_url(self) -> SplitResult:
        """
        Property representing the parsed URL.

        Returns:
            SplitResult: The parsed URL.
        """
        return cast(SplitResult, getattr(self, "_parsed_url", None))

    @parsed_url.setter
    def parsed_url(self, value: Any) -> None:
        """
        Setter for the parsed URL.

        Args:
            value: The value to set as the parsed URL.
        """
        self._parsed_url = value

    @property
    def is_secure(self) -> bool:
        """
        Property indicating whether the URL uses a secure scheme.

        Returns:
            bool: True if the URL is secure, False otherwise.
        """
        return self.scheme in ("https", "wss")

    @property
    def base_url(self) -> str:
        """
        Property representing the base URL.

        Returns:
            str: The base URL.
        """
        return str(
            urlunsplit(
                SplitResult(
                    scheme=self.scheme,
                    netloc=self.netloc,
                    path=self.path,
                    fragment=self.fragment,
                    query=self.query,
                )
            )
        )

    def _build_netloc(
        self,
        hostname: Any | None = None,
        port: Any | None = None,
        username: Any | None = None,
        password: Any | None = None,
    ) -> Any:
        """
        Builds the netloc part of the URL.

        Args:
            hostname (Any | None): The hostname.
            port (Any | None): The port.
            username (Any | None): The username.
            password (Any | None): The password.

        Returns:
            Any: The built netloc.
        """
        if hostname is None:
            netloc = self.netloc
            _, _, hostname = netloc.rpartition("@")

            if hostname[-1] != "]":
                hostname = hostname.rsplit(":", 1)[0]

        netloc = hostname
        if port is not None:
            netloc += f":{port}"
        if username is not None:
            userpass = username
            if password is not None:
                userpass += f":{password}"
            netloc = f"{userpass}@{netloc}"
        return netloc

    def replace(self, **kwargs: Any) -> URL:
        """
        Creates a new URL with replaced components.

        Args:
            **kwargs: Keyword arguments representing URL components.

        Returns:
            URL: The new URL instance with replaced components.
        """
        if (
            "username" in kwargs
            or "password" in kwargs
            or "hostname" in kwargs
            or "port" in kwargs
        ):
            hostname = kwargs.pop("hostname", None)
            port = kwargs.pop("port", self.port)
            username = kwargs.pop("username", self.username)
            password = kwargs.pop("password", self.password)
            kwargs["netloc"] = self._build_netloc(hostname, port, username, password)

        components = self.parsed_url._replace(**kwargs)
        return self.__class__(components.geturl())

    def include_query_params(self, **kwargs: Any) -> URL:
        """
        Adds query parameters to the URL.

        Args:
            **kwargs: Query parameters.

        Returns:
            URL: The new URL instance with added query parameters.
        """
        params = MultiDict(parse_qsl(self.query, keep_blank_values=True))
        params.update({str(key): str(value) for key, value in kwargs.items()})
        query = urlencode(sorted(params.multi_items()))
        return self.replace(query=query)

    def remove_query_params(self, keys: str | Sequence[str]) -> URL:
        """
        Removes query parameters from the URL.

        Args:
            keys (str | Sequence[str]): Query parameters to remove.

        Returns:
            URL: The new URL instance with removed query parameters.
        """
        if isinstance(keys, str):
            keys = [keys]
        params = MultiDict(parse_qsl(self.query, keep_blank_values=True))
        for key in keys:
            params.pop(key, None)
        query = urlencode(sorted(params.multi_items()))
        return self.replace(query=query)

    def replace_query_params(self, **kwargs: Any) -> URL:
        """
        Replaces query parameters in the URL.

        Args:
            **kwargs: Query parameters to replace.

        Returns:
            URL: The new URL instance with replaced query parameters.
        """
        values = [(str(key), str(value)) for key, value in kwargs.items()]
        query = urlencode(values)
        return self.replace(query=query)

    def relative_url(self) -> URL:
        """
        Creates a relative URL from the current URL.

        Returns:
            URL: A new URL instance with the same path, query, and fragment.
        """
        url = urlunsplit(
            SplitResult(
                scheme="",
                netloc="",
                path=self.path,
                query=self.query,
                fragment=self.fragment,
            )
        )
        return self.__class__(url)

    def __eq__(self, other: Any) -> bool:
        """
        Checks if two URLs are equal.

        Args:
            other: The other object to compare.

        Returns:
            bool: True if the URLs are equal, False otherwise.
        """
        return str(self) == str(other)

    def __str__(self) -> str:
        """
        Returns the string representation of the URL.

        Returns:
            str: The string representation of the URL.
        """
        return self.url

    def __repr__(self) -> str:
        """
        Returns the string representation of the URL for debugging purposes.

        Returns:
            str: The string representation of the URL.
        """
        url = str(self)
        if self.password:
            url = str(self.replace(password="***********"))
        return f"{self.__class__.__name__}({repr(url)})"


class URLPath(str):
    def __new__(cls, path: str, protocol: str = "", host: str = "") -> URLPath:
        assert protocol in (ScopeType.HTTP.value, ScopeType.WEBSOCKET.value, "")
        return str.__new__(cls, path)

    def __init__(self, path: str, protocol: str = "", host: str = "") -> None:
        self.protocol = protocol
        self.host = host
        self.path = path

    def make_absolute_url(self, base_url: str | URL) -> URL:
        if isinstance(base_url, str):
            base_url = URL(base_url)
        if self.protocol:
            scheme = {
                ScopeType.HTTP.value: {True: HTTPType.HTTPS.value, False: HTTPType.HTTP.value},
                ScopeType.WEBSOCKET.value: {
                    True: WebsocketType.WSS.value,
                    False: WebsocketType.WS.value,
                },
            }[self.protocol][base_url.is_secure]
        else:
            scheme = base_url.scheme

        netloc = self.host or base_url.netloc
        path = base_url.path.rstrip("/") + str(self)
        return URL(scheme=scheme, netloc=netloc, path=path)


class Secret:
    """
    Holds the information about a string secret.
    This will make sure no secrets are leaked
    in stack traces.
    """

    def __init__(self, value: str = None) -> None:
        self.value = value

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('***********')"

    def __bool__(self) -> bool:
        return bool(self.value)

    def __len__(self) -> int:
        return len(self.value)


class QueryParam(ImmutableMultiDict[Any]):
    """
    An immutable multidict.
    """

    def __init__(
        self,
        *args: MultiMapping | Mapping[str, Any] | Iterable[tuple[str, Any]] | None,
    ) -> None:
        assert len(args) < 2, "Too many arguments."
        value = args[0] if args else []

        if isinstance(value, str):  # type: ignore
            super().__init__(parse_qsl(value, keep_blank_values=True))  # type: ignore
        elif isinstance(value, bytes):  # type: ignore
            super().__init__(parse_qsl(value.decode("utf-8"), keep_blank_values=True))  # type: ignore
        else:
            super().__init__(*args)

    def __str__(self) -> str:
        return urlencode(sorted(self.multi_items()))

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        query_string = str(self)
        return f"{class_name}({query_string!r})"


class DataUpload:
    __slots__ = ("file", "size", "filename", "headers")

    def __init__(
        self,
        *,
        file: anyio.SpooledTemporaryFile,
        size: int | None = None,
        filename: str | None = None,
        headers: Header | None = None,
    ) -> None:
        self.filename = filename
        self.size = size
        self.headers = headers or Header()
        self.file = file

    @property
    def content_type(self) -> str | None:
        return self.headers.get("content-type", None)

    async def write(self, data: bytes) -> None:
        if self.size is not None:
            self.size += len(data)
        await self.file.write(data)

    async def read(self, size: int = -1) -> bytes:
        return cast(bytes, await self.file.read(size))

    async def seek(self, offset: int) -> None:
        await self.file.seek(offset)

    async def close(self) -> None:
        await self.file.aclose()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(filename={self.filename!r}, size={self.size!r}, headers={self.headers!r})"


class Cookie:
    def __init__(
        self,
        key: str,
        value: str | None = None,
        max_age: int | None = None,
        expires: int | None = None,
        path: str = "/",
        domain: str | None = None,
        secure: bool | None = None,
        httponly: bool | None = None,
        samesite: Literal["lax", "strict", "none"] = "lax",
        description: str | None = None,
    ) -> None:
        self.key = key
        self.value = value
        self.max_age = max_age
        self.expires = expires
        self.path = path
        self.domain = domain
        self.secure = secure
        self.httponly = httponly
        self.samesite = samesite
        self.description = description

    def to_header(self, **kwargs: Any) -> str:
        simple_cookie: SimpleCookie = SimpleCookie()
        simple_cookie[self.key] = self.value or ""
        if self.max_age:
            simple_cookie[self.key]["max-age"] = self.max_age
        cookie_dict = dict(self.__dict__)
        for key in ["expires", "path", "domain", "secure", "httponly", "samesite"]:
            if self.__dict__[key] is not None:
                simple_cookie[self.key][key] = cookie_dict[key]
        return simple_cookie.output(**kwargs).strip()


class FormData(ImmutableMultiDict[Any]):
    """
    An immutable multidict, containing both file uploads and text input.
    """

    def __init__(
        self,
        *args: FormData | Mapping[str, str | DataUpload] | list[tuple[str, str | DataUpload]],
        **kwargs: str | DataUpload,
    ) -> None:
        super().__init__(*args, **kwargs)

    async def close(self) -> None:
        for _, value in self.multi_items():
            if isinstance(value, DataUpload):
                await value.close()


class ScopeHandler:
    """
    Represents a route handler that handles incoming requests.

    Args:
        scope (Scope): The scope of the handler.
        receive (Receive): The receive function for handling incoming messages.
        send (Send): The send function for sending messages.

    Attributes:
        scope (Scope): The scope of the handler.
        receive (Receive): The receive function for handling incoming messages.
        send (Send): The send function for sending messages.
    """

    def __init__(self, scope: Scope, receive: Receive, send: Send) -> None:
        self.scope = scope
        self.receive = receive
        self.send = send

    def __hash__(self) -> int:
        values: dict[str, Any] = {}
        for key, value in self.__dict__.items():
            values[key] = None
            if isinstance(value, (list, set)):
                values[key] = tuple(value)
            else:
                values[key] = value
        return hash((type(self),) + tuple(values))


class SendReceiveSniffer:
    """
    Sniffs send, receive usage of asgi apps
    """

    __slots__ = ("_receive", "_send", "received", "sent", "message", "repeat_message")
    _receive: Receive
    _send: Send
    received: bool
    sent: bool
    # repeat message one time if available
    repeat_message: bool
    message: None | Message

    def __init__(self, receive: Receive, send: Send) -> None:
        self._receive = receive
        self._send = send
        self.received = False
        self.sent = False
        self.repeat_message = False
        self.message = None

    async def receive(self) -> Message:
        self.received = True
        if not self.repeat_message or self.message is None:
            self.message = await self._receive()
        self.repeat_message = False
        return self.message

    async def send(self, message: Message) -> None:
        self.sent = True
        await self._send(message)

    def __bool__(self) -> bool:
        return self.sent
