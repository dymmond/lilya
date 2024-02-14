from json import loads

from lilya import status
from lilya.app import Lilya
from lilya.requests import Request
from lilya.responses import JSONResponse
from lilya.routing import Include, Path


async def handle_type_error(request: Request, exc: TypeError):
    status_code = status.HTTP_400_BAD_REQUEST
    details = loads(exc.json()) if hasattr(exc, "json") else exc.args[0]
    return JSONResponse({"detail": details}, status_code=status_code)


async def handle_value_error(request: Request, exc: ValueError):
    status_code = status.HTTP_400_BAD_REQUEST
    details = loads(exc.json()) if hasattr(exc, "json") else exc.args[0]
    return JSONResponse({"detail": details}, status_code=status_code)


async def me():
    return "Hello, world!"


app = Lilya(
    routes=[
        Include(
            "/",
            routes=[
                Path(
                    "/me",
                    handler=me,
                )
            ],
        )
    ],
    exception_handlers={
        TypeError: handle_type_error,
        ValueError: handle_value_error,
    },
)
