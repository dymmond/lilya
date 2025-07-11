from __future__ import annotations

import re
from collections import namedtuple
from collections.abc import Iterable
from functools import lru_cache
from re import Pattern
from typing import Any, TypeVar, cast

from lilya._internal._path_transformers import (
    TRANSFORMER_PYTHON_TYPES,
    TRANSFORMER_TYPES,
    Transformer,
)
from lilya.types import Scope

T = TypeVar("T")

PathParameter = namedtuple("PathParameter", ["name", "type"])


def clean_path(path: str) -> str:
    """
    Make sure a given path by ensuring it starts with a slash and does not
    end with a slash.
    """
    path = path.rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    path = re.sub("//+", "/", path)
    return path


def remove_start_slashes(path: str) -> str:
    """
    Removes all the beginning starting with slashes
    """
    path = path.lstrip("/")
    return path


def join_paths(paths: Iterable[str]) -> str:
    return clean_path("/".join(paths))


def get_route_path(scope: Scope) -> str:
    root_path = scope.get("root_path", "")
    return cast(
        str,
        (
            scope["path"][len(root_path) :]
            if root_path and scope["path"].startswith(root_path)
            else scope["path"]
        ),
    )


def replace_params(
    path: str,
    param_convertors: dict[str, Transformer[Any]],
    path_params: dict[str, str],
    is_host: bool = False,
) -> tuple[str, dict[str, str]]:
    """
    Replaces placeholders in the given path with normalized values from path parameters.

    Args:
        path (str): The path string with placeholders.
        param_convertors (Dict[str, Transformer[Any]]): Dictionary of parameter names and transformers.
        path_params (Dict[str, str]): Dictionary of path parameters.

    Returns:
        Tuple[str, Dict[str, str]]: The updated path and any remaining path parameters.
    """
    updated_path = path
    remaining_params = {}
    for key, value in list(path_params.items()):
        placeholder = "{" + key + "}"

        if placeholder in updated_path:
            transformer = param_convertors[key]
            normalized_value = transformer.normalise(value)
            updated_path = updated_path.replace(placeholder, normalized_value)
            path_params.pop(key)
        else:
            remaining_params[key] = value

    if not is_host:
        return clean_path(updated_path), remaining_params
    return updated_path, remaining_params


@lru_cache(maxsize=1024)
def compile_path(path: str) -> tuple[Pattern[str], str, dict[str, Transformer[Any]], str]:
    """
    Compile a path or host string into a three-tuple of (regex, format, {param_name:convertor}).

    Args:
        path (str): The path or host string.

    Returns:
        Tuple[Pattern[str], str, Dict[str, 'Transformer[Any]']]: The compiled regex pattern, format string,
        and a dictionary of parameter names and converters.
    """
    is_host = not path.startswith("/")
    path_regex, path_format, param_convertors, path_start = generate_regex_and_format(
        path, is_host
    )

    return re.compile(path_regex), path_format, param_convertors, path_start


def generate_regex_and_format(
    path: str, is_host: bool
) -> tuple[str, str, dict[str, Transformer[Any]], str]:
    path_regex, path_format, param_convertors, index = "^", "", {}, 0  # type: ignore
    duplicate_params: set[str] = set()

    for match in re.finditer(r"[\{\<]([a-zA-Z_]\w*)(:[a-zA-Z_]\w*)?[\}\>]", path):
        param_name, convertor_type = match.groups("str")
        convertor_type = convertor_type.lstrip(":")

        convertor = get_transformer(convertor_type)
        (
            path_regex,
            path_format,
            param_convertors,
            index,
            path_start,
            duplicate_param,
        ) = update_paths_and_convertors(
            path,
            path_regex,
            path_format,
            param_convertors,
            index,
            param_name,
            convertor,
            match,
        )
        if duplicate_param:
            duplicate_params.add(duplicate_param)
    else:
        path_start = path

    if is_host:
        hostname = extract_hostname(path, index)
        path_regex += re.escape(hostname) + "$"
    else:
        path_regex += re.escape(path[index:]) + "$"

    raise_for_duplicate_params(path, duplicate_params)
    path_format += path[index:]
    return path_regex, path_format, param_convertors, path_start


def get_transformer(transformer_type: str) -> Transformer[Any]:
    assert transformer_type in TRANSFORMER_TYPES, f"Unknown path transformer '{transformer_type}'"
    return TRANSFORMER_TYPES[transformer_type]


def update_paths_and_convertors(
    path: str,
    path_regex: str,
    path_format: str,
    param_convertors: dict[str, Transformer[Any]],
    index: int,
    param_name: str,
    convertor: Transformer[Any],
    match: re.Match,
) -> tuple[str, str, dict[str, Transformer[Any]], int, str, str]:
    path_start = path[index : match.start()]

    path_regex += re.escape(path_start)
    path_regex += f"(?P<{param_name}>{convertor.regex})"

    path_format += path_start
    path_format += f"{{{param_name}}}"
    duplicate_param: str = None

    if param_name in param_convertors:
        duplicate_param = param_name

    param_convertors[param_name] = convertor
    index = match.end()

    return path_regex, path_format, param_convertors, index, path_start, duplicate_param


def raise_for_duplicate_params(path: str, duplicate_params: set[str] | None = None) -> None:
    """
    Builds and generates the error message for duplicate parameters
    in the path.
    """
    if not duplicate_params:
        return

    names = ", ".join(sorted(duplicate_params))
    ending = "s" if len(duplicate_params) > 1 else ""
    raise ValueError(f"Duplicated param name{ending} {names} in the path {path}")


def extract_hostname(path: str, index: int) -> str:
    return path[index:].split(":")[0]


def parse_path(path: str) -> list[str | Any]:
    """
    Using the TRANSFORMERS and the application registered convertors,
    transforms the path into definition.
    """
    _, path, variables, _ = compile_path(path)

    parsed_components: list[str | Any] = []

    for name, transformer in variables.items():
        _type = TRANSFORMER_PYTHON_TYPES[transformer.__class__.__name__]
        parsed_components.append(PathParameter(name=name, type=_type))
    return parsed_components
