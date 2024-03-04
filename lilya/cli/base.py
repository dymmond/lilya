from __future__ import annotations

import argparse
import os
import sys
from abc import ABC, abstractmethod
from typing import Any

import lilya
from lilya.cli.exceptions import DirectiveError
from lilya.cli.parsers import DirectiveParser
from lilya.cli.terminal.print import Print
from lilya.compat import is_async_callable

printer = Print()


class BaseDirective(ABC):
    """The base class from which all directrives derive"""

    help: str = ""

    def get_version(self) -> str:
        """
        Returns the current version of Lilya.
        """
        return lilya.__version__

    def add_arguments(self, parser: type[argparse.ArgumentParser]) -> Any:
        """
        Entrypoint for directives and custom arguments
        """
        raise NotImplementedError()

    def create_parser(self, name: str, subdirective: str, **kwargs: Any) -> DirectiveParser:
        parser = DirectiveParser(
            prog=f"{os.path.basename(name)} {subdirective}",
            description=self.help,
            **kwargs,
        )
        self.add_arguments(parser)  # type: ignore
        return parser

    async def execute_from_command(self, argv: Any, program_name: str, position: int = 5) -> None:
        """
        Executes dynamically the directive from the command line and passing the parameters
        """
        parser = self.create_parser(program_name, argv[position])

        options = parser.parse_args(argv[position + 1 :])
        cmd_options = vars(options)

        # Move positional args out of options to mimic legacy optparse
        args = cmd_options.pop("args", ())
        try:
            await self.run(*args, **cmd_options)
        except DirectiveError as e:
            printer.write_error(f"{e.__class__.__name__}: {e}")
            sys.exit(e.returncode)

    async def run(self, *args: Any, **options: Any) -> Any:
        """
        Executes the handle()
        """
        if not is_async_callable(self.handle):
            output = self.handle(*args, **options)
        else:
            output = await self.handle(*args, **options)
        if output:
            printer.write_info(output)
        return output

    @abstractmethod
    def handle(self, *args: Any, **options: Any) -> Any:
        """The logic of the directive. Subclasses must implement this method"""
        raise NotImplementedError("subclasses of BaseDirective must provide a handle() method.")
