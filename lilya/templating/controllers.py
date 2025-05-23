from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from lilya.controllers import Controller
from lilya.exceptions import ImproperlyConfigured  # noqa
from lilya.requests import Request
from lilya.responses import HTMLResponse
from lilya.templating import Jinja2Template

templates = Jinja2Template(directory="templates")

__all__ = ["TemplateController", "ListController"]


class TemplateControllerMetaclass(type):
    """
    Metaclass for BaseTemplateController and its subclasses that validates the 'template_name' attribute.

    Ensures that any concrete subclass intended for direct use (not BaseTemplateController itself,
    and potentially not TemplateController if it's just an intermediary) has the
    `template_name` attribute explicitly set to a non-None value.
    """

    def __init__(cls, name: str, bases: Any, dct: Any) -> None:
        """
        Initializes the class and performs the validation check.

        Args:
            name: The name of the class being created.
            bases: A tuple of the base classes.
            dct: A dictionary containing the class's namespace.

        Raises:
            ImproperlyConfigured: If a subclass intended for direct use does not
                                   have the 'template_name' attribute set.
        """
        super().__init__(name, bases, dct)

        base_classes = ["BaseTemplateController", "TemplateController", "ListController"]
        is_base_or_template_view = name in base_classes

        if (
            not is_base_or_template_view  # Not the base or the specific TemplateController class
            and getattr(cls, "template_name", None) is None  # template_name is not set or is None
        ):
            # Also check if template_name is explicitly set to None in the dict
            # This covers cases where template_name = None is explicitly written
            if "template_name" not in dct or dct["template_name"] is None:
                raise ImproperlyConfigured(
                    f"'{name}' requires the 'template_name' attribute to be set or inherit from a class that sets it."
                )


class BaseTemplateController(Controller, metaclass=TemplateControllerMetaclass):
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
            data = {}
        else:
            data.update(context)

        if "request" in data:
            del data["request"]

        merged_context = await self.get_context_data(request=request)
        merged_context.update(data)
        return self.templates.get_template_response(
            request,
            self.template_name,  # Use self.template_name as defined in the class
            merged_context,
        )


class TemplateController(BaseTemplateController):
    """
    A basic class-based view similar to Django's TemplateController for Lilya.

    This view is designed to render a specified template in response to a GET request.
    Subclasses must set the `template_name` attribute.

    Example usage:
        class HomePageView(TemplateController):
            template_name = "home.html"

    Note:
        This class itself does not implement the `get` method; it serves as
        a base for subclasses that will implement the HTTP method handlers
        (like `get`, `post`, etc.) and typically call `render_template`.
    """

    ...


class ListController(BaseTemplateController):
    """
    A class-based view to display a list of objects.

    This view retrieves a list of items using the `get_queryset` method and
    includes it in the template context under the name specified by `context_object_name`.

    Attributes:
        template_name: The name of the template file to render. Must be set.
        context_object_name: The name of the context variable containing the list
                             of objects (defaults to "object_list").
        templates: The initialized Jinja2Template instance used for rendering.

    Example usage:
        class ArticleListController(ListController):
            template_name = "articles/list.html"
            context_object_name = "articles" # Optional, defaults to "object_list"

            async def get_queryset(self) -> list[dict]:
                 # Replace with actual data fetching logic (e.g., ORM query)
                 return [
                     {"id": 1, "title": "First Article"},
                     {"id": 2, "title": "Second Article"},
                 ]

        # In your urls:
        # Path("/articles", ArticleListController)

    """

    context_object_name: str = "object_list"

    async def get_queryset(self) -> Iterable[Any]:  # noqa
        """
        Return the list of items for this view.

        Override this method to fetch your data (e.g., from a database, API).
        The returned value should be an iterable (list, query result, etc.).
        This method should be asynchronous if data fetching is async.
        """
        return []

    async def get_context_data(self, request: Request, **kwargs: Any) -> dict:
        """
        Return the context data for displaying the template.

        Includes the list of items from `get_queryset` in the context
        under the name specified by `self.context_object_name`.
        """
        # Get context from the parent class (includes 'request' and any kwargs like path parameters)
        context = await super().get_context_data(request, **kwargs)

        # Get the list of objects from the queryset method
        object_list = await self.get_queryset()

        # Add the object list to the context using the specified name
        context[self.context_object_name] = object_list

        return context
