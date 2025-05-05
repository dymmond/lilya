# Templates

Lilya is not inherently tied to any specific templating engine, but Jinja2 stands out as an excellent choice
due to its proven origins and widely adoption in the Python world.

## Jinja2Template

This is what Lilya brings out of the box and allows serving HTML via the handlers.

```python
from lilya.templating import Jinja2Template
```

### Parameters

- `directory`: A string, [os.Pathlike][pathlike], or a list of strings or [os.Pathlike][pathlike] indicating a directory path.
- `env`: Any different `jinja2.Environment` instance _(Optional)_.
- `**options`: Additional keyword arguments to pass to the Jinja2 environment.

[pathlike]: https://docs.python.org/3/library/os.html#os.PathLike

## Use of Jinja2Template

Lilya brings a pre-configured `Jinja2Template` configuration that it will be probably what you will
want to use. In case you want a different `jinja2.Enviroment`, that can be also passed when instantiating
the `Jinja2Template`.

```python
{!> ../../../docs_src/templates/template.py !}
```

### Templates response parameters

The get_template_response function expects the following arguments:

- `request` (required): The HTTP request object.
- `name` (required): The name of the template to render.
- `context` (optional): A dictionary allowing you to include dynamic data in the template rendering process.


Any additional arguments or keyword arguments provided will be passed directly to `TemplateResponse`.
This is for example handy when you need async templates.

### Async templates

