from lilya.apps import Lilya
from lilya.routing import Path
from lilya.types import Scope, Receive, Send


class BeforePathRequest:
    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        # Add logging on entering the request
        ...

class AfterPathRequest:
    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        # Add logging on exiting the request
        ...


async def home() -> str:
    return "Hello, World!"


app = Lilya(
    routes=[
        Path("/", home,
            before_request=[BeforePathRequest],
            after_request=[AfterPathRequest],
        ),
    ]
)
