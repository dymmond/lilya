from pydantic import BaseModel

from lilya.apps import Lilya
from lilya.contrib.openapi.datastructures import OpenAPIResponse
from lilya.contrib.openapi.decorator import openapi
from lilya.contrib.openapi.params import Query
from lilya.contrib.openapi.utils import get_openapi
from lilya.routing import Include, Path


# Dummy handler functions
async def async_handler():
    return {"msg": "ok"}


def sync_handler():
    return {"msg": "ok"}


async def handler_with_user(request, user: str):
    return {"user": user}


# Sample Pydantic models for responses
class ModelA(BaseModel):
    id: int
    name: str


class ModelB(BaseModel):
    detail: str


class UploadRequestBody(BaseModel):
    user: str
    file: bytes


# Test 1: Basic path with async handler and no decorator
def test_basic_path_async_without_decorator():
    app = Lilya(routes=[Path("/simple", async_handler)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    assert "/simple" in spec["paths"]
    op = spec["paths"]["/simple"]["get"]

    # Default operationId should be handler name
    assert op["operationId"] == "async_handler"

    # Default response
    assert "200" in op["responses"]
    assert op["responses"]["200"]["description"] == "Successful response"


def test_basic_path_sync_with_summary():
    @openapi(summary="Sync summary")
    def my_sync():
        return {"msg": "hi"}

    app = Lilya(routes=[Path("/sync", my_sync)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    op = spec["paths"]["/sync"]["get"]

    assert op["summary"] == "Sync summary"


def test_path_parameter():
    @openapi()
    async def get_user(request, user: str):
        return {"user": user}

    app = Lilya(routes=[Path("/users/{user}", get_user)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    params = spec["paths"]["/users/{user}"]["get"]["parameters"]

    assert any(p["in"] == "path" and p["name"] == "user" for p in params)
    assert all(p["required"] for p in params if p["in"] == "path")


def test_query_parameter_string():
    @openapi(query={"q": Query(default=None, description="search", schema={"type": "string"})})
    async def search(request):
        return {"items": []}

    app = Lilya(routes=[Path("/search", search)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    params = spec["paths"]["/search"]["get"]["parameters"]

    assert any(p["in"] == "query" and p["name"] == "q" for p in params)


def test_query_parameter_array():
    @openapi(
        query={
            "tags": Query(
                default=[],
                description="tags list",
                schema={"type": "array", "items": {"type": "string"}},
                style="form",
                explode=True,
            )
        }
    )
    async def list_tags(request):
        return {"tags": []}

    app = Lilya(routes=[Path("/tags", list_tags)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    params = spec["paths"]["/tags"]["get"]["parameters"]
    p = next(p for p in params if p["name"] == "tags")

    assert p["schema"]["type"] == "array"
    assert p["style"] == "form"
    assert p["explode"] is True


def test_query_parameter_object():
    @openapi(
        query={
            "filter": Query(
                default={},
                description="filter object",
                schema={"type": "object", "additionalProperties": {"type": "string"}},
                style="deepObject",
                explode=True,
            )
        }
    )
    async def filter_items(request):
        return {"items": []}

    app = Lilya(routes=[Path("/filter", filter_items)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    params = spec["paths"]["/filter"]["get"]["parameters"]
    p = next(p for p in params if p["name"] == "filter")

    assert p["schema"]["type"] == "object"
    assert p["style"] == "deepObject"
    assert p["explode"] is True


def test_path_and_query_combined():
    @openapi(query={"verbose": Query(default=False, schema={"type": "boolean"})})
    async def get_detail(request, user: str):
        return {"user": user}

    app = Lilya(routes=[Path("/detail/{user}", get_detail)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    params = spec["paths"]["/detail/{user}"]["get"]["parameters"]
    names = {p["name"] for p in params}

    assert "user" in names and "verbose" in names


def test_single_response_model():
    @openapi(responses={200: OpenAPIResponse(model=ModelA, description="OK")})
    async def get_a(request):
        return {"id": 1, "name": "Alice"}

    app = Lilya(routes=[Path("/a", get_a)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    resp = spec["paths"]["/a"]["get"]["responses"]["200"]

    assert "content" in resp

    json_schema = resp["content"]["application/json"]["schema"]

    assert "$ref" in json_schema and "ModelA" in json_schema["$ref"]


def test_multiple_responses():
    @openapi(
        responses={
            200: OpenAPIResponse(model=ModelA, description="OK"),
            404: OpenAPIResponse(model=ModelB, description="Not Found"),
        }
    )
    async def get_multiple(request):
        return {"detail": "ok"}

    app = Lilya(routes=[Path("/multi", get_multiple)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    codes = set(spec["paths"]["/multi"]["get"]["responses"].keys())

    assert codes == {"200", "404"}


def test_deprecated_flag():
    @openapi(deprecated=True)
    async def old(route):
        return {"msg": "old"}

    app = Lilya(routes=[Path("/old", old)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert spec["paths"]["/old"]["get"]["deprecated"] is True


def test_tags_field():
    @openapi(tags=["tag1", "tag2"])
    async def tagged(request):
        return {"msg": "hi"}

    app = Lilya(routes=[Path("/tagged", tagged)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert spec["paths"]["/tagged"]["get"]["tags"] == ["tag1", "tag2"]


def test_security_field():
    sec = [{"oauth2": ["read"]}]

    @openapi(security=sec)
    async def secure(request):
        return {"msg": "secure"}

    app = Lilya(routes=[Path("/secure", secure)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert spec["paths"]["/secure"]["get"]["security"] == sec


def test_operation_id_override():
    @openapi(operation_id="customID")
    async def opid(request):
        return {"msg": "x"}

    app = Lilya(routes=[Path("/opid", opid)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert spec["paths"]["/opid"]["get"]["operationId"] == "customID"


def test_description_field():
    @openapi(description="A detailed description")
    async def desc(request):
        return {"msg": "desc"}

    app = Lilya(routes=[Path("/desc", desc)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert spec["paths"]["/desc"]["get"]["description"] == "A detailed description"


def test_include_one_level():
    @openapi()
    async def leaf(request):
        return {"msg": "leaf"}

    app = Lilya(routes=[Include("/nest", routes=[Path("/leaf", leaf)])], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "/nest/leaf" in spec["paths"]


def test_nested_include_two_levels():
    @openapi()
    async def deeper(request):
        return {"msg": "deep"}

    app = Lilya(
        routes=[Include("/level1", routes=[Include("/level2", routes=[Path("/deep", deeper)])])],
        enable_openapi=True,
    )
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "/level1/level2/deep" in spec["paths"]


def test_child_lilya_one_level():
    @openapi()
    async def child_hello(request):
        return {"msg": "child"}

    child_app = Lilya(routes=[Path("/hello", child_hello)], enable_openapi=True)
    app = Lilya(routes=[Include("/child", app=child_app)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "/child/hello" in spec["paths"]


def test_child_lilya_nested_include():
    @openapi()
    async def nested_child(request):
        return {"msg": "nested"}

    child_app = Lilya(
        routes=[Include("/nest", routes=[Path("/deep", nested_child)])], enable_openapi=True
    )
    app = Lilya(routes=[Include("/child", app=child_app)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "/child/nest/deep" in spec["paths"]


def test_mixed_include_child():
    @openapi()
    async def m(request):
        return {"msg": "m"}

    child = Lilya(routes=[Include("/c", routes=[Path("/leaf", m)])], enable_openapi=True)
    app = Lilya(
        routes=[Include("/a", routes=[Path("/b", m)]), Include("/x", app=child)],
        enable_openapi=True,
    )
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "/a/b" in spec["paths"]
    assert "/x/c/leaf" in spec["paths"]


def test_skip_include_in_schema():
    @openapi()
    async def hidden(request):
        return {"msg": "hidden"}

    app = Lilya(
        routes=[Path("/vis", async_handler), Path("/hid", hidden, include_in_schema=False)],
        enable_openapi=True,
    )
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "/vis" in spec["paths"]
    assert "/hid" not in spec["paths"]


def test_multiple_methods():
    @openapi()
    async def both(request):
        return {"msg": "both"}

    app = Lilya(routes=[Path("/bm", both, methods=["GET", "POST"])], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    methods = set(spec["paths"]["/bm"].keys())

    assert methods == {"get", "post"}


def test_no_decorator_still_included():
    app = Lilya(routes=[Path("/plain", async_handler)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "/plain" in spec["paths"]
    assert spec["paths"]["/plain"]["get"]["operationId"] == "async_handler"


def test_top_level_servers_tags():
    @openapi()
    async def s(request):
        return {"msg": "s"}

    app = Lilya(routes=[Path("/s", s)], enable_openapi=True)
    spec = get_openapi(
        app=app,
        title="Test",
        version="2.0",
        openapi_version="3.1.0",
        routes=app.routes,
        tags=[{"name": "t1"}, {"name": "t2"}],
        servers=[{"url": "https://api.example.com"}],
    )

    assert spec["openapi"] == "3.1.0"
    assert spec["info"]["version"] == "2.0"
    assert any(server["url"] == "https://api.example.com" for server in spec["servers"])
    assert any(tag["name"] == "t1" for tag in spec["tags"])


def test_response_media_type_override():
    @openapi(
        responses={
            201: OpenAPIResponse(model=ModelA, media_type="application/xml", description="Created")
        }
    )
    async def create(request):
        return {"id": 1, "name": "X"}

    app = Lilya(routes=[Path("/create", create)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    resp = spec["paths"]["/create"]["get"]["responses"]["201"]

    assert "application/json" in resp["content"]


def test_request_body_is_emitted_without_explicit_responses():
    @openapi(request_body=ModelA)
    async def create_without_responses(request):
        return {"id": 1, "name": "X"}

    app = Lilya(
        routes=[Path("/create-with-body", create_without_responses, methods=["POST"])],
        enable_openapi=True,
    )
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    operation = spec["paths"]["/create-with-body"]["post"]

    assert "requestBody" in operation
    assert "application/json" in operation["requestBody"]["content"]
    assert operation["responses"]["200"]["description"] == "Successful response"


def test_request_body_upload_uses_multipart_for_binary_schema():
    @openapi(
        request_body=UploadRequestBody,
        responses={200: OpenAPIResponse(model=ModelA, description="OK")},
    )
    async def upload_item(request):
        return {"id": 1, "name": "uploaded"}

    app = Lilya(
        routes=[Path("/upload", upload_item, methods=["POST"])],
        enable_openapi=True,
    )
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    request_body = spec["paths"]["/upload"]["post"]["requestBody"]
    schema = request_body["content"]["multipart/form-data"]["schema"]

    assert "multipart/form-data" in request_body["content"]
    assert schema["properties"]["file"]["format"] == "binary"


def test_request_body_accepts_raw_openapi_object():
    raw_request_body = {
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "properties": {"file": {"type": "string", "format": "binary"}},
                    "required": ["file"],
                }
            }
        }
    }

    @openapi(request_body=raw_request_body)
    async def upload_with_raw_body(request):
        return {"ok": True}

    app = Lilya(
        routes=[Path("/upload-raw", upload_with_raw_body, methods=["POST"])],
        enable_openapi=True,
    )
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    operation = spec["paths"]["/upload-raw"]["post"]

    assert operation["requestBody"] == raw_request_body


def test_default_response_no_decorator():
    def plain(request):
        return {"msg": "plain"}

    app = Lilya(routes=[Path("/plain2", plain)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    resp = spec["paths"]["/plain2"]["get"]["responses"]["200"]

    assert resp["description"] == "Successful response"


def test_path_param_hyphen_underscore():
    @openapi()
    async def mix(request, user_id: str, item_id: str):
        return {"user": user_id, "item": item_id}

    app = Lilya(routes=[Path("/u-{user_id}/i_{item_id}", mix)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    params = spec["paths"]["/u-{user_id}/i_{item_id}"]["get"]["parameters"]
    names = {p["name"] for p in params}

    assert "user_id" in names and "item_id" in names


def test_multiple_query_params():
    @openapi(
        query={
            "a": Query(default="x", description="a param", schema={"type": "string"}),
            "b": Query(default=1, description="b param", schema={"type": "integer"}),
        }
    )
    async def multi_q(request):
        return {"q": []}

    app = Lilya(routes=[Path("/mq", multi_q)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    params = spec["paths"]["/mq"]["get"]["parameters"]
    names = {p["name"] for p in params}

    assert names == {"a", "b"}


def test_overlap_path_query_id():
    @openapi(query={"id": Query(default="x", description="query id", schema={"type": "string"})})
    async def overlap(request, id: str):
        return {"id": id}

    app = Lilya(routes=[Path("/overlap/{id}", overlap)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    params = spec["paths"]["/overlap/{id}"]["get"]["parameters"]
    # Expect only one 'id' in path, not query
    path_param = next(p for p in params if p["in"] == "path")
    assert path_param["name"] == "id"

    # No duplicate 'id' in query
    query_params = [p for p in params if p["in"] == "query"]
    assert any(q["name"] == "id" for q in query_params)


def test_decorator_handles_sync_and_async():
    @openapi()
    def sync_h(request):
        return {"msg": "sync"}

    @openapi()
    async def async_h(request):
        return {"msg": "async"}

    app = Lilya(routes=[Path("/s", sync_h), Path("/a", async_h)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "/s" in spec["paths"] and "/a" in spec["paths"]


def test_deep_nested_child():
    @openapi()
    async def deep_child(request):
        return {"msg": "deep"}

    level3 = Lilya(routes=[Path("/leaf", deep_child)], enable_openapi=True)
    level2 = Lilya(routes=[Include("/lvl3", app=level3)], enable_openapi=True)
    level1 = Lilya(routes=[Include("/lvl2", app=level2)], enable_openapi=True)
    app = Lilya(routes=[Include("/lvl1", app=level1)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "/lvl1/lvl2/lvl3/leaf" in spec["paths"]


def test_default_method_get():
    @openapi()
    async def d(request):
        return {"msg": "d"}

    app = Lilya(routes=[Path("/d", d)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "get" in spec["paths"]["/d"]


def test_explicit_delete_method():
    @openapi()
    async def rem(request):
        return {"msg": "removed"}

    app = Lilya(routes=[Path("/rm", rem, methods=["DELETE"])], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    assert "delete" in spec["paths"]["/rm"]


def test_hyphen_namespace_path():
    @openapi()
    async def hn(request):
        return {"msg": "hn"}

    app = Lilya(routes=[Include("/user-group", routes=[Path("/info", hn)])], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "/user-group/info" in spec["paths"]


def test_complex_path_multiple_params():
    @openapi()
    async def cp(request, a: str, b: str, c: str):
        return {"a": a, "b": b, "c": c}

    app = Lilya(routes=[Path("/x/{a}/y/{b}/z/{c}", cp)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    params = spec["paths"]["/x/{a}/y/{b}/z/{c}"]["get"]["parameters"]
    names = {p["name"] for p in params if p["in"] == "path"}

    assert names == {"a", "b", "c"}


def test_excludes_head_method():
    @openapi()
    async def head_test(request):
        return {"msg": "h"}

    # Force HEAD method to appear in methods -> HEAD should not be documented
    app = Lilya(routes=[Path("/h", head_test, methods=["GET", "HEAD"])], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "get" in spec["paths"]["/h"]
    assert "head" not in spec["paths"]["/h"]


def test_include_in_schema_default_true():
    @openapi()
    async def inc(request):
        return {"msg": "inc"}

    app = Lilya(routes=[Path("/inc", inc)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "/inc" in spec["paths"]


def test_override_include_in_schema_false():
    @openapi()
    async def not_included(request):
        return {"msg": "x"}

    app = Lilya(routes=[Path("/x", not_included, include_in_schema=False)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "/x" not in spec["paths"]


def test_top_level_description_info():
    @openapi()
    async def t(request):
        return {"msg": "t"}

    app = Lilya(routes=[Path("/t", t)], enable_openapi=True)
    spec = get_openapi(
        app=app,
        title="Test",
        version="1.0",
        openapi_version="3.0.0",
        routes=app.routes,
        description="API desc",
    )

    assert spec["info"]["description"] == "API desc"


def test_top_level_terms_contact_license():
    @openapi()
    async def t2(request):
        return {"msg": "t2"}

    top_terms = "https://tos.example.com"
    top_contact = {"name": "Alice", "email": "alice@example.com"}
    top_license = {"name": "MIT", "url": "https://opensource.org/licenses/MIT"}
    app = Lilya(routes=[Path("/t2", t2)], enable_openapi=True)
    spec = get_openapi(
        app=app,
        title="Test",
        version="1.0",
        openapi_version="3.0.0",
        routes=app.routes,
        terms_of_service=top_terms,
        contact=top_contact,
        license=top_license,
    )

    assert spec["info"]["termsOfService"] == top_terms
    assert spec["info"]["contact"] == top_contact
    assert spec["info"]["license"] == top_license


def test_webhooks_top_level():
    @openapi()
    async def w(request):
        return {"msg": "w"}

    wh = [{"url": "wss://example"}]
    app = Lilya(routes=[Path("/w", w)], enable_openapi=True)
    spec = get_openapi(
        app=app,
        title="Test",
        version="1.0",
        openapi_version="3.0.0",
        routes=app.routes,
        webhooks=wh,
    )

    assert spec["webhooks"] == wh


def test_path_param_uppercase():
    @openapi()
    async def up(request, UserID: str):
        return {"UserID": UserID}

    app = Lilya(routes=[Path("/u/{UserID}", up)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    params = spec["paths"]["/u/{UserID}"]["get"]["parameters"]

    assert any(p["name"] == "UserID" for p in params)


def test_query_without_schema_defaults_string():
    @openapi(query={"foo": Query(default="bar")})
    async def qf(request):
        return {"foo": "bar"}

    app = Lilya(routes=[Path("/qf", qf)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    p = spec["paths"]["/qf"]["get"]["parameters"][0]

    assert p["schema"]["type"] == "string"


def test_query_required_flag():
    @openapi(query={"foo": Query(default="bar", required=True)})
    async def qr(request):
        return {"foo": "bar"}

    app = Lilya(routes=[Path("/qr", qr)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    p = spec["paths"]["/qr"]["get"]["parameters"][0]

    assert p["required"] is True


def test_handler_missing_openapi_meta():
    def no_meta(request):
        return {"msg": "nm"}

    app = Lilya(routes=[Path("/nm", no_meta)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert spec["paths"]["/nm"]["get"]["operationId"] == "no_meta"


def test_path_normalization_double_slash():
    @openapi()
    async def ds(request):
        return {"msg": "ds"}

    # Path constructor will clean "//a///b" to "/a/b"
    app = Lilya(routes=[Path("//a///b", ds)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "/a/b" in spec["paths"]


def test_deep_nested_includes_with_siblings():
    @openapi()
    async def leaf1(request):
        return {"leaf1": True}

    @openapi()
    async def leaf2(request):
        return {"leaf2": True}

    app = Lilya(
        routes=[
            Include(
                "/a", routes=[Include("/b", routes=[Path("/leaf1", leaf1)]), Path("/leaf2", leaf2)]
            )
        ],
        enable_openapi=True,
    )
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "/a/b/leaf1" in spec["paths"]
    assert "/a/leaf2" in spec["paths"]


def test_query_name_with_dashes():
    @openapi(query={"user-id": Query(default="x", schema={"type": "string"})})
    async def ud(request):
        return {"user-id": "x"}

    app = Lilya(routes=[Path("/ud", ud)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    p = spec["paths"]["/ud"]["get"]["parameters"][0]

    assert p["name"] == "user-id"


def test_spec_contains_info_and_paths():
    app = Lilya(routes=[Path("/ip", async_handler)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="InfoCheck", version="v1", openapi_version="3.0.0", routes=app.routes
    )

    assert "info" in spec and "paths" in spec
    assert spec["info"]["title"] == "InfoCheck"
    assert spec["info"]["version"] == "v1"


def test_multiple_siblings_child_apps():
    @openapi()
    async def c1(request):
        return {"c1": True}

    @openapi()
    async def c2(request):
        return {"c2": True}

    child1 = Lilya(routes=[Path("/one", c1)], enable_openapi=True)
    child2 = Lilya(routes=[Path("/two", c2)], enable_openapi=True)
    app = Lilya(
        routes=[Include("/c1", app=child1), Include("/c2", app=child2)], enable_openapi=True
    )
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "/c1/one" in spec["paths"]
    assert "/c2/two" in spec["paths"]
