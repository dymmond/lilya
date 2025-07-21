from __future__ import annotations

import io

import anyio
import pytest
from pytest_mock import MockerFixture

from lilya.datastructures import (
    URL,
    DataUpload,
    FormData,
    FormMultiDict,
    Header,
    ImmutableMultiDict,
    MultiDict,
    QueryParam,
    Secret,
)


def test_url_structure():
    url = URL("https://example.org:123/path/to/somewhere?abc=123#anchor")
    assert url.scheme == "https"
    assert url.hostname == "example.org"
    assert url.port == 123
    assert url.netloc == "example.org:123"
    assert url.username is None
    assert url.password is None
    assert url.path == "/path/to/somewhere"
    assert url.query == "abc=123"
    assert url.fragment == "anchor"

    new = url.replace(scheme="http")
    assert new == "http://example.org:123/path/to/somewhere?abc=123#anchor"
    assert new.scheme == "http"

    new = url.replace(port=None)
    assert new == "https://example.org/path/to/somewhere?abc=123#anchor"
    assert new.port is None

    new = url.replace(hostname="example.com")
    assert new == "https://example.com:123/path/to/somewhere?abc=123#anchor"
    assert new.hostname == "example.com"

    ipv6_url = URL("https://[fe::2]:12345")
    new = ipv6_url.replace(port=8080)
    assert new == "https://[fe::2]:8080"

    new = ipv6_url.replace(username="username", password="password")
    assert new == "https://username:password@[fe::2]:12345"
    assert new.netloc == "username:password@[fe::2]:12345"

    ipv6_url = URL("https://[fe::2]")
    new = ipv6_url.replace(port=123)
    assert new == "https://[fe::2]:123"

    url = URL("http://u:p@host/")
    assert url.replace(hostname="bar") == URL("http://u:p@bar/")

    url = URL("http://u:p@host:80")
    assert url.replace(port=88) == URL("http://u:p@host:88")


def test_url_query_params():
    url = URL("https://example.org/path/?page=3")
    assert url.query == "page=3"

    url = url.include_query_params(page=4)
    assert str(url) == "https://example.org/path/?page=4"

    url = url.include_query_params(search="testing")
    assert str(url) == "https://example.org/path/?page=4&search=testing"

    url = url.replace_query_params(order="name")
    assert str(url) == "https://example.org/path/?order=name"

    url = url.remove_query_params("order")
    assert str(url) == "https://example.org/path/"


def test_hidden_password():
    url = URL("https://example.org/path/to/somewhere")
    assert repr(url) == "URL('https://example.org/path/to/somewhere')"

    url = URL("https://username@example.org/path/to/somewhere")
    assert repr(url) == "URL('https://username@example.org/path/to/somewhere')"

    url = URL("https://username:password@example.org/path/to/somewhere")
    assert repr(url) == "URL('https://username:***********@example.org/path/to/somewhere')"


def test_secret():
    value = Secret("a-value-being-passed")

    assert repr(value) == "Secret('***********')"
    assert str(value) == "a-value-being-passed"


def test_relative_url():
    u = URL("https://lilya.dev/path/to/something")
    assert u.relative_url() == URL("/path/to/something")

    u = URL("https://username:password@lilya.dev/path/to/something?abc=123")
    assert u.relative_url() == URL("/path/to/something?abc=123")

    u = URL("https://[fe::2]:12345/path/to/something?abc=123#anchor")
    assert u.relative_url() == URL("/path/to/something?abc=123#anchor")


