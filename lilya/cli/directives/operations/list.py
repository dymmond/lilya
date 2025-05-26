from __future__ import annotations

from collections import defaultdict

from sayer import command

from lilya.cli.directives.operations._constants import PATH
from lilya.cli.env import DirectiveEnv
from lilya.cli.terminal import OutputColour, Terminal
from lilya.cli.utils import get_application_directives, get_directives


@command
def directives(env: DirectiveEnv) -> None:
    """
    Lists the available directives

    Goes through the Lilya core native directives and given --app
    and lists all the available directives in the system.
    """
    output = Terminal()
    usage = [
        "",
        "Type '<directive> <subcommand> --help' for help on a specific subcommand.",
        "",
        "Available directives:",
    ]
    directives = get_directives(PATH)

    # Handles the application directives
    if getattr(env, "app", None) is not None:
        app_directives = get_application_directives(env.command_path)
        if app_directives:
            directives.extend(app_directives)

    directives_dict = defaultdict(lambda: [])
    for directive in directives:
        for name, app in directive.items():  # type: ignore
            if name == "location":
                continue

            if app == "lilya.core":
                app = "lilya"
            else:
                app = app.rpartition(".")[-1]
            directives_dict[app].append(name)

    for app in sorted(directives_dict):
        usage.append("")
        usage.append(output.message(f"\\[{app}]", colour=OutputColour.SUCCESS))

        for name in sorted(directives_dict[app]):
            usage.append(output.message(f"    {name}", colour=OutputColour.INFO))
    output.write("\n".join(usage))
