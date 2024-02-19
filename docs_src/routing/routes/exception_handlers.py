from lilya.app import Lilya
from lilya.exceptions import InternalServerError, LilyaException, NotAuthorized
from lilya.requests import Request
from lilya.responses import JSONResponse
from lilya.routing import Path


async def http_lilya_handler(_: Request, exc: LilyaException):
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


async def http_internal_server_error_handler(_: Request, exc: InternalServerError):
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


async def http_not_authorized_handler(_: Request, exc: NotAuthorized):
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


async def homepage() -> dict:
    return {"page": "ok"}


app = Lilya(
    routes=[
        Path(
            "/home",
            handler=homepage,
            exception_handlers={
                NotAuthorized: http_not_authorized_handler,
                InternalServerError: http_internal_server_error_handler,
            },
        )
    ],
    exception_handlers={LilyaException: http_lilya_handler},
)
