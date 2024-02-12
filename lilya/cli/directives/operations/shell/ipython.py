import os
import sys
import typing

from lilya.cli.directives.operations.shell.utils import import_objects
from lilya.cli.terminal import Print
from lilya.conf import settings

printer = Print()


def get_ipython_arguments(options: typing.Any = None) -> typing.Any:
    """Loads the IPython arguments from the settings or defaults to
    main lilya settings.
    """
    ipython_args = "IPYTHON_ARGUMENTS"
    arguments = getattr(settings, "ipython_args", [])
    if not arguments:
        arguments = os.environ.get(ipython_args, "").split()
    return arguments


def get_ipython(app: typing.Any, options: typing.Any = None) -> typing.Any:
    """Gets the IPython shell.

    Loads the initial configurations from the main lilya settings
    and boots up the kernel.
    """
    try:
        from IPython import start_ipython

        def run_ipython() -> None:
            imported_objects = import_objects(app)
            ipython_arguments = get_ipython_arguments(options)
            start_ipython(argv=ipython_arguments, user_ns=imported_objects)  # type: ignore

    except (ModuleNotFoundError, ImportError):
        error = "You must have IPython installed to run this. Run `pip install lilya[ipython]`"
        printer.write_error(error)
        sys.exit(1)

    return run_ipython
