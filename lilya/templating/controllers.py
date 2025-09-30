from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from lilya.conf import _monkay
from lilya.contrib.security.csrf import get_or_set_csrf_token
from lilya.controllers import Controller
from lilya.exceptions import ImproperlyConfigured  # noqa
from lilya.requests import Request
from lilya.responses import HTMLResponse, RedirectResponse, Response
from lilya.templating import Jinja2Template

templates = Jinja2Template(directory="templates")

__all__ = ["TemplateController", "ListController", "FormController"]


class TemplateControllerMetaclass(type):
    """
    Metaclass for BaseTemplateController and its subclasses that validates the 'template_name' attribute.

    Ensures that any concrete subclass intended for direct use (not BaseTemplateController itself,
    and potentially not TemplateController if it's just an intermediary) has the
    `template_name` attribute explicitly set to a non-None value.
    """

    def __new__(cls: type[type], name: str, bases: tuple[type, ...], attrs: dict[str, Any]) -> Any:
        def make_wrapper(method_name: str, original: Callable[..., Any]) -> Callable[..., Any]:
            async def wrapper(
                self: Any,
                request: Any,
                *args: Any,
                **kwargs: Any,
            ) -> Any:
                # Call subclass override
                result = await original(self, request, *args, **kwargs)

                # If no result, delegate to parent implementation
                if result is None:
                    for base in type(self).mro()[1:]:
                        if hasattr(base, method_name):
                            base_method = getattr(base, method_name)
                            return await base_method(self, request, *args, **kwargs)
                return result

            return wrapper

        for method_name in ("form_valid", "form_invalid"):
            if method_name in attrs:
                attrs[method_name] = make_wrapper(method_name, attrs[method_name])

        return super().__new__(cls, name, bases, attrs)

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

        base_classes = [
            "BaseTemplateController",
            "TemplateController",
            "ListController",
            "FormController",
        ]
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

    __exclude_from_openapi__: bool = True
    template_name: str = None
    csrf_enabled: bool = False
    csrf_token_form_name: str = "csrf_token"
    templates: Jinja2Template = templates

    async def get_csrf_token(self, request: Request) -> Any:
        """
        Generates the CSRF token for the given request.
        """
        return get_or_set_csrf_token(
            request,
            secret=_monkay.settings.secret_key,
            httponly=True,
        )

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
        if self.csrf_enabled and request.method.lower in {"GET", "HEAD"}:
            context[self.csrf_token_form_name] = await self.get_csrf_token(request)
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


