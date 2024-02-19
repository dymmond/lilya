from lilya.requests import Request
from lilya.responses import JSONResponse
from lilya.routing import Path, Router


async def create(request: Request):
    data = await request.json()
    return JSONResponse({"created": True})


async def get_customer(customer_id: int):
    return JSONResponse({"created": customer_id})


router = Router(
    path="/customers",
    routes=[
        Path(
            "/{customer_id:int}",
            handler=get_customer,
        ),
        Path(
            "/create",
            handler=create,
            methods=["POST"],
        ),
    ],
)
