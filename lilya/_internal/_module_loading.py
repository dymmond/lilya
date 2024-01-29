import inspect
from importlib import import_module
from typing import Any, ParamSpec

P = ParamSpec("P")


def import_string(dotted_path: str) -> Any:
    """
    Import a dotted module path and return the attribute/class designated by the
    last name in the path. Raise ImportError if the import failed.
    """
    try:
        module_path, class_name = dotted_path.rsplit(".", 1)
    except ValueError as err:
        raise ImportError("%s doesn't look like a module path" % dotted_path) from err

    module = import_module(module_path)

    try:
        return getattr(module, class_name)
    except AttributeError as err:
        raise ImportError(
            'Module "{}" does not define a "{}" attribute/class'.format(module_path, class_name)
        ) from err


class ProxyLoad:
    """
    Loads any object by a string value and
    proxies every method.
    """

    __obj__: Any = None

    def __init__(self, module_path: Any, *args: P.args, **kwargs: P.kwargs) -> None:
        object.__setattr__(self, "__obj__", import_string(module_path)(*args, **kwargs))

    def __getattribute__(self, name: str) -> Any:
        return getattr(object.__getattribute__(self, "__obj__"), name)

    def __delattr__(self, name: str) -> None:
        delattr(object.__getattribute__(self, "__obj__"), name)

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(object.__getattribute__(self, "__obj__"), name, value)

    def __nonzero__(self) -> bool:
        return bool(object.__getattribute__(self, "__obj__"))

    def __str__(self) -> str:
        obj = object.__getattribute__(self, "__obj__")
        if not inspect.isclass(obj):
            return f"<Proxy{obj.__class__.__name__}()>"
        return f"<Proxy{obj.__name__}()>"

    def __repr__(self) -> str:
        return str(self)

    def __hash__(self) -> int:
        return hash(object.__getattribute__(self, "__obj__"))
