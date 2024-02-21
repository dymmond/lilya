from lilya.apps import Lilya
from lilya.exceptions import HTTPException
from lilya.requests import Request
from lilya.responses import Error


async def not_found(request: Request, exc: HTTPException):
    return Error("Oops", status_code=exc.status_code)


async def server_error(request: Request, exc: HTTPException):
    return Error("Oops", status_code=exc.status_code)


app = Lilya(
    routes=...,
    exception_handlers={
        404: not_found,
        500: server_error,
    },
)
