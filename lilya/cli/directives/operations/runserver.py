from __future__ import annotations

import os
import sys
from typing import Annotated, Any, cast

from sayer import Option, command, error

from lilya.cli.env import DirectiveEnv
from lilya.cli.exceptions import DirectiveError
from lilya.cli.terminal import OutputColour, Terminal

terminal = Terminal()


@command
def runserver(
    env: DirectiveEnv,
    port: Annotated[
        int, Option(8000, "-p", help="Port to run the development server.", show_default=True)
    ],
    reload: Annotated[
        bool, Option(True, "-r", help="Reload server on file changes.", show_default=True)
    ],
    host: Annotated[
        str, Option(default="localhost", help="Host to run the server on.", show_default=True)
    ],
    debug: Annotated[
        bool, Option(default=True, help="Run the server in debug mode.", show_default=True)
    ],
    log_level: Annotated[
        str, Option(default="debug", help="Log level for the server.", show_default=True)
    ],
    lifespan: Annotated[
        str, Option(default="on", help="Enable lifespan events.", show_default=True)
    ],
    settings: Annotated[
        str | None,
        Option(help="Any custom settings to be initialised.", required=False, show_default=False),
    ],
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
        error(
            "You cannot specify a custom directive without specifying the --app or setting "
            "LILYA_DEFAULT_APP environment variable."
        )
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
