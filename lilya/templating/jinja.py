from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Union

from lilya.exceptions import MissingDependency, TemplateNotFound

try:
    from jinja2 import Environment, FileSystemLoader
    from jinja2 import Template as JinjaTemplate
    from jinja2 import TemplateNotFound as JinjaTemplateNotFound
except ImportError as exc:
    raise MissingDependency("jinja2 is not installed") from exc


try:
    import jinja2

    if hasattr(jinja2, "pass_context"):
        pass_context = jinja2.pass_context
    else:
        pass_context = jinja2.contextfunction
except ImportError:
    jinja2 = None


if TYPE_CHECKING:
    from lilya.requests import Request

PathLike = Union[str, "os.PathLike[str]"]


class Jinja2Template:
    def __init__(self, directory: str | PathLike | list[Path], **env_options: Any) -> None:
        self.env = self._create_environment(directory, **env_options)

    def _create_environment(
        self, directory: Union[str, PathLike, List[Path]], **env_options: Any
    ) -> Environment:
        @pass_context
        def url_for(context: dict, name: str, **path_params: Any) -> Any:
            request: Request = context["request"]
            return request.path_for(name, **path_params)

        loader = FileSystemLoader(directory)
        env_options.setdefault("loader", loader)

        env = Environment(autoescape=True, **env_options)
        env.globals.setdefault("url_for", url_for)
        return env

    def get_template(self, template_name: str) -> JinjaTemplate:
        try:
            return self.env.get_template(template_name)
        except JinjaTemplateNotFound as e:  # pragma: no cover
            raise TemplateNotFound(template_name=template_name) from e
