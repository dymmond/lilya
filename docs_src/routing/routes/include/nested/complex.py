from lilya.apps import Lilya
from lilya.routing import Include, Path


async def me() -> None: ...


app = Lilya(
    routes=[
        Include(
            "/",
            routes=[
                Include(
                    "/another",
                    routes=[
                        Include(
                            "/multi",
                            routes=[
                                Include(
                                    "/nested",
                                    routes=[
                                        Include(
                                            "/routing",
                                            routes=[
                                                Path(path="/me", handler=me),
                                                Include(
                                                    path="/imported",
                                                    namespace="myapp.routes",
                                                ),
                                            ],
                                        )
                                    ],
                                )
                            ],
                        )
                    ],
                )
            ],
        )
    ]
)
