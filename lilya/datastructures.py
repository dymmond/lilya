from __future__ import annotations

from abc import ABC
from copy import copy
from dataclasses import dataclass
from functools import lru_cache
from shlex import shlex
from typing import (
    Any,
    BinaryIO,
    Dict,
    Generator,
    Generic,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    cast,
)
from urllib.parse import SplitResult, parse_qsl, urlencode, urlsplit, urlunsplit

from anyio.to_thread import run_sync
from multidict import MultiDict as BaseMultiDict
from multidict import MultiDictProxy, MultiMapping

from lilya.enums import DefaultPort, HTTPType, ScopeType, WebsocketType
from lilya.types import Scope

T = TypeVar("T")


class MultiMixin(Generic[T], MultiMapping[T], ABC):
    """Mixin providing common methods for multi dicts"""

    def dump(self) -> Dict[str, Any]:
        """
        Returns the dictionary without duplicates.
        """
        return dict(self.items())

    def dump_list(self) -> List[Any]:
        """
        Returns the dictionary without duplicates.
        """
        return list(self.dump().items())

    def dict(self) -> Dict[str, List[Any]]:
        """Return the multi-dict as a dict of lists.

        Returns:
            A dict of lists
        """
        return {k: self.getall(k) for k in set(self.keys())}

    def multi_items(self) -> Generator[tuple[str, T], None, None]:
        """Get all keys and values, including duplicates.

        Returns:
            A list of tuples containing key-value pairs
        """
        for key in set(self):
            for value in self.getall(key):
                yield key, value

    def get_multi_items(self) -> List[Any]:
        """
        Returns a list of values from the multi items
        """
        return list(self.multi_items())


