import io
from typing import Any

from msgspec import Struct
from pydantic import BaseModel

from lilya.controllers import Controller
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


class Test(Controller):
    async def post(self, user: User, item: Item):
        return {**user.model_dump(), "sku": item.sku}


def test_infer_body(test_client_factory):
    data = {"user": {"name": "lilya", "age": 10}, "item": {"sku": "test"}}

    with create_client(
        routes=[Path("/infer", handler=Test, methods=["POST"])],
        settings_module=EncoderSettings,
    ) as client:
        response = client.post("/infer", json=data)

        assert response.status_code == 200
        assert response.json() == {"name": "lilya", "age": 10, "sku": "test"}


class TestWithDep(Controller):
    async def post(self, user: User, item: Item, x=Provides()):
        return {**user.model_dump(), "sku": item.sku, "x": x}


def test_infer_body_with_dependency(test_client_factory):
    data = {"user": {"name": "lilya", "age": 10}, "item": {"sku": "test"}}

    with create_client(
        routes=[Path("/infer", handler=TestWithDep, methods=["POST"])],
        dependencies={"x": Provide(lambda: "app_value")},
        settings_module=EncoderSettings,
    ) as client:
        response = client.post("/infer", json=data)

        assert response.status_code == 200
        assert response.json() == {"name": "lilya", "age": 10, "sku": "test", "x": "app_value"}


class TestOptDep(Controller):
    async def post(self, user: User, item: Item):
        return {**user.model_dump(), "sku": item.sku}


def test_infer_body_with_dependency_not_passed(test_client_factory):
    data = {"user": {"name": "lilya", "age": 10}, "item": {"sku": "test"}}

    with create_client(
        routes=[Path("/infer", handler=TestOptDep, methods=["POST"])],
        dependencies={"x": Provide(lambda: "app_value")},
        settings_module=EncoderSettings,
    ) as client:
        response = client.post("/infer", json=data)

        assert response.status_code == 200
        assert response.json() == {"name": "lilya", "age": 10, "sku": "test"}


class TestOptDepNP(Controller):
    async def post(self, user: User, item: Item, x: Any):
        return {**user.model_dump(), "sku": item.sku, "x": x}


def test_infer_body_with_dependency_without_provides(test_client_factory):
    data = {"user": {"name": "lilya", "age": 10}, "item": {"sku": "test"}}

    with create_client(
        routes=[Path("/infer", handler=TestOptDepNP, methods=["POST"])],
        dependencies={"x": Provide(lambda: "app_value")},
        settings_module=EncoderSettings,
    ) as client:
        response = client.post("/infer", json=data)

        assert response.status_code == 200
        assert response.json() == {"name": "lilya", "age": 10, "sku": "test", "x": "app_value"}


class FormController(Controller):
    async def post(self, user: User, item: Item):
        return {**user.model_dump(), "sku": item.sku}


def test_infer_body_from_form(test_client_factory):
    data = {"user": '{"name": "lilya", "age": 10}', "item": '{"sku": "test"}'}

    with create_client(
        routes=[Path("/infer-form", handler=FormController)],
        settings_module=EncoderSettings,
    ) as client:
        # send as form
        response = client.post("/infer-form", data=data)

        assert response.status_code == 200
        assert response.json() == {"name": "lilya", "age": 10, "sku": "test"}


class ProfileController(Controller):
    async def post(self, user: User, file: UploadFile):
        content = await file.read()
        return {
            "user": user.model_dump(),
            "filename": file.filename,
            "filesize": len(content),
        }


def test_infer_body_with_json_field_and_file(test_client_factory):
    with create_client(
        routes=[Path("/upload-json", handler=ProfileController, methods=["POST"])],
        settings_module=EncoderSettings,
    ) as client:
        response = client.post(
            "/upload-json",
            data={"user": '{"name":"lilya","age":10}'},
            files={"file": ("hello.txt", io.BytesIO(b"hello world"), "text/plain")},
        )

        assert response.status_code == 200
        assert response.json() == {
            "user": {"name": "lilya", "age": 10},
            "filename": "hello.txt",
            "filesize": 11,
        }


def test_infer_body_with_flat_form_and_file(test_client_factory):
    with create_client(
        routes=[Path("/upload-flat", handler=ProfileController, methods=["POST"])],
        settings_module=EncoderSettings,
    ) as client:
        response = client.post(
            "/upload-flat",
            data={"user.name": "lilya", "user.age": "10"},
            files={"file": ("hello.txt", io.BytesIO(b"hello world"), "text/plain")},
        )

        assert response.status_code == 200
        assert response.json() == {
            "user": {"name": "lilya", "age": 10},
            "filename": "hello.txt",
            "filesize": 11,
        }


class ProcessController(Controller):
    async def post(self, items: list[Item]):
        return [item.sku for item in items]


def test_infer_body_with_list_in_form(test_client_factory):
    with create_client(
        routes=[Path("/items", handler=ProcessController)],
        settings_module=EncoderSettings,
    ) as client:
        response = client.post(
            "/items",
            data={
                "items[0].sku": "test1",
                "items[1].sku": "test2",
            },
        )

        assert response.status_code == 200
        assert response.json() == ["test1", "test2"]
