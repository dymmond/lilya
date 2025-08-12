# SchedulerConfig

The SchedulerConfig is simply an interface that allows you to integrate any scheduler into Lilya in a cleaner way.

!!! Warning
    If you want to run your own implementation and integration with different schedulers, please feel free to jump this
    section and ignore all of this.

This is possible due to the fact that Lilya implements the **SchedulerConfig**.

## How to import it

You can import the configuration from the following:

```python
from lilya.contrib.schedulers.config import SchedulerConfig
```

## The SchedulerConfig class

When implementing a scheduler configurations **you must implement** two functions.

1. [async def start()](#the-start-function)
2. [async def shutdown()](#the-shutdown-function)

This is what makes the `SchedulerConfig` modular because there are plenty of schedulers out there and each one of them
with a lot of different options and configurations but the one thing they all have in common is the fact that all
of them must start and shutdown at some point. The only thing Lilya "cares" is that by encapsulating that functionality
into two simple functions.

### The start function

The start function, as the name suggests, its the function that Lilya calls to start the scheduler for you. These are
usually passed into the `on_startup` or in the upper part of the `lifespan` above the `yield`.

### The shutdown function

The shutdown function, as the name suggests, its the function that Lilya calls to shutdown the scheduler for you. These are
usually passed into the `on_shutdowb` or in the lower part of the `lifespan` below the `yield`.

### How to use it

Lilya already implements this interface with the custom `AsynczConfig`. This functionality is very handy since Asyncz
has a lot of configurations that can be passed and used within an Lilya application.

Let us see how the implementation looks like.

```python
{!> ../../../docs_src/scheduler/asyncz.py !}
```

We won't be dueling on the technicalities of this configuration because its unique to Asyncz provided by Lilya but
**it is not mandatory to use it as you can build your own**.

### SchedulerConfig and application

To use the `SchedulerConfig` in an application, like the one [shown above with asyncz](#how-to-use-it), you can simply do this:

!!! Note
    We use the existing AsynczConfig as example but feel free to use your own if you require something else.

```python
{!> ../../../docs_src/scheduler/example.py !}
```

### Application lifecycle

Lilya scheduler is tight to the application lifecycle and that means the `on_startup/on_shutdown` and `lifespan`.
You can [read more about this](../../lifespan.md) in the appropriate section of the documentation.

By default, the scheduler is linked to `on_startup/on_shutdown` events.

The following example serves as a suggestion but feel free to use your own design. Let us check how we could manage
this using the `lifespan` instead.

```python
{!> ../../../docs_src/scheduler/example2.py !}
```

Pretty easy, right? Lilya then understands what needs to be done as normal.

### The SchedulerConfig and the settings

Like everything in Lilya, the SchedulerConfig can be also made available via settings.

```python
{!> ../../../docs_src/scheduler/via_settings.py !}
```

## Important Notes

- You can create your own [custom scheduler config](#how-to-use-it).
- You **must implement** the `start/shutdown` functions in any scheduler configuration.
- You can use or `on_startup/shutdown` or `lifespan` events. The first is automatically managed for you.

[asyncz]: https://asyncz.dymmond.com
