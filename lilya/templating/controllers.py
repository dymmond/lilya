from __future__ import annotations

from typing import Any

from lilya.controllers import Controller
from lilya.exceptions import ImproperlyConfigured  # noqa
from lilya.requests import Request
from lilya.responses import HTMLResponse
from lilya.templating import Jinja2Template

# Initialize a Jinja2 template engine instance.
# The 'directory' specifies the location of the template files relative to the application root.
templates = Jinja2Template(directory="templates")

# Defines the public API of this module.
__all__ = ["TemplateView"]


class TemplateViewMetaclass(type):
    """
    Metaclass for BaseTemplateView that validates the 'template_name' attribute.

    Ensures that any concrete subclass of BaseTemplateView (that is not BaseTemplateView itself)
    has the `template_name` attribute explicitly set to a non-None value.
    """

    def __init__(cls, name: str, bases: Any, dct: Any) -> None:
        """
        Initializes the class and performs the validation check.

        Args:
            name: The name of the class being created.
            bases: A tuple of the base classes.
            dct: A dictionary containing the class's namespace.

        Raises:
            ImproperlyConfigured: If a subclass of BaseTemplateView does not
                                   have the 'template_name' attribute set.
        """
        super().__init__(name, bases, dct)

        # We check if the class being created is NOT the base class itself,
        # and if it still has template_name set to None.
        # This relies on the convention that the base class is named 'BaseTemplateView'.
        # A more robust check might involve a special class attribute marker.
        if (
            name != "BaseTemplateView"
            and name != "TemplateView"
            and getattr(cls, "template_name", None) is None
        ):
            # Also check if template_name is explicitly set to None in the dict
            if "template_name" not in dct or dct["template_name"] is None:
                raise ImproperlyConfigured(
                    f"TemplateView subclass '{name}' requires the 'template_name' attribute to be set."
                )


class BaseTemplateView(Controller, metaclass=TemplateViewMetaclass):
    """
    A base class for template-based views in Lilya.

    This class provides the core logic for rendering templates, handling context,
    and integrating with a template engine. Subclasses must define the
    `template_name` attribute.

    Attributes:
        template_name: The name of the template file to render. Must be set in subclasses.
        templates: The initialized Jinja2Template instance used for rendering.
    """

    template_name: str = None
    templates: Jinja2Template = templates

    async def get_context_data(self, request: Request, **kwargs: Any) -> dict:
        """
        Return the context data for displaying the template.

        Override this method in subclasses to add custom context variables.
        The base implementation provides the 'request' object in the context,
        which is necessary for template features like `url_for`.

        Args:
            request: The incoming request object.
            **kwargs: Arbitrary keyword arguments that might be passed to the view.

        Returns:
            A dictionary representing the context data for the template.
        """
        # Lilya requires 'request' in the context for url_for and other template features
        # Add existing kwargs to the context, allowing subclasses to pass initial data.
        context = {"request": request}
        context.update(kwargs)
        return context

    async def render_template(
        self, request: Request, context: dict[str, Any] | None = None
    ) -> HTMLResponse:
        """
        Renders the specified template with the given context into an HTMLResponse.

        This method mirrors Django's render_to_response logic. It merges the
        base context (including the request) with the provided context dictionary
        before rendering.

        Args:
            request: The incoming request object.
            template_name: The name of the template file to render.
            context: A dictionary containing data to be available in the template.

        Returns:
            An HTMLResponse containing the rendered template.

        Note:
            The `template_name` argument here is primarily for compatibility or
            potential overrides, but the class's `self.template_name` is
            typically used for rendering in the `get` method of concrete subclasses.
        """
        # Get the base context data and update it with the provided context
        data: dict[str, Any] = {}
        if context is None:
            data = await self.get_context_data(request=request)

        if data is None:
            data = {}

        if "request" in data:
            del data["request"]

        merged_context = await self.get_context_data(request=request, **data)
        return self.templates.get_template_response(
            request,
            self.template_name,  # Use self.template_name as defined in the class
            merged_context,
        )


class TemplateView(BaseTemplateView):
    """
    A basic class-based view similar to Django's TemplateView for Lilya.

    This view is designed to render a specified template in response to a GET request.
    Subclasses must set the `template_name` attribute.

    Example usage:
        class HomePageView(TemplateView):
            template_name = "home.html"

    Note:
        This class itself does not implement the `get` method; it serves as
        a base for subclasses that will implement the HTTP method handlers
        (like `get`, `post`, etc.) and typically call `render_template`.
    """

    ...
