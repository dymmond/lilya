from __future__ import annotations

import sys
from functools import wraps
from typing import Any

from lilya.conf import settings
from lilya.conf.context_vars import set_override_settings
from lilya.conf.global_settings import Settings

if sys.version_info >= (3, 10):  # pragma: no cover
    from typing import ParamSpec
else:  # pragma: no cover
    from typing_extensions import ParamSpec

P = ParamSpec("P")


class override_settings:
    """
    A context manager that allows overriding Lilya settings temporarily.

    Usage:
    ```
    with override_settings(SETTING_NAME=value):
        # code that uses the overridden settings
    ```

    The `override_settings` class can also be used as a decorator.

    Usage:
    ```
    @override_settings(SETTING_NAME=value)
    def test_function():
        # code that uses the overridden settings
    ```
    """

    def __init__(self, **kwargs: Any) -> None:
        """
        Initialize the class with the given keyword arguments.

        Args:
            **kwargs: Additional keyword arguments to be stored as options.

        Returns:
            None
        """
        self.app = kwargs.pop("app", None)
        self.options = kwargs

    def __enter__(self) -> None:
        """
        Enter the context manager and set the modified settings.

        Saves the original settings and sets the modified settings
        based on the provided options.

        Returns:
            None
        """
        self._original_settings = settings._wrapped
        settings._wrapped = Settings(settings._wrapped, **self.options)
        set_override_settings(True)

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        """
        Restores the original settings and sets them up again.

        Args:
            exc_type (Any): The type of the exception raised, if any.
            exc_value (Any): The exception instance raised, if any.
            traceback (Any): The traceback for the exception raised, if any.
        """
        settings._wrapped = self._original_settings
        settings._setup()
        set_override_settings(False)

    def __call__(self, test_func: Any) -> Any:
        """
        Decorator that wraps a test function and executes it within a context manager.

        Args:
            test_func (Any): The test function to be wrapped.

        Returns:
            Any: The result of the test function.

        """

        @wraps(test_func)
        def inner(*args: P.args, **kwargs: P.kwargs) -> Any:
            with self:
                return test_func(*args, **kwargs)

        return inner
