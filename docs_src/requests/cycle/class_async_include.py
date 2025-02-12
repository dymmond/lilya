from lilya.apps import Lilya
from lilya.routing import Path, Include
from lilya.types import Scope, Receive, Send


class BeforePathRequest:
    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        # Add logging on entering the request
        ...

class AfterPathRequest:
    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        # Add logging on exiting the request
        ...

class BeforeIncludeRequest:
    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        # Add logging on entering the include
        ...

class AfterIncludeRequest:
    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        # Add logging on exiting the include
        ...


async def home() -> str:
    return "Hello, World!"


app = Lilya(
    routes=[
        Include("/",
            before_request=[BeforeIncludeRequest],
            after_request=[AfterIncludeRequest],
            routes=[
                Path("/", home,
                    before_request=[BeforePathRequest],
                    after_request=[AfterPathRequest],
                ),
            ]
        ),
    ]
)
