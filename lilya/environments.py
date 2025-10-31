from __future__ import annotations

import io
import os
import re
import warnings
from collections.abc import Callable, Generator
from pathlib import Path
from typing import Any, TypeVar

from multidict import MultiDict

from lilya.exceptions import EnvError

try:
    from yaml import CSafeLoader as SafeLoader, YAMLError
except ImportError:
    try:
        from yaml import SafeLoader, YAMLError
    except ImportError:
        SafeLoader = None
        YAMLError = None

T = TypeVar("T")
Cast = Callable[[Any], T]

# Pre-compiled regex for parsing 'key=value' pairs from .env files.
RE_ENV = re.compile(r"^(?!\d+)(?P<name>[\w\-\.]+)\s*=\s*(?P<value>.*)$", re.MULTILINE)

# Pre-compiled regex for finding variable expansions, e.g., $VAR or ${VAR|default}.
RE_EXPAND = re.compile(
    r"\$(?:(?P<braced>{(?P<name1>[\w\-\.]+)(?:\|(?P<default1>.*?))?})|(?P<name2>[\w\-\.]+)(?:\|(?P<default2>.*))?)"
)


class _Empty:
    """A sentinel class to detect if a default value was provided."""

    ...


Empty = _Empty()

# A mapping of common string representations to boolean values.
_BOOLEAN_MAPPING: dict[str, bool] = {
    "true": True,
    "1": True,
    "y": True,
    "yes": True,
    "on": True,
    "false": False,
    "0": False,
    "n": False,
    "no": False,
    "off": False,
}


def _parse_boolean(key: str, value: Any) -> bool:
    """
    Casts common string representations of booleans to a bool.

    Args:
        key: The name of the environment variable (for error reporting).
        value: The value to cast.

    Returns:
        The cast boolean value.

    Raises:
        ValueError: If the value is not a valid boolean string.
    """
    str_value = str(value).lower()
    if str_value not in _BOOLEAN_MAPPING:
        raise ValueError(f"'{key}' has an invalid boolean value '{value}'.")
    return _BOOLEAN_MAPPING[str_value]


