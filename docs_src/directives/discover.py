from lilya.app import Lilya
from lilya.requests import Request
from lilya.responses import JSONResponse
from lilya.routing import Path


async def show_name(name: str):
    return JSONResponse({"name": name})


async def create_or_update_item(request: Request, name: str):
    data = await request.json()
    # Does something with PUT or POST
    ...


def get_application():
    app = Lilya(
        routes=[
            Path("/{name}", handler=show_name),
            Path(path="/item/create", handler=create_or_update_item),
        ],
    )

    return app


app = get_application()
