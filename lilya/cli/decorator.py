from collections.abc import Callable
from typing import Any


def directive(
    func: Callable[..., Any] | None = None,
    *,
    display_in_cli: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Marks a function-based Sayer CLI command as a custom Lilya directive.

    This decorator factory allows optional configuration via parameters, such as `show_on_cli`.

    Example usage:

        @directive(display_in_cli=True)
        @command(name="create")
        async def create(name: Annotated[str, Option(help="Your name")]):
            ...

    Parameters:
        display_in_cli (bool): Whether the directive should be visible in the CLI help output.

    Returns:
        Callable: A decorator that marks the function as a custom directive.
    """

    def wrapper(f: Callable[..., Any]) -> Callable[..., Any]:
        f.__is_custom_directive__ = True
        f.__display_in_cli__ = display_in_cli
        return f

    if func is not None:
        return wrapper(func)

    return wrapper
