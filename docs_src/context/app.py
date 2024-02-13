from lilya.context import Context
from lilya.requests import Request
from lilya.responses import make_response
from lilya.routing import BasePath
from lilya.types import Scope


def home(context: Context):
    """
    Accessing the context object.
    """
    request: Request = context.request
    scope: Scope = context.scope
    handler: BasePath = context.handler
    return make_response(content=None, status_code=204)
