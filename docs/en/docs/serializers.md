# Serializers

## What is the Lilya `SerializerConfig`

In building applications, serializing is one of the many crucial parts for optimizing responses of your data.

Originally, Lilya relied on developers manually configuring their own serializers systems. However, to provide a consistent,
extensible, and framework-integrated way to handle serializers, Lilya introduced a first-class serializer system built around
the `SerializerConfig` concept.

The goals of introducing `SerializerConfig` were:

- **Consistency**: Applications have a predictable and reliable way of setting up serializers.
- **Flexibility**: Support standard Python `json` (default) and any other.
- **Simplicity**: Only one central serializer (`lilya.serializers.serializer`) needs to be imported and used across the entire app.
- **Extensibility**: Developers can easily subclass and provide their own custom serializer configurations.

Lilya now automatically configures a global `serializer` instance, based on the `SerializerConfig` provided during startup.

## How `SerializerConfig` Works

`SerializerConfig` is an **abstract base class** that defines how to configure the serializer system.

Lilya provides:

- `StandardSerializerConfig` — for classic Python `serializing`.

You can also implement your own custom serializer backend by subclassing `SerializerConfig`.

When `setup_serializer(serializer_config)` is called during app startup (you don't have access to this as this is internal), Lilya:

1. Applies the provided `SerializerConfig`.
2. Binds the global `lilya.serializers.serializer` to the correct backend.

!!! Note
    After configuration, importing and using `from lilya.serializer import serializer` will always point to the correct
    serializer system automatically.

## Available Serializer Backends

### Standard Python Serializer

Default behavior if nothing is specified.

```python
from lilya.apps import Lilya

app = Lilya()
```

Or inside `Lilya` (with an example of a ORJSON serializer):

```python
{!> ../../../docs_src/serializer/example1.py!}
```

## Defining a Custom Serializer Configuration

You can easily define your own `SerializerConfig` by subclassing it:

```python
{!> ../../../docs_src/serializer/example2.py!}
```

When creating a custom serializer **you must** declare the following methods:

- `configure()` (optional) - This method is called to set up the serializer configuration.
- `get_serializer()` - This method should return the serializer library.

These methods are called during the application startup process and will make sure the serializer is set up correctly
using a common interface.

Usage:

```python
from lilya.apps import Lilya

app = Lilya(serializer_config=CustomSerializerConfig())
```

## Using `serializer_config` via `Settings`

If you are using settings classes to configure your app, you can pass the serializer configuration there too:

```python
{!> ../../../docs_src/serializer/settings.py!}
```

Then when initializing Lilya:

```python
from lilya.apps import Lilya

app = Lilya(settings_config=AppSettings())
```

!!! Tip
    You can also initialise Lilya settings via `LILYA_SETTINGS_MODULE` as you can see in [settings](./settings.md)
    documentation. This is useful for separating your settings from the application instance.

Lilya will automatically extract and configure the serializer from your settings class.

## Accessing the Global Serializer

Anywhere in your project, simply do:

```python
from lilya.serializers import serializer

serializer.dumps("This is a message.")
```

No matter what backend you use, the `serializer` will behave correctly.

## Important Notes

- If you need to **reconfigure the serializer** during runtime (e.g., in tests), you should explicitly teardown/reset first.
- If no `serializer_config` is provided, Lilya defaults to a safe `StandardSerializerConfig`.

## Conclusion

`SerializerConfig` provides a powerful, flexible, and unified way to configure serializers in Lilya applications.

It ensures that regardless of the serializer backend used, your app's serializer behavior is predictable, extensible, and simple to maintain.
