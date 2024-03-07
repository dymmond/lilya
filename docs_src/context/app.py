from lilya.context import Context
from lilya.responses import make_response


def home(context: Context):
    """
    Accessing the context object.
    """
    return make_response(content=None, status_code=204)
