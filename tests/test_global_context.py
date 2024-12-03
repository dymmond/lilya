import functools

from lilya.context import g
from lilya.routing import Path
from lilya.testclient import create_client


def activate_stuff():
    g.name = "Lilya"
    g.age = 25


async def show_g() -> dict[str, str]:
    return g.store


def test_global_context():
    activate_stuff()

    with create_client(routes=[Path("/show", show_g)]) as client:
        response = client.get("/show")
        assert response.status_code == 200
        assert response.json() == {"name": "Lilya", "age": 25}


def test_empty_global_context():
    with create_client(routes=[Path("/show", show_g)]) as client:
        response = client.get("/show")
        assert response.status_code == 200
        assert response.json() == {}


def user_check(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if not hasattr(g, "user"):
            g.user = "not logged in"
        return await func(*args, **kwargs)

    return wrapper


@user_check
async def get_data() -> str:
    return g.user


async def get_g() -> dict[str, str]:
    return g.store


def test_global_context_with_decorator():
    with create_client(
        routes=[
            Path("/data", get_data),
            Path("/show", get_g),
        ],
        debug=True,
    ) as client:
        response = client.get("/data")
        assert response.status_code == 200
        assert response.json() == "not logged in"

        response = client.get("/show")
        assert response.status_code == 200
        assert response.json() == {}
