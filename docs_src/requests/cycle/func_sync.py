from lilya.apps import Lilya
from lilya.routing import Path
from lilya.types import Scope, Receive, Send

def before_path_request(scope: Scope, receive: Receive, send: Send):
    # Add logging on entering the request
    ...

def after_path_request(scope: Scope, receive: Receive, send: Send):
    # Add logging on exiting the request
    ...


async def home() -> str:
    return "Hello, World!"


app = Lilya(
    routes=[
        Path("/", home,
            before_request=[before_path_request],
            after_request=[after_path_request],
        ),
    ]
)
