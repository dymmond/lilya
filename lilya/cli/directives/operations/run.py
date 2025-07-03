from __future__ import annotations

import inspect
import os
import sys
from enum import Enum
from typing import TYPE_CHECKING, Annotated, Any, TypeVar

import click
from sayer import Argument, Option, command, error

from lilya._internal._events import generate_lifespan_events
from lilya.cli.base import BaseDirective
from lilya.cli.constants import APP_PARAMETER, LILYA_DISCOVER_APP
from lilya.cli.env import DirectiveEnv
from lilya.cli.utils import fetch_directive
from lilya.context import G, g_context
from lilya.types import Lifespan

if TYPE_CHECKING:
    from lilya.apps import ChildLilya, Lilya

T = TypeVar("T")


class Position(int, Enum):
    DEFAULT = 5
    BACK = 3


@command(  # type: ignore
    context_settings={
        "ignore_unknown_options": True,
        "allow_extra_args": True,
    },
)
async def run(
    directive: Annotated[
        str | None,
        Option(required=False, help="The name of the file of the custom directive to run."),
    ],
    directive_args: Annotated[
        list[str],
        Argument(
            nargs=-1,
            type=click.UNPROCESSED,
            help="The arguments needed to be passed to the custom directive",
            required=False,
        ),
    ],
) -> None:
    """
    Runs every single custom directive in the system.

    How to run:

    ```shell
    lilya --app <APP-LOCATION> run <DIRECTIVE NAME> <ARGS>
    ````

    You can also run with the `@directive` on top of a Sayer command.

    ```shell
    lilya run <directive-name> <ARGS>
    ```

    Example: `lilya --app myapp:app run createsuperuser`
    """
    ctx = click.get_current_context()
    env = ctx.ensure_object(DirectiveEnv)

    name = directive
    if name is not None and getattr(env, "app", None) is None:
        error(
            "You cannot specify a custom directive without specifying the --app or setting "
            "LILYA_DEFAULT_APP environment variable."
        )
        sys.exit(1)

    directive = (
        fetch_directive(name, env.command_path, True)
        if name is not None
        else fetch_directive(directive_args[0], env.command_path, True)
    )
    if not directive:
        error(f"Unknown directive: {name!r}")
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
    await execute_lifespan(env.app, lifespan, directive, program_name, position)


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


async def set_global_context() -> Any:
    """
    Sets the global context for the directive.
    This is used to store any global variables that can be accessed
    by the directive.
    """
    initial_context: Any = None

    # Set the global context to an empty dictionary
    token = g_context.set(G(initial_context))
    return token


async def reset_global_context(token: Any) -> None:
    """
    Resets the global context for the directive.
    This is used to clear any global variables that were set by the directive.
    """
    g_context.reset(token)


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
        token = await set_global_context()
        if isinstance(directive, BaseDirective):
            await directive.execute_from_command(sys.argv[:], program_name, position)
        elif callable(directive):
            if inspect.iscoroutinefunction(directive):
                await directive()
            else:
                args_to_run = [
                    "--help" if arg in ["-h", "--h"] else arg for arg in sys.argv[position:]
                ]

                # Build CLI context and parse args
                ctx = directive.make_context(directive.name, args_to_run, resilient_parsing=False)
                # Get parsed CLI params
                kwargs = ctx.params
                callback = directive.callback

                while hasattr(callback, "__wrapped__"):
                    callback = callback.__wrapped__

                if inspect.iscoroutinefunction(callback):
                    await callback(**kwargs)
                else:
                    callback(**kwargs)
        else:
            raise TypeError("Invalid directive type. Must be a BaseDirective or a callable.")

        await reset_global_context(token)
