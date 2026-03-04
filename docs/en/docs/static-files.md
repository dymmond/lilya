# StaticFiles

Lilya provides a convenient `StaticFiles` class for serving files from a specified directory:

## Parameters

- `directory` - A string or [os.PathLike][pathlike] indicating the directory path. You can also provide a list or tuple for using multiple directories.
- `packages` - A list of strings or list of tuples of strings representing Python packages.
- `html` - Operate in HTML mode, automatically loading `index.html` for directories if it exists.
- `check_dir` - Ensure that the directory exists upon instantiation. Defaults to `True`.
- `follow_symlink` - A boolean indicating whether symbolic links for files and directories should be followed. Defaults to `False`.
- `fall_through` - Raises `ContinueRouting` on missing files. Defaults to `False`.

```python
    {!> ../../../docs_src/static_files/basic.py!}
```

For requests that do not match, static files will respond with "404 Not Found" or "405 Method Not Allowed" responses.
In HTML mode, if a `404.html` file exists, it will be displayed as the 404 response.

## Request behavior

`StaticFiles` serves only `GET` and `HEAD` requests.

If `html=True`:

* directory requests can resolve to `index.html`;
* paths without trailing slash can be redirected to slash form;
* `404.html` is used (if present) for not found responses.

When `fall_through=True`, missing files raise `ContinueRouting` and routing can continue to the next matching handler.

As directory also a tuple or list can be provided. This is useful for overwrites or multiple directories which should served under the same
location.

```python
    {!> ../../../docs_src/static_files/basic_overwrite.py!}
```

You can provide multiple `StaticFiles` and use `fall_through=True` for all except the last one to maintain the fall-through behavior.

```python
    {!> ../../../docs_src/static_files/overwrite_fall_through.py!}
```

This is especially useful for layered assets:

* custom project statics first (`fall_through=True`)
* package/default statics second (`fall_through=False`)

The `packages` option allows inclusion of "static" directories from within a Python package.
The Python "bootstrap4" package serves as an example.

```python
    {!> ../../../docs_src/static_files/packages.py!}
```

By default, `StaticFiles` looks for the `statics` directory in each package. You can modify the default directory by specifying a tuple of strings.

```python
    {!> ../../../docs_src/static_files/packages_custom.py!}
```

While you may choose to include static files directly within the "static" directory, using Python packaging to include static files can be beneficial for bundling reusable components.

## Conditional requests and 304 responses

Lilya compares request headers (`If-None-Match`, `If-Modified-Since`) with file response headers and returns `304 Not Modified` when possible.

This reduces bandwidth and improves browser cache behavior for unchanged assets.

## Common pitfalls

* `check_dir=True` and directory missing -> startup/runtime error.
* File exists but wrong mount prefix -> still 404.
* Symlink setups require `follow_symlink=True` when needed.
* Multi-worker deployments should rely on shared static storage when applicable.

## See also

* [Routing](./routing.md#include) for mount/include behavior.
* [Server Push](./server-push.md) for proactive asset delivery.
* [Troubleshooting](./troubleshooting.md) for static path debugging checklist.

[pathlike]: https://docs.python.org/3/library/os.html#os.PathLike
