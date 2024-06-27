from functools import wraps
from typing import Any

from lilya.conf import settings
from lilya.conf.global_settings import Settings


class override_settings:
    def __init__(self, **kwargs: Any) -> None:
        self.options = kwargs

    def __enter__(self) -> None:
        breakpoint()
        self._original_settings = settings._wrapped
        settings._wrapped = Settings(settings._wrapped, **self.options)
        settings._setup()

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        settings._wrapped = self._original_settings
        settings._setup()

    def __call__(self, test_func: Any) -> Any:
        @wraps(test_func)
        def inner(*args, **kwargs):
            with self:
                return test_func(*args, **kwargs)

        return inner
