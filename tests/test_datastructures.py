import io
from tempfile import SpooledTemporaryFile
from typing import BinaryIO, Type, Union

import pytest
from pytest_mock import MockerFixture

from lilya.datastructures import (
    URL,
    CommaSeparatedStr,
    FormData,
    FormMultiDict,
    Header,
    ImmutableMultiDict,
    MultiDict,
    QueryParam,
    Secret,
    UploadFile,
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


def test_comma_separated():
    csv = CommaSeparatedStr('"localhost", "127.0.0.1", 0.0.0.0')
    assert list(csv) == ["localhost", "127.0.0.1", "0.0.0.0"]
    assert repr(csv) == "CommaSeparatedStr(['localhost', '127.0.0.1', '0.0.0.0'])"
    assert str(csv) == "'localhost', '127.0.0.1', '0.0.0.0'"
    assert csv[0] == "localhost"
    assert len(csv) == 3

    csv = CommaSeparatedStr("'localhost', '127.0.0.1', 0.0.0.0")
    assert list(csv) == ["localhost", "127.0.0.1", "0.0.0.0"]
    assert repr(csv) == "CommaSeparatedStr(['localhost', '127.0.0.1', '0.0.0.0'])"
    assert str(csv) == "'localhost', '127.0.0.1', '0.0.0.0'"

    csv = CommaSeparatedStr("localhost, 127.0.0.1, 0.0.0.0")
    assert list(csv) == ["localhost", "127.0.0.1", "0.0.0.0"]
    assert repr(csv) == "CommaSeparatedStr(['localhost', '127.0.0.1', '0.0.0.0'])"
    assert str(csv) == "'localhost', '127.0.0.1', '0.0.0.0'"

    csv = CommaSeparatedStr(["localhost", "127.0.0.1", "0.0.0.0"])
    assert list(csv) == ["localhost", "127.0.0.1", "0.0.0.0"]
    assert repr(csv) == "CommaSeparatedStr(['localhost', '127.0.0.1', '0.0.0.0'])"
    assert str(csv) == "'localhost', '127.0.0.1', '0.0.0.0'"


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

    query = MultiDict([("a", "123"), ("a", "456"), ("b", "789")])
    item = query.popitem()
    assert query.get(item[0]) == "456"

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
    """Test passing file/stream into the UploadFile constructor"""
    stream = io.BytesIO(b"data")
    file = UploadFile(filename="file", file=stream, size=4)
    assert await file.read() == b"data"
    assert file.size == 4
    await file.write(b" and more data!")
    assert await file.read() == b""
    assert file.size == 19
    await file.seek(0)
    assert await file.read() == b"data and more data!"


@pytest.mark.anyio
async def test_upload_file_without_size():
    """Test passing file/stream into the UploadFile constructor without size"""
    stream = io.BytesIO(b"data")
    file = UploadFile(filename="file", file=stream)
    assert await file.read() == b"data"
    assert file.size is None
    await file.write(b" and more data!")
    assert await file.read() == b""
    assert file.size is None
    await file.seek(0)
    assert await file.read() == b"data and more data!"


@pytest.mark.anyio
@pytest.mark.parametrize("max_size", [1, 1024], ids=["rolled", "unrolled"])
async def test_uploadfile_rolling(max_size: int) -> None:
    """Test that we can r/w to a SpooledTemporaryFile
    managed by UploadFile before and after it rolls to disk
    """
    stream: BinaryIO = SpooledTemporaryFile(max_size=max_size)  # type: ignore[assignment]
    file = UploadFile(filename="file", file=stream, size=0)
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
    await file.close()


def xtest_formdata():
    stream = io.BytesIO(b"data")
    upload = UploadFile(filename="file", file=stream, size=4)
    form = FormData([("a", "123"), ("a", "456"), ("b", upload)])
    assert "a" in form
    assert "A" not in form
    assert "c" not in form
    assert form["a"] == "456"
    assert form.get("a") == "456"
    assert form.get("nope", default=None) is None
    assert form.getlist("a") == ["123", "456"]
    assert list(form.keys()) == ["a", "b"]
    assert list(form.values()) == ["456", upload]
    assert list(form.items()) == [("a", "456"), ("b", upload)]
    assert len(form) == 2
    assert list(form) == ["a", "b"]
    assert dict(form) == {"a": "456", "b": upload}
    assert repr(form) == "FormData([('a', '123'), ('a', '456'), ('b', " + repr(upload) + ")])"
    assert FormData(form) == form
    assert FormData({"a": "123", "b": "789"}) == FormData([("a", "123"), ("b", "789")])
    assert FormData({"a": "123", "b": "789"}) != {"a": "123", "b": "789"}


@pytest.mark.anyio
async def test_upload_file_repr():
    stream = io.BytesIO(b"data")
    file = UploadFile(filename="file", file=stream, size=4)
    assert repr(file) == "UploadFile(filename='file', size=4, headers=Header({}))"


@pytest.mark.anyio
async def test_upload_file_repr_headers():
    stream = io.BytesIO(b"data")
    file = UploadFile(filename="file", file=stream, headers=Header({"foo": "bar"}))
    assert repr(file) == "UploadFile(filename='file', size=None, headers=Header({'foo': 'bar'}))"


@pytest.mark.parametrize("multi_dict", [MultiDict, ImmutableMultiDict, Header, QueryParam])
def test_multi_to_dict(multi_dict: Type[Union[MultiDict, ImmutableMultiDict]]) -> None:
    multi = multi_dict([("a", "a"), ("a", "a2"), ("b", "b")])

    assert multi.dict() == {"a": ["a", "a2"], "b": ["b"]}


@pytest.mark.parametrize("multi_dict", [MultiDict, ImmutableMultiDict, Header, QueryParam])
def test_multi_items(multi_dict: Type[Union[MultiDict, ImmutableMultiDict]]) -> None:
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
    close = mocker.patch("lilya.datastructures.UploadFile.close")
    stream = io.BytesIO(b"data")

    multi_dict = FormMultiDict(
        [
            ("file", UploadFile(filename="file", file=stream)),
            ("another-file", UploadFile(filename="another-file", file=stream)),
        ]
    )

    await multi_dict.close()
    assert close.call_count == 2
