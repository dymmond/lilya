from __future__ import annotations

from sayer import command, success

from lilya.cli.decorator import directive
from lilya.context import g
from tests.cli.global_context.objects import Test  # noqa: F401


@directive
@command
async def run_test():
    """
    Test directive for creating a user
    """
    g.name = "Lilya from global"

    name = Test().get_name()
    success(f"Context successfully set to {name}.")
