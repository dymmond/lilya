from __future__ import annotations

import os
import sys
from enum import Enum
from typing import TYPE_CHECKING, Any, TypeVar

import click

from lilya._internal._events import generate_lifespan_events
from lilya.cli.constants import APP_PARAMETER, LILYA_DISCOVER_APP
from lilya.cli.env import DirectiveEnv
from lilya.cli.terminal.print import Print
from lilya.cli.utils import fetch_directive
from lilya.compat import run_sync
from lilya.types import Lifespan

if TYPE_CHECKING:
    from lilya.apps import ChildLilya, Lilya

T = TypeVar("T")

printer = Print()


class Position(int, Enum):
    DEFAULT = 5
    BACK = 3


@click.option(
    "--directive",
    "directive",
    required=True,
    help=("The name of the file of the custom directive to run."),
)
@click.argument("directive_args", nargs=-1, type=click.UNPROCESSED)
@click.command(
    name="run",
    context_settings={
        "ignore_unknown_options": True,
    },
)
def run(env: DirectiveEnv, directive: str, directive_args: Any) -> None:
    """
    Runs every single custom directive in the system.

    How to run: `lilya --app <APP-LOCATION> run -n <DIRECTIVE NAME> <ARGS>`.

        Example: `lilya --app myapp:app run -n createsuperuser`
    """
    name = directive
    if name is not None and getattr(env, "app", None) is None:
        error = (
            "You cannot specify a custom directive without specifying the --app or setting "
            "LILYA_DEFAULT_APP environment variable."
        )
        printer.write_error(error)
        sys.exit(1)

    # Loads the directive object
    directive = fetch_directive(name, env.command_path, True)
    if not directive:
        printer.write_error(f"Unknown directive: {name!r}")
        sys.exit(1)

    # Execute the directive
    # The arguments for the directives start at the position 6
    position = get_position()
    program_name = " ".join(value for value in sys.argv[:position])

    ## Check if application is up and execute any event
    # Shutting down after
    lifespan = generate_lifespan_events(
        env.app.router.on_startup,
        env.app.router.on_shutdown,
        env.app.router.lifespan_context,
    )
    run_sync(execute_lifespan(env.app, lifespan, directive, program_name, position))


def get_position() -> int:
    """
    Gets the position of the arguments to read and pass them
    onto the directive.
    """
    if os.getenv(LILYA_DISCOVER_APP) is None and APP_PARAMETER in sys.argv:
        return Position.DEFAULT
    elif os.getenv(LILYA_DISCOVER_APP) is not None and APP_PARAMETER in sys.argv:
        return Position.DEFAULT
    return Position.BACK


async def execute_lifespan(
    app: Lilya | ChildLilya | None,
    lifespan: Lifespan,
    directive: Any,
    program_name: str,
    position: int,
) -> None:
    """
    Executes the lifespan events and the directive.
    """
    async with lifespan(app):
        await directive.execute_from_command(sys.argv[:], program_name, position)
