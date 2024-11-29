import os
import stat
import tempfile
import time
from pathlib import Path

import anyio
import pytest

from lilya.apps import Lilya
from lilya.exceptions import HTTPException

# from lilya.middleware.base import BaseHTTPMiddleware
from lilya.routing import Include

# from lilya.middleware import DefineMiddleware
# from lilya.requests import Request
from lilya.staticfiles import StaticFiles


@pytest.mark.parametrize(
    "wrapper", [lambda x: x, lambda x: [x], lambda x: (x,)], ids=["direct", "list", "tuple"]
)
def test_staticfiles(tmpdir, test_client_factory, wrapper):
    path = os.path.join(tmpdir, "example.txt")
    with open(path, "w") as file:
        file.write("<file content>")

    app = StaticFiles(directory=wrapper(tmpdir))
    client = test_client_factory(app)
    response = client.get("/example.txt")
    assert response.status_code == 200
    assert response.text == "<file content>"


@pytest.mark.parametrize(
    "wrapper", [lambda x: x, lambda x: [x], lambda x: (x,)], ids=["direct", "list", "tuple"]
)
def test_staticfiles_with_pathlib(tmp_path: Path, test_client_factory, wrapper):
    path = tmp_path / "example.txt"
    with open(path, "w") as file:
        file.write("<file content>")

    app = StaticFiles(directory=wrapper(tmp_path))
    client = test_client_factory(app)
    response = client.get("/example.txt")
    assert response.status_code == 200
    assert response.text == "<file content>"


def test_staticfiles_with_package(test_client_factory):
    app = StaticFiles(packages=["tests"])
    client = test_client_factory(app)
    response = client.get("/example.txt")
    assert response.status_code == 200
    assert response.text == "123\n"

    app = StaticFiles(packages=[("tests", "statics")])
    client = test_client_factory(app)
    response = client.get("/example.txt")
    assert response.status_code == 200
    assert response.text == "123\n"


def test_staticfiles_post(tmpdir, test_client_factory):
    path = os.path.join(tmpdir, "example.txt")
    with open(path, "w") as file:
        file.write("<file content>")

    routes = [Include("/", app=StaticFiles(directory=tmpdir), name="static")]
    app = Lilya(routes=routes)
    client = test_client_factory(app)

    response = client.post("/example.txt")
    assert response.status_code == 405
    assert response.text == "Method Not Allowed"


def test_staticfiles_with_directory_returns_404(tmpdir, test_client_factory):
    path = os.path.join(tmpdir, "example.txt")
    with open(path, "w") as file:
        file.write("<file content>")

    routes = [Include("/", app=StaticFiles(directory=tmpdir), name="static")]
    app = Lilya(routes=routes)
    client = test_client_factory(app)

    response = client.get("/")
    assert response.status_code == 404
    assert response.text == "Not Found"


def test_staticfiles_with_missing_file_returns_404(tmpdir, test_client_factory):
    path = os.path.join(tmpdir, "example.txt")
    with open(path, "w") as file:
        file.write("<file content>")

    routes = [Include("/", app=StaticFiles(directory=tmpdir), name="static")]
    app = Lilya(routes=routes)
    client = test_client_factory(app)

    response = client.get("/404.txt")
    assert response.status_code == 404
    assert response.text == "Not Found"


def test_staticfiles_instantiated_with_missing_directory(tmpdir):
    with pytest.raises(RuntimeError) as exc_info:
        path = os.path.join(tmpdir, "no_such_directory")
        StaticFiles(directory=path)
    assert "does not exist" in str(exc_info.value)


def test_staticfiles_configured_with_missing_directory(tmpdir, test_client_factory):
    path = os.path.join(tmpdir, "no_such_directory")
    app = StaticFiles(directory=path, check_dir=False)
    client = test_client_factory(app)
    with pytest.raises(RuntimeError) as exc_info:
        client.get("/example.txt")
    assert "does not exist" in str(exc_info.value)


def test_staticfiles_configured_with_file_instead_of_directory(tmpdir, test_client_factory):
    path = os.path.join(tmpdir, "example.txt")
    with open(path, "w") as file:
        file.write("<file content>")

    app = StaticFiles(directory=path, check_dir=False)
    client = test_client_factory(app)
    with pytest.raises(RuntimeError) as exc_info:
        client.get("/example.txt")
    assert "is not a directory" in str(exc_info.value)


