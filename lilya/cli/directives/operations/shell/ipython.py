import asyncio
import os
import sys
import typing

from monkay.asgi import Lifespan

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

    Loads the initial configurations from the main Edgy settings
    and boots up the kernel.
    """
    try:
        from IPython import start_ipython  # pyright: ignore[reportMissingModuleSource]
        from IPython.core.async_helpers import (
            get_asyncio_loop,  # pyright: ignore[reportMissingModuleSource]
        )

        def run_ipython() -> None:
            ipython_arguments = get_ipython_arguments(options)
            loop: asyncio.BaseEventLoop = get_asyncio_loop()  # type: ignore
            ctx = Lifespan(app)
            loop.run_until_complete(ctx.__aenter__())
            try:
                # we need an initialized registry first to detect reflected models
                imported_objects: dict[str, typing.Any] = import_objects(app)
                start_ipython(argv=ipython_arguments, user_ns=imported_objects)  # type: ignore
            finally:
                loop.run_until_complete(ctx.__aexit__())

    except ImportError:
        printer.write_error(
            "You must have IPython installed to run this. Run `pip install ipython`."
        )
        sys.exit(1)

    return run_ipython
