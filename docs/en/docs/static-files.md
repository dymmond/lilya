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

As directory also a tuple or list can be provided. This is useful for overwrites or multiple directories which should served under the same
location.

```python
    {!> ../../../docs_src/static_files/basic_overwrite.py!}
```

You can also provide multiple `StaticFiles` and use `fall_through=True` for all except the last to keep the fall-through behavior.

```python
    {!> ../../../docs_src/static_files/overwrite_fall_through.py!}
```



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

[pathlike]: https://docs.python.org/3/library/os.html#os.PathLike
