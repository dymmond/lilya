# `Scheduler` decorator

Almost every application in one way or another needs some sort of automated scheduler to run automated tasks.
In that in mind and with the help of the great widely used
<a href='https://asyncz.dymmond.com' target='_blank'>Asyncz</a>, Lilya comes with a built-in
scheduler, saving you tons of headaches and simplifying the process of creating them.

## Requirements

Lilya uses `asyncz` for this integration. You can install by running:

```shell
$ pip install asyncz
```

## AsynczConfig

The [AsynczConfig](./config.md) is the main object that manages the internal scheduler of `Lilya` with asyncz expecting:

* `scheduler_class` - An instance of the `Asyncz` schedule type. Passed via `scheduler_class`.

    <sup>Default: `AsyncIOScheduler`</sup>

* `tasks` - A python dictionary of both key, value string mapping the tasks. Passed via
`scheduler_tasks`.

    <sup>Default: `{}`</sup>

* `timezone` - The `timezone` of the scheduler. Passed via `timezone`.

    <sup>Default: `UTC`</sup>

* `configurations` - A python dictionary containing some extra configurations for the scheduler.
Passed via `scheduler_configurations`.
* `kwargs` - Any keyword argument that can be passed and injected into the `scheduler_class`.

Since `Lilya` is an `ASGI` framework, it is already provided a default scheduler class that works alongside with
the application, the `AsyncIOScheduler`.

```python
from lilya.apps import Lilya
from lilya.contrib.schedulers.asyncz.config import AsynczConfig

scheduler_config = AsynczConfig()
app = Lilya(on_startup=[scheduler_config.start], on_shutdown=[scheduler_config.shutdown])
```

You can have your own scheduler config class as well, check the [SchedulerConfig](./config.md#how-to-use-it).
for more information.

!!! warning
    Anything else that does not work with `AsyncIO` is very likely also not to work with Lilya.

## AsynczConfig and the application

This is the default Lilya integration with Asyncz and the class can be accessed via:

```python
from lilya.contrib.schedulers.asyncz.config import AsynczConfig
```

Because this is an Lilya offer, you can always implement your own version if you don't like the way Lilya handles
the Asyncz default integration and adapt to your own needs. This is thanks to the [SchedulerConfig](./config.md#how-to-use-it)
from where AsynczConfig is derived.

## Tasks

Tasks are simple pieces of functionality that contains the logic needed to run on a specific time.
Lilya does not enforce any specific file name where the tasks should be, you can place them anywhere you want.

Once the tasks are created, you need to pass that same information to your Lilya instance.

!!! tip
    There are more details about [how to create tasks](./handler.md) in the next section.

```python title="accounts/tasks.py"
{!> ../../../docs_src/scheduler/tasks/example1.py !}
```

There are two tasks created, the `collect_market_data` and `send_newsletter` which are placed inside a
`accounts/tasks`.

Now it is time to tell the application to activate the scheduler and run the tasks based on the settings provided
into the `scheduler` handler.

```python hl_lines="6-10"
{!> ../../../docs_src/scheduler/tasks/app_scheduler.py !}
```

**Or from the settings file**:

```python hl_lines="6 10-14"
{!> ../../../docs_src/scheduler/tasks/from_settings.py !}
```

Start the server with the newly created settings.

=== "MacOS & Linux"

    ```shell
    LILYA_SETTINGS_MODULE=AppSettings palfrey src:app --reload

    INFO:     Listening on ('127.0.0.1', 8000) (Press CTRL+C to quit)
    INFO:     Started reloader process [28720]
    INFO:     Started server process [28722]
    INFO:     Waiting for application startup.
    INFO:     Application startup complete.
    ```

=== "Windows"

    ```shell
    $env:LILYA_SETTINGS_MODULE="AppSettings"; palfrey src:app --reload

    INFO:     Listening on ('127.0.0.1', 8000) (Press CTRL+C to quit)
    INFO:     Started reloader process [28720]
    INFO:     Started server process [28722]
    INFO:     Waiting for application startup.
    INFO:     Application startup complete.
    ```

The `scheduler_tasks` is expecting a python dictionary where the both key and value are strings.

* `key` - The name of the task.
* `value` - Where the task is located.
