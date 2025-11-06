from dataclasses import dataclass


@dataclass(frozen=True)
class Doc:
    """Define the documentation of a type annotation using `Annotated`, to be
    used in class attributes, function and method parameters, return values,
    and variables.

    The value should be a positional-only string literal to allow static tools
    like editors and documentation generators to use it.

    This complements docstrings.

    The string value passed is available in the attribute `documentation`.

    Example:

    ```Python
    from typing import Annotated
    # from annotated_doc import Doc # This is the class defined below

    def hi(name: Annotated[str, Doc("Who to say hi to")]) -> None:
        print(f"Hi, {name}!")
    ```
    """

    documentation: str
