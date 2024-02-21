# **`Settings`** class

Reference for the `Settings` class object and how to use it.

Read more about [how to use the settings](https://lilya.dev/settings/) in your
application and leverage the system.

The settings are used by **any Lilya application** and used as the defaults for the
[Lilya](../index.md) class instance if nothing is provided.

## How to import

```python
from esmerald.conf import settings
```

**Via application instance**

```python
from lilya.apps import Lilya

app = Lilya()
app.settings
```

::: lilya.conf.global_settings.Settings
    options:
        filters:
        - "!^app"
        - "!^ipython_args"
        - "!^ptpython_config_file"
