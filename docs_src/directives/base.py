import argparse
from typing import Any, Type

from lilya.cli.base import BaseDirective


class Directive(BaseDirective):
    def add_arguments(self, parser: Type["argparse.ArgumentParser"]) -> Any:
        # Add argments
        ...
