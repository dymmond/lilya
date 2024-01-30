from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Pattern, Tuple, TypeVar

from lilya._internal._path_transformers import CONVERTOR_TYPES, Transformer
from lilya.types import Scope

T = TypeVar("T")

PATH_REGEX = re.compile("{([a-zA-Z_][a-zA-Z0-9_]*)(:[a-zA-Z_][a-zA-Z0-9_]*)?}")


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


def join_paths(paths: Iterable[str]) -> str:
    return clean_path("/".join(paths))


def get_route_path(scope: Scope) -> str:
    root_path = scope.get("root_path", "")
    route_path = re.sub(r"^" + root_path, "", scope["path"])
    return route_path


def replace_params(
    path: str,
    param_convertors: Dict[str, Transformer[Any]],
    path_params: Dict[str, str],
) -> Tuple[str, Dict[str, str]]:
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

    return updated_path, remaining_params


def compile_path(path: str) -> Tuple[Pattern[str], str, Dict[str, Transformer[Any]]]:
    """
    Compile a path or host string into a three-tuple of (regex, format, {param_name:convertor}).

    Args:
        path (str): The path or host string.

    Returns:
        Tuple[Pattern[str], str, Dict[str, 'Transformer[Any]']]: The compiled regex pattern, format string,
        and a dictionary of parameter names and converters.
    """
    is_host = not path.startswith("/")
    path_regex, path_format, param_convertors, path_start = generate_regex_and_format(path)

    check_for_duplicate_params(param_convertors)

    if is_host:
        hostname = extract_hostname(path)
        path_regex += re.escape(hostname) + "$"

    return re.compile(path_regex), path_format, param_convertors, path_start


def generate_regex_and_format(path: str) -> Tuple[str, str, Dict[str, Transformer[Any]]]:
    path_regex, path_format, param_convertors, idx = "^", "", {}, 0

    for match in re.finditer(r"{([^:]+)(?::([^}]+))?}", path):
        param_name, convertor_type = match.groups("str")
        convertor_type = convertor_type.lstrip(":")

        convertor = get_convertor(convertor_type)
        path_regex, path_format, param_convertors, idx, path_start = update_paths_and_convertors(
            path, path_regex, path_format, param_convertors, idx, param_name, convertor, match
        )

    path_regex += re.escape(path[idx:]) + "$"
    path_format += path[idx:]

    return path_regex, path_format, param_convertors, path_start


def get_convertor(convertor_type: str) -> Transformer[Any]:
    assert convertor_type in CONVERTOR_TYPES, f"Unknown path convertor '{convertor_type}'"
    return CONVERTOR_TYPES[convertor_type]


def update_paths_and_convertors(
    path: str,
    path_regex: str,
    path_format: str,
    param_convertors: Dict[str, Transformer[Any]],
    idx: int,
    param_name: str,
    convertor: Transformer[Any],
    match: re.Match,
) -> Tuple[str, str, Dict[str, Transformer[Any]], int]:
    path_start = path[idx : match.start()]

    path_regex += re.escape(path_start)
    path_regex += f"(?P<{param_name}>{convertor.regex})"

    path_format += path_start
    path_format += f"{{{param_name}}}"

    if param_name in param_convertors:
        raise ValueError(f"Duplicated param name {param_name} at path {match.string}")

    param_convertors[param_name] = convertor
    idx = match.end()

    return path_regex, path_format, param_convertors, idx, path_start


def check_for_duplicate_params(param_convertors: Dict[str, Transformer[Any]]) -> None:
    duplicated_params = {
        name for name in param_convertors if list(param_convertors).count(name) > 1
    }
    if duplicated_params:
        names = ", ".join(sorted(duplicated_params))
        ending = "s" if len(duplicated_params) > 1 else ""
        raise ValueError(f"Duplicated param name{ending} {names} in the path")


def extract_hostname(path: str) -> str:
    return path[len(path) :].split(":")[0]
