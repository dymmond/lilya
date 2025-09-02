from __future__ import annotations

import json
import threading
from abc import ABC, abstractmethod
from typing import Any, cast

from lilya.protocols.serializer import SerializerProtocol


class SerializerProxy:
    """
    Proxy for the real serializer used by Lilya.
    """

    def __init__(self) -> None:
        self._serializer: SerializerProtocol | None = None
        self._lock: threading.RLock = threading.RLock()

    def bind_serializer(self, serializer: SerializerProtocol | None) -> None:  # noqa
        with self._lock:
            self._serializer = serializer

    def __getattr__(self, item: str) -> Any:
        with self._lock:
            if not self._serializer:
                setup_serializer()
                return getattr(self._serializer, item)
            return getattr(self._serializer, item)


serializer: SerializerProtocol = cast(SerializerProtocol, SerializerProxy())


class SerializerConfig(ABC):
    """
    An instance of [SerializerConfig](https://lilya.dev/serialization/).

    !!! Tip
        You can create your own `SerializerMiddleware` version and pass your own
        configurations. You don't need to use the built-in version although it
        is recommended to do it so.

    **Example**

    ```python
    from lilya.apps import Lilya
    from lilya.serializer import SerializerConfig

    serializer_config = SerializerConfig()

    app = Lilya(serializer_config=serializer_config)
    ```
    """

    def __init__(
        self,
        **kwargs: Any,
    ) -> None:
        self.options = kwargs
        self.skip_setup_configure: bool = kwargs.get("skip_setup_configure", True)

    def configure(self) -> None:
        """
        Configures the serializer settings.
        """
        raise NotImplementedError("`configure()` must be implemented in subclasses.")

    @abstractmethod
    def get_serializer(self) -> Any:
        """
        Returns the serializer instance.
        """
        raise NotImplementedError("`get_serializer()` must be implemented in subclasses.")


class CompactSerializer:
    load = json.load
    loads = json.loads

    @staticmethod
    def dump(obj: Any, **kwargs: Any) -> None:
        kwargs.setdefault("ensure_ascii", False)
        kwargs.setdefault("allow_nan", False)
        kwargs.setdefault("indent", None)
        kwargs.setdefault("separators", (",", ":"))
        json.dump(obj, **kwargs)

    @staticmethod
    def dumps(obj: Any, **kwargs: Any) -> str:
        kwargs.setdefault("ensure_ascii", False)
        kwargs.setdefault("allow_nan", False)
        kwargs.setdefault("indent", None)
        kwargs.setdefault("separators", (",", ":"))
        return json.dumps(obj, **kwargs)


class StandardSerializerConfig(SerializerConfig):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def configure(self) -> None: ...

    def get_serializer(self) -> Any:
        return CompactSerializer


def setup_serializer(serializer_config: SerializerConfig | None = None) -> None:
    """
    Sets up the serializer system for the application.

    If a custom `SerializerConfig` is provided, it will be used to configure
    the serializer system. Otherwise, a default `StandardSerializerConfig` will be applied.

    This allows full flexibility to use different serialization backends such as
    the standard Python `json`, `orjson`, `ujson`, or any custom
    implementation based on the `SerializerConfig` interface.

    Args:
        serializer_config: An optional instance of `SerializerConfig` to customize
            the serializer behavior. If not provided, the default standard serializer
            configuration will be used.

    Raises:
        ValueError: If the provided `serializer_config` is not an instance of `SerializerConfig`.
    """
    if serializer_config is not None and not isinstance(serializer_config, SerializerConfig):
        raise ValueError("`serializer_config` must be an instance of SerializerConfig.")

    config = serializer_config or StandardSerializerConfig()

    if not config.skip_setup_configure:
        config.configure()

    # Gets the serializer instance from the serializer_config
    _serializer = config.get_serializer()
    serializer.bind_serializer(_serializer)