def test_multidict():
    query = MultiDict([("a", "123"), ("a", "456"), ("b", "789")])
    assert "a" in query
    assert "A" not in query
    assert "c" not in query
    assert query["a"] == "123"
    assert "456" in query.getall("a")
    assert query.getall("a") == ["123", "456"]
    assert list(query.keys()) == ["a", "a", "b"]
    assert list(query.values()) == ["123", "456", "789"]
    assert list(query.items()) == [("a", "123"), ("a", "456"), ("b", "789")]
    assert len(query) == 3
    assert list(query) == ["a", "a", "b"]
    assert dict(query) == {"a": "123", "b": "789"}
    assert str(query) == "MultiDict([('a', '123'), ('a', '456'), ('b', '789')])"
    assert repr(query) == "MultiDict([('a', '123'), ('a', '456'), ('b', '789')])"
    assert MultiDict({"a": "123", "b": "456"}) == MultiDict([("a", "123"), ("b", "456")])
    assert MultiDict({"a": "123", "b": "456"}) == MultiDict({"b": "456", "a": "123"})
    assert MultiDict() == MultiDict({})
    assert MultiDict({"a": "123", "b": "456"}) != "invalid"

    query = MultiDict([("a", "123"), ("a", "456")])
    assert MultiDict(query) == query

    query = MultiDict([("a", "123"), ("a", "456")])
    query["a"] = "789"
    assert query["a"] == "789"
    assert query.get("a") == "789"
    assert query.getlist("a") == ["789"]

    query = MultiDict([("a", "123"), ("a", "456")])
    del query["a"]
    assert query.get("a") is None
    assert repr(query) == "MultiDict([])"

    query = MultiDict([("a", "123"), ("a", "456"), ("b", "789")])
    assert query.pop("a") == "123"
    assert query.get("a", None) == "456"
    assert repr(query) == "MultiDict([('a', '456'), ('b', '789')])"

    query = MultiDict([("a", "123"), ("a", "456")])
    # MultiDict.popitem removes an arbitary item and makes no gurantees about the order
    # see: https://multidict.aio-libs.org/en/stable/multidict/#multidict.MultiDict.popitem
    item = query.popitem()
    assert query.get(item[0]) is not None

    query = MultiDict([("a", "123"), ("a", "456"), ("b", "789")])
    assert query.poplist("a") == ["123", "456"]
    assert query.get("a") == "456"
    assert repr(query) == "MultiDict([('a', '456'), ('b', '789')])"

    query = MultiDict([("a", "123"), ("a", "456"), ("b", "789")])
    query.clear()
    assert query.get("a") is None
    assert repr(query) == "MultiDict([])"

    query = MultiDict([("a", "123")])
    assert query.setdefault("a", "456") == "123"
    assert query.getlist("a") == ["123"]
    assert query.setdefault("b", "456") == "456"
    assert query.getlist("b") == ["456"]
    assert repr(query) == "MultiDict([('a', '123'), ('b', '456')])"

    query = MultiDict([("a", "123")])
    query.add("a", "456")
    assert query.getlist("a") == ["123", "456"]
    assert repr(query) == "MultiDict([('a', '123'), ('a', '456')])"

    query = MultiDict([("a", "123"), ("b", "456")])
    query.update({"a": "789"})
    assert query.getlist("a") == ["789"]
    assert query == MultiDict([("a", "789"), ("b", "456")])

    query = MultiDict([("a", "123"), ("b", "456")])
    query.update(query)
    assert repr(query) == "MultiDict([('a', '123'), ('b', '456')])"

    query = MultiDict([("a", "123"), ("a", "456")])
    query.update([("a", "123")])
    assert query.getlist("a") == ["123"]
    query.update([("a", "456")], a="789", b="123")
    assert query == MultiDict([("a", "456"), ("a", "789"), ("b", "123")])


def test_url_blank_params():
    query = QueryParam("a=123&abc&def&b=456")
    assert "a" in query
    assert "abc" in query
    assert "def" in query
    assert "b" in query
    val = query.get("abc")
    assert val is not None
    assert len(val) == 0
    assert len(query["a"]) == 3
    assert list(query.keys()) == ["a", "abc", "def", "b"]


def test_queryparams():
    query = QueryParam("a=123&a=456&b=789")
    assert "a" in query
    assert "A" not in query
    assert "c" not in query
    assert query["a"] == "123"
    assert query.get("a") == "123"
    assert query.getall("a") == ["123", "456"]
    assert list(query.keys()) == ["a", "a", "b"]
    assert list(query.values()) == ["123", "456", "789"]
    assert list(query.items()) == [("a", "123"), ("a", "456"), ("b", "789")]
    assert len(query) == 3
    assert list(query) == ["a", "a", "b"]
    assert query.dump() == {"a": "456", "b": "789"}
    assert str(query) == "a=123&a=456&b=789"
    assert repr(query) == "QueryParam('a=123&a=456&b=789')"
    assert QueryParam({"a": "123", "b": "456"}) == QueryParam([("a", "123"), ("b", "456")])
    assert QueryParam({"a": "123", "b": "456"}) == QueryParam("a=123&b=456")
    assert QueryParam({"a": "123", "b": "456"}) == QueryParam({"b": "456", "a": "123"})
    assert QueryParam() == QueryParam({})

    assert QueryParam([("a", "123"), ("a", "456")]) == QueryParam("a=123&a=456")
    assert QueryParam({"a": "123", "b": "456"}) != "invalid"

    query = QueryParam([("a", "123"), ("a", "456")])
    assert QueryParam(query) == query


@pytest.mark.anyio
async def test_upload_file_file_input():
    """Test passing file/stream into the DataUpload constructor"""
    async with anyio.SpooledTemporaryFile(max_size=1024 * 1024) as stream:
        await stream.write(b"data")
        await stream.seek(0)

        file = DataUpload(filename="file", file=stream, size=4)
        try:
            assert await file.read() == b"data"
            assert file.size == 4
            await file.write(b" and more data!")
            assert await file.read() == b""
            assert file.size == 19
            await file.seek(0)
            assert await file.read() == b"data and more data!"
        finally:
            await file.close()


