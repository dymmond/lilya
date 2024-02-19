from lilya.app import Lilya
from lilya.requests import Request
from lilya.responses import JSONResponse
from lilya.routing import Path


def update(request: Request):
    item_id = request.path_params["item_id"]
    return JSONResponse({"Success", {item_id}})


app = Lilya(
    routes=[
        Path(
            "/update/{item_id:int}",
            handler=update,
            methods=["PUT"],
        ),
    ]
)
