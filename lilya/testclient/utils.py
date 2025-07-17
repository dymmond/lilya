from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, Any

from lilya.compat import is_async_callable
from lilya.conf import _monkay as monkay_for_settings

if TYPE_CHECKING:
    from lilya.conf.global_settings import Settings


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
        self._innermanager: Any = None

    async def __aenter__(self) -> None:
        """
        Enter the context manager and set the modified settings.

        Saves the original settings and sets the modified settings
        based on the provided options.

        Returns:
            None
        """
        return self.__enter__()

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        """
        Restores the original settings and sets them up again.

        Args:
            exc_type (Any): The type of the exception raised, if any.
            exc_value (Any): The exception instance raised, if any.
            traceback (Any): The traceback for the exception raised, if any.
        """
        self.__exit__(exc_type, exc_value, traceback)

    def __enter__(self) -> None:
        """
        Enter the context manager and set the modified settings.

        Saves the original settings and sets the modified settings
        based on the provided options.

        Returns:
            None
        """
        _original_settings: Settings = monkay_for_settings.settings
        opts = _original_settings.dict()
        opts.update(self.options)
        self._innermanager = monkay_for_settings.with_settings(
            _original_settings.__class__(**opts)
        )
        self._innermanager.__enter__()

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        """
        Restores the original settings and sets them up again.

        Args:
            exc_type (Any): The type of the exception raised, if any.
            exc_value (Any): The exception instance raised, if any.
            traceback (Any): The traceback for the exception raised, if any.
        """
        self._innermanager.__exit__(exc_type, exc_value, traceback)

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """
        Decorator that wraps a test function and executes it within a context manager.

        Args:
            test_func (Any): The test function to be wrapped.

        Returns:
            Any: The result of the test function.

        """
        if is_async_callable(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                async with self:
                    return await func(*args, **kwargs)

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                with self:
                    return func(*args, **kwargs)

            return sync_wrapper
