import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any


def directive(func: Callable[..., Any]) -> Callable:
    """
    Wrapper of a Sayer command-line directive.
    """

    if inspect.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        wrapper = async_wrapper
    else:

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        wrapper = sync_wrapper

    # Declare a custom directive property
    wrapper.__is_custom_directive__ = True
    return wrapper
