from __future__ import annotations

from sayer import command

from lilya import cli as cli_module
from lilya.cli.env import DirectiveEnv
from lilya.cli.utils import (
    evaluate_directive,
    fetch_directives_via_module,
    fetch_directives_via_path,
)


@command
def directives(env: DirectiveEnv) -> None:
    """
    Lists the available directives

    Goes through the Lilya core native directives and given --app
    and lists all the available directives in the system.
    """
    usage = [
        "",
        "Type '<directive> <subcommand> --help' for help on a specific subcommand.",
        "",
        "Available directives:",
    ]
    directives = fetch_directives_via_module("lilya")
    directives.update(
        fetch_directives_via_path(
            env.command_path or "", ignore={cli_module.__spec__.origin, *directives}
        )
    )
    evaluate_directive(directives, None, help_text_preamble="\n".join(usage))
