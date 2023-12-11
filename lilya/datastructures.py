from __future__ import annotations

from copy import copy
from typing import Any, Dict, Optional

from multidict import CIMultiDict


class Header(CIMultiDict):
    """
    Header that handles both request and response.
    It subclasses the [CIMultiDict](https://multidict.readthedocs.io/en/stable/multidict.html#cimultidictproxy)

    [MultiDict documentation](https://multidict.readthedocs.io/en/stable/multidict.html#multidict)
    for more details about how to use the object. In general, it should work
    very similar to a regular dictionary.
    """

    def __getattr__(self, key: str) -> str:
        if not key.startswith("_"):
            key = key.rstrip("_").replace("_", "-")
            return ",".join(self.getall(key, default=[]))
        return self.__getattribute__(key)

    def get_all(self, key: str):
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
