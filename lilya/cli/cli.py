from __future__ import annotations

import inspect
import os
import sys
import typing
from functools import wraps
from typing import Callable, TypeVar

import click

from lilya.cli.constants import (
    APP_PARAMETER,
    EXCLUDED_DIRECTIVES,
    HELP_PARAMETER,
    IGNORE_DIRECTIVES,
)
from lilya.cli.directives.operations import (
    create_app,
    create_deployment,
    create_project,
    list,
    run,
    runserver,
    shell,
    show_urls,
)
from lilya.cli.directives.operations._constants import LILYA_SETTINGS_MODULE
from lilya.cli.env import DirectiveEnv
from lilya.cli.terminal.print import Print

T = TypeVar("T")

printer = Print()


class DirectiveGroup(click.Group):
    """Custom directive group to handle with the context and directives commands"""

    def add_command(self, cmd: click.Command, name: str | None = None) -> None:
        if cmd.callback:
            cmd.callback = self.wrap_args(cmd.callback)
        return super().add_command(cmd, name)

    def wrap_args(self, func: Callable[..., T]) -> Callable[..., T]:
        params = inspect.signature(func).parameters

        @wraps(func)
        def wrapped(ctx: click.Context, /, *args: typing.Any, **kwargs: typing.Any) -> T:
            scaffold = ctx.ensure_object(DirectiveEnv)
            if "env" in params:
                kwargs["env"] = scaffold
            return func(*args, **kwargs)

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
        path = ctx.params.get("path", None)

        # Process any settings
        self.process_settings(ctx)

        if HELP_PARAMETER not in sys.argv and not any(
            value in sys.argv for value in EXCLUDED_DIRECTIVES
        ):
            try:
                directive = DirectiveEnv()
                app_env = directive.load_from_env(path=path)
                ctx.obj = app_env
            except OSError as e:
                if not any(value in sys.argv for value in IGNORE_DIRECTIVES):
                    printer.write_error(str(e))
                    sys.exit(1)
        return super().invoke(ctx)


@click.group(cls=DirectiveGroup)
@click.option(
    APP_PARAMETER,
    "path",
    help="Module path to the application to generate the migrations. In a module:path formatyping.",
)
@click.option("--n", "name", help="The directive name to run.")
@click.pass_context
def lilya_cli(
    ctx: click.Context,
    path: str | None,
    name: str,
) -> None:
    """
    Lilya command line tool allowing to run Lilya native directives or
    project unique and specific directives by passing the `-n` parameter.

    How to run Lilya native: `lilya createproject <NAME>`. Or any other Lilya native command.

        Example: `lilya createproject myapp`


    How to run custom directives: `lilya --app <APP-LOCATION> run -n <DIRECTIVE NAME> <ARGS>`.

        Example: `lilya --app myapp:app run -n createsuperuser`

    """
    ...


lilya_cli.add_command(list)
lilya_cli.add_command(show_urls)
lilya_cli.add_command(run)
lilya_cli.add_command(create_project)
lilya_cli.add_command(create_app)
lilya_cli.add_command(create_deployment)
lilya_cli.add_command(runserver)
lilya_cli.add_command(shell)
