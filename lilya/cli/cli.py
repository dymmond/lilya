from __future__ import annotations

import inspect
import os
import sys
import typing
from collections.abc import Callable
from functools import wraps
from typing import TypeVar

import click
from sayer import Sayer, error
from sayer.core.groups.sayer import SayerGroup
from sayer.params import Argument, Option

from lilya import __version__
from lilya.cli.constants import (
    EXCLUDED_DIRECTIVES,
    HELP_PARAMETER,
    IGNORE_DIRECTIVES,
)
from lilya.cli.directives.operations._constants import LILYA_SETTINGS_MODULE
from lilya.cli.directives.operations.createapp import create_app as create_app  # noqa
from lilya.cli.directives.operations.createdeployment import (
    create_deployment as create_deployment,  # noqa
)
from lilya.cli.directives.operations.createproject import create_project as create_project  # noqa
from lilya.cli.directives.operations.list import directives as directives  # noqa
from lilya.cli.directives.operations.run import run as run  # noqa
from lilya.cli.directives.operations.runserver import runserver as runserver  # noqa
from lilya.cli.directives.operations.shell import shell as shell  # noqa
from lilya.cli.directives.operations.show_urls import show_urls as show_urls  # noqa
from lilya.cli.env import DirectiveEnv
from lilya.exceptions import EnvError

T = TypeVar("T")


class DirectiveGroup(SayerGroup):
    """Custom directive group to handle with the context and directives commands"""

    def add_command(self, cmd: click.Command, name: str | None = None) -> None:
        if cmd.callback:
            cmd.callback = self.wrap_args(cmd.callback)
        return super().add_command(cmd, name)

    def wrap_args(self, func: Callable[..., T]) -> Callable[..., T]:
        original = inspect.unwrap(func)
        params = inspect.signature(original).parameters

        @wraps(func)
        def wrapped(ctx: click.Context, /, *args: typing.Any, **kwargs: typing.Any) -> T:
            scaffold = ctx.ensure_object(DirectiveEnv)
            if "env" in params:
                kwargs["env"] = scaffold
            return func(*args, **kwargs)

        # click.pass_context makes sure that 'ctx' is the first argument
        return click.pass_context(wrapped)

    def process_settings(self, ctx: click.Context) -> None:
        """
        Process the settings context" if any is passed.

        Exports any LILYA_SETTINGS_MODULE to the environment if --settings is passed and exists
        as one of the params of any subcommand.
        """
        args = [*ctx.protected_args, *ctx.args]
        cmd_name, cmd, args = self.resolve_command(ctx, args)
        sub_ctx = cmd.make_context(cmd_name, args, parent=ctx)

        settings = sub_ctx.params.get("settings", None)
        if settings:
            settings_module: str = os.environ.get(LILYA_SETTINGS_MODULE, settings)
            os.environ.setdefault(LILYA_SETTINGS_MODULE, settings_module)

    def invoke(self, ctx: click.Context) -> typing.Any:
        """
        Directives can be ignored depending of the functionality from what is being
        called.
        """
        path = ctx.params.get("app", None)

        # Process any settings
        self.process_settings(ctx)

        if HELP_PARAMETER not in sys.argv and not any(
            value in sys.argv for value in EXCLUDED_DIRECTIVES
        ):
            try:
                directive = DirectiveEnv()
                app_env = directive.load_from_env(path=path)
                ctx.obj = app_env
            except EnvError as e:
                if not any(value in sys.argv for value in IGNORE_DIRECTIVES):
                    error(str(e))
                    sys.exit(1)
        return super().invoke(ctx)


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
    name: typing.Annotated[str, Argument(help="The directive name.")],
    app: typing.Annotated[
        str,
        Option(
            required=False, help="Module path to the Lilya application. In a module:path format."
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