def test_staticfiles_config_check_occurs_only_once(tmpdir, test_client_factory):
    app = StaticFiles(directory=tmpdir)
    client = test_client_factory(app)
    assert not app.config_checked

    with pytest.raises(HTTPException):
        client.get("/")

    assert app.config_checked

    with pytest.raises(HTTPException):
        client.get("/")


def test_staticfiles_prevents_breaking_out_of_directory(tmpdir):
    directory = os.path.join(tmpdir, "foo")
    os.mkdir(directory)

    path = os.path.join(tmpdir, "example.txt")
    with open(path, "w") as file:
        file.write("outside root dir")

    app = StaticFiles(directory=directory)
    # We can't test this with 'httpx', so we test the app directly here.
    path = app.get_path({"path": "/../example.txt"})
    scope = {"method": "GET"}

    with pytest.raises(HTTPException) as exc_info:
        anyio.run(app.get_response, path, scope)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Not Found"


def test_staticfiles_never_read_file_for_head_method(tmpdir, test_client_factory):
    path = os.path.join(tmpdir, "example.txt")
    with open(path, "w") as file:
        file.write("<file content>")

    app = StaticFiles(directory=tmpdir)
    client = test_client_factory(app)
    response = client.head("/example.txt")
    assert response.status_code == 200
    assert response.content == b""
    assert response.headers["content-length"] == "14"


def test_staticfiles_304_with_etag_match(tmpdir, test_client_factory):
    path = os.path.join(tmpdir, "example.txt")
    with open(path, "w") as file:
        file.write("<file content>")

    app = StaticFiles(directory=tmpdir)
    client = test_client_factory(app)
    first_resp = client.get("/example.txt")
    assert first_resp.status_code == 200
    last_etag = first_resp.headers["etag"]
    second_resp = client.get("/example.txt", headers={"if-none-match": last_etag})
    assert second_resp.status_code == 304
    assert second_resp.content == b""
    second_resp = client.get("/example.txt", headers={"if-none-match": f'W/{last_etag}, "123"'})
    assert second_resp.status_code == 304
    assert second_resp.content == b""


def test_staticfiles_304_with_last_modified_compare_last_req(tmpdir, test_client_factory):
    path = os.path.join(tmpdir, "example.txt")
    file_last_modified_time = time.mktime(
        time.strptime("2013-10-10 23:40:00", "%Y-%m-%d %H:%M:%S")
    )
    with open(path, "w") as file:
        file.write("<file content>")
    os.utime(path, (file_last_modified_time, file_last_modified_time))

    app = StaticFiles(directory=tmpdir)
    client = test_client_factory(app)
    # last modified less than last request, 304
    response = client.get(
        "/example.txt", headers={"If-Modified-Since": "Thu, 11 Oct 2013 15:30:19 GMT"}
    )
    assert response.status_code == 304
    assert response.content == b""
    # last modified greater than last request, 200 with content
    response = client.get(
        "/example.txt", headers={"If-Modified-Since": "Thu, 20 Feb 2012 15:30:19 GMT"}
    )
    assert response.status_code == 200
    assert response.content == b"<file content>"


def test_staticfiles_html_normal(tmpdir, test_client_factory):
    path = os.path.join(tmpdir, "404.html")
    with open(path, "w") as file:
        file.write("<h1>Custom not found page</h1>")
    path = os.path.join(tmpdir, "dir")
    os.mkdir(path)
    path = os.path.join(path, "index.html")
    with open(path, "w") as file:
        file.write("<h1>Hello</h1>")

    app = StaticFiles(directory=tmpdir, html=True)
    client = test_client_factory(app)

    response = client.get("/dir/")
    assert response.url == "http://testserver/dir/"
    assert response.status_code == 200
    assert response.text == "<h1>Hello</h1>"

    response = client.get("/dir")
    assert response.url == "http://testserver/dir/"
    assert response.status_code == 200
    assert response.text == "<h1>Hello</h1>"

    response = client.get("/dir/index.html")
    assert response.url == "http://testserver/dir/index.html"
    assert response.status_code == 200
    assert response.text == "<h1>Hello</h1>"

    response = client.get("/missing")
    assert response.status_code == 404
    assert response.text == "<h1>Custom not found page</h1>"


