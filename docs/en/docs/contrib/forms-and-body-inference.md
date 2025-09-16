# Forms and Body Inference

Lilya provides a powerful mechanism to parse request bodies that can seamlessly
handle **JSON payloads**, **URL-encoded forms**, **multipart forms** (including file
uploads), and **mixed cases** where form fields contain JSON-encoded strings.

This allows you to declare typed parameters in your handlers and let Lilya
take care of converting incoming requests into strongly typed Python objects.

## The `infer_body` flag

As you know, the body inference is activated via [settings](../settings.md) `infer_body=True`.

This will enable the following examples and explanations for your project.

---

## Basic Form Handling

You can receive form data directly by annotating parameters in your handler.

This is the basic of the basics and **works without the `infer_body`** flag enabled as this
is pretty much standard.

```python
from lilya.requests import Request
from lilya.routing import Path

async def submit_form(request: Request):
    form = await request.form()
    return dict(form)

routes = [Path("/submit", handler=submit_form, methods=["POST"])]
```

---

## Body Inference with Pydantic and Msgspec

When `infer_body` is enabled in your Lilya settings, Lilya will automatically
attempt to parse the request body into the types declared in your handler
signature.

!!! Note
    We use Pydantic and Msgspec as examples as they are used also as examples in the
    [encoders](../encoders.md) section. **You still need to create your encoders for this to work, anyway**

### Example: JSON vs Form

```python
from pydantic import BaseModel
from msgspec import Struct

class User(BaseModel):
    name: str
    age: int

class Item(Struct):
    sku: str

async def process(user: User, item: Item):
    return {"user": user.model_dump(), "item": {"sku": item.sku}}
```

### Sending JSON

```http
POST /process
Content-Type: application/json

{
  "user": {"name": "lilya", "age": 10},
  "item": {"sku": "abc"}
}
```

### Sending Form Data

```http
POST /process
Content-Type: application/x-www-form-urlencoded

user={"name": "lilya", "age": 10}&item={"sku": "abc"}
```

Both will result in the same handler parameters being populated.

---

## Nested Fields with Dotted Keys

Forms can’t natively encode nested structures. Lilya supports **dotted key**
notation to express them:

```http
POST /process
Content-Type: application/x-www-form-urlencoded

user.name=lilya&user.age=10&item.sku=abc
```

This expands automatically to:

```json
{
  "user": {"name": "lilya", "age": 10},
  "item": {"sku": "abc"}
}
```

Pretty cool, right?

---

## Lists with Bracket Notation

You can also use `[]` notation to represent lists in forms:

```http
POST /items
Content-Type: application/x-www-form-urlencoded

items[0].sku=test1&items[1].sku=test2
```

Expands to:

```json
{
  "items": [
    {"sku": "test1"},
    {"sku": "test2"}
  ]
}
```

When your handler signature expects `items: list[Item]`, Lilya will pass
a list of `Item` objects.

---

## Nested JSON Strings

Sometimes form fields themselves contain JSON strings. Lilya recursively parses these into objects:

```http
POST /items-meta
Content-Type: application/x-www-form-urlencoded

items[0].sku=test1&items[0].meta={"x": 1}
```

Expands to:

```json
{
  "items": [
    {"sku": "test1", "meta": {"x": 1}}
  ]
}
```

---

## File Uploads

Multipart forms with files are also supported. Simply annotate your handler
with `UploadFile`:

```python
from lilya.datastructures import DataUpload as UploadFile
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int

async def upload(user: User, files: list[UploadFile]):
    return {
        "user": user.model_dump(),
        "files": [f.filename for f in files]
    }
```

Client request:

```http
POST /upload
Content-Type: multipart/form-data

user={"name": "lilya", "age": 10}
files=@hello.txt
```

Result:

```json
{
  "user": {"name": "lilya", "age": 10},
  "files": ["hello.txt"]
}
```

## Notes

* **JSON payloads**: Parsed directly
* **Forms**: Converted to dicts and nested structures using dotted/bracket keys
* **Recursive JSON strings**: Parsed anywhere inside the body
* **File uploads**: Injected as `UploadFile` objects
* **Typed inference**: `list[Item]`, `dict[str, User]`, `tuple[Item, ...]`, etc. all supported

---

This makes Lilya’s body inference flexible enough to handle **real-world  form submissions** without sacrificing strong typing.
