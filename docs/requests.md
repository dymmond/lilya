# Request

Lilya brings the `Request` class object. This object is a nice interface between the incoming
request and the ASGI scope.

This means, you don't need to access directly the scope and extract all the information required
for a `request` type of object.

```python
from lilya.requests import Request
```

## The `Request` class

A `Request` instance receives a `scope`, a `receive` and a `send` parameter.

```python
{!> ../docs_src/requests/example.py !}
```

The requests, as mentioned before, present an interface to the `scope`, which means if you use
`requests['app']` or `requests['headers']` or `requests['path']` it will retrieve the same information
as it was retrieving from the scope.

### Note

If there is not a need to access the request body, you can instantiate a request without
providing a `receive` argument.

**Example**

```python
from lilya.requests import Request

request = Request(scope)
```

### Attributes

There are many available attributes that you can access within the request.

#### Method

The request method that is used to access.

```python
from lilya.requests import Request

request = Request(scope)

request.method
```

#### URL

```python
from lilya.requests import Request

request = Request(scope)

request.url
```

This property exposes all the components that can be parsed out of the URL.

**Example**

```python
from lilya.requests import Request

request = Request(scope)

request.url.port
request.url.path
request.url.scheme
request.url.netloc
request.url.query
```

#### Header

Lilya uses the [multidict](https://multidict.aio-libs.org/en/stable/) for its headers and adds
some extra flavours on the top of it.

```python
from lilya.requests import Request

request = Request(scope)

request.headers['content-type']
```

#### Query Params

Lilya uses the [multidict](https://multidict.aio-libs.org/en/stable/) for its query parameters and adds
some extra flavours on the top of it.

```python
from lilya.requests import Request

request = Request(scope)

request.query_params['search']
```

#### Path Params

Extracted directly from the `scope` as a dictionary like python object

```python
from lilya.requests import Request

request = Request(scope)

request.path_params['username']
```

#### Client Address

The client's remote address is exposed as a dataclass `request.client`.

```python
from lilya.requests import Request

request = Request(scope)

request.client.host
request.client.port
```

#### Cookies

Extracted directly from the headers and parsed as a dictionary like python object.

```python
from lilya.requests import Request

request = Request(scope)

request.cookies.get('a-cookie')
```

#### Body

Now here it is different. To extract and use the `body`, a `receive` must be passed into the
request instance and it can be extracted in different ways.

##### As bytes

```python
from lilya.requests import Request

request = Request(scope, receive)

await request.body()
```

##### As JSON

```python
from lilya.requests import Request

request = Request(scope, receive)

await request.json()
```

##### As text

```python
from lilya.requests import Request

request = Request(scope, receive)

await request.text()
```

##### As form data or multipart form

```python
from lilya.requests import Request

request = Request(scope, receive)

async with request.form() as form:
    ...
```

##### As data

```python
from lilya.requests import Request

request = Request(scope, receive)

await request.data()
```

##### As a stream

```python
{!> ../docs_src/requests/stream.py !}
```

When employing .stream(), byte chunks are furnished without the necessity of storing the entire body in memory.
Subsequent calls to `.body()`, `.form()`, or `.json()` will result in an error.

In specific situations, such as long-polling or streaming responses, it becomes crucial
to determine whether the client has disconnected.

This status can be ascertained using the following:
`disconnected = await request.is_disconnected().`


##### Request files

Typically, files are transmitted as multipart form data (multipart/form-data).

```python
from lilya.requests import Request

request = Request(scope, receive)

request.form(max_files=1000, max_fields=1000)
```

You have the flexibility to set the maximum number of fields or files using the `max_files`
and `max_fields` parameters:

```python
async with request.form(max_files=1000, max_fields=1000):
    ...
```

!!! warning
    These limitations serve security purposes. Allowing an unlimited number of fields or files could
    pose a risk of a denial-of-service attack, consuming excessive CPU and memory
    resources by parsing numerous empty fields.

When invoking async with `request.form() as form`, you obtain a `lilya.datastructures.FormData`,
which is an immutable multidict containing both file uploads and text input.

File upload items are represented as instances of `lilya.datastructures.DataUpload`.

###### DataUpload

DataUpload has the following attributes:

* **filename**: A `str` with the original file name that was uploaded or `None` if its not available (e.g. `profile.png`).
* **file**: A `SpooledTemporaryFile` (a file-like object). This is the actual Python file that you can pass directly to other
functions or libraries that expect a "file-like" object.
* **headers**: A `Header` object. Often this will only be the `Content-Type` header, but if additional
headers were included in the multipart field they will be included here. Note that these headers have no relationship with the headers in `Request.headers`.
* **size**: An `int` with uploaded file's size in bytes. This value is calculated from request's contents, making it better choice to find uploaded file's size than `Content-Length` header. None if not set.


The `DataUpload` class provides several asynchronous methods that invoke the corresponding
file operations using the internal `SpooledTemporaryFile`:

* `async write(data)`: Writes the specified data (in bytes) to the file.
* `async read(size)`: Reads the specified number of bytes (as an integer) from the file.
* `async seek(offset)`: Positions the file cursor at the byte offset specified (as an integer). For example, using await `profile.seek(0)` would move the cursor to the beginning of the file.
* `async close()`: Closes the file.

Since all these methods are asynchronous, the `await` keyword is necessary when invoking them.

**Example**

```python
async with request.form() as form:
    filename = form["upload_file"].filename
    contents = await form["upload_file"].read()
```

#### Application

The Lilya application.

```python
from lilya.requests import Request

request = Request(scope)

request.app
```

#### State

If you wish to include supplementary information with the request, you can achieve this by using
the `request.state`.

```python
from lilya.requests import Request

request = Request(scope)

request.state.admin = "example@lilya.dev"
```
