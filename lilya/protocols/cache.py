from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class CacheBackend(ABC):
    """
    Abstract Base Class (ABC) defining the interface for cache backends.

    This protocol ensures that any cache backend implementation used with
    the caching decorator (or similar components) adheres to a consistent
    API for basic cache operations: get, set, and delete.
    """

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """
        Asynchronously retrieves a cached value associated with the given key.

        If the key is not found in the cache, or if the value has expired,
        this method should return `None`.

        Args:
            key (str): The unique identifier for the cached item.

        Returns:
            Any | None: The cached value if found and valid, otherwise `None`.

        Raises:
            NotImplementedError: If the concrete cache backend does not implement this method.
        """
        raise NotImplementedError("Cache backend must implement get method.")

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        Asynchronously stores a value in the cache under the specified key.

        An optional Time-To-Live (TTL) can be provided, after which the
        cached item should be considered expired. If `ttl` is `None`, the
        item should ideally persist indefinitely or according to the backend's
        default expiration policy.

        Args:
            key (str): The unique identifier for the item to cache.
            value (Any): The data to be cached. This can be any serializable Python object.
            ttl (int | None, optional): The time in seconds after which the cached item
                                        should expire. `None` for no explicit expiration.
                                        Defaults to `None`.

        Raises:
            NotImplementedError: If the concrete cache backend does not implement this method.
        """
        raise NotImplementedError("Cache backend must implement set method.")

    @abstractmethod
    async def delete(self, key: str) -> None:
        """
        Asynchronously removes a value from the cache associated with the given key.

        If the key does not exist in the cache, this method should typically
        do nothing and not raise an error.

        Args:
            key (str): The unique identifier of the item to remove from the cache.

        Raises:
            NotImplementedError: If the concrete cache backend does not implement this method.
        """
        raise NotImplementedError("Cache backend must implement delete method.")
