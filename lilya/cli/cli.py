from __future__ import annotations

import typing
from pathlib import Path

import click
from sayer import Sayer
from sayer.params import Option

from lilya import __version__
from lilya.cli.directives.operations.createapp import create_app as create_app  # noqa
from lilya.cli.directives.operations.createdeployment import (
    create_deployment as create_deployment,  # noqa
)
from lilya.cli.directives.operations.createproject import create_project as create_project  # noqa
from lilya.cli.directives.operations.list import directives as directives  # noqa
from lilya.cli.directives.operations.mail import mail as mail  # noqa
from lilya.cli.directives.operations.run import run as run  # noqa
from lilya.cli.directives.operations.runserver import runserver as runserver  # noqa
from lilya.cli.directives.operations.shell import shell as shell  # noqa
from lilya.cli.directives.operations.show_urls import show_urls as show_urls  # noqa
from lilya.cli.groups import DirectiveGroup
from lilya.cli.utils import get_custom_directives_to_cli

help_text = """
Lilya command line tool allowing to run Lilya native directives or
project unique and specific directives by passing the `-n` parameter.

How to run Lilya native: `lilya createproject <NAME>`. Or any other Lilya native command.

    Example: `lilya createproject myapp`


How to run custom directives: `lilya --app <APP-LOCATION> run -n <DIRECTIVE NAME> <ARGS>`.

    Example: `lilya --app myapp:app run -n createsuperuser`

"""

lilya_cli = Sayer(
    name="Lilya",
    help=help_text,
    add_version_option=True,
    version=__version__,
    group_class=DirectiveGroup,
)


@lilya_cli.callback(invoke_without_command=True)
def lilya_callback(
    ctx: click.Context,
    app: typing.Annotated[
        str,
        Option(
            required=False, help="Module path to the Lilya application. In a module:path format."
        ),
    ],
    path: typing.Annotated[
        str | None,
        Option(
            required=False,
            help="A path to a Python file or package directory with ([blue]__init__.py[/blue] files) containing a [bold]Lilya[/bold] app. If not provided, Lilya will try to discover.",
        ),
    ],
) -> None: ...


lilya_cli.add_command(directives)
lilya_cli.add_command(show_urls)
lilya_cli.add_command(runserver)
lilya_cli.add_command(run)
lilya_cli.add_command(create_project)
lilya_cli.add_command(create_app)
lilya_cli.add_command(create_deployment)
lilya_cli.add_command(shell)
lilya_cli.add_app("mail", mail)

# Load custom directives if any
application_directives = get_custom_directives_to_cli(str(Path.cwd()))

# Add application directives to the CLI
if application_directives:
    for _, command in application_directives.items():
        if isinstance(command, Sayer):
            lilya_cli.add_custom_command(command, command._group.name)
        else:
            lilya_cli.add_custom_command(command)
