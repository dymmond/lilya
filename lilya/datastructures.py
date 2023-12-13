from __future__ import annotations

from copy import copy
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence, Union, cast
from urllib.parse import SplitResult, parse_qsl, urlencode, urlsplit, urlunsplit

import multidict

from lilya.enums import HTTPType


class MultiDict(multidict.MultiDict):
    """
    Multidict that handles with majority of the multidict cases
    an adds some extra functionalities on top of it.

    You can read more about how the [Multidict](https://multidict.aio-libs.org/en/stable/multidict.html#multidict) operates and what you can do with it.
    """

    def multi_items(self) -> List[Any]:
        return list(self.items())


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
