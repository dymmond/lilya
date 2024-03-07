# Settings

In every application, there arises a need for project-specific settings to ensure its uniqueness.

As a project grows in complexity, and settings become dispersed throughout the codebase,
managing them can become challenging, leading to a potential organizational mess.

Lilya leverages [Dymmond Setings](https://settings.dymmond.com).

!!! warning
    All the settings in Lilya use Python dataclasses.

## How to use

There are two ways of using the settings object within a Lilya application.

* Using the **LILYA_SETTINGS_MODULE** environment variable
* Using the **[settings_module](#the-settings_module)** instance attribute.

Each one of them has particular use cases but they also work together is perfect harmony.

## Settings and the application

When starting a Lilya instance if no parameters are provided, it will automatically load the defaults from the
system settings object, the `Settings`.

=== "No parameters"

    ```python
    {!> ../docs_src/settings/app/no_parameters.py!}
    ```

=== "With Parameters"

    ```python
    {!> ../docs_src/settings/app/with_parameters.py!}
    ```

## Custom settings

Using the defaults from `Settings` generally will not do too much for majority of the applications.

For that reason custom settings are needed.

**All the custom settings should be inherited from the `Settings`**.

Let's assume we have three environment for one application: `production`, `testing`, `development` and a base settings
file that contains common settings across the three environments.

=== "Base"

    ```python
    {!> ../docs_src/settings/custom/base.py!}
    ```

=== "Development"

    ```python
    {!> ../docs_src/settings/custom/development.py!}
    ```

=== "Testing"

    ```python
    {!> ../docs_src/settings/custom/testing.py!}
    ```

=== "Production"

    ```python
    {!> ../docs_src/settings/custom/production.py!}
    ```

What just happened?

1. Created an `AppSettings` inherited from the `Settings` with common cross environment properties.
2. Created one settings file per environment and inherited from the base `AppSettings`.
3. Created specific  events `on_startup` and `on_shutdown` for each environment.


## Settings Module

Lilya by default is looking for a `LILYA_SETTINGS_MODULE` environment variable to execute any custom settings,
if nothing is provided then it will execute the application defaults.

=== "Without LILYA_SETTINGS_MODULE"

    ```shell
    uvicorn src:app --reload

    INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
    INFO:     Started reloader process [28720]
    INFO:     Started server process [28722]
    INFO:     Waiting for application startup.
    INFO:     Application startup complete.
    ```

=== "With LILYA_SETTINGS_MODULE"

    ```shell
    LILYA_SETTINGS_MODULE=src.configs.production.ProductionSettings uvicorn src:app

    INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
    INFO:     Started reloader process [28720]
    INFO:     Started server process [28722]
    INFO:     Waiting for application startup.
    INFO:     Application startup complete.
    ```

It is very simple, `LILYA_SETTINGS_MODULE` looks for the custom settings class created for the application
and loads it in lazy mode and make it globaly available.

## The settings_module

This is a great tool to make your Lilya applications 100% independent and modular. There are cases
where you simply want to plug an existing lilya application into another and that same lilya application
already has unique settings and defaults.

The `settings_config` is a parameter available in every single `Lilya` instance as well as `ChildLilya`.

### Creating a settings_config

The configurations have **literally the same concept**
as the [Settings](#settings-and-the-application), which means that every single
`settings_module` **must be derived from the Settings** or a `FieldException` is thrown.

The reason why the above is to keep the integrity of the application and settings.

```python
{!> ../docs_src/applications/settings/settings_config/example2.py !}
```

Is this simple, literally, Lilya simplifies the way you can manipulate settings on each level
and keeping the intregrity at the same time.

Check out the [order of priority](#order-of-priority) to understand a bit more.

## Order of priority

There is an order or priority in which Lilya reads your settings.

If a `settings_config` is passed into a Lilya instance, that same object takes priority above
anything else. Let us imagine the following:

* A Lilya application with normal settings.
* A `ChildLilya` with a specific set of configurations unique to it.

```python
{!> ../docs_src/applications/settings/settings_config/example1.py !}
```


**What is happenening here?**

In the example above we:

* Created a settings object derived from the main `Settings` and
passed some defaults.
* Passed the `ChildLilyaSettings` into the `ChildLilya` instance.
* Passed the `ChildLilya` into the `Lilya` application.

So, how does the priority take place here using the `settings_module`?

* If no parameter value (upon instantiation), for example `app_name`, is provided, it will check for that same value
inside the `settings_module`.
* If `settings_module` does not provide an `app_name` value, it will look for the value in the
`LILYA_SETTINGS_MODULE`.
* If no `LILYA_SETTINGS_MODULE` environment variable is provided by you, then it will default
to the Lilya defaults. [Read more about this here](#settings-module).

So the order of priority:

* Parameter instance value takes priority above `settings_module`.
* `settings_module` takes priority above `LILYA_SETTINGS_MODULE`.
* `LILYA_SETTINGS_MODULE` is the last being checked.


## Settings config and Lilya settings module

The beauty of this modular approach is the fact that makes it possible to use **both** approaches at
the same time ([order of priority](#order-of-priority)).

Let us use an example where:

1. We create a main Lilya settings object to be used by the `LILYA_SETTINGS_MODULE`.
2. We create a `settings_module` to be used by the Lilya instance.
3. We start the application using both.

Let us also assume you have all the settings inside a `src/configs` directory.

**Create a configuration to be used by the LILYA_SETTINGS_MODULE**

```python title="src/configs/main_settings.py"
{!> ../docs_src/applications/settings/settings_config/main_settings.py !}
```

**Create a configuration to be used by the setting_config**

```python title="src/configs/app_settings.py"
{!> ../docs_src/applications/settings/settings_config/app_settings.py !}
```

**Create a Lilya instance**

```python title="src/app.py"
{!> ../docs_src/applications/settings/settings_config/app.py !}
```

Now we can start the server using the `AppSettings` as global and `InstanceSettings` being passed
via instantiation. The AppSettings from the main_settings.py is used to call from the command-line.

```shell
LILYA_SETTINGS_MODULE=src.configs.main_settings.AppSettings uvicorn src:app --reload

INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [28720]
INFO:     Started server process [28722]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

Great! Now not only we have used the `settings_module` and `LILYA_SETTINGS_MODULE` but we used
them at the same time!

Check out the [order of priority](#order-of-priority) to understand which value takes precedence
and how Lilya reads them out.

## Parameters

The parameters available inside `Settings` can be overridden by any custom settings.

## Accessing settings

To access the application settings there are different ways:

=== "Within the application request"

    ```python
    {!> ../docs_src/settings/access/within_app.py!}
    ```

=== "From the global settings"

    ```python
    {!> ../docs_src/settings/access/global.py!}
    ```

!!! info
    Some of this information might have been mentioned in some other parts of the documentation but we assume
    the people reading it might have missed.


## Order of importance

Using the settings to start an application instead of providing the parameters directly in the moment of
instantiation does not mean that one will work with the other.

When you instantiate an application **or you pass parameters directly or you use settings or a mix of both**.

Passing parameters in the object will always override the values from the default settings.

```python
from dataclasses import dataclass

from lilya.conf import Settings
from lilya.middleware.httpsredirect import HTTPSRedirectMiddleware
from lilya.middleware import DefineMiddleware


@dataclass
class AppSettings(Settings):
    debug: bool = False

    @property
    def middleware(self) -> List[DefineMiddleware]:
        return [DefineMiddleware(HTTPSRedirectMiddleware)]

```

The application will:

1. Start with `debug` as `False`.
2. Will start with a middleware `HTTPSRedirectMiddleware`.

Starting the application with the above settings will make sure that has an initial `HTTPSRedirectMiddleware` and `debug`
set with values **but** what happens if you use the settings + parameters on instantiation?

```python
from lilya.apps import Lilya

app = Lilya(debug=True, middleware=[])
```

The application will:

1. Start with `debug` as `True`.
2. Will start without custom middlewares it the `HTTPSRedirectMiddleware` it was overridden by `[]`.

Although it was set in the settings to start with `HTTPSRedirectMiddleware` and debug as `False`, once you pass different
values in the moment of instantiating a `Lilya` object, those will become the values to be used.

**Declaring parameters in the instance will always precede the values from your settings**.

The reason why you should be using settings it is because will make your codebase more organised and easier
to maintain.

!!! Check
    When you pass the parameters via instantiation of a Lilya object and not via parameters, when accessing the
    values via `request.app.settings`, the values **won't be in the settings** as those were passed via application
    instantiation and not via settings object. The way to access those values is, for example, `request.app.debug`
    directly.
