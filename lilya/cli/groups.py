from __future__ import annotations

import inspect
import os
import sys
import typing
from collections.abc import Callable
from functools import wraps
from typing import TypeVar

import click
from sayer import error
from sayer.core.commands.config import CustomCommandConfig
from sayer.core.groups.sayer import SayerGroup

from lilya.cli.constants import (
    EXCLUDED_DIRECTIVES,
    HELP_PARAMETER,
    IGNORE_DIRECTIVES,
)
from lilya.cli.directives.operations._constants import LILYA_SETTINGS_MODULE
from lilya.cli.directives.operations.createapp import create_app as create_app  # noqa
from lilya.cli.env import DirectiveEnv
from lilya.exceptions import EnvError

T = TypeVar("T")


class DirectiveGroup(SayerGroup):
    """Custom directive group to handle with the context and directives commands"""

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self._custom_command_config: CustomCommandConfig = CustomCommandConfig(
            title="Custom directives"
        )

    def add_command(
        self, cmd: click.Command, name: str | None = None, is_custom: bool = False
    ) -> None:
        if cmd.callback:
            cmd.callback = self.wrap_args(cmd.callback)
        return super().add_command(cmd, name, is_custom=is_custom)

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
        app = ctx.params.get("app", None)
        path = ctx.params.get("path", None)

        # Process any settings
        self.process_settings(ctx)

        if HELP_PARAMETER not in sys.argv and not any(
            value in sys.argv for value in EXCLUDED_DIRECTIVES
        ):
            try:
                directive = DirectiveEnv()
                app_env = directive.load_from_env(path=app, cwd=path)
                ctx.obj = app_env
            except EnvError as e:
                if not any(value in sys.argv for value in IGNORE_DIRECTIVES):
                    error(str(e))
                    sys.exit(1)
        return super().invoke(ctx)
