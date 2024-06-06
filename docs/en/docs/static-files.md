# StaticFiles

Lilya provides a convenient `StaticFiles` class for serving files from a specified directory:

## Parameters

- `directory` - A string or [os.PathLike][pathlike] indicating the directory path.
- `packages` - A list of strings or list of tuples of strings representing Python packages.
- `html` - Operate in HTML mode, automatically loading `index.html` for directories if it exists.
- `check_dir` - Ensure that the directory exists upon instantiation. Defaults to `True`.
- `follow_symlink` - A boolean indicating whether symbolic links for files and directories should be followed. Defaults to `False`.

```python
from lilya.apps import Lilya
from lilya.routing import Include
from lilya.staticfiles import StaticFiles


app = Lilya(routes=[
    Include('/static', app=StaticFiles(directory='static'), name="static"),
])
```

For requests that do not match, static files will respond with "404 Not Found" or "405 Method Not Allowed" responses.
In HTML mode, if a `404.html` file exists, it will be displayed as the 404 response.

The `packages` option allows inclusion of "static" directories from within a Python package.
The Python "bootstrap4" package serves as an example.

```python
from lilya.apps import Lilya
from lilya.routing import Include
from lilya.staticfiles import StaticFiles


app = Lilya(routes=[
    Include('/static', app=StaticFiles(directory='static', packages=['bootstrap4']), name="static"),
])
```

By default, `StaticFiles` looks for the `statics` directory in each package. You can modify the default directory by specifying a tuple of strings.

```python
routes=[
    Include('/static', app=StaticFiles(packages=[('bootstrap4', 'static')]), name="static"),
]
```

While you may choose to include static files directly within the "static" directory, using Python packaging to include static files can be beneficial for bundling reusable components.

[pathlike]: https://docs.python.org/3/library/os.html#os.PathLike
