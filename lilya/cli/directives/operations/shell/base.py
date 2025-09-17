from __future__ import annotations

import asyncio
import select
import sys
from contextvars import copy_context
from typing import Annotated, Any

import click
from monkay import Lifespan
from sayer import Option, command

from lilya.cli.directives.operations.shell.enums import ShellOption
from lilya.cli.env import DirectiveEnv


@command
async def shell(
    env: DirectiveEnv,
    kernel: Annotated[
        str,
        Option(
            default="ipython",
            help="Which shell should start.",
            type=click.Choice(["ipython", "ptpython"]),
            show_default=True,
        ),
    ],
) -> None:
    """
    Starts an interactive ipython shell with all the models
    and important python libraries.
    """
    if (
        sys.platform != "win32"
        and not sys.stdin.isatty()
        and select.select([sys.stdin], [], [], 0)[0]
    ):
        exec(sys.stdin.read(), globals())
        return

    await run_shell(env.app, kernel)
    return None


async def run_shell(app: Any, kernel: str) -> None:
    """Executes the database shell connection"""

    async with Lifespan(app):
        if kernel == ShellOption.IPYTHON:
            from lilya.cli.directives.operations.shell.ipython import get_ipython

            ipython_shell = get_ipython(app=app)
            await asyncio.to_thread(copy_context().run, ipython_shell)
        else:
            from lilya.cli.directives.operations.shell.ptpython import get_ptpython

            ptpython = get_ptpython(app=app)
            await asyncio.to_thread(copy_context().run, ptpython)
