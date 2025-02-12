from lilya.apps import Lilya
from lilya.routing import Path, Include
from lilya.types import Scope, Receive, Send


class BeforePathRequest:
    def __call__(self, scope: Scope, receive: Receive, send: Send):
        # Add logging on entering the request
        ...

class AfterPathRequest:
    def __call__(self, scope: Scope, receive: Receive, send: Send):
        # Add logging on exiting the request
        ...

class BeforeIncludeRequest:
    def __call__(self, scope: Scope, receive: Receive, send: Send):
        # Add logging on entering the include
        ...

class AfterIncludeRequest:
    def __call__(self, scope: Scope, receive: Receive, send: Send):
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
