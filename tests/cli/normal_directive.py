from typing import Any

from lilya.cli.base import BaseDirective
from lilya.cli.terminal import Print

printer = Print()


class Directive(BaseDirective):
    help: str = "Creates a superuser"

    async def handle(self, *args: Any, **options: Any) -> Any:
        """
        Generates a superuser
        """
        printer.write_success("Working")
