from pydantic import BaseModel

from lilya.controllers import Controller
from lilya.routing import Path
from lilya.testclient import create_client
from tests.encoders.settings import EncoderSettings


class User(BaseModel):
    name: str
    age: int


class Test(Controller):
    async def post(self, user: User):
        return user


def test_infer_body_error(test_client_factory):
    with create_client(
        routes=[Path("/infer", handler=Test, methods=["POST"])],
        settings_module=EncoderSettings,
    ) as client:
        response = client.post("/infer")

        assert response.status_code == 422
        assert "detail" in response.json()
