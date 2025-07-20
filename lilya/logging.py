from __future__ import annotations

import logging.config
import threading
from abc import ABC, abstractmethod
from typing import Annotated, Any, cast

from lilya.protocols.logging import LoggerProtocol
from lilya.types import Doc


class LoggerProxy:
    """
    Proxy for the real logger used by Esmerald.
    """

    def __init__(self) -> None:
        self._logger: LoggerProtocol | None = None
        self._lock: threading.RLock = threading.RLock()

    def bind_logger(self, logger: LoggerProtocol | None) -> None:  # noqa
        with self._lock:
            self._logger = logger

    def __getattr__(self, item: str) -> Any:
        with self._lock:
            if not self._logger:
                setup_logging()
                return getattr(self._logger, item)
            return getattr(self._logger, item)


logger: LoggerProtocol = cast(LoggerProtocol, LoggerProxy())


class LoggingConfig(ABC):
    """
    An instance of [LoggingConfig](https://lilya.dev/logging/).

    !!! Tip
        You can create your own `LoggingMiddleware` version and pass your own
        configurations. You don't need to use the built-in version although it
        is recommended to do it so.

    **Example**

    ```python
    from lilya.apps import Lilya
    from lilya.logging import LoggingConfig

    logging_config = LoggingConfig()

    app = Lilya(logging_config=logging_config)
    ```
    """

    __logging_levels__: list[str] = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    def __init__(
        self,
        level: Annotated[
            str,
            Doc(
                """
                The logging level.
                """
            ),
        ] = "DEBUG",
        **kwargs: Any,
    ) -> None:
        levels: str = ", ".join(self.__logging_levels__)
        assert level in self.__logging_levels__, (
            f"'{level}' is not a valid logging level. Available levels: '{levels}'."
        )

        self.level = level.upper()
        self.options = kwargs
        self.skip_setup_configure: bool = kwargs.get("skip_setup_configure", False)

    def configure(self) -> None:
        """
        Configures the logging settings.
        """
        raise NotImplementedError("`configure()` must be implemented in subclasses.")

    @abstractmethod
    def get_logger(self) -> Any:
        """
        Returns the logger instance.
        """
        raise NotImplementedError("`get_logger()` must be implemented in subclasses.")


class StandardLoggingConfig(LoggingConfig):
    def __init__(self, config: dict[str, Any] | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.config = config or self.default_config()

    def default_config(self) -> dict[str, Any]:  # noqa
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                },
            },
            "root": {
                "level": self.level,
                "handlers": ["console"],
            },
        }

    def configure(self) -> None:
        logging.config.dictConfig(self.config)

    def get_logger(self) -> Any:
        return logging.getLogger("lilya")


def setup_logging(logging_config: LoggingConfig | None = None) -> None:
    """
    Sets up the logging system for the application.

    If a custom `LoggingConfig` is provided, it will be used to configure
    the logging system. Otherwise, a default `StandardLoggingConfig` will be applied.

    This allows full flexibility to use different logging backends such as
    the standard Python `logging`, `loguru`, `structlog`, or any custom
    implementation based on the `LoggingConfig` interface.

    Args:
        logging_config: An optional instance of `LoggingConfig` to customize
            the logging behavior. If not provided, the default standard logging
            configuration will be used.

    Raises:
        ValueError: If the provided `logging_config` is not an instance of `LoggingConfig`.
    """
    if logging_config is not None and not isinstance(logging_config, LoggingConfig):
        raise ValueError("`logging_config` must be an instance of LoggingConfig.")

    config = logging_config or StandardLoggingConfig()

    if not config.skip_setup_configure:
        config.configure()

    # Gets the logger instance from the logging_config
    _logger = config.get_logger()
    logger.bind_logger(_logger)
