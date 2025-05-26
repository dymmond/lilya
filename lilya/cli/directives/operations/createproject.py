from __future__ import annotations

from typing import Annotated

from sayer import Argument, Option, command, error, success

from lilya.cli.directives.operations._constants import SECRET_KEY_INSECURE_PREFIX
from lilya.cli.exceptions import DirectiveError
from lilya.cli.templates import TemplateDirective
from lilya.cli.terminal import Print
from lilya.crypto import get_random_secret_key

printer = Print()


@command(name="createproject")  # type: ignore
def create_project(
    name: Annotated[str, Argument(help="The name of the project to create.")],
    verbosity: Annotated[int, Option(1, "-v", help="Verbosity level for the output.")],
    with_deployment: Annotated[
        bool,
        Option(False, help="Creates a project with base deployment files.", show_default=True),
    ],
    deployment_folder_name: Annotated[
        str,
        Option(
            "deployment",
            help="The name of the folder for the deployment files.",
            show_default=True,
        ),
    ],
    with_structure: Annotated[
        bool,
        Option(
            False,
            help="Creates a project with a given structure of folders and files.",
            show_default=True,
        ),
    ],
) -> None:
    """
    Creates the scaffold of a project.

    How to run: `lilya createproject <NAME>`

    Example: `lilya createproject myproject`
    """
    options = {
        "secret_key": SECRET_KEY_INSECURE_PREFIX + get_random_secret_key(),
        "verbosity": verbosity,
        "with_deployment": with_deployment,
        "deployment_folder_name": deployment_folder_name,
        "is_simple": with_structure,
    }
    directive = TemplateDirective()

    try:
        directive.handle("project", name=name, **options)
        success(f"Project {name} generated successfully!")
    except DirectiveError as e:
        error(str(e))
