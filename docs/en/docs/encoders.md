# Encoders

Encoders are basically converters between datastructures and json. Its main use is in response were different return values are automatically
parsed into json objects.

For understanding what they are doing, it is helpful to see the manual usage

## Manual usage

Encoders provide two public methods:

- json_encode
- apply_structure

### json_encode

`json_encode` is basically an enhanced json.dumps. It provides via the encoders converters which parse additional
types to json.
By default only a simplification is done, therefore the json string is deserialized again so a simple datastructure is returned.

``` python
from lilya.encoders import json_encode

json_string = json_encode({"hello": "world"}, post_transform_fn=None)
# or
json_string = json_encode({"hello": "world"}, post_transform_fn=lambda x: x)

```

### apply_structure

`apply_structure` is basically the inverse of `json_encode`.
It assumes it is known from which structure a value was serlialized.
If one encoder matches via `is_type_structure` (for Encoder by default `isclass(structure) and issubclass(structure, self.__type__)`) the encoder is used.
First is checked via `is_type` if the value is already converted and if yes simply returned.
Otherwise the value is molded via the structure in an instance and returned.

``` python
{!> ../../../docs_src/encoders/molding.py !}
```

## Default Encoders

In order to understand how to serialize a specific object into `json`, Lilya has some default
encoders that evaluates when tries to *guess* the response type.

* `DataclassEncoder` - Serialises `dataclass` objects.
* `NamedTupleEncoder` - Serialises `NamedTuple` objects.
* `ModelDumpEncoder` - Serialises objects by calling its model_dump method. This allows serializing pydantic objects out of the box.
* `EnumEncoder` - Serialises `Enum` objects.
* `PurePathEncoder` - Serializes `PurePath` objects.
* `DateEncoder` - Serializes date and datetime objects.
* `StructureEncoder` - Serializes more complex data types. `set, frozenset, GeneratorType, tuple, deque`.

What a brand new encoder is needed and it is not natively supported by Lilya? Well, [building a custom encoder](#build-a-custom-encoder)
is extremly easy and possible.

## Build a custom encoder

As mentioned before, Lilya has [default encoders](#default-encoders) that are used to transform a response
into a `json` serialisable response.

To build a custom encoder you must implement the `EncoderProtocol`. You can use the `Encoder` helper class from Lilya for that and override the `serialize()` function
where it applies the serialisation process of the encoder type.
If the encoder should also be able to deserialize a value in an provided object, you need additionally the method:
`encode` and maybe the method `is_type_structure` (you can use the `MoldingProtocol` for type checks).

Then you **must register the encoder** for Lilya to use it.

When defining an encoder the `def is_type(self, value: Any) -> bool:` or (Encoder helper class only)`__type__`
**must be declared or overridden**.

When in an Encoder subclass the `__type__` is properly declared, the default `is_type` and `is_type_structure` will evaluate the object against the
type and return `True` or `False`. `__type__` can be a single type or a tuple of types.

This is used internally to understand the type of encoder that will be applied to a given object.

!!! Warning
    If you are not able to provide the `__type__` for any reason and you just want to override the
    default evaluation process, simple use EncoderProtocol, override the `is_type()` and apply your custom logic there.

    E.g.: In Python 3.8, for a Pydantic `BaseModel` if passed in the `__type__`, it will throw an
    error due to Pydantic internals, so to workaround this issue, you can simply override the `is_type()`
    and apply the logic that validates the type of the object and returns a boolean.

```python
from lilya.encoders import Encoder, register_encoder
```

**Example**

Create and register an encoder that handles `msgspec.Struct` types.

```python
{!> ../../../docs_src/responses/encoders/msgspec.py !}
```

Simple right? Because now the `MsgSpecEncoder` is registered, you can simply do this in your handlers
and return **directly** the `msgspec.Struct` object type.

```python
from msgspec import Struct

from lilya.routing import Path


class User(Struct):
    name: str
    email: str


def msgspec_struct():
    return User(name="lilya", url="example@lilya.dev")
```

### Design specific custom encoders

**Lilya being 100% pure python and not tight to any particular validation library** allows you to
design custom encoders that are later used by Lilya responses.

Ok, this sounds a bit confusing right? I bet it does so let us go slowly.

Imagine you want to use a particular validation library such as [Pydantic](https://pydantic.dev/),
[msgspec](https://jcristharif.com/msgspec/) or even [attrs](https://www.attrs.org/en/stable/) or something
else at your choice.

You want to make sure that if you return a pydantic model or a msgspec Struct or even a `define` attr class.

Let us see how it would look like for all of them.

**For pydantic**

Nothing required anymore. Works out of the box thanks to the ModelDumpEncoder. But we can do an instance check instead:

```python
{!> ../../../docs_src/encoders/pydantic.py !}
```


**For msgspec Struct**

```python
{!> ../../../docs_src/encoders/example.py !}
```

**For attrs**

```python
{!> ../../../docs_src/encoders/attrs.py !}
```

Easy and poweful, right? Yes.

Do you understand what does this mean? Means you can design **any encoder** at your choice using
also any library of your choice as well.

The flexibility of Lilya allows you to be free and for Lilya not to be tight to any particular
library.

#### Custom encoders and responses

After the [custom encoders in the examples](#build-a-custom-encoder) are created, this allows to
do something like this directly.

```python
{!> ../../../docs_src/encoders/responses.py !}
```

#### Custom encoders and the `make_response`

Well, here its where the `make_response` helps you. The `make_response` will generate a `JSONResponse`
by default and when you return a custom encoder type, there are some limitations to it.

For example, what if you want to return with a different `status_code`? Or even attach a [task](./tasks.md)
to it?

The custom encoder **does not handle** that for you but the `make_response` does!

Let us see how it would look like now using the `make_response`.

```python
{!> ../../../docs_src/encoders/make_response.py !}
```
