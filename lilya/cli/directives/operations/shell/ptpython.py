import os
import sys
import typing

from lilya.cli.directives.operations.shell.utils import import_objects
from lilya.cli.terminal import Print
from lilya.conf import settings

printer = Print()


def vi_mode() -> typing.Any:
    editor = os.environ.get("EDITOR")
    if not editor:
        return False
    editor = os.path.basename(editor)
    return editor.startswith("vi") or editor.endswith("vim")


def get_ptpython(app: typing.Any, options: typing.Any = None) -> typing.Any:
    """Gets the PTPython shell.

    Loads the initial configurations from the main lilya settings
    and boots up the kernel.
    """
    try:
        from ptpython.repl import embed, run_config

        def run_ptpython() -> None:
            imported_objects = import_objects(app)
            history_filename = os.path.expanduser("~/.ptpython_history")

            config_file = os.path.expanduser(settings.ptpython_config_file)
            if not os.path.exists(config_file):
                embed(
                    globals=imported_objects,
                    history_filename=history_filename,
                    vi_mode=vi_mode(),
                )
            else:
                embed(
                    globals=imported_objects,
                    history_filename=history_filename,
                    vi_mode=vi_mode(),
                    configure=run_config,
                )

    except (ModuleNotFoundError, ImportError):
        error = "You must have PTPython installed to run this. Run `pip install ptpython`"
        printer.write_error(error)
        sys.exit(1)

    return run_ptpython
