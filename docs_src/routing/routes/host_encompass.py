from lilya.requests import Request
from lilya.routing import Host, Include, Path, Router


def user(): ...


def detail(username: str): ...


routes = [
    Host(
        "{subdomain}.example.com",
        name="sub",
        app=Router(
            routes=[
                Include(
                    "/users",
                    name="users",
                    routes=[
                        Path("/", user, name="user"),
                        Path("/{username}", detail, name="detail"),
                    ],
                )
            ]
        ),
    )
]

request = Request(...)

url = request.path_for("sub:users:user", username=..., subdomain=...)
url = request.path_for("sub:users:detail", subdomain=...)
