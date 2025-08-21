from pydantic import BaseModel

from lilya.apps import Lilya
from lilya.conf import settings
from lilya.contrib.openapi.datastructures import OpenAPIResponse
from lilya.contrib.openapi.decorator import openapi
from lilya.contrib.openapi.params import Query
from lilya.contrib.openapi.utils import get_openapi
from lilya.controllers import Controller
from lilya.routing import Include, Path
from lilya.testclient import TestClient


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


def test_basic_path_sync_with_summary():
    class HandlerController(Controller):
        @openapi(summary="Sync summary")
        def get(self):
            return {"msg": "hi"}

    app = Lilya(routes=[Path("/sync", HandlerController)], enable_openapi=True)
    client = TestClient(app)

    response = client.get("/openapi.json")
    assert response.status_code == 200

    assert response.json() == {
        "openapi": "3.1.0",
        "info": {
            "title": "Lilya",
            "version": settings.version,
            "summary": "Lilya application",
            "description": "Yet another framework/toolkit that delivers.",
            "contact": {"name": "Lilya", "url": "https://lilya.dev", "email": "admin@myapp.com"},
        },
        "paths": {
            "/sync": {
                "get": {
                    "summary": "Sync summary",
                    "parameters": [],
                    "responses": {"200": {"description": "Successful response"}},
                }
            }
        },
        "components": {"schemas": {}, "securitySchemes": {}},
        "servers": [{"url": "/"}],
    }


def test_path_parameter():
    class UserController(Controller):
        @openapi()
        async def get(self, request, user: str):
            return {"user": user}

    app = Lilya(routes=[Path("/users/{user}", UserController)], enable_openapi=True)

    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    params = spec["paths"]["/users/{user}"]["get"]["parameters"]

    assert any(p["in"] == "path" and p["name"] == "user" for p in params)
    assert all(p["required"] for p in params if p["in"] == "path")


