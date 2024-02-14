import click

from lilya.cli.exceptions import DirectiveError
from lilya.cli.templates import TemplateDirective
from lilya.cli.terminal import Print

printer = Print()


@click.option("-v", "--verbosity", default=1, type=int, help="Displays the files generated")
@click.option(
    "--deployment-folder-name",
    default="deployment",
    show_default=True,
    type=str,
    help="The name of the folder for the deployment files.",
)
@click.argument("name", type=str)
@click.command(name="createdeployment")
def create_deployment(name: str, verbosity: int, deployment_folder_name: str) -> None:
    """
    Generates the scaffold for the deployment of a Lilya application.

    The scaffold contains the configurations for docker, nginx, supervisor and gunicorn.

    The configurations should be adapted accordingly.
    The parameter <NAME> corresponds to the name of the
    project where the deployment should be placed.

    How to run: `lilya createdeployment <NAME>`

    Example: `lilya createdeployment myproject`
    """
    options = {
        "verbosity": verbosity,
        "deployment_folder_name": deployment_folder_name,
        "is_simple": False,
    }
    directive = TemplateDirective()

    try:
        directive.handle("deployment", name=name, **options)
        printer.write_success(f"Deployment for {name} generated successfully!")
    except DirectiveError as e:
        printer.write_error(str(e))
