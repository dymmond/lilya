from __future__ import annotations

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
        assert response.json() == {
            "name": "lilya",
            "age": 10,
            "sku": "test",
            "x": "app_value",
        }


async def process_body_with_dependency_not_passed(user: User, item: Item):
    return {**user.model_dump(), "sku": item.sku}


def test_infer_body_with_dependency_not_passed(test_client_factory):
    data = {"user": {"name": "lilya", "age": 10}, "item": {"sku": "test"}}

    with create_client(
        routes=[
            Path(
                "/infer",
                handler=process_body_with_dependency_not_passed,
                methods=["POST"],
            )
        ],
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
            Path(
                "/infer",
                handler=process_body_with_dependency_without_provides,
                methods=["POST"],
            )
        ],
        dependencies={"x": Provide(lambda: "app_value")},
        settings_module=EncoderSettings,
    ) as client:
        response = client.post("/infer", json=data)

        assert response.status_code == 200
        assert response.json() == {
            "name": "lilya",
            "age": 10,
            "sku": "test",
            "x": "app_value",
        }


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


def test_infer_body_with_json_field_and_file(test_client_factory):
    with create_client(
        routes=[Path("/upload-json", handler=process_upload, methods=["POST"])],
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
        routes=[Path("/upload-flat", handler=process_upload, methods=["POST"])],
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


async def process_items(items: list[Item]):
    return [item.sku for item in items]


def test_infer_body_with_list_in_form(test_client_factory):
    with create_client(
        routes=[Path("/items", handler=process_items, methods=["POST"])],
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


async def process_list_items(items: list[Item]):
    return {
        "is_items_list": isinstance(items, list),
        "elem_types": [type(x).__name__ for x in items],
        "skus": [x.sku for x in items],
    }


def test_single_param_list_structuring_root_and_wrapped(test_client_factory):
    with create_client(
        routes=[Path("/items", handler=process_list_items, methods=["POST"])],
        settings_module=EncoderSettings,
    ) as client:
        response = client.post("/items", json=[{"sku": "a"}, {"sku": "b"}])

        assert response.status_code == 200
        assert response.json()["elem_types"] == ["Item", "Item"]
        assert response.json()["skus"] == ["a", "b"]

        response = client.post("/items", json={"items": [{"sku": "x"}, {"sku": "y"}]})

        assert response.status_code == 200
        assert response.json()["elem_types"] == ["Item", "Item"]
        assert response.json()["skus"] == ["x", "y"]


# Dict[str, Item]
async def process_map(items: dict[str, Item]):
    return {
        "keys": sorted(items.keys()),
        "types": [type(v).__name__ for v in items.values()],
        "skus": [v.sku for v in items.values()],
    }


def test_single_param_dict_of_items(test_client_factory):
    with create_client(
        routes=[Path("/map", handler=process_map, methods=["POST"])],
        settings_module=EncoderSettings,
    ) as client:
        response = client.post("/map", json={"a": {"sku": "A"}, "b": {"sku": "B"}})

        assert response.status_code == 200

        body = response.json()

        assert body["keys"] == ["a", "b"]
        assert body["types"] == ["Item", "Item"]
        assert body["skus"] == ["A", "B"]


# Tuple[Item, ...]
async def process_tuple(items: tuple[Item, ...]):
    return {
        "is_tuple": isinstance(items, tuple),
        "types": [type(v).__name__ for v in items],
        "skus": [v.sku for v in items],
    }


def test_single_param_var_tuple_of_items(test_client_factory):
    with create_client(
        routes=[Path("/tuple", handler=process_tuple, methods=["POST"])],
        settings_module=EncoderSettings,
    ) as client:
        response = client.post("/tuple", json=[{"sku": "t1"}, {"sku": "t2"}])

        assert response.status_code == 200

        body = response.json()

        assert body["is_tuple"] is True
        assert body["types"] == ["Item", "Item"]
        assert body["skus"] == ["t1", "t2"]


async def process_items_with_meta(items: list[dict[str, Any]]):
    return items


def test_infer_body_nested_json_strings_in_form(test_client_factory):
    with create_client(
        routes=[Path("/items-meta", handler=process_items_with_meta, methods=["POST"])],
        settings_module=EncoderSettings,
    ) as client:
        response = client.post(
            "/items-meta",
            data={
                "items[0].sku": "test1",
                "items[0].meta": '{"x": 1}',
                "items[1].sku": "test2",
                "items[1].meta": '{"x": 2}',
            },
        )

        assert response.status_code == 200
        assert response.json() == [
            {"sku": "test1", "meta": {"x": 1}},
            {"sku": "test2", "meta": {"x": 2}},
        ]
