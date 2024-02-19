from esmerald import Lilya, Path, Request, get


@get()
async def homepage(request: Request) -> str:
    return "Hello, home!"


app = Lilya(routes=[Path(handler=homepage)])