class EnvironLoader(MultiDict):
    """
    A unified environment loader with support for multiple sources and features.

    This class provides a dictionary-like interface to configuration values loaded
    from OS environment variables, .env files, and YAML files. It merges these
    sources with a clear order of precedence and supports variable expansion,
    type casting, and a read-only-after-access protection mechanism.

    Attributes:
        _read_keys (set[str]): A set of keys that have been accessed, making them immutable.
        _prefix (str): A prefix to be automatically added to all keys.
        _ignore_case (bool): Flag indicating if keys should be case-insensitive.
    """

    def __init__(
        self,
        environ: MultiDict | dict[str, Any] | str | Path | None = None,
        *,
        env_file: str | Path | None = None,
        prefix: str | None = None,
        ignore_case: bool = False,
        strict: bool = False,
    ) -> None:
        """
        Initializes the EnvironLoader.

        Args:
            environ: An optional dictionary of initial variables, or a path to a .env file
                     for backward compatibility. If None, `os.environ` is used.
            env_file: (Optional) Path to a `.env` file to load immediately.
            prefix: An optional prefix to prepend to all keys upon access.
            ignore_case: If True, all key lookups will be case-insensitive by
                         normalizing keys to uppercase.
        """
        self._ignore_case = ignore_case
        self._read_keys: set[str] = set()
        self._prefix = prefix or ""
        self._strict = strict

        if self._ignore_case:
            self._prefix = self._prefix.upper()

        actual_environ: MultiDict | dict[str, Any] | None = None
        actual_env_file: str | Path | None = env_file

        if isinstance(environ, (str, Path)):
            actual_env_file = environ
        else:
            actual_environ = environ

        initial_environ: MultiDict | dict[str, Any] | Any = (
            os.environ if actual_environ is None else actual_environ
        )
        if self._ignore_case:
            initial_environ = {k.upper(): v for k, v in initial_environ.items()}

        super().__init__(initial_environ)

        if actual_env_file:
            self.load_from_files(env_file=actual_env_file)

    def load_all(
        self,
        *,
        env_file: str | Path | None = None,
        yaml_file: str | Path | None = None,
        include_os_env: bool = True,
        flatten: bool = True,
        overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Loads and returns a merged configuration dictionary from environment sources,
        file sources, and explicit overrides.

        This function is a **convenience wrapper** that:
        1. Calls `self.load_from_files()` with the loader's stored `self._strict` flag.
        2. Returns the final, compiled configuration using `self.export()`.

        Args:
            env_file: Path to a `.env` file to load environment variables from.
            yaml_file: Path to a YAML configuration file to load structural configuration from.
            include_os_env: If `True`, includes environment variables already present in `os.environ`.
            flatten: If `True`, flattens the structured YAML configuration into a single
                     dictionary using dot notation keys.
            overrides: A dictionary of key/value pairs that explicitly override any settings
                       loaded from files or the environment.

        Returns:
            The final, merged, and processed configuration as a dictionary.
        """
        self.load_from_files(
            env_file=env_file,
            yaml_file=yaml_file,
            include_os_env=include_os_env,
            strict=self._strict,
            flatten=flatten,
            overrides=overrides,
        )
        return self.export()

    def _expand_variable(
        self, match: re.Match, context: dict[str, Any], strict: bool
    ) -> str | Any:
        """
        Resolves a single matched variable like $VAR or ${VAR|default}.

        Args:
            match: The regex match object from `RE_EXPAND`.
            context: The dictionary of values to use for expansion.
            strict: If True, raises an error for missing variables without a default.

        Returns:
            The expanded variable's value as a string.

        Raises:
            EnvError: In strict mode, if a variable is not in the context and has no default.
        """
        name = match.group("name1") or match.group("name2")
        default = match.group("default1") or match.group("default2")

        if self._ignore_case and name:
            name = name.upper()

        value = context.get(name)

        if value is not None:
            return str(value)
        if default is not None:
            return default
        if strict:
            raise EnvError(
                f"Missing required variable '{name}' during expansion and no default was provided."
            )
        return ""

    def _read_env_file(self, file_path: str | Path, strict: bool) -> dict[str, str]:
        """
        Reads a .env file, expands variables, and returns the key-value pairs.

        Variable expansion within the .env file can reference OS environment variables
        or other variables previously defined in the same file.

        Args:
            file_path: The path to the .env file.
            strict: If True, raises an error for duplicate keys.

        Returns:
            A dictionary of variables from the .env file.
        """
        env_vars: dict[str, str] = {}
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            warnings.warn(f"EnvironLoader file '{file_path}' not found.", stacklevel=2)
            return {}

        for match in RE_ENV.finditer(content):
            key = match.group("name")
            value = match.group("value").strip().strip("'\"")

            if self._ignore_case:
                key = key.upper()

            # Context for expansion: OS environment + variables defined so far.
            expansion_context: dict[str, Any] = {**os.environ, **env_vars}

            def _expand_match(
                m: re.Match,
                expansion_context: Any = expansion_context,
                strict: bool = strict,
            ) -> str:
                return self._expand_variable(m, expansion_context, strict)

            value = RE_EXPAND.sub(_expand_match, value)

            if key in env_vars:
                msg = f"Duplicate variable '{key}' in '{file_path}'."
                if strict:
                    raise EnvError(msg)
                warnings.warn(msg, stacklevel=2)
            env_vars[key] = value
        return env_vars

    def _read_yaml_file(
        self,
        file_path: str | Path,
        context: dict[str, Any] | None = None,
        strict: bool = True,
    ) -> dict[str, Any]:
        """
        Reads a YAML file, expands variables using the given context, and returns it.

        Args:
            file_path: The path to the YAML file.
            context: The dictionary of values to use for variable expansion.
            strict: Passed to the variable expansion engine.

        Returns:
            A dictionary of data loaded from the YAML file.

        Raises:
            ImportError: If the 'PyYAML' library is not installed.
        """
        if SafeLoader is None:
            raise ImportError("The 'PyYAML' library is required to load YAML files.")

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            warnings.warn(f"EnvironLoader file '{file_path}' not found.", stacklevel=2)
            return {}

        # Expansion context should always include OS environ as a base.
        expansion_context: dict[str, Any] = {**os.environ, **(context or {})}

        # Temporarily replace '$$' to escape it from variable expansion.
        sentinel = "__ESCAPED_DOLLAR_SIGN__"
        content = content.replace("$$", sentinel)
        content = RE_EXPAND.sub(
            lambda m: self._expand_variable(m, expansion_context, strict), content
        )
        content = content.replace(sentinel, "$")

        try:
            data = SafeLoader(io.StringIO(content)).get_data()
            return data if isinstance(data, dict) else {}
        except (YAMLError, AttributeError) as e:
            raise EnvError(f"Failed to parse YAML file '{file_path}': {e}") from e

    def _flatten_dict(self, data: dict[str, Any], parent_key: str = "") -> dict[str, Any]:
        """
        Flattens a nested dictionary into a single level with dot-separated keys.

        Example:
            {'db': {'host': 'localhost', 'ports': [5432, 5433]}}
            becomes
            {'db.host': 'localhost', 'db.ports.0': 5432, 'db.ports.1': 5433}

        Args:
            data: The dictionary to flatten.
            parent_key: The base key for the current recursion level.

        Returns:
            The flattened dictionary.
        """
        items: dict[str, Any] = {}
        for k, v in data.items():
            new_key = f"{parent_key}.{k}" if parent_key else str(k)
            if self._ignore_case:
                new_key = new_key.upper()

            if isinstance(v, dict):
                items.update(self._flatten_dict(v, new_key))
            elif isinstance(v, list):
                for i, item in enumerate(v):
                    if isinstance(item, (dict, list)):
                        # Recurse for nested structures within lists
                        items.update(self._flatten_dict({str(i): item}, new_key))
                    else:
                        items[f"{new_key}.{i}"] = item
            else:
                items[new_key] = v
        return items

    def load_from_files(
        self,
        *,
        env_file: str | Path | None = None,
        yaml_file: str | Path | None = None,
        include_os_env: bool = True,
        strict: bool = True,
        flatten: bool = True,
        overrides: dict[str, Any] | None = None,
    ) -> None:
        """
        Loads configuration from multiple sources with a defined order of precedence.

        The loading order ensures that more specific sources override more general ones:
        1. Initial `environ` from `__init__`.
        2. OS environment variables (if `include_os_env` is True).
        3. `.env` file.
        4. `YAML` file.
        5. `overrides` dictionary.

        This method replaces all existing variables in the loader instance.

        Args:
            env_file: Path to a `.env` file to load.
            yaml_file: Path to a `YAML` file to load.
            include_os_env: If True, includes variables from `os.environ`.
            strict: If True, raises errors for duplicates in `.env` or missing
                    variables during expansion.
            flatten: If True, nested YAML structures are flattened into
                     dot-separated keys.
            overrides: A dictionary of values that will take the highest precedence.
        """
        final_values: dict[str, Any] = {}

        # Step 1: Start with initial environ
        if self._ignore_case:
            final_values.update({k.upper(): v for k, v in dict(self.items()).items()})
        else:
            final_values.update(self.items())

        # Step 2: Layer OS environment
        if include_os_env:
            os_env = os.environ
            if self._ignore_case:
                os_env = {k.upper(): v for k, v in os_env.items()}  # type: ignore
            final_values.update(os_env)

        # Step 3: Layer .env file
        if env_file:
            env_file_values = self._read_env_file(env_file, strict)
            final_values.update(env_file_values)

        # Step 4: Layer YAML file
        if yaml_file:
            # Context for YAML expansion is everything loaded so far + overrides
            expansion_context = {**final_values}
            if overrides:
                override_context = overrides
                if self._ignore_case:
                    override_context = {k.upper(): str(v) for k, v in overrides.items()}
                expansion_context.update(override_context)

            yaml_data = self._read_yaml_file(yaml_file, expansion_context, strict)
            if flatten:
                yaml_data = self._flatten_dict(yaml_data)
            final_values.update(yaml_data)

        # Step 5: Layer overrides
        if overrides:
            override_values = overrides
            if self._ignore_case:
                override_values = {k.upper(): v for k, v in overrides.items()}
            final_values.update(override_values)

        # Step 6: Clear existing state and load the merged values
        self.clear()
        self._read_keys.clear()
        for k, v in final_values.items():
            # Preserve dict/list objects when not flattening
            if not flatten and isinstance(v, (dict, list)):
                super().__setitem__(k, v)
            else:
                super().__setitem__(k, str(v))

    def _cast(self, key: str, value: Any, cast: Cast[T] | None) -> T | Any:
        """
        Casts a value to a specified type with detailed error handling.

        Args:
            key: The variable name (for error messages).
            value: The value to cast.
            cast: The type or function to cast with (e.g., `int`, `bool`, `float`).

        Returns:
            The casted value.

        Raises:
            ValueError: If the value cannot be cast to the specified type.
        """
        if cast is None:
            return value
        if cast is bool:
            if value is None:
                return None
            return _parse_boolean(key, value)
        try:
            return cast(value)
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"Cannot cast value '{value}' for key '{key}' to type '{cast.__name__}'."
            ) from e

    def env(self, key: str, cast: Cast[T] | None = None, default: Any = Empty) -> T | Any:
        """
        Retrieves a variable, optionally casting it and providing a default.

        This is the primary method for accessing configuration values. It checks the
        loader's internal state first, then falls back to the live `os.environ`.

        Args:
            key: The name of the variable to retrieve. The prefix (if any) is
                 prepended automatically.
            cast: A callable (e.g., `int`, `bool`) to convert the value's type.
            default: A default value to return if the key is not found. If not
                     provided, a `KeyError` is raised for missing keys.

        Returns:
            The processed variable.

        Raises:
            KeyError: If the key is not found and no default is provided.
            ValueError: If the value fails to cast to the specified type.
        """
        key_with_prefix = self._prefix + key
        if self._ignore_case:
            key_with_prefix = key_with_prefix.upper()

        self._read_keys.add(key_with_prefix)

        # Check internal storage first
        if key_with_prefix in self:
            value = self.getone(key_with_prefix)
            return self._cast(key, value, cast)

        # Fallback to live os.environ for variables set after initialization
        if key_with_prefix in os.environ:
            value = os.environ[key_with_prefix]
            return self._cast(key, value, cast)

        if default is not Empty:
            return self._cast(key, default, cast)

        raise KeyError(f"'{key}' not found in environment and no default was provided.")

    def __call__(self, key: str, cast: Cast[T] | None = None, default: Any = Empty) -> T | Any:
        """A convenient alias for the `env()` method."""
        return self.env(key=key, cast=cast, default=default)

    def __getitem__(self, key: str) -> Any:
        """
        Retrieves a variable using dictionary-style access.

        Note: This marks the key as "read", making it immutable. The return
        value may not be a string if `flatten=False` was used.

        Raises:
            KeyError: If the key is not found.
        """
        key_with_prefix = self._prefix + key
        if self._ignore_case:
            key_with_prefix = key_with_prefix.upper()

        if key_with_prefix not in self:
            raise KeyError(key_with_prefix)

        self._read_keys.add(key_with_prefix)
        return self.getone(key_with_prefix)

    def __setitem__(self, key: str, value: Any) -> None:
        """
        Sets a variable.

        Raises:
            EnvError: If the variable has already been read.
        """
        key_with_prefix = self._prefix + key
        if self._ignore_case:
            key_with_prefix = key_with_prefix.upper()

        if key_with_prefix in self._read_keys:
            raise EnvError(f"Cannot set variable '{key}' after it has been read.")

        super().__setitem__(key_with_prefix, value)

    def __delitem__(self, key: str) -> None:
        """
        Deletes a variable.

        Raises:
            EnvError: If the variable has already been read or does not exist.
        """
        key_with_prefix = self._prefix + key
        if self._ignore_case:
            key_with_prefix = key_with_prefix.upper()

        if key_with_prefix in self._read_keys:
            raise EnvError(f"Cannot delete variable '{key}' after it has been read.")

        try:
            super().__delitem__(key_with_prefix)
        except KeyError:
            raise EnvError(f"Attempting to delete '{key}'. Value does not exist.") from None

    def export(self) -> dict[str, Any]:
        """Returns all current environment variables as a standard dictionary."""
        return dict(self.items())

    def multi_items(self) -> Generator[tuple[str, Any], None, None]:
        """
        Yields all key-value pairs, including duplicates.

        This is useful when a variable can be defined multiple times.

        Yields:
            A tuple of (key, value).
        """
        for key in set(self):
            for value in self.getall(key):
                yield key, value

    def get_multi_items(self) -> list[tuple[str, Any]]:
        """Returns all multi-item pairs as a list."""
        return list(self.multi_items())
