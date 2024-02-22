from lilya.apps import Lilya
from lilya.routing import Include, Path


async def me() -> None: ...


app = Lilya(
    routes=[
        Include(
            "/",
            routes=[
                Path(
                    path="/me",
                    handler=me,
                )
            ],
        )
    ]
)
