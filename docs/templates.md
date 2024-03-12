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
- `env`: Any different `jinja2.Environment` instance *(Optional)*.
- `**options`: Additional keyword arguments to pass to the Jinja2 environment.

[pathlike]: https://docs.python.org/3/library/os.html#os.PathLike

## Use of Jinja2Template

Lilya brings a pre-configured `Jinja2Template` configuration that it will be probably what you will
want to use. In case you want a different `jinja2.Enviroment`, that can be also passed when instantiating
the `Jinja2Template`.

```python
{!> ../docs_src/templates/template.py !}
```
### Templates response parameters

The get_template_response function expects the following arguments:

- `request`: (required): The HTTP request object.
- `name`: (required): The name of the template to render.

Any additional arguments or keyword arguments provided will be passed directly to the template as context. 
This allows you to include dynamic data in the template rendering process.
You can pass these arguments either as keyword arguments or positional arguments, depending on your preference.

!!! warning
    It's imperative to include the incoming request instance as part of the template context.

The Jinja2 template context automatically incorporates a `url_for` function, allowing correct hyperlinking to other pages within the application.

For instance, static files can be linked from within HTML templates:

```jinja
{!> ../docs_src/_shared/jinja.html !}
```

Should you wish to utilize [custom filters][jinja2], you will need to update the `env` property of `Jinja2Template`:

```python
{!> ../docs_src/templates/custom.py !}
```

## The `jinja2.Environment`

Lilya accepts a preconfigured [jinja2.Environment](https://jinja.palletsprojects.com/en/3.0.x/api/#api) instance by
passing it inside the `env` attribute when instantiaing the `Jinja2Template`.

```python
{!> ../docs_src/templates/env.py !}
```

## Context Processors

A context processor is a function that returns a dictionary to be merged into a template context. Each function takes only one argument,
`request`, and must return a dictionary to be added to the context.

A typical use case for template processors is to enhance the template context with shared variables.

```python
{!> ../docs_src/templates/ctx.py !}
```

### Registering Context Processors

To register context processors, pass them to the `context_processors` argument of the `Jinja2Template` class.

```python
{!> ../docs_src/templates/ctx_register.py !}
```

## Custom Jinja2 Environment

`Jinja2Template` accepts all options supported by the Jinja2 `Environment`.
This grants greater control over the `Environment` instance created by Lilya.

For the list of options available to `Environment`, refer to the Jinja2 documentation
[here](https://jinja.palletsprojects.com/en/3.0.x/api/#jinja2.Environment).

```python
{!> ../docs_src/templates/custom_jinja.py !}
```

## Asynchronous Template Rendering

While Jinja2 supports asynchronous template rendering, it is advisable to avoid including logic in
templates that trigger database lookups or other I/O operations.

A recommended practice is to ensure that your endpoints handle all I/O operations.
For instance, perform database queries within the view and include the final results in the context.
This approach helps keep templates focused on presentation logic rather than I/O operations.

[jinja2]: https://jinja.palletsprojects.com/en/3.0.x/api/?highlight=environment#writing-filters