class FormController(BaseTemplateController):
    """
    A controller for handling forms in Lilya applications.

    Inspired by Django's ``FormView``, this controller renders a form on GET
    requests and processes submitted data on POST requests. Unlike Django,
    it is validation-library agnostic, allowing you to use Pydantic, msgspec,
    attrs, dataclasses, or any other validation system.

    Typical workflow:
        - On ``GET`` → renders the template with an empty or initial form.
        - On ``POST`` → validates/instantiates the form class.
            - If valid → delegates to :meth:`form_valid`.
            - If invalid → delegates to :meth:`form_invalid`.

    Attributes:
        form_class (type[Any] | None): The class used to instantiate and validate
            form data. Must be set or ``get_form_class()`` must be overridden.
        success_url (str | None): The URL to redirect to upon successful form
            submission. Must be set or ``form_valid()`` must be overridden.
        validator (Callable[[type[Any], dict[str, Any]], Any] | None): Optional
            callable that receives ``(form_class, form_data)`` and returns an
            instantiated form object, or raises an error. Use this to plug in
            Pydantic, msgspec, attrs, etc.
    """

    form_class: type[Any] | None = None
    success_url: str | None = None
    validator: Callable[[type[Any], dict[str, Any]], Any] | None = None
    """
    A callable that takes (form_class, form_data) and returns an instance
    or raises an exception. This allows plugging in Pydantic, msgspec,
    attrs, dataclasses, etc.
    """

    def get_form_class(self) -> type[Any]:
        """
        Return the form class used for instantiation and validation.

        Returns:
            type[Any]: The form class to use.

        Raises:
            ImproperlyConfigured: If ``form_class`` is not set and this method
            is not overridden.
        """
        if self.form_class is None:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} requires either a definition of 'form_class' "
                "or an override of 'get_form_class()'."
            )
        return self.form_class

    def get_initial(self) -> dict[str, Any]:
        """
        Return the initial data for the form.

        Subclasses can override this method to pre-populate form fields.
        By default, returns an empty dict.

        Returns:
            dict[str, Any]: The initial form data.
        """
        return {}

    async def get_context_data(self, request: Request, **kwargs: Any) -> dict[str, Any]:
        """
        Return the template context for rendering the form.

        By default, includes:
            - ``form``: The initial form data (from :meth:`get_initial`).
            - ``errors``: An empty dict (populated by :meth:`form_invalid`).

        Args:
            request (Request): The incoming HTTP request.
            **kwargs: Additional context data.

        Returns:
            dict[str, Any]: The template context.
        """
        context = await super().get_context_data(request, **kwargs)
        context["form"] = self.get_initial()
        context.setdefault("errors", {})
        return context

    async def get(self, request: Request, **kwargs: Any) -> HTMLResponse:
        """
        Handle GET requests.

        Renders the form template with the initial context.

        Args:
            request (Request): The incoming HTTP request.
            **kwargs: Additional context data.

        Returns:
            HTMLResponse: The rendered template response.
        """
        return await self.render_template(request, await self.get_context_data(request, **kwargs))

    async def post(self, request: Request, **kwargs: Any) -> Response:
        """
        Handle POST requests.

        Validates the submitted form data. If valid, delegates to
        :meth:`form_valid`; otherwise, delegates to :meth:`form_invalid`.

        Args:
            request (Request): The incoming HTTP request.
            **kwargs: Additional context data.

        Returns:
            HTMLResponse | RedirectResponse: The response after processing.
        """
        form_class = self.get_form_class()
        form_data = dict(await request.form())

        try:
            instance = await self.validate_form(form_class, form_data)
        except Exception as exc:
            return await self.form_invalid(request, str(exc), form_data, **kwargs)

        return await self.form_valid(request, instance, **kwargs)

    async def patch(self, request: Request, **kwargs: Any) -> Response:
        return await self.post(request, **kwargs)

    async def put(self, request: Request, **kwargs: Any) -> Response:
        return await self.post(request, **kwargs)

    async def validate_form(self, form_class: type[Any], data: dict[str, Any]) -> Any:
        """
        Validate and instantiate the form.

        By default, this method instantiates ``form_class`` with the submitted
        data. Subclasses can override this method or provide a ``validator``
        callable for integration with libraries like Pydantic, msgspec, or attrs.

        Args:
            form_class (type[Any]): The form class to instantiate.
            data (dict[str, Any]): The submitted form data.

        Returns:
            Any: The instantiated form object.

        Raises:
            Exception: If validation or instantiation fails.
        """
        if self.validator:
            return self.validator(form_class, data)
        return form_class(**data)

    async def form_valid(self, request: Request, form: Any, **kwargs: Any) -> Response:
        """
        Called when submitted form data is valid.

        By default, redirects to :attr:`success_url`. Subclasses can override
        this method to save data, send emails, etc.

        Args:
            request (Request): The incoming HTTP request.
            form (Any): The validated form instance.
            **kwargs: Additional context data.

        Returns:
            HTMLResponse | RedirectResponse: A response, typically a redirect.
        """
        if not self.success_url:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} requires 'success_url' or an override of form_valid()."
            )
        return RedirectResponse(url=self.success_url, status_code=303)

    async def form_invalid(
        self, request: Request, errors: Any, data: dict[str, Any], **kwargs: Any
    ) -> Response:
        """
        Called when submitted form data is invalid.

        By default, re-renders the template with the submitted data and error
        messages in the context.

        Args:
            request (Request): The incoming HTTP request.
            errors (Any): The validation errors (format depends on validator).
            data (dict[str, Any]): The submitted form data.
            **kwargs: Additional context data.

        Returns:
            HTMLResponse: The rendered template response with errors.
        """
        context = await super().get_context_data(request, **kwargs)
        context["form"] = data
        context["errors"] = errors
        return await self.render_template(request, context)
