import io
from typing import Any

from msgspec import Struct
from pydantic import BaseModel

from lilya.datastructures import DataUpload as UploadFile
from lilya.dependencies import Provide, Provides
from lilya.routing import Path
from lilya.testclient import create_client
from tests.encoders.settings import EncoderSettings


class User(BaseModel):
    name: str
    age: int


class Item(Struct):
    sku: str


async def process_body(user: User, item: Item):
    return {**user.model_dump(), "sku": item.sku}


def test_infer_body(test_client_factory):
    data = {"user": {"name": "lilya", "age": 10}, "item": {"sku": "test"}}

    with create_client(
        routes=[Path("/infer", handler=process_body, methods=["POST"])],
        settings_module=EncoderSettings,
    ) as client:
        response = client.post("/infer", json=data)

        assert response.status_code == 200
        assert response.json() == {"name": "lilya", "age": 10, "sku": "test"}


async def process_body_with_dependency(user: User, item: Item, x=Provides()):
    return {**user.model_dump(), "sku": item.sku, "x": x}


def test_infer_body_with_dependency(test_client_factory):
    data = {"user": {"name": "lilya", "age": 10}, "item": {"sku": "test"}}

    with create_client(
        routes=[Path("/infer", handler=process_body_with_dependency, methods=["POST"])],
        dependencies={"x": Provide(lambda: "app_value")},
        settings_module=EncoderSettings,
    ) as client:
        response = client.post("/infer", json=data)

        assert response.status_code == 200
        assert response.json() == {"name": "lilya", "age": 10, "sku": "test", "x": "app_value"}


async def process_body_with_dependency_not_passed(user: User, item: Item):
    return {**user.model_dump(), "sku": item.sku}


def test_infer_body_with_dependency_not_passed(test_client_factory):
    data = {"user": {"name": "lilya", "age": 10}, "item": {"sku": "test"}}

    with create_client(
        routes=[Path("/infer", handler=process_body_with_dependency_not_passed, methods=["POST"])],
        dependencies={"x": Provide(lambda: "app_value")},
        settings_module=EncoderSettings,
    ) as client:
        response = client.post("/infer", json=data)

        assert response.status_code == 200
        assert response.json() == {"name": "lilya", "age": 10, "sku": "test"}


async def process_body_with_dependency_without_provides(user: User, item: Item, x: Any):
    return {**user.model_dump(), "sku": item.sku, "x": x}


def test_infer_body_with_dependency_without_provides(test_client_factory):
    data = {"user": {"name": "lilya", "age": 10}, "item": {"sku": "test"}}

    with create_client(
        routes=[
            Path("/infer", handler=process_body_with_dependency_without_provides, methods=["POST"])
        ],
        dependencies={"x": Provide(lambda: "app_value")},
        settings_module=EncoderSettings,
    ) as client:
        response = client.post("/infer", json=data)

        assert response.status_code == 200
        assert response.json() == {"name": "lilya", "age": 10, "sku": "test", "x": "app_value"}


async def process_form(user: User, item: Item):
    return {**user.model_dump(), "sku": item.sku}


def test_infer_body_from_form(test_client_factory):
    data = {"user": '{"name": "lilya", "age": 10}', "item": '{"sku": "test"}'}

    with create_client(
        routes=[Path("/infer-form", handler=process_form, methods=["POST"])],
        settings_module=EncoderSettings,
    ) as client:
        # send as form
        response = client.post("/infer-form", data=data)

        assert response.status_code == 200
        assert response.json() == {"name": "lilya", "age": 10, "sku": "test"}


async def process_upload(user: User, file: UploadFile):
    content = await file.read()
    return {
        "user": user.model_dump(),
        "filename": file.filename,
        "filesize": len(content),
    }


def test_infer_body_with_file_upload(test_client_factory):
    with create_client(
        routes=[Path("/upload", handler=process_upload, methods=["POST"])],
        settings_module=EncoderSettings,
    ) as client:
        response = client.post(
            "/upload",
            data={"user": '{"name":"lilya","age":10}'},
            files={"file": ("hello.txt", io.BytesIO(b"hello world"), "text/plain")},
        )

        assert response.status_code == 200
        assert response.json() == {
            "user": {"name": "lilya", "age": 10},
            "filename": "hello.txt",
            "filesize": 11,
        }