class MultiDict(BaseMultiDict, MultiMixin[T], Generic[T]):
    def __init__(
        self,
        args: Union[MultiMapping, Mapping[str, T], Iterable[tuple[str, T]], None] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize MultiDict from a MultiMapping, :class:`Mapping <Mapping>` or an iterable of tuples.

        Args:
            args: Mapping-like structure to create the MultiDict from
        """
        super().__init__(args or {})

    def immutable(self) -> ImmutableMultiDict[T]:
        """Create an immutable dict view.

        Returns:
            An immutable multi dict
        """
        return ImmutableMultiDict[T](self)

    def getlist(self, key: Any) -> List[Any]:
        return [item_value for item_key, item_value in list(self.multi_items()) if item_key == key]

    def poplist(self, key: Any) -> List[Any]:
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
        args: Union[MultiMapping, Mapping[str, Any], Iterable[tuple[str, Any]], Any, None] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(BaseMultiDict(args or {}))

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return sorted(self.multi_items()) == sorted(other.multi_items())

    def mutablecopy(self) -> MultiDict[T]:
        """Create a mutable copy as a.

        Returns:
            A mutable MultiDict.
        """
        return MultiDict(list(self.multi_items()))

    def __repr__(self) -> str:
        """
        Visual representation of the object sorted by keys.
        """
        items = sorted(self.items())
        return f"{self.__class__.__name__}({items!r})"


class FormMultiDict(ImmutableMultiDict[Any]):
    """MultiDict for form data."""

    async def close(self) -> None:
        """Close all files in the multi-dict.

        Returns:
            None
        """
        for _, value in self.multi_items():
            if isinstance(value, UploadFile):
                await value.close()


class Header(MultiDict):
    """Container used for both request and response headers.
    It is a subclass of  [CIMultiDict](https://multidict.readthedocs.io/en/stable/multidict.html#cimultidictproxy)

    Please checkout [the MultiDict documentation](https://multidict.readthedocs.io/en/stable/multidict.html#multidict)
    for more details about how to use the object.
    """  # noqa: E501

    def __getattr__(self, key: str) -> str:
        if key.startswith("_"):
            return cast(str, self.__getattribute__(key))
        key = key.rstrip("_").replace("_", "-")
        return ",".join(self.getall(key, default=[]))

    def get_all(self, key: str) -> List[Any]:
        """Convenience method mapped to getall()."""
        return self.getall(key, default=[])

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        as_dict = dict(self.items())
        if len(as_dict) == len(self):
            return f"{class_name}({as_dict!r})"
        return f"{class_name}(raw={self.raw!r})"


@dataclass(init=True)
class State:
    state: Dict[str, Any] = None

    def __init__(self, state: Optional[Dict[str, Any]] = None):
        if state is None:
            self.state = {}
        super().__setattr__("state", state)

    def __setattr__(self, key: Any, value: Any) -> None:
        self.state[key] = value

    def __delattr__(self, key: Any) -> None:
        del self.state[key]

    def __copy__(self) -> State:
        return self.__class__(copy(self.state))

    def __len__(self) -> int:
        return len(self.state)

    def __getattr__(self, key: str) -> Any:
        try:
            return self.state[key]
        except KeyError as e:
            raise AttributeError(f"State has no key '{key}'") from e

    def __getitem__(self, key: str) -> Any:
        return self.state[key]

    def copy(self) -> State:
        return copy(self)


class URL:
    url: str
    scheme: Union[str, None] = None
    netloc: Union[str, None] = None
    path: Union[str, None] = None
    fragment: Union[str, None] = None
    query: Union[str, None] = None
    username: Union[str, None] = None
    password: Union[str, None] = None
    port: Union[int, None] = None
    hostname: Union[str, None] = None

    def __new__(cls, url: Union[str, SplitResult]) -> URL:
        """
        Overrides the new base class to create a new structure
        for the URL.
        """
        instance = cls.__create__(url)
        return instance

    @classmethod
    @lru_cache
    def __create__(cls, url: Union[str, SplitResult]) -> URL:
        """
        Creates a new url
        """
        instance: URL = super().__new__(cls)

        assert isinstance(
            url, (str, SplitResult)
        ), "The url must be a string or a SplitResult instance."

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
    @lru_cache
    def build_from_scope(cls, scope: Scope) -> URL:
        """
        Builds the URL from the Scope.

        The path is built based on the `root_path` with the `path` provided
        by the scope.
        """
        scheme = scope.get("scheme", HTTPType.HTTP.value)
        server = scope.get("server")
        path = scope.get("root_path", "") + scope["path"]
        query_string = scope.get("query_string", b"")

        host_header = None
        for key, value in scope["headers"]:
            if key == b"host":
                host_header = value.decode("latin-1")
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
        return cast(SplitResult, getattr(self, "_parsed_url", None))

    @parsed_url.setter
    def parsed_url(self, value: Any) -> None:
        self._parsed_url = value

    @property
    def is_secure(self) -> bool:
        return self.scheme in HTTPType.get_https_types()

    @property
    def base_url(self) -> str:
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
        hostname: Union[Any, None] = None,
        port: Union[Any, None] = None,
        username: Union[Any, None] = None,
        password: Union[Any, None] = None,
    ) -> Any:
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
        params = MultiDict(parse_qsl(self.query, keep_blank_values=True))
        params.update({str(key): str(value) for key, value in kwargs.items()})
        query = urlencode(sorted(params.multi_items()))
        return self.replace(query=query)

    def remove_query_params(self, keys: Union[str, Sequence[str]]) -> URL:
        if isinstance(keys, str):
            keys = [keys]
        params = MultiDict(parse_qsl(self.query, keep_blank_values=True))
        for key in keys:
            params.pop(key, None)
        query = urlencode(sorted(params.multi_items()))
        return self.replace(query=query)

    def replace_query_params(self, **kwargs: Any) -> URL:
        values = [(str(key), str(value)) for key, value in kwargs.items()]
        query = urlencode(values)
        return self.replace(query=query)

    def __eq__(self, other: Any) -> bool:
        return str(self) == str(other)

    def __str__(self) -> str:
        return self.url

    def __repr__(self) -> str:
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

    def make_absolute_url(self, base_url: Union[str, URL]) -> URL:
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
        url = f"{scheme}://{netloc}{path}"
        return URL(url)


class CommaSeparatedStr:
    value: Union[str, Sequence[str]]

    def __new__(cls, value: Union[str, Sequence[str]]) -> CommaSeparatedStr:
        instance = cls.__create__(value=value)
        return instance

    @classmethod
    def __create__(
        cls,
        value: Union[str, Sequence[str]],
        whitespace: str = ",",
        whitespace_split: bool = True,
    ) -> CommaSeparatedStr:
        instance: CommaSeparatedStr = super().__new__(cls)
        if not isinstance(value, str):
            instance.items = list(value)
            return instance
        split = shlex(value, posix=True)
        split.whitespace = whitespace
        split.whitespace_split = whitespace_split
        instance.items = [item.strip() for item in split]
        return instance

    @property
    def items(self) -> List[str]:
        return getattr(self, "_items", [])

    @items.setter
    def items(self, value: Union[str, Sequence[str]]) -> None:
        self._items = value

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: Union[int, slice]) -> Any:
        return self.items[index]

    def __iter__(self) -> Iterator[str]:
        return iter(self.items)

    def __repr__(self) -> str:
        items = list(self)
        return f"{self.__class__.__name__}({items!r})"

    def __str__(self) -> str:
        return ", ".join(repr(item) for item in self)


@dataclass
class Secret:
    """
    Holds the information about a string secret.
    This will make sure no secrets are leaked
    in stack traces.
    """

    value: str = None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('***********')"

    def __str__(self) -> str:
        return self.value

    def __bool__(self) -> bool:
        return bool(self.value)


class QueryParam(ImmutableMultiDict[Any]):
    """
    An immutable multidict.
    """

    def __init__(
        self,
        *args: Union[MultiMapping, Mapping[str, Any], Iterable[tuple[str, Any]], None],
    ) -> None:
        assert len(args) < 2, "Too many arguments."
        value = args[0] if args else []

        if isinstance(value, str):  # type: ignore
            super().__init__(parse_qsl(value, keep_blank_values=True))  # type: ignore
        elif isinstance(value, bytes):  # type: ignore
            super().__init__(parse_qsl(value.decode("latin-1"), keep_blank_values=True))  # type: ignore
        else:
            super().__init__(*args)

    def __str__(self) -> str:
        return urlencode(sorted(self.multi_items()))

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        query_string = str(self)
        return f"{class_name}({query_string!r})"


class UploadFile:
    """
    An uploaded file included as part of the request data.
    """

    def __init__(
        self,
        file: BinaryIO,
        *,
        size: Optional[int] = None,
        filename: Optional[str] = None,
        headers: Optional[Header] = None,
    ) -> None:
        self.filename = filename
        self.file = file
        self.size = size
        self.headers = headers or Header()

    @property
    def content_type(self) -> Optional[str]:
        return self.headers.get("content-type", None)

    @property
    def in_memory(self) -> bool:
        return getattr(self.file, "_rolled", False)

    async def write(self, data: bytes) -> int:
        if self.size is not None:
            self.size += len(data)

        if self.in_memory:
            return await run_sync(self.file.write, data)
        return self.file.write(data)

    async def read(self, size: int = -1) -> bytes:
        if self.in_memory:
            return self.file.read(size)
        return await run_sync(self.file.read, size)

    async def seek(self, offset: int) -> int:
        if self.in_memory:
            return await run_sync(self.file.seek, offset)
        return self.file.seek(offset)

    async def close(self) -> int:
        if self.in_memory:
            return await run_sync(self.file.close)
        return self.file.close()

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"filename={self.filename!r}, "
            f"size={self.size!r}, "
            f"headers={self.headers!r})"
        )


class FormData(ImmutableMultiDict[Any]):
    """
    An immutable multidict, containing both file uploads and text input.
    """

    def __init__(
        self,
        *args: Union[
            FormData,
            Mapping[str, Union[str, UploadFile]],
            List[Tuple[str, Union[str, UploadFile]]],
        ],
        **kwargs: Union[str, UploadFile],
    ) -> None:
        super().__init__(*args, **kwargs)

    async def close(self) -> None:
        for _, value in self.multi_items():
            if isinstance(value, UploadFile):
                await value.close()
