import threading
import time
from typing import Any

import loguru
import pytest
import structlog
from loguru import logger as loguru_logger

from lilya.logging import LoggingConfig, setup_logging


# Simulate a clean logger for each test
def reset_global_logger():
    from lilya import logging as lilya_logger

    lilya_logger.logger.bind_logger(None)


@pytest.fixture(autouse=True)
def clean_logger():
    reset_global_logger()
    yield
    reset_global_logger()


class CustomLoguruLoggingConfig(LoggingConfig):
    def __init__(self, sink_list, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.sink_list = sink_list

    def configure(self) -> None:
        loguru_logger.remove()
        loguru_logger.add(
            sink=self.sink_list.append,
            level=self.level,
            format="<green>{time}</green> | <level>{level}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
        )

    def get_logger(self) -> Any:
        return loguru.logger


class ListLogger:
    def __init__(self, sink: list[str]):
        self.sink = sink

    def info(self, event: str, **kwargs):
        self.sink.append(event)

    def debug(self, event: str, **kwargs):
        self.sink.append(event)

    def warning(self, event: str, **kwargs):
        self.sink.append(event)

    def error(self, event: str, **kwargs):
        self.sink.append(event)

    def critical(self, event: str, **kwargs):
        self.sink.append(event)


class CustomStructlogLoggingConfig(LoggingConfig):
    def __init__(self, sink_list, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.sink_list = sink_list

    def configure(self) -> None:
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger("info"),
            processors=[],
            context_class=dict,
            logger_factory=lambda *_: ListLogger(self.sink_list),
        )

    def get_logger(self) -> Any:
        return structlog.get_logger(__name__)


def test_loguru_logger_setup():
    sink = []
    setup_logging(CustomLoguruLoggingConfig(sink_list=sink))
    from lilya.logging import logger

    logger.debug("Debug message from Loguru")
    logger.info("Info message from Loguru")

    assert any("Debug message from Loguru" in message for message in sink)
    assert any("Info message from Loguru" in message for message in sink)


def test_structlog_logger_capture():
    sink = []
    setup_logging(CustomStructlogLoggingConfig(sink_list=sink))

    from lilya.logging import logger

    logger.info("Info message from Structlog")
    logger.error("Error message from Structlog")

    # The logs are captured as JSON strings in the sink
    assert any("Info message from Structlog" in message for message in sink)
    assert any("Error message from Structlog" in message for message in sink)


def test_invalid_logging_config():
    with pytest.raises(ValueError):
        setup_logging(logging_config="not_a_valid_config")


def test_standard_logging_fallback(monkeypatch):
    setup_logging()

    from lilya.logging import logger

    assert hasattr(logger, "info")
    assert hasattr(logger, "debug")


@pytest.mark.parametrize(
    "level", [None, "lilya", 1, 2.5, "5-da"], ids=["none", "str", "int", "float", "str-int"]
)
def test_raises_assert_error(level):
    with pytest.raises(AssertionError):

        class CustomLog(LoggingConfig):
            def __init__(self):
                super().__init__(level=level)

            def configure(self) -> None:
                return None

            def get_logger(self) -> Any:
                return structlog.get_logger(__name__)

        CustomLog()


def test_concurrent_logging_after_setup():
    """
    After a one-time setup_logging, multiple threads should all be able to log
    concurrently without errors, and all messages should be captured.
    """
    sink: list[str] = []
    setup_logging(CustomLoguruLoggingConfig(sink_list=sink))

    def worker():
        from lilya.logging import logger

        for _ in range(1000):
            logger.info("thread-safe test")

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 5 threads × 1000 messages each
    assert len(sink) == 5000


def test_rebinding_during_logging_thread_safe():
    """
    While one thread is rebinding logger via setup_logging, other threads
    should continue logging without raising, and messages should end up
    in at least one of the two sinks.
    """
    sink1: list[str] = []
    sink2: list[str] = []
    config1 = CustomLoguruLoggingConfig(sink_list=sink1)
    config2 = CustomLoguruLoggingConfig(sink_list=sink2)

    errors: list[Exception] = []

    def binder():
        # bind first config, then rebind to second after a short sleep
        setup_logging(config1)
        time.sleep(0.01)
        setup_logging(config2)

    def worker():
        from lilya.logging import logger

        for _ in range(1000):
            try:
                logger.info("rebind test")
            except Exception as e:
                errors.append(e)

    binder_thread = threading.Thread(target=binder)
    worker_threads = [threading.Thread(target=worker) for _ in range(5)]

    binder_thread.start()
    for w in worker_threads:
        w.start()

    binder_thread.join()
    for w in worker_threads:
        w.join()

    # No logging calls should have thrown
    assert not errors

    # At least some messages should have been captured
    assert sink1 or sink2