def test_staticfiles_html_without_index(tmpdir, test_client_factory):
    path = os.path.join(tmpdir, "404.html")
    with open(path, "w") as file:
        file.write("<h1>Custom not found page</h1>")
    path = os.path.join(tmpdir, "dir")
    os.mkdir(path)

    app = StaticFiles(directory=tmpdir, html=True)
    client = test_client_factory(app)

    response = client.get("/dir/")
    assert response.url == "http://testserver/dir/"
    assert response.status_code == 404
    assert response.text == "<h1>Custom not found page</h1>"

    response = client.get("/dir")
    assert response.url == "http://testserver/dir"
    assert response.status_code == 404
    assert response.text == "<h1>Custom not found page</h1>"

    response = client.get("/missing")
    assert response.status_code == 404
    assert response.text == "<h1>Custom not found page</h1>"


def test_staticfiles_html_without_404(tmpdir, test_client_factory):
    path = os.path.join(tmpdir, "dir")
    os.mkdir(path)
    path = os.path.join(path, "index.html")
    with open(path, "w") as file:
        file.write("<h1>Hello</h1>")

    app = StaticFiles(directory=tmpdir, html=True)
    client = test_client_factory(app)

    response = client.get("/dir/")
    assert response.url == "http://testserver/dir/"
    assert response.status_code == 200
    assert response.text == "<h1>Hello</h1>"

    response = client.get("/dir")
    assert response.url == "http://testserver/dir/"
    assert response.status_code == 200
    assert response.text == "<h1>Hello</h1>"

    with pytest.raises(HTTPException) as exc_info:
        response = client.get("/missing")
    assert exc_info.value.status_code == 404


def test_staticfiles_html_only_files(tmpdir, test_client_factory):
    path = os.path.join(tmpdir, "hello.html")
    with open(path, "w") as file:
        file.write("<h1>Hello</h1>")

    app = StaticFiles(directory=tmpdir, html=True)
    client = test_client_factory(app)

    with pytest.raises(HTTPException) as exc_info:
        response = client.get("/")
    assert exc_info.value.status_code == 404

    response = client.get("/hello.html")
    assert response.status_code == 200
    assert response.text == "<h1>Hello</h1>"


def test_staticfiles_cache_invalidation_for_deleted_file_html_mode(tmpdir, test_client_factory):
    path_404 = os.path.join(tmpdir, "404.html")
    with open(path_404, "w") as file:
        file.write("<p>404 file</p>")
    path_some = os.path.join(tmpdir, "some.html")
    with open(path_some, "w") as file:
        file.write("<p>some file</p>")

    common_modified_time = time.mktime(time.strptime("2013-10-10 23:40:00", "%Y-%m-%d %H:%M:%S"))
    os.utime(path_404, (common_modified_time, common_modified_time))
    os.utime(path_some, (common_modified_time, common_modified_time))

    app = StaticFiles(directory=tmpdir, html=True)
    client = test_client_factory(app)

    resp_exists = client.get("/some.html")
    assert resp_exists.status_code == 200
    assert resp_exists.text == "<p>some file</p>"

    resp_cached = client.get(
        "/some.html",
        headers={"If-Modified-Since": resp_exists.headers["last-modified"]},
    )
    assert resp_cached.status_code == 304

    os.remove(path_some)

    resp_deleted = client.get(
        "/some.html",
        headers={"If-Modified-Since": resp_exists.headers["last-modified"]},
    )
    assert resp_deleted.status_code == 404
    assert resp_deleted.text == "<p>404 file</p>"


def test_staticfiles_with_invalid_dir_permissions_returns_401(tmp_path, test_client_factory):
    (tmp_path / "example.txt").write_bytes(b"<file content>")

    original_mode = tmp_path.stat().st_mode
    tmp_path.chmod(stat.S_IRWXO)
    try:
        routes = [
            Include(
                "/",
                app=StaticFiles(directory=os.fsdecode(tmp_path)),
                name="static",
            )
        ]
        app = Lilya(routes=routes)
        client = test_client_factory(app)

        response = client.get("/example.txt")
        assert response.status_code == 401
        assert response.text == "Unauthorized"
    finally:
        tmp_path.chmod(original_mode)


def test_staticfiles_with_missing_dir_returns_404(tmpdir, test_client_factory):
    path = os.path.join(tmpdir, "example.txt")
    with open(path, "w") as file:
        file.write("<file content>")

    routes = [Include("/", app=StaticFiles(directory=tmpdir), name="static")]
    app = Lilya(routes=routes)
    client = test_client_factory(app)

    response = client.get("/foo/example.txt")
    assert response.status_code == 404
    assert response.text == "Not Found"


