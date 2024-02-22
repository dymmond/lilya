from lilya.apps import ChildLilya
from lilya.routing import Include, Path
from lilya.testclient import create_client


def home():
    return "Hello, from proxy"


def user(user: str):
    return f"Hello, {user}"


child_lilya = ChildLilya(
    routes=[Path("/home", handler=home)],
)


def test_can_load_from_proxy(test_client_factory):
    with create_client(
        routes=[
            Path("/{user}", user),
            Include("/child", app="tests.routing.test_proxy_load.child_lilya"),
        ]
    ) as client:
        response = client.get("/child/home")

        assert response.status_code == 200
        assert response.json() == "Hello, from proxy"

        response = client.get("/lilya")

        assert response.status_code == 200
        assert response.json() == "Hello, lilya"