@pytest.mark.anyio
async def test_upload_file_without_size():
    """Test passing file/stream into the DataUpload constructor without size"""
    async with anyio.SpooledTemporaryFile(max_size=1024 * 1024) as stream:
        await stream.write(b"data")
        await stream.seek(0)

        file = DataUpload(filename="file", file=stream)
        try:
            assert await file.read() == b"data"
            assert file.size is None
            await file.write(b" and more data!")
            assert await file.read() == b""
            assert file.size is None
            await file.seek(0)
            assert await file.read() == b"data and more data!"
        finally:
            await file.close()


@pytest.mark.anyio
@pytest.mark.parametrize("max_size", [1, 1024], ids=["rolled", "unrolled"])
async def test_uploadfile_rolling(max_size: int) -> None:
    """Test that we can r/w to a SpooledTemporaryFile
    managed by DataUpload before and after it rolls to disk
    """
    async with anyio.SpooledTemporaryFile(max_size=max_size) as stream:
        file = DataUpload(filename="file", file=stream, size=0)
        try:
            assert await file.read() == b""
            assert file.size == 0
            await file.write(b"data")
            assert await file.read() == b""
            assert file.size == 4
            await file.seek(0)
            assert await file.read() == b"data"
            await file.write(b" more")
            assert await file.read() == b""
            assert file.size == 9
            await file.seek(0)
            assert await file.read() == b"data more"
            assert file.size == 9
        finally:
            await file.close()


@pytest.mark.anyio
async def test_formdata():
    async with anyio.SpooledTemporaryFile(max_size=1024) as stream:
        await stream.write(b"data")
        await stream.seek(0)

        upload = DataUpload(filename="file", file=stream, size=4)

        form = FormData([("a", "123"), ("a", "456"), ("b", upload)])

        assert "a" in form
        assert "A" not in form
        assert "c" not in form
        assert form["a"] == "123"
        assert form.get("a") == "123"
        assert form.get("nope", default=None) is None


@pytest.mark.anyio
async def test_upload_file_repr():
    async with anyio.SpooledTemporaryFile(max_size=1024 * 1024) as stream:
        await stream.write(b"data")
        await stream.seek(0)

        file = DataUpload(filename="file", file=stream, size=4)
        try:
            assert repr(file) == "DataUpload(filename='file', size=4, headers=Header({}))"
        finally:
            await file.close()


def test_header_in():
    # required for uvicorn
    multi = Header([(b"content-length", b"6"), (b"Connection", b"close")])
    assert "ConnecTion" in multi
    assert b"ConnecTion" in multi
    assert (b"Connection", b"close") in multi
    assert (b"ConnecTion", b"close") in multi
    assert (b"foo", b"close") not in multi


@pytest.mark.anyio
async def test_upload_file_repr_headers():
    async with anyio.SpooledTemporaryFile(max_size=1024 * 1024) as stream:
        await stream.write(b"data")
        await stream.seek(0)

        file = DataUpload(filename="file", file=stream, headers=Header({"foo": "bar"}))
        try:
            assert (
                repr(file)
                == "DataUpload(filename='file', size=None, headers=Header({'foo': 'bar'}))"
            )
        finally:
            await file.close()


@pytest.mark.parametrize("multi_dict", [MultiDict, ImmutableMultiDict, Header, QueryParam])
def test_multi_to_dict(multi_dict: type[MultiDict | ImmutableMultiDict]) -> None:
    multi = multi_dict([("a", "a"), ("a", "a2"), ("b", "b")])

    assert multi.dict() == {"a": ["a", "a2"], "b": ["b"]}


@pytest.mark.parametrize("multi_dict", [MultiDict, ImmutableMultiDict, Header, QueryParam])
def test_multi_items(multi_dict: type[MultiDict | ImmutableMultiDict]) -> None:
    data = [("a", "a"), ("a", "a2"), ("b", "b")]
    multi = multi_dict(data)

    assert sorted(multi.multi_items()) == sorted(data)


@pytest.mark.parametrize("multi_dict", [MultiDict, Header])
def test_to_immutable(multi_dict) -> None:
    data = [("a", "a"), ("a", "a2"), ("b", "b")]
    multi = multi_dict[str](data)
    assert multi.to_immutable().dict() == ImmutableMultiDict(data).dict()


def test_to_immutable_multi_dict_as_mutable() -> None:
    data = [("a", "a"), ("a", "a2"), ("b", "b")]
    multi = ImmutableMultiDict[str](data)
    assert multi.mutablecopy().dict() == MultiDict(data).dict()


@pytest.mark.anyio
async def test_form_multi_close(mocker: MockerFixture) -> None:
    close = mocker.patch("lilya.datastructures.DataUpload.close")
    stream = io.BytesIO(b"data")

    multi_dict = FormMultiDict(
        [
            ("file", DataUpload(filename="file", file=stream)),
            ("another-file", DataUpload(filename="another-file", file=stream)),
        ]
    )

    await multi_dict.close()
    assert close.call_count == 2
