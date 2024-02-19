from lilya.app import ChildLilya
from lilya.requests import Request
from lilya.responses import JSONResponse
from lilya.routing import Path


async def create(request: Request) -> JSONResponse:
    data = await request.json()
    return JSONResponse({"created": True})


async def get_customer() -> JSONResponse:
    return JSONResponse({"created": True})


router = ChildLilya(
    routes=[
        Path("/{customer_id:int}", handler=get_customer),
        Path("/create", handler=create, methods=["POST"]),
    ],
    include_in_schema=...,
)
