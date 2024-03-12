# Permissions

Lilya incorporates an inherent permission system designed to facilitate the principle of
*separation of concerns*. Interestingly, this permission system closely resembles [middlewares](./middleware.md).

In essence, permissions in Lilya function as pure ASGI applications, akin to middlewares,
but are specifically tailored to manage access control within an application.

The rationale behind introducing another ASGI-like application, akin to middleware but for permissions,
lies in maintaining a clear and singular purpose for each component. Lilya ensures this distinction.

Permissions operate in the sequence **after the middleware** and **before reaching the handler**,
positioning them ideally for controlling access to the application.

## Using the permission

The Lilya application class provides a means to include the ASGI permission in a manner that
guarantees it remains encapsulated within the exception handler.

```python
{!> ../docs_src/permissions/sample.py !}
```

When defining a `permission`, it is imperative to utilize `lilya.permissions.DefinePermission` to encapsulate it.
Additionally, it is advisable to adhere to the `PermissionProtocol` from
`lilya.protocols.permissions.PermissionProtocol` as it provides an interface for the definition.

Lilya includes a default exception specifically for denying permissions. Typically, when denying a permission,
a status code `403` is raised along with a specific message. This functionality is encapsulated in
`lilya.exceptions.PermissionDenied`.

Furthermore, the details of the message can be customized as needed.

### PermissionProtocol

For those coming from a more enforced typed language like Java or C#, a protocol is the python equivalent to an
interface.

The `PermissionProtocol` is simply an interface to build permissions for **Lilya** by enforcing the implementation of
the `__init__` and the `async def __call__`.

Enforcing this protocol also aligns with writing a [Pure ASGI Permission](#pure-asgi-permission).

### Quick sample

```python
{!> ../docs_src/permissions/quick_sample.py !}
```

## Permission and the application

Creating this type of permissions will make sure the protocols are followed and therefore reducing development errors
by removing common mistakes.

To add middlewares to the application is very simple. You can add it at any level of the application.
Those can be included in the `Lilya`/`ChildLilya`, `Include`, `Path` and `WebSocketPath`.

=== "Application level"

    ```python
    {!> ../docs_src/permissions/adding_permission.py !}
    ```

=== "Any other level"

    ```python
    {!> ../docs_src/permissions/any_other_level.py !}
    ```

## Pure ASGI permission

Lilya follows the [ASGI spec](https://asgi.readthedocs.io/en/latest/).
This capability allows for the implementation of ASGI permissions using the
ASGI interface directly. This involves creating a chain of ASGI applications that call into the next one.

**Example of the most common approach**

```python
from lilya.types import ASGIApp, Scope, Receive, Send


class MyPermission:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        await self.app(scope, receive, send)
```

When implementing a Pure ASGI permission, it is like implementing an ASGI application, the first
parameter **should always be an app** and the `__call__` should **always return the app**.

## Permissions and the settings

One of the advantages of Lilya is leveraging the settings to make the codebase tidy, clean and easy to maintain.
As mentioned in the [settings](./settings.md) document, the permissions is one of the properties available
to use to start a Lilya application.

```python
{!> ../docs_src/permissions/settings.py !}
```
