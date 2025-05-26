from __future__ import annotations

from typing import Annotated

from sayer import Argument, Option, command, error, success

from lilya.cli.directives.operations._constants import SECRET_KEY_INSECURE_PREFIX
from lilya.cli.exceptions import DirectiveError
from lilya.cli.templates import TemplateDirective
from lilya.cli.terminal import Print
from lilya.crypto import get_random_secret_key

printer = Print()


@command(name="createapp")  # type: ignore
def create_app(
    name: Annotated[str, Argument(help="The name of the app.")],
    verbosity: Annotated[int, Option(1, "-v", help="Displays the files generated")],
) -> None:
    """Creates the scaffold of an application

    How to run: `lilya createapp <NAME>`

    Example: `lilya createapp myapp`
    """
    options = {
        "secret_key": SECRET_KEY_INSECURE_PREFIX + get_random_secret_key(),
        "verbosity": verbosity,
        "is_simple": True,
    }
    directive = TemplateDirective()

    try:
        directive.handle("app", name=name, **options)
        success(f"App {name} generated successfully!")
    except DirectiveError as e:
        error(str(e))
