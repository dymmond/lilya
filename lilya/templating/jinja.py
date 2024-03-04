from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Union

from lilya import status
from lilya.exceptions import MissingDependency, TemplateNotFound
from lilya.requests import Request
from lilya.responses import TemplateResponse
from lilya.templating.base import BaseTemplateRenderer

try:
    from jinja2 import (
        Environment,
        FileSystemLoader,
        Template as JinjaTemplate,
        TemplateNotFound as JinjaTemplateNotFound,
    )
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
    """
    Custom Template Renderer.

    This class provides a simplified interface for rendering templates with
    context processing and response preparation.
    """

    def __call__(self, *args: Any, **kwargs: Any) -> TemplateResponse:
        """
        Render a template based on the provided arguments.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            TemplateResponse: The rendered template response.
        """
        request, name, context, status_code, headers, media_type, background = self._parse_args(
            *args, **kwargs
        )

        if hasattr(self.template, "context_processors"):
            for context_processor in self.template.context_processors:
                context.update(context_processor(request))

        template_response = self.prepare_response(
            request, name, context, status_code, headers, media_type, background
        )
        return template_response

    def _parse_args(self, *args: P.args, **kwargs: P.kwargs) -> tuple:
        """
        Parse arguments and keyword arguments for template rendering.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            tuple: Parsed arguments.
        """
        request = self._get_request(*args, **kwargs)
        name = args[1] if len(args) > 1 else kwargs["name"]
        context = args[2] if len(args) > 2 else kwargs.get("context", {})
        status_code = args[3] if len(args) > 3 else kwargs.get("status_code", status.HTTP_200_OK)
        headers = args[4] if len(args) > 4 else kwargs.get("headers")
        media_type = args[5] if len(args) > 5 else kwargs.get("media_type")
        background = args[6] if len(args) > 6 else kwargs.get("background")

        return request, name, context, status_code, headers, media_type, background

    def _get_request(self, *args: P.args, **kwargs: P.kwargs) -> Request | None:
        """
        Extract and validate the 'request' instance from the arguments.

        Args:
            args: Positional arguments.

        Returns:
            Request: The 'request' instance.

        Raises:
            AssertionError: If the 'request' instance is not present or is invalid.
        """
        request = args[0] if len(args) > 0 else kwargs.get("request")
        assert isinstance(
            request, Request
        ), "The first argument should always be a 'Request' instance."
        return request


class Jinja2Template:
    """
    Wrapper class for Jinja2 templating engine.
    """

    def __init__(
        self,
        directory: str | Path | list[Path] | None = None,
        *,
        env: Environment | None = None,
        **options: Any,
    ) -> None:
        """
        Initialize the Jinja2Template instance.

        Args:
            directory (Union[str, Path, List[Path]], optional): Path or list of paths to the template directories.
            env (Environment, optional): Pre-existing Jinja2 Environment instance.
            **options (Any): Additional options to configure the Jinja2 environment.
        """
        self.context_processors: Any = options.pop("context_processors", {})
        assert (
            env or directory
        ), "either 'env' or 'directory' arguments must be passed but not both."

        if env is None:
            self.env = self._create_environment(directory, **options)
        else:
            self.env = self._add_defaults(env=env)

    def _add_defaults(self, env: Environment) -> Environment:
        """
        Add default Jinja2 environment settings.

        Args:
            env (Environment): Existing Jinja2 environment.

        Returns:
            Environment: Modified Jinja2 environment.
        """

        @pass_context
        def path_for(context: dict, name: str, **path_params: Any) -> Any:
            """
            Custom Jinja2 global function to generate URLs using Lilya's Request instance.

            Args:
                context (dict): Jinja2 context, including 'request'.
                name (str): Name of the Lilya route.
                **path_params (Any): Additional path parameters.

            Returns:
                Any: The generated URL.
            """
            request: Request = context["request"]
            return request.path_for(name, **path_params)

        env.globals.setdefault("url_for", path_for)
        return env

    def _create_environment(
        self, directory: str | Path | list[Path], **env_options: Any
    ) -> Environment:
        """
        Create a new Jinja2 environment with the specified options.

        Args:
            directory (Union[str, Path, List[Path]]): Path or list of paths to the template directories.
            **env_options (Any): Additional options to configure the Jinja2 environment.

        Returns:
            Environment: Newly created Jinja2 environment.
        """
        loader = FileSystemLoader(directory)
        env_options.setdefault("loader", loader)
        autoescape = env_options.pop("autoescape", True)

        env = Environment(autoescape=autoescape, **env_options)
        env = self._add_defaults(env=env)
        return env

    def get_template(self, name: str) -> JinjaTemplate:
        """
        Get a Jinja template by name.

        Args:
            name (str): Name of the Jinja template.

        Returns:
            JinjaTemplate: Jinja template instance.

        Raises:
            TemplateNotFound: If the template is not found in the Jinja2 environment.
        """
        try:
            return self.env.get_template(name)
        except JinjaTemplateNotFound as e:
            raise TemplateNotFound(name=name) from e

    def get_template_response(self, *args: Any, **kwargs: Any) -> TemplateResponse:
        """
        Get a TemplateResponse using the provided arguments.

        Args:
            *args (Any): Positional arguments.
            **kwargs (Any): Keyword arguments.

        Returns:
            TemplateResponse: The rendered template response.
        """
        template_renderer = TemplateRenderer(template=self)
        return template_renderer(*args, **kwargs)