A very good feature of jinja2 is that you can you can have async templates. This means awaitables are automatically resolved
and async iteration is supported out of the box.
This is especially useful for the async ORMs, for example [Edgy](https://edgy.dymmond.com).

```python
{!> ../../../docs_src/templates/template_async.py !}
```

And now you can iterate over QuerySets out of the box. Nothing else is required.

Note that internally the template response switches the render method and uses the [async content](./responses.md#async-content) feature
so you can only access the body attribute after calling `__call__` or `resolve_async_content()`.

### Optional Arguments

- `status_code` (int, optional): The status code of the response. Defaults to 200.
- `background` (BackgroundTask, optional): An instance of BackgroundTask. Defaults to None.
- `headers` (dict[str, Any], optional): A dictionary of response headers. Defaults to None.
- `media_type` (str, optional): The media type of the response. Defaults to "text/html".

You can pass these arguments either as keyword arguments or positional arguments, depending on your preference.

!!! warning
    It's imperative to include the incoming request instance as part of the template context.

The Jinja2 template context automatically incorporates a `url_for` function, allowing correct hyperlinking to other pages within the application.

For instance, static files can be linked from within HTML templates:

```jinja
{!> ../../../docs_src/_shared/jinja.html !}
```

Should you wish to utilize [custom filters][jinja2], you will need to update the `env` property of `Jinja2Template`:

```python
{!> ../../../docs_src/templates/custom.py !}
```

## The `jinja2.Environment`

Lilya accepts a preconfigured [jinja2.Environment](https://jinja.palletsprojects.com/en/3.0.x/api/#api) instance by
passing it inside the `env` attribute when instantiaing the `Jinja2Template`.

```python
{!> ../../../docs_src/templates/env.py !}
```

## Context Processors

A context processor is a function that returns a dictionary to be merged into a template context. Each function takes only one argument,
`request`, and must return a dictionary to be added to the context.

A typical use case for template processors is to enhance the template context with shared variables.

```python
{!> ../../../docs_src/templates/ctx.py !}
```

### Registering Context Processors

To register context processors, pass them to the `context_processors` argument of the `Jinja2Template` class.

```python
{!> ../../../docs_src/templates/ctx_register.py !}
```

## Custom Jinja2 Environment

`Jinja2Template` accepts all options supported by the Jinja2 `Environment`.
This grants greater control over the `Environment` instance created by Lilya.

For the list of options available to `Environment`, refer to the Jinja2 documentation
[here](https://jinja.palletsprojects.com/en/3.0.x/api/#jinja2.Environment).

```python
{!> ../../../docs_src/templates/custom_jinja.py !}
```

## Asynchronous Template Rendering

While Jinja2 supports asynchronous template rendering, it is advisable to avoid including logic in
templates that trigger database lookups or other I/O operations.

A recommended practice is to ensure that your endpoints handle all I/O operations.
For instance, perform database queries within the view and include the final results in the context.
This approach helps keep templates focused on presentation logic rather than I/O operations.

[jinja2]: https://jinja.palletsprojects.com/en/3.0.x/api/?highlight=environment#writing-filters

Okay, here is the documentation section formatted for MkDocs. It uses standard Markdown with triple backticks for code blocks, specifying the language (`python` or `jinja`). The `{!> ... !}` syntax is kept as it seems to be part of your MkDocs setup for including files.

## Class-Based Template Controllers

Leveraging Lilya's `Controller` class provides a structured and reusable approach to handling requests.
For common patterns like rendering templates or displaying lists of objects, class-based controllers offer a clean way
to encapsulate logic.

Lilya provides a base class and specific implementations to simplify these tasks.

### BaseTemplateController

`BaseTemplateController` serves as the foundation for template-rendering controllers. It provides core functionalities such as:

* Managing the `Jinja2Template` instance used for rendering.
* Implementing the `render_template` method, which handles the process of rendering a template with a given context.
* Providing a base implementation for `get_context_data`, which prepares the default context dictionary for the template.

Controllers like `TemplateController` and `ListController` inherit from this base to gain its core template rendering
capabilities.

### TemplateController

The `TemplateController` is a simple, concrete implementation of `BaseTemplateController` designed for rendering a
single template. It's analogous to Django's `TemplateView`.

Subclasses of `TemplateController` are required to define the `template_name` attribute, specifying which template
file should be rendered when the controller is invoked (typically via a `get` method handler).


**Example:**

```python
import asyncio # You might need this if simulating async like in the ListView example
from lilya.requests import Request
from lilya.responses import HTMLResponse
from lilya.templating.controllers import TemplateController

class HomePageController(TemplateController):
    template_name = "home.html"

    async def get(self, request: Request) -> HTMLResponse:
        """Handles GET requests for the home page."""
        # render_template uses the template_name set on the class
        # and calls get_context_data internally.
        # You can pass additional context here if needed:
        # return await self.render_template(request, context={"title": "Home"})
        return await self.render_template(request)
```

### ListController

The `ListController` is designed specifically for displaying lists of objects. It extends `BaseTemplateController`
by providing a standard pattern for fetching data and making it available to the template context.

Key features:

* ***get_queryset*** method: This async method is the primary place where you'll write logic to fetch the
list of items (e.g., querying a database, calling an API). Subclasses must override this method.
* ***context_object_name*** attribute: A string specifying the key name under which the fetched list of objects
will be available in the template context. It defaults to `"object_list"`.
* **Overridden ***get_context_data***:** This method calls `get_queryset`, retrieves the list of items, and adds
it to the context dictionary using the `context_object_name`.

**Example:**

```python
import asyncio
from lilya.requests import Request
from lilya.responses import HTMLResponse
from lilya.templating.controllers import ListController


class ArticleListController(ListController):
    template_name = "articles/list.html"
    context_object_name = "articles" # The list will be available as 'articles' in the template

    async def get_queryset(self) -> list[dict]:
         # Replace with actual data fetching logic (e.g., ORM query)
         # Simulate fetching data
         print("Fetching article list...")
         await asyncio.sleep(0.01) # Simulate async operation
         return [
             {"id": 1, "title": "First Article", "published": True},
             {"id": 2, "title": "Second Article", "published": False},
             {"id": 3, "title": "Third Article", "published": True},
         ]

    async def get(self, request: Request) -> HTMLResponse:
        """Handles GET requests for the article list page."""
        # render_template calls get_context_data, which calls get_queryset
        # You can pass path parameters or other data as context if needed:
        # return await self.render_template(request, context={"page_title": "All Articles"})
        return await self.render_template(request)
```

**Example of the template (`articles/list.html`):**

```jinja
<h1>Articles</h1>
<ul>
{% for article in articles %}
  <li>{{ article.title }} {% if not article.published %}(Draft){% endif %}</li>
{% endfor %}
</ul>
```

By using these class-based controllers, you can structure your template-rendering endpoints in a more
organized and maintainable way, separating concerns like data fetching, context preparation, and rendering.
