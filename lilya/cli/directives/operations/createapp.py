import click

from lilya.cli.directives.operations._constants import SECRET_KEY_INSECURE_PREFIX
from lilya.cli.exceptions import DirectiveError
from lilya.cli.templates import TemplateDirective
from lilya.cli.terminal import Print
from lilya.crypto import get_random_secret_key

printer = Print()


@click.option("-v", "--verbosity", default=1, type=int, help="Displays the files generated")
@click.argument("name", type=str)
@click.command(name="createapp")
def create_app(name: str, verbosity: int) -> None:
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
        printer.write_success(f"App {name} generated successfully!")
    except DirectiveError as e:
        printer.write_error(str(e))
