from pydantic import BaseModel

from lilya.routing import Path
from lilya.testclient import create_client
from tests.encoders.settings import EncoderSettings


class Message(BaseModel):
    id: int
    content: str


class Notification(BaseModel):
    channel: str
    message: Message


async def process_body(message: Notification):
    return message.model_dump()


def test_infer_body_does_not_extract_values(test_client_factory):
    data = {
        "channel": "email",
        "message": {"id": 1, "content": "Hello, World!"},
    }

    with create_client(
        routes=[Path("/infer", handler=process_body, methods=["POST"])],
        settings_module=EncoderSettings,
    ) as client:
        response = client.post("/infer", json=data)

        assert response.status_code == 200
        assert response.json() == {
            "channel": "email",
            "message": {"id": 1, "content": "Hello, World!"},
        }


async def process_multiple_body(message: Notification, channel: Notification):
    return {"message": message.model_dump(), "channel": channel.model_dump()}


def test_with_multiple_body_params(test_client_factory):
    data = {
        "message": {
            "channel": "email",
            "message": {"id": 1, "content": "Hello, World!"},
        },
        "channel": {
            "channel": "sms",
            "message": {"id": 2, "content": "Hi there!"},
        },
    }

    with create_client(
        routes=[Path("/infer", handler=process_multiple_body, methods=["POST"])],
        settings_module=EncoderSettings,
    ) as client:
        response = client.post("/infer", json=data)

        assert response.status_code == 200
        assert response.json() == {
            "message": {"channel": "email", "message": {"id": 1, "content": "Hello, World!"}},
            "channel": {"channel": "sms", "message": {"id": 2, "content": "Hi there!"}},
        }
