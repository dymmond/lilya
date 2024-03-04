from __future__ import annotations

import inspect
import os
import sys
from typing import TYPE_CHECKING, Any

import click
from rich.console import Console
from rich.table import Table

from lilya._internal._path import clean_path
from lilya.cli.constants import LILYA_DISCOVER_APP
from lilya.cli.env import DirectiveEnv
from lilya.cli.terminal import OutputColour, Print, Terminal
from lilya.controllers import Controller as View
from lilya.enums import HTTPMethod
from lilya.routing import Path

if TYPE_CHECKING:
    from lilya.apps import ChildLilya, Lilya
    from lilya.routing import BasePath, Router

printer = Print()
writer = Terminal()
console = Console()

DOCS_ELEMENTS = [
    "/swagger",
    "/redoc",
    "/openapi.json",
    "/openapi.yaml",
    "/openapi.yml",
    "/elements",
]


def get_http_verb(mapping: Any) -> str:
    if getattr(mapping, "get", None):
        return HTTPMethod.GET.value
    elif getattr(mapping, "post", None):
        return HTTPMethod.POST.value
    elif getattr(mapping, "put", None):
        return HTTPMethod.PUT.value
    elif getattr(mapping, "patch", None):
        return HTTPMethod.PATCH.value
    elif getattr(mapping, "delete", None):
        return HTTPMethod.DELETE.value
    elif getattr(mapping, "header", None):
        return HTTPMethod.HEAD.value
    return HTTPMethod.GET.value


@click.command(name="show_urls")
def show_urls(env: DirectiveEnv) -> None:
    """Shows the information regarding the urls of a given application

    How to run: `lilya show_urls`

    Example: `lilya show_urls`
    """
    if os.getenv(LILYA_DISCOVER_APP) is None and getattr(env, "app", None) is None:
        error = (
            "You cannot specify a custom directive without specifying the --app or setting "
            "LILYA_DEFAULT_APP environment variable."
        )
        printer.write_error(error)
        sys.exit(1)

    app = env.app
    table = Table(title="Application Paths")
    table = get_routes_table(app, table)
    printer.write(table)


def get_routes_table(app: Lilya | ChildLilya | None, table: Table) -> Table:
    """Prints the routing system"""
    table.add_column("Path", style=OutputColour.GREEN, vertical="middle")
    table.add_column("Path Parameters", style=OutputColour.BRIGHT_CYAN, vertical="middle")
    table.add_column("Handler", style=OutputColour.CYAN, vertical="middle")
    table.add_column("Type", style=OutputColour.YELLOW, vertical="middle")
    table.add_column("HTTP Methods", style=OutputColour.RED, vertical="middle")

    def parse_routes(
        app: Lilya | ChildLilya | Router | BasePath | None,
        table: Table,
        route: Any | None = None,
        prefix: str | None = "",
    ) -> None:
        if getattr(app, "routes", None) is None:
            return

        for route in app.routes:  # type: ignore
            if isinstance(route, Path):
                path = clean_path(prefix + route.path)

                if any(element in path for element in DOCS_ELEMENTS):
                    continue

                if not isinstance(route.handler, View):
                    if inspect.iscoroutinefunction(route.handler):
                        fn_type = "async"
                    else:
                        fn_type = "sync"

                http_methods = ", ".join(sorted(route.methods))
                parameters = ", ".join(sorted(route.stringify_parameters))
                table.add_row(path, parameters, route.name, fn_type, http_methods)
                continue

            route_app = getattr(route, "app", None)
            if not route_app:
                continue

            path = clean_path(prefix + route.path)  # type: ignore
            if any(element in path for element in DOCS_ELEMENTS):
                continue

            parse_routes(route, table, prefix=f"{path}")

    parse_routes(app, table)
    return table