def test_query_parameter_string():
    class QueryController(Controller):
        @openapi(query={"q": Query(default=None, description="search", schema={"type": "string"})})
        async def get(self, request):
            return {"items": []}

    app = Lilya(routes=[Path("/search", QueryController)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    params = spec["paths"]["/search"]["get"]["parameters"]

    assert any(p["in"] == "query" and p["name"] == "q" for p in params)


def test_query_parameter_array():
    class QueryParamArrayController(Controller):
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
        async def get(self, request):
            return {"tags": []}

    app = Lilya(routes=[Path("/tags", QueryParamArrayController)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    params = spec["paths"]["/tags"]["get"]["parameters"]
    p = next(p for p in params if p["name"] == "tags")

    assert p["schema"]["type"] == "array"
    assert p["style"] == "form"
    assert p["explode"] is True


def test_query_parameter_object():
    class QueryParamObjectController(Controller):
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
        async def get(self, request):
            return {"items": []}

    app = Lilya(routes=[Path("/filter", QueryParamObjectController)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    params = spec["paths"]["/filter"]["get"]["parameters"]
    p = next(p for p in params if p["name"] == "filter")

    assert p["schema"]["type"] == "object"
    assert p["style"] == "deepObject"
    assert p["explode"] is True


def test_path_and_query_combined():
    class UserDetailController(Controller):
        @openapi(
            query={"verbose": Query(default=False, schema={"type": "boolean"})},
        )
        async def get(self, request, user: str):
            return {"user": user, "verbose": request.query_params.get("verbose", False)}

    app = Lilya(routes=[Path("/detail/{user}", UserDetailController)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    params = spec["paths"]["/detail/{user}"]["get"]["parameters"]
    names = {p["name"] for p in params}

    assert "user" in names and "verbose" in names


def test_single_response_model():
    class SingleResponseController(Controller):
        @openapi(responses={200: OpenAPIResponse(model=ModelA, description="OK")})
        async def get(self, request):
            return {"id": 1, "name": "Alice"}

    app = Lilya(routes=[Path("/a", SingleResponseController)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    resp = spec["paths"]["/a"]["get"]["responses"]["200"]

    assert "content" in resp

    json_schema = resp["content"]["application/json"]["schema"]

    assert "$ref" in json_schema and "ModelA" in json_schema["$ref"]


def test_multiple_responses():
    class MultipleResponsesController(Controller):
        @openapi(
            responses={
                200: OpenAPIResponse(model=ModelA, description="OK"),
                404: OpenAPIResponse(model=ModelB, description="Not Found"),
            }
        )
        async def get(self, request):
            return {"id": 1, "name": "Alice"}

    app = Lilya(routes=[Path("/multi", MultipleResponsesController)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    codes = set(spec["paths"]["/multi"]["get"]["responses"].keys())

    assert codes == {"200", "404"}


def test_deprecated_flag():
    class DeprecatedController(Controller):
        @openapi(deprecated=True)
        async def get(self, request):
            return {"msg": "deprecated"}

    app = Lilya(routes=[Path("/old", DeprecatedController)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert spec["paths"]["/old"]["get"]["deprecated"] is True


def test_tags_field():
    class TaggedController(Controller):
        @openapi(tags=["tag1", "tag2"])
        async def get(self, request):
            return {"msg": "hi"}

    app = Lilya(routes=[Path("/tagged", TaggedController)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert spec["paths"]["/tagged"]["get"]["tags"] == ["tag1", "tag2"]


def test_security_field():
    sec = [{"oauth2": ["read"]}]

    class SecureController(Controller):
        @openapi(security=sec)
        async def get(self, request):
            return {"msg": "secure"}

    app = Lilya(routes=[Path("/secure", SecureController)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert spec["paths"]["/secure"]["get"]["security"] == sec


def test_operation_id_override():
    class CustomIDController(Controller):
        @openapi(operation_id="customID")
        async def get(self, request):
            return {"msg": "x"}

    app = Lilya(routes=[Path("/opid", CustomIDController)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert spec["paths"]["/opid"]["get"]["operationId"] == "customID"


def test_description_field():
    class DetailedDescriptionController(Controller):
        @openapi(description="A detailed description")
        async def get(self, request):
            return {"msg": "desc"}

    app = Lilya(routes=[Path("/desc", DetailedDescriptionController)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert spec["paths"]["/desc"]["get"]["description"] == "A detailed description"


def test_include_one_level():
    class NestedController(Controller):
        @openapi()
        async def get(self, request):
            return {"msg": "nested"}

    app = Lilya(
        routes=[Include("/nest", routes=[Path("/leaf", NestedController)])], enable_openapi=True
    )
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "/nest/leaf" in spec["paths"]


def test_nested_include_two_levels():
    class DeeperController(Controller):
        @openapi()
        async def get(self, request):
            return {"msg": "deep"}

    app = Lilya(
        routes=[
            Include(
                "/level1", routes=[Include("/level2", routes=[Path("/deep", DeeperController)])]
            )
        ],
        enable_openapi=True,
    )
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "/level1/level2/deep" in spec["paths"]


def test_child_lilya_one_level():
    class ChildController(Controller):
        @openapi()
        async def get(self, request):
            return {"msg": "child"}

    child_app = Lilya(routes=[Path("/hello", ChildController)], enable_openapi=True)
    app = Lilya(routes=[Include("/child", app=child_app)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "/child/hello" in spec["paths"]


def test_child_lilya_nested_include():
    class NestedChildController(Controller):
        @openapi()
        async def get(request):
            return {"msg": "nested"}

    child_app = Lilya(
        routes=[Include("/nest", routes=[Path("/deep", NestedChildController)])],
        enable_openapi=True,
    )
    app = Lilya(routes=[Include("/child", app=child_app)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "/child/nest/deep" in spec["paths"]


def test_mixed_include_child():
    class PathController(Controller):
        @openapi()
        async def get(self, request):
            return {"msg": "path"}

    child = Lilya(
        routes=[Include("/c", routes=[Path("/leaf", PathController)])], enable_openapi=True
    )
    app = Lilya(
        routes=[Include("/a", routes=[Path("/b", PathController)]), Include("/x", app=child)],
        enable_openapi=True,
    )
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "/a/b" in spec["paths"]
    assert "/x/c/leaf" in spec["paths"]


def test_skip_include_in_schema():
    class AsyncController(Controller):
        @openapi()
        async def get(self, request):
            return {"msg": "async"}

    app = Lilya(
        routes=[
            Path("/vis", async_handler),
            Path("/hid", AsyncController, include_in_schema=False),
        ],
        enable_openapi=True,
    )
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "/vis" in spec["paths"]
    assert "/hid" not in spec["paths"]


def test_multiple_methods():
    class BothMethodsController(Controller):
        @openapi()
        async def get(self, request):
            return {"msg": "get"}

        @openapi()
        async def post(self, request):
            return {"msg": "post"}

    app = Lilya(
        routes=[Path("/bm", BothMethodsController, methods=["GET", "POST"])], enable_openapi=True
    )
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    methods = set(spec["paths"]["/bm"].keys())

    assert methods == {"get", "post"}


def test_no_decorator_still_included():
    class AsyncHandler(Controller):
        async def get(self, request):
            return {"msg": "ok"}

    app = Lilya(routes=[Path("/plain", AsyncHandler)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "/plain" in spec["paths"]
    assert spec["paths"]["/plain"]["get"]["operationId"] == "get"


def test_top_level_servers_tags():
    class ServerController(Controller):
        @openapi()
        async def get(self, request):
            return {"msg": "server"}

    app = Lilya(routes=[Path("/s", ServerController)], enable_openapi=True)
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
    class ResponseMediaController(Controller):
        @openapi(
            responses={
                201: OpenAPIResponse(
                    model=ModelA, media_type="application/xml", description="Created"
                )
            }
        )
        async def get(self, request):
            return {"id": 1, "name": "X"}

    app = Lilya(routes=[Path("/create", ResponseMediaController)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    resp = spec["paths"]["/create"]["get"]["responses"]["201"]

    assert "application/json" in resp["content"]


def test_default_response_no_decorator():
    class LilyaController(Controller):
        def get(self, request):
            return {"msg": "default"}

    app = Lilya(routes=[Path("/plain2", LilyaController)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    resp = spec["paths"]["/plain2"]["get"]["responses"]["200"]

    assert resp["description"] == "Successful response"


def test_path_param_hyphen_underscore():
    class HyphenUnderscoreController(Controller):
        @openapi()
        async def get(self, request, user_id: str, item_id: str):
            return {"user": user_id, "item": item_id}

    app = Lilya(
        routes=[Path("/u-{user_id}/i_{item_id}", HyphenUnderscoreController)], enable_openapi=True
    )
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    params = spec["paths"]["/u-{user_id}/i_{item_id}"]["get"]["parameters"]
    names = {p["name"] for p in params}

    assert "user_id" in names and "item_id" in names


def test_multiple_query_params():
    class MultiQueryController(Controller):
        @openapi(
            query={
                "a": Query(default="x", description="a param", schema={"type": "string"}),
                "b": Query(default=1, description="b param", schema={"type": "integer"}),
            }
        )
        async def get(request):
            return {"q": []}

    app = Lilya(routes=[Path("/mq", MultiQueryController)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    params = spec["paths"]["/mq"]["get"]["parameters"]
    names = {p["name"] for p in params}

    assert names == {"a", "b"}


def test_overlap_path_query_id():
    class OverlapController(Controller):
        @openapi(
            query={"id": Query(default="x", description="query id", schema={"type": "string"})}
        )
        async def get(self, request, id: str):
            return {"id": id}

    app = Lilya(routes=[Path("/overlap/{id}", OverlapController)], enable_openapi=True)
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
    class LilyaSyncController(Controller):
        @openapi()
        def get(self, request):
            return {"msg": "sync"}

    class LilyaAsyncController(Controller):
        @openapi()
        async def get(self, request):
            return {"msg": "async"}

    app = Lilya(
        routes=[Path("/s", LilyaSyncController), Path("/a", LilyaAsyncController)],
        enable_openapi=True,
    )
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "/s" in spec["paths"] and "/a" in spec["paths"]


def test_deep_nested_child():
    class DeepNestedController(Controller):
        @openapi()
        async def get(self, request):
            return {"msg": "deep"}

    level3 = Lilya(routes=[Path("/leaf", DeepNestedController)], enable_openapi=True)
    level2 = Lilya(routes=[Include("/lvl3", app=level3)], enable_openapi=True)
    level1 = Lilya(routes=[Include("/lvl2", app=level2)], enable_openapi=True)
    app = Lilya(routes=[Include("/lvl1", app=level1)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "/lvl1/lvl2/lvl3/leaf" in spec["paths"]


def test_default_method_get():
    class DefaultGetController(Controller):
        @openapi()
        async def get(self, request):
            return {"msg": "default get"}

    app = Lilya(routes=[Path("/d", DefaultGetController)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "get" in spec["paths"]["/d"]


def test_explicit_delete_method():
    class DeleteController(Controller):
        @openapi()
        async def delete(self, request):
            return {"msg": "deleted"}

    app = Lilya(routes=[Path("/rm", DeleteController, methods=["DELETE"])], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    assert "delete" in spec["paths"]["/rm"]


def test_hyphen_namespace_path():
    class HyphenController(Controller):
        @openapi()
        async def get(self, request):
            return {"msg": "hyphen"}

    app = Lilya(
        routes=[Include("/user-group", routes=[Path("/info", HyphenController)])],
        enable_openapi=True,
    )
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "/user-group/info" in spec["paths"]


def test_complex_path_multiple_params():
    class ComplexPathController(Controller):
        @openapi()
        async def get(self, request, a: str, b: str, c: str):
            return {"a": a, "b": b, "c": c}

    app = Lilya(routes=[Path("/x/{a}/y/{b}/z/{c}", ComplexPathController)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    params = spec["paths"]["/x/{a}/y/{b}/z/{c}"]["get"]["parameters"]
    names = {p["name"] for p in params if p["in"] == "path"}

    assert names == {"a", "b", "c"}


def test_excludes_head_method():
    class HeadTestController(Controller):
        @openapi()
        async def get(self, request):
            return {"msg": "get"}

        @openapi()
        async def head(self, request):
            return {"msg": "head"}

    # Force HEAD method to appear in methods → HEAD should not be documented
    app = Lilya(
        routes=[Path("/h", HeadTestController, methods=["GET", "HEAD"])], enable_openapi=True
    )
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "get" in spec["paths"]["/h"]
    assert "head" not in spec["paths"]["/h"]


def test_include_in_schema_default_true():
    class DefaultIncludeController(Controller):
        @openapi()
        async def get(self, request):
            return {"msg": "default include"}

    app = Lilya(routes=[Path("/inc", DefaultIncludeController)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "/inc" in spec["paths"]


def test_override_include_in_schema_false():
    class OverrideIncludeController(Controller):
        @openapi()
        async def get(self, request):
            return {"msg": "override include"}

    app = Lilya(
        routes=[Path("/x", OverrideIncludeController, include_in_schema=False)],
        enable_openapi=True,
    )
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "/x" not in spec["paths"]


def test_top_level_description_info():
    class TopLevelController(Controller):
        @openapi()
        async def get(self, request):
            return {"msg": "top level"}

    app = Lilya(routes=[Path("/t", TopLevelController)], enable_openapi=True)
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
    class TopLevelController(Controller):
        @openapi()
        async def get(self, request):
            return {"msg": "top level"}

    top_terms = "https://tos.example.com"
    top_contact = {"name": "Alice", "email": "alice@example.com"}
    top_license = {"name": "MIT", "url": "https://opensource.org/licenses/MIT"}
    app = Lilya(routes=[Path("/t2", TopLevelController)], enable_openapi=True)
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
    class WebhookController(Controller):
        @openapi()
        async def post(self, request):
            return {"msg": "webhook"}

    wh = [{"url": "wss://example"}]
    app = Lilya(routes=[Path("/w", WebhookController)], enable_openapi=True)
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
    class UpperCaseController(Controller):
        @openapi()
        async def get(self, request, UserID: str):
            return {"UserID": UserID}

    app = Lilya(routes=[Path("/u/{UserID}", UpperCaseController)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    params = spec["paths"]["/u/{UserID}"]["get"]["parameters"]

    assert any(p["name"] == "UserID" for p in params)


def test_query_without_schema_defaults_string():
    class QueryWithoutSchemaController(Controller):
        @openapi(query={"foo": Query(default="bar")})
        async def get(self, request):
            return {"foo": "bar"}

    app = Lilya(routes=[Path("/qf", QueryWithoutSchemaController)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    p = spec["paths"]["/qf"]["get"]["parameters"][0]

    assert p["schema"]["type"] == "string"


def test_query_required_flag():
    class QueryRequiredController(Controller):
        @openapi(query={"foo": Query(default="bar", required=True)})
        async def get(self, request):
            return {"foo": "bar"}

    app = Lilya(routes=[Path("/qr", QueryRequiredController)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    p = spec["paths"]["/qr"]["get"]["parameters"][0]

    assert p["required"] is True


def test_handler_missing_openapi_meta():
    class NoMetaController(Controller):
        async def get(self, request):
            return {"msg": "no meta"}

    app = Lilya(routes=[Path("/nm", NoMetaController)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert spec["paths"]["/nm"]["get"]["operationId"] == "get"


def test_path_normalization_double_slash():
    class LilyaController(Controller):
        @openapi()
        async def get(self, request):
            return {"msg": "ds"}

    # Path constructor will clean "//a///b" to "/a/b"
    app = Lilya(routes=[Path("//a///b", LilyaController)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "/a/b" in spec["paths"]


def test_deep_nested_includes_with_siblings():
    class LeafController(Controller):
        @openapi()
        async def get(self, request):
            return {"leaf1": True}

    class Leaf2Controller(Controller):
        @openapi()
        async def get(self, request):
            return {"leaf2": True}

    app = Lilya(
        routes=[
            Include(
                "/a",
                routes=[
                    Include("/b", routes=[Path("/leaf1", LeafController)]),
                    Path("/leaf2", Leaf2Controller),
                ],
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
    class UserIDController(Controller):
        @openapi(query={"user-id": Query(default="x", schema={"type": "string"})})
        async def get(self, request):
            return {"user-id": "x"}

    app = Lilya(routes=[Path("/ud", UserIDController)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )
    p = spec["paths"]["/ud"]["get"]["parameters"][0]

    assert p["name"] == "user-id"


def test_spec_contains_info_and_paths():
    class InfoCheckController(Controller):
        @openapi()
        async def get(self, request):
            return {"msg": "info check"}

    app = Lilya(routes=[Path("/ip", InfoCheckController)], enable_openapi=True)
    spec = get_openapi(
        app=app, title="InfoCheck", version="v1", openapi_version="3.0.0", routes=app.routes
    )

    assert "info" in spec and "paths" in spec
    assert spec["info"]["title"] == "InfoCheck"
    assert spec["info"]["version"] == "v1"


def test_multiple_siblings_child_apps():
    class LilyaChild1Controller(Controller):
        @openapi()
        async def get(self, request):
            return {"c1": True}

    class LilyaChild2Controller(Controller):
        @openapi()
        async def get(self, request):
            return {"c2": True}

    child1 = Lilya(routes=[Path("/one", LilyaChild1Controller)], enable_openapi=True)
    child2 = Lilya(routes=[Path("/two", LilyaChild2Controller)], enable_openapi=True)
    app = Lilya(
        routes=[Include("/c1", app=child1), Include("/c2", app=child2)], enable_openapi=True
    )
    spec = get_openapi(
        app=app, title="Test", version="1.0", openapi_version="3.0.0", routes=app.routes
    )

    assert "/c1/one" in spec["paths"]
    assert "/c2/two" in spec["paths"]
