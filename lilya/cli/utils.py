import functools
import os
from collections.abc import Callable, Container
from inspect import isroutine
from pathlib import Path
from types import ModuleType
from typing import cast

from sayer.core.commands.base import BaseSayerCommand
from sayer.utils.directives import (
    DirectiveTuple,
    directive_function_or_help,
    find_directives_from_module,
    find_directives_from_path,
    transpose_directives,
)

from lilya.cli.base import BaseDirective
from lilya.cli.directives.operations._constants import IGNORED_INTERNAL_DIRECTIVES
from lilya.cli.exceptions import DirectiveError


def extractor_directive(module: ModuleType, relative: Path, *, internal: bool):
    found: Callable | None = None
    is_internal_operations = module.__name__.startswith("lilya.cli.directives.operations")
    if is_internal_operations and internal:
        # ignore these modules
        if module.__name__.rsplit(".")[-1] in IGNORED_INTERNAL_DIRECTIVES:
            return None
        for attr in dir(module):
            obj = getattr(module, attr)
            if isinstance(obj, BaseSayerCommand):
                new_found = obj
                if found is not None:
                    raise DirectiveError(
                        f"Detected multiple directives in the same file: `{module.__file__}`."
                    )
                found = new_found
    elif not is_internal_operations and not internal:
        for attr in dir(module):
            obj = getattr(module, attr)
            if getattr(obj, "__is_custom_directive__", False):
                if isroutine(obj):
                    new_found = obj
                elif obj.__name__ == "Directive" and issubclass(obj, BaseDirective):
                    new_found = obj()
                else:
                    continue
                if found is not None:
                    raise DirectiveError(
                        f"Detected multiple directives in the same file: `{module.__file__}`."
                    )
                found = new_found
    return found


def extractor_help(tup: DirectiveTuple) -> str | None:
    is_internal_operations = tup[0].__name__.startswith("lilya.cli.directives.operations")
    if not getattr(tup.directive, "__display_in_cli__", False) and not is_internal_operations:
        return None
    return tup.directive.__doc__ or ""


def fetch_directives_via_path(
    path: os.PathLike,
    use_files: bool = True,
    cleanup_imports: bool = True,
    ignore: Container = frozenset(),
) -> dict:
    return find_directives_from_path(
        path,
        patterns=[
            "**/directives/operations/[!_]*.py",
            "**/directives/operations/*/__init__.py",
            "**/directives/operations/[!_]*.pyc",
            "**/directives/operations/*/__init__.pyc",
        ],
        extractor_directive=functools.partial(extractor_directive, internal=False),
        ignore=ignore,
        use_files=use_files,
        cleanup_imports=cleanup_imports,
    )


def fetch_directives_via_module(module: str | ModuleType, ignore: Container = frozenset()) -> dict:
    mod_name = module.__name__ if isinstance(module, ModuleType) else module
    internal: bool = mod_name == "lilya" or mod_name.startswith("lilya.")
    return find_directives_from_module(
        module,
        patterns=[
            "**/directives/operations/[!_]*.py",
            "**/directives/operations/*/__init__.py",
            "**/directives/operations/[!_]*.pyc",
            "**/directives/operations/*/__init__.pyc",
        ],
        extractor_directive=functools.partial(extractor_directive, internal=internal),
        ignore=ignore,
    )


def extractor_app_name(directive_tuple: DirectiveTuple) -> str:
    if app_name := getattr(directive_tuple.module, "app_name", None):
        return app_name
    if directive_tuple[0].__name__.startswith("lilya.cli.directives.operations"):
        return "lilya"
    # is an __init__
    if Path(directive_tuple.module.__spec__.origin).stem == "__init__":
        return (
            directive_tuple.relative.parts[0]
            if len(directive_tuple.relative.parts) > 2
            else directive_tuple.root.name
        )
    else:
        return (
            directive_tuple.relative.parts[0]
            if len(directive_tuple.relative.parts) > 1
            else directive_tuple.root.name
        )


def evaluate_directive(
    directives: dict, directive: str | None, help_text_preamble: str = "Available directives:"
) -> None | Callable:
    transposed = transpose_directives(
        directives, extractor_help=extractor_help, extractor_app_name=extractor_app_name
    )
    obj_or_func = directive_function_or_help(
        transposed, directive=directive, help_text_preamble=help_text_preamble
    )
    return (
        cast("Callable", obj_or_func.run)
        if hasattr(obj_or_func, "run")
        else cast("Callable | None", obj_or_func)
    )
