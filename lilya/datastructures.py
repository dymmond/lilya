from __future__ import annotations

from copy import copy
from dataclasses import dataclass
from functools import lru_cache
from typing import (
    Any,
    Dict,
    ItemsView,
    Iterable,
    Iterator,
    KeysView,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    ValuesView,
    cast,
)
from urllib.parse import SplitResult, parse_qsl, urlencode, urlsplit, urlunsplit

import multidict

from lilya.enums import HTTPType

_KeyType = TypeVar("_KeyType")
# Mapping keys are invariant but their values are covariant since
# you can only read them
# that is, you can't do `Mapping[str, Animal]()["fido"] = Dog()`
_CovariantValueType = TypeVar("_CovariantValueType", covariant=True)


class ImmutableMultiDict(Mapping[_KeyType, _CovariantValueType]):
    _dict: Dict[_KeyType, _CovariantValueType]

    def __init__(
        self,
        *args: Union[
            ImmutableMultiDict[_KeyType, _CovariantValueType],
            Mapping[_KeyType, _CovariantValueType],
            Iterable[Tuple[_KeyType, _CovariantValueType]],
        ],
        **kwargs: Any,
    ) -> None:
        assert len(args) < 2, "Too many arguments."

        value: Any = args[0] if args else []
        if kwargs:
            value = (
                ImmutableMultiDict(value).multi_items() + ImmutableMultiDict(kwargs).multi_items()
            )

        if not value:
            _items: List[Tuple[Any, Any]] = []
        elif hasattr(value, "multi_items"):
            value = cast(ImmutableMultiDict[_KeyType, _CovariantValueType], value)
            _items = list(value.multi_items())
        elif hasattr(value, "items"):
            value = cast(Mapping[_KeyType, _CovariantValueType], value)
            _items = list(value.items())
        else:
            value = cast(List[Tuple[Any, Any]], value)
            _items = list(value)

        self._dict = dict(_items)
        self._list = _items

    def getlist(self, key: Any) -> List[_CovariantValueType]:
        return [item_value for item_key, item_value in self._list if item_key == key]

    def keys(self) -> KeysView[_KeyType]:
        return self._dict.keys()

    def values(self) -> ValuesView[_CovariantValueType]:
        return self._dict.values()

    def items(self) -> ItemsView[_KeyType, _CovariantValueType]:
        return self._dict.items()

    def multi_items(self) -> List[Tuple[_KeyType, _CovariantValueType]]:
        return list(self._list)

    def __getitem__(self, key: _KeyType) -> _CovariantValueType:
        return self._dict[key]

    def __contains__(self, key: Any) -> bool:
        return key in self._dict

    def __iter__(self) -> Iterator[_KeyType]:
        return iter(self.keys())

    def __len__(self) -> int:
        return len(self._dict)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return sorted(self._list) == sorted(other._list)

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        items = self.multi_items()
        return f"{class_name}({items!r})"


class MultiDict(ImmutableMultiDict[Any, Any]):
    def __setitem__(self, key: Any, value: Any) -> None:
        self.setlist(key, [value])

    def __delitem__(self, key: Any) -> None:
        self._list = [(k, v) for k, v in self._list if k != key]
        del self._dict[key]

    def pop(self, key: Any, default: Any = None) -> Any:
        self._list = [(k, v) for k, v in self._list if k != key]
        return self._dict.pop(key, default)

    def popitem(self) -> Tuple[Any, Any]:
        key, value = self._dict.popitem()
        self._list = [(k, v) for k, v in self._list if k != key]
        return key, value

    def poplist(self, key: Any) -> List[Any]:
        values = [v for k, v in self._list if k == key]
        self.pop(key)
        return values

    def clear(self) -> None:
        self._dict.clear()
        self._list.clear()

    def setdefault(self, key: Any, default: Any = None) -> Any:
        if key not in self:
            self._dict[key] = default
            self._list.append((key, default))

        return self[key]

    def setlist(self, key: Any, values: List[Any]) -> None:
        if not values:
            self.pop(key, None)
        else:
            existing_items = [(k, v) for (k, v) in self._list if k != key]
            self._list = existing_items + [(key, value) for value in values]
            self._dict[key] = values[-1]

    def append(self, key: Any, value: Any) -> None:
        self._list.append((key, value))
        self._dict[key] = value

    def update(
        self,
        *args: Union[
            MultiDict,
            Mapping[Any, Any],
            List[Tuple[Any, Any]],
        ],
        **kwargs: Any,
    ) -> None:
        value = MultiDict(*args, **kwargs)
        existing_items = [(k, v) for (k, v) in self._list if k not in value.keys()]
        self._list = existing_items + value.multi_items()
        self._dict.update(value)


class Header(multidict.CIMultiDict):
    """
    Header that handles both request and response.
    It subclasses the [CIMultiDict](https://multidict.readthedocs.io/en/stable/multidict.html#cimultidictproxy)

    [MultiDict documentation](https://multidict.readthedocs.io/en/stable/multidict.html#multidict)
    for more details about how to use the object. In general, it should work
    very similar to a regular dictionary.
    """

    def __getattr__(self, key: str) -> Any:
        if not key.startswith("_"):
            key = key.rstrip("_").replace("_", "-")
            return ",".join(self.getall(key, default=[]))
        return self.__getattribute__(key)

    def get_all(self, key: str) -> Any:
        """Convenience method mapped to ``getall()``."""
        return self.getall(key, default=[])


class State:
    _state: Dict[str, Any]

    def __init__(self, state: Optional[Dict[str, Any]] = None):
        if state is None:
            state = {}
        super().__setattr__("_state", state)

    def __setattr__(self, key: Any, value: Any) -> None:
        self._state[key] = value

    def __delattr__(self, key: Any) -> None:
        del self._state[key]

    def __copy__(self) -> State:
        return self.__class__(copy(self._state))

    def __len__(self) -> int:
        return len(self._state)

    def __getattr__(self, key: str) -> Any:
        try:
            return self._state[key]
        except KeyError as e:
            raise AttributeError(f"State has no key '{key}'") from e

    def __getitem__(self, key: str) -> Any:
        return self._state[key]

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
        query = urlencode(params.multi_items())
        return self.replace(query=query)

    def remove_query_params(self, keys: Union[str, Sequence[str]]) -> URL:
        if isinstance(keys, str):
            keys = [keys]
        params = MultiDict(parse_qsl(self.query, keep_blank_values=True))
        for key in keys:
            params.pop(key, None)
        query = urlencode(params.multi_items())
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
