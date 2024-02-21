# WebSocket

Lilya provides a `WebSocket` class that serves a comparable function to an HTTP request but facilitates the exchange
of data over a WebSocket, enabling both sending and receiving operations.

### WebSocket

```python
{!> ../docs_src/websockets/websocket.py !}
```

WebSockets present a mapping interface, so you can use them in the same
way as a `scope`.

For instance: `websocket['path']` will return the ASGI path.

#### URL

The websocket URL is accessed as `websocket.url`.

Accessing the WebSocket URL is accomplished using `websocket.url`. This property, a subclass of `str`,
not only represents the URL itself but also exposes all the individual components that can be extracted from the URL.

```python
from lilya.websockets import WebSocket

websocket = WebSocket(scope, receive, send)

websocket.url.scheme
websocket.url.path
websocket.url.port
```

#### Header

Lilya uses the [multidict](https://multidict.aio-libs.org/en/stable/) for its headers and adds
some extra flavours on the top of it.

```python
from lilya.websockets import WebSocket

websocket = WebSocket(scope, receive, send)

websocket.headers['sec-websocket-version']
```

#### Query Params

Lilya uses the [multidict](https://multidict.aio-libs.org/en/stable/) for its query parameters and adds
some extra flavours on the top of it.

```python
from lilya.websockets import WebSocket

websocket = WebSocket(scope, receive, send)

websocket.query_params['search']
```

#### Path Params

Extracted directly from the `scope` as a dictionary like python object

```python
from lilya.websockets import WebSocket

websocket = WebSocket(scope, receive, send)

websocket.path_params['username']
```

### Operations

#### Accepting connection

* `await websocket.accept(subprotocol=None, headers=None)`

#### Sending data

* `await websocket.send_text(data)`
* `await websocket.send_bytes(data)`
* `await websocket.send_json(data)`

JSON messages are sent by default using text data frames.
To send JSON over binary data frames, utilize `websocket.send_json(data, mode="binary")`.

#### Receiving data

* `await websocket.receive_text()`
* `await websocket.receive_bytes()`
* `await websocket.receive_json()`

!!! warning
    It's important to note that the operation may raise `lilya.websockets.WebSocketDisconnect()`.

JSON messages are automatically received over text data frames by default.
To receive JSON over binary data frames, employ `websocket.receive_json(data, mode="binary")`.

#### Iterating data

* `websocket.iter_text()`
* `websocket.iter_bytes()`
* `websocket.iter_json()`

Much like `receive_text`, `receive_bytes`, and `receive_json`, this function returns an asynchronous iterator.

```python
{!> ../docs_src/websockets/example.py !}
```

Upon the occurrence of `lilya.websockets.WebSocketDisconnect`, the iterator will terminate.

#### Closing the connection

* `await websocket.close(code=1000, reason=None)`

#### Sending and receiving messages

In cases where sending or receiving raw ASGI messages is required, it is advisable to utilize
`websocket.send()` and `websocket.receive()` instead of directly employing the raw `send` and `receive` callables.
This approach ensures proper upkeep of the WebSocket's internal state.

* `await websocket.send(message)`
* `await websocket.receive()`

#### Send Denial Response

Should `websocket.close()` be invoked prior to `websocket.accept()`, the server will automatically
dispatch an HTTP 403 error to the client.

For customized error responses, the `websocket.send_denial_response()` method can be employed.
This method facilitates the transmission of the specified response before closing the connection.

* `await websocket.send_denial_response(response)`

!!! warning
    This functionality relies on the ASGI server supporting the WebSocket Denial Response extension.
    In the absence of support, attempting to use it will result in a `RuntimeError` being raised.
