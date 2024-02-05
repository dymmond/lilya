from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, List, Union

from lilya import status
from lilya.exceptions import MissingDependency, TemplateNotFound
from lilya.requests import Request
from lilya.responses import TemplateResponse
from lilya.templating.base import BaseTemplateRenderer

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

if sys.version_info >= (3, 10):  # pragma: no cover
    from typing import ParamSpec
else:  # pragma: no cover
    from typing_extensions import ParamSpec

P = ParamSpec("P")


PathLike = Union[str, "os.PathLike[str]"]


class TemplateRenderer(BaseTemplateRenderer):
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> TemplateResponse:
        if args:
            (
                request,
                name,
                context,
                status_code,
                headers,
                media_type,
                background,
            ) = self._parse_args(*args, **kwargs)
        else:
            (
                request,
                name,
                context,
                status_code,
                headers,
                media_type,
                background,
            ) = self._parse_kwargs(**kwargs)

        if hasattr(self.template, "context_processors"):
            for context_processor in self.template.context_processors:
                context.update(context_processor(request))

        template_response = self.prepare_response(
            request, name, context, status_code, headers, media_type, background
        )
        return template_response

    def _parse_args(self, *args: P.args, **kwargs: P.kwargs) -> tuple:
        request = args[0]
        assert isinstance(
            request, Request
        ), "first argument should always be a 'request' instance."

        name = args[1] if len(args) > 1 else kwargs["name"]
        context = args[2] if len(args) > 2 else kwargs.get("context", {})
        status_code = args[3] if len(args) > 3 else kwargs.get("status_code", 200)
        headers = args[4] if len(args) > 4 else kwargs.get("headers")
        media_type = args[5] if len(args) > 5 else kwargs.get("media_type")
        background = args[6] if len(args) > 6 else kwargs.get("background")

        return request, name, context, status_code, headers, media_type, background

    def _parse_kwargs(self, **kwargs: Any) -> tuple:
        assert (
            "request" in kwargs.get("context", {}) or "request" in kwargs
        ), "`request` is missing from the parameters."

        context: dict[str, Any] = kwargs.get("context", {})
        request = kwargs.get("context", context.get("request"))
        name = kwargs.pop("name")
        status_code = kwargs.pop("status_code", status.HTTP_200_OK)
        headers = kwargs.pop("headers", None)
        media_type = kwargs.pop("media_type", None)
        background = kwargs.pop("background", None)

        return request, name, context, status_code, headers, media_type, background


class Jinja2Template:
    def __init__(
        self,
        directory: str | PathLike | list[Path] | None = None,
        *,
        env: Environment | None = None,
        **options: Any,
    ) -> None:
        self.context_processors: Any = options.pop("context_processors", {})
        assert (
            env or directory
        ), "either 'env' or 'directory' arguments must be passed but not both."

        if env is None:
            self.env = self._create_environment(directory, **options)
        else:
            self.env = self._add_defaults(env=env)

    def _add_defaults(self, env: Environment) -> Environment:
        @pass_context
        def url_for(context: dict, name: str, **path_params: Any) -> Any:
            request: Request = context["request"]
            return request.path_for(name, **path_params)

        env.globals.setdefault("url_for", url_for)
        return env

    def _create_environment(
        self, directory: Union[str, PathLike, List[Path]], **env_options: Any
    ) -> Environment:
        loader = FileSystemLoader(directory)
        env_options.setdefault("loader", loader)
        autoescape = env_options.pop("autoescape", True)

        env = Environment(autoescape=autoescape, **env_options)
        env = self._add_defaults(env=env)
        return env

    def get_template(self, name: str) -> JinjaTemplate:
        try:
            return self.env.get_template(name)
        except JinjaTemplateNotFound as e:
            raise TemplateNotFound(name=name) from e

    def get_template_response(self, *args: P.args, **kwargs: P.kwargs) -> TemplateResponse:
        """
        Returns the Jinja2Template response format from the jinja template.
        """
        template_renderer = TemplateRenderer(template=self)
        return template_renderer(*args, **kwargs)
