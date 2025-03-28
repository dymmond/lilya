from __future__ import annotations

import os
import sys
from typing import Any, cast

import click

from lilya.cli.env import DirectiveEnv
from lilya.cli.exceptions import DirectiveError
from lilya.cli.terminal import OutputColour, Print, Terminal

printer = Print()
terminal = Terminal()


@click.option(
    "-p",
    "--port",
    type=int,
    default=8000,
    help="Port to run the development server.",
    show_default=True,
)
@click.option(
    "-r",
    "--reload",
    type=bool,
    default=True,
    help="Reload server on file changes.",
    is_flag=True,
    show_default=True,
)
@click.option(
    "--host",
    type=str,
    default="localhost",
    help="Server host. Tipically localhost.",
    show_default=True,
)
@click.option(
    "--debug",
    type=bool,
    default=True,
    help="Start the application in debug mode.",
    show_default=True,
    is_flag=True,
)
@click.option(
    "--log-level",
    type=str,
    default="debug",
    help="What log level should uvicorn run.",
    show_default=True,
)
@click.option(
    "--lifespan",
    type=str,
    default="on",
    help="Enable lifespan events.",
    show_default=True,
)
@click.option(
    "--settings", type=str, help="Any custom settings to be initialised.", required=False
)
@click.command(name="runserver")
def runserver(
    env: DirectiveEnv,
    port: int,
    reload: bool,
    host: str,
    debug: bool,
    log_level: str,
    lifespan: str,
    settings: str | None = None,
) -> None:
    """Starts the Lilya development server.

    The --app can be passed in the form of <module>.<submodule>:<app> or be set
    as environment variable LILYA_DEFAULT_APP.

    Alternatively, if none is passed, Lilya will perform the application discovery.

    It is strongly advised not to run this command in any pther environment but developmentyping.
    This was designed to facilitate the development environment and should not be used in pr

    How to run: `lilya runserver`
    """
    if getattr(env, "app", None) is None:
        error = (
            "You cannot specify a custom directive without specifying the --app or setting "
            "LILYA_DEFAULT_APP environment variable."
        )
        printer.write_error(error)
        sys.exit(1)

    if settings is not None:
        os.environ.setdefault("LILYA_SETTINGS_MODULE", settings)

    try:
        import uvicorn
    except ImportError:
        raise DirectiveError(detail="Uvicorn needs to be installed to run Lilya.") from None

    server_environment: str = ""
    if os.environ.get("LILYA_SETTINGS_MODULE"):
        from lilya.conf import settings as lilya_settings

        server_environment = f"{lilya_settings.environment} "

    app = env.app
    message = terminal.write_info(
        f"Starting {server_environment}server @ {host} server @ {host}",
        colour=OutputColour.BRIGHT_CYAN,
    )
    terminal.rule(message, align="center")

    if os.environ.get("LILYA_SETTINGS_MODULE"):
        custom_message = f"'{os.environ.get('LILYA_SETTINGS_MODULE')}'"
        terminal.rule(custom_message, align="center")

    if debug:
        app.debug = debug

    uvicorn.run(
        app=env.path,
        port=port,
        host=host,
        reload=reload,
        lifespan=cast(Any, lifespan),
        log_level=log_level,
    )
