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


def test_concurrent_logging_after_initial_setup():
    """
    Verify that, once setup_logging() has been called,
    multiple threads can log concurrently without ever raising,
    and that all messages make it into the sink.
    """
    sink: list[str] = []
    # initial bind
    setup_logging(CustomLoguruLoggingConfig(sink_list=sink))

    errors: list[Exception] = []

    def worker():
        from lilya.logging import logger

        for _ in range(1000):
            try:
                logger.info("thread-safe test")
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # No errors should have occurred
    assert not errors

    # 5 threads × 1000 messages each
    assert len(sink) == 5000


def test_rebinding_during_logging_keeps_all_threads_happy():
    """
    Start with one logging config, then rebind to a second while workers are
    still churning. No thread should ever see `_logger is None`, and we
    should end up with messages in both sinks.
    """
    sink1: list[str] = []
    sink2: list[str] = []
    config1 = CustomLoguruLoggingConfig(sink_list=sink1)
    config2 = CustomLoguruLoggingConfig(sink_list=sink2)

    # 1) Bind the first logger before any threads start.
    setup_logging(config1)

    errors: list[Exception] = []

    def binder():
        # Let the workers run for a moment, then switch to config2
        time.sleep(0.01)
        setup_logging(config2)

    def worker():
        from lilya.logging import logger

        for _ in range(2000):
            try:
                logger.info("rebind test")
            except Exception as e:
                errors.append(e)

    # 2) Launch workers + binder
    binder_thread = threading.Thread(target=binder)
    worker_threads = [threading.Thread(target=worker) for _ in range(5)]

    for w in worker_threads:
        w.start()
    binder_thread.start()

    for w in worker_threads:
        w.join()
    binder_thread.join()

    # 3) Assertions:

    # (a) No worker ever saw “logger not configured”
    assert not errors, f"Unexpected errors: {errors}"

    # (b) We logged *some* messages under config1...
    assert len(sink1) > 0, f"Expected some messages in the *first* sink, got {len(sink1)}"

    # (c) ...and *some* under config2
    assert len(sink2) > 0, f"Expected some messages in the *second* sink, got {len(sink2)}"
