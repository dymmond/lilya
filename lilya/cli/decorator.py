from collections.abc import Callable
from typing import Any, Protocol


class DirectiveFunction(Protocol):
    """Protocol for functions marked as directives."""

    __is_custom_directive__: bool
    __display_in_cli__: bool

    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...


def directive(
    func: Callable[..., Any] | None = None,
    *,
    display_in_cli: bool = False,
) -> Callable[[Callable[..., Any]], DirectiveFunction]:
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

    def wrapper(f: Callable[..., Any]) -> DirectiveFunction:
        f.__is_custom_directive__ = True  # type: ignore[attr-defined]
        f.__display_in_cli__ = display_in_cli  # type: ignore[attr-defined]
        return f  # type: ignore[return-value]

    if func is not None:
        return wrapper(func)

    return wrapper