def test_staticfiles_access_file_as_dir_returns_404(tmpdir, test_client_factory):
    path = os.path.join(tmpdir, "example.txt")
    with open(path, "w") as file:
        file.write("<file content>")

    routes = [Include("/", app=StaticFiles(directory=tmpdir), name="static")]
    app = Lilya(routes=routes)
    client = test_client_factory(app)

    response = client.get("/example.txt/foo")
    assert response.status_code == 404
    assert response.text == "Not Found"


def test_staticfiles_unhandled_os_error_returns_500(tmpdir, test_client_factory, monkeypatch):
    def mock_timeout(*args, **kwargs):
        raise TimeoutError

    path = os.path.join(tmpdir, "example.txt")
    with open(path, "w") as file:
        file.write("<file content>")

    routes = [Include("/", app=StaticFiles(directory=tmpdir), name="static")]
    app = Lilya(routes=routes)
    client = test_client_factory(app, raise_server_exceptions=False)

    monkeypatch.setattr("lilya.staticfiles.StaticFiles.lookup_path", mock_timeout)

    response = client.get("/example.txt")
    assert response.status_code == 500
    assert response.text == "Internal Server Error"


def test_staticfiles_follows_symlinks(tmpdir, test_client_factory):
    statics_path = os.path.join(tmpdir, "statics")
    os.mkdir(statics_path)

    source_path = tempfile.mkdtemp()
    source_file_path = os.path.join(source_path, "page.html")
    with open(source_file_path, "w") as file:
        file.write("<h1>Hello</h1>")

    statics_file_path = os.path.join(statics_path, "index.html")
    os.symlink(source_file_path, statics_file_path)

    app = StaticFiles(directory=statics_path, follow_symlink=True)
    client = test_client_factory(app)

    response = client.get("/index.html")
    assert response.url == "http://testserver/index.html"
    assert response.status_code == 200
    assert response.text == "<h1>Hello</h1>"


def test_staticfiles_follows_symlink_directories(tmpdir, test_client_factory):
    statics_path = os.path.join(tmpdir, "statics")
    statics_html_path = os.path.join(statics_path, "html")
    os.mkdir(statics_path)

    source_path = tempfile.mkdtemp()
    source_file_path = os.path.join(source_path, "page.html")
    with open(source_file_path, "w") as file:
        file.write("<h1>Hello</h1>")

    os.symlink(source_path, statics_html_path)

    app = StaticFiles(directory=statics_path, follow_symlink=True)
    client = test_client_factory(app)

    response = client.get("/html/page.html")
    assert response.url == "http://testserver/html/page.html"
    assert response.status_code == 200
    assert response.text == "<h1>Hello</h1>"


def test_staticfiles_disallows_path_traversal_with_symlinks(tmpdir):
    statics_path = os.path.join(tmpdir, "statics")

    root_source_path = tempfile.mkdtemp()
    source_path = os.path.join(root_source_path, "statics")
    os.mkdir(source_path)

    source_file_path = os.path.join(root_source_path, "index.html")
    with open(source_file_path, "w") as file:
        file.write("<h1>Hello</h1>")

    os.symlink(source_path, statics_path)

    app = StaticFiles(directory=statics_path, follow_symlink=True)
    # We can't test this with 'httpx', so we test the app directly here.
    path = app.get_path({"path": "/../index.html"})
    scope = {"method": "GET"}

    with pytest.raises(HTTPException) as exc_info:
        anyio.run(app.get_response, path, scope)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Not Found"


def test_staticfiles_avoids_path_traversal(tmp_path: Path):
    statics_path = tmp_path / "static"
    statics_disallow_path = tmp_path / "static_disallow"

    statics_path.mkdir()
    statics_disallow_path.mkdir()

    static_index_file = statics_path / "index.html"
    statics_disallow_path_index_file = statics_disallow_path / "index.html"
    static_file = tmp_path / "static1.txt"

    static_index_file.write_text("<h1>Hello</h1>")
    statics_disallow_path_index_file.write_text("<h1>Private</h1>")
    static_file.write_text("Private")

    app = StaticFiles(directory=statics_path)

    # We can't test this with 'httpx', so we test the app directly here.
    path = app.get_path({"path": "/../static1.txt"})
    with pytest.raises(HTTPException) as exc_info:
        anyio.run(app.get_response, path, {"method": "GET"})

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Not Found"

    path = app.get_path({"path": "/../static_disallow/index.html"})
    with pytest.raises(HTTPException) as exc_info:
        anyio.run(app.get_response, path, {"method": "GET"})

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Not Found"
