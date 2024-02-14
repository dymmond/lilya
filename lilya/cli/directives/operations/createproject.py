import click

from lilya.cli.directives.operations._constants import SECRET_KEY_INSECURE_PREFIX
from lilya.cli.exceptions import DirectiveError
from lilya.cli.templates import TemplateDirective
from lilya.cli.terminal import Print
from lilya.crypto import get_random_secret_key

printer = Print()


@click.option(
    "--with-deployment",
    is_flag=True,
    show_default=True,
    default=False,
    help="Creates a project with base deployment files.",
)
@click.option(
    "--deployment-folder-name",
    default="deployment",
    show_default=True,
    type=str,
    help="The name of the folder for the deployment files.",
)
@click.option(
    "--with-structure",
    is_flag=True,
    show_default=True,
    default=False,
    help="Creates a project with a given structure of folders and files.",
)
@click.option("-v", "--verbosity", default=1, type=int, help="Displays the files generated.")
@click.argument("name", type=str)
@click.command(name="createproject")
def create_project(
    name: str,
    verbosity: int,
    with_deployment: bool,
    deployment_folder_name: str,
    with_structure: bool,
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
        printer.write_success(f"Project {name} generated successfully!")
    except DirectiveError as e:
        printer.write_error(str(e))
