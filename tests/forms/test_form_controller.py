from __future__ import annotations

import json
from typing import Any

import msgspec
import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from lilya.apps import Lilya
from lilya.exceptions import ImproperlyConfigured
from lilya.requests import Request
from lilya.responses import HTMLResponse
from lilya.routing import RoutePath
from lilya.templating.controllers import FormController

pytestmark = pytest.mark.anyio


class _FakeTemplates:
    """
    Minimal drop-in replacement for Jinja2Template used in tests.

    - Records calls for assertions.
    - Returns a JSON response encoding the *sanitized* context:
      * 'has_request' indicates whether 'request' key is present
      * 'context' contains the context with request removed/replaced
      * 'template' echoes the template name used
    """

    def __init__(self) -> None:
        self.calls: list[tuple[Request, str, dict[str, Any]]] = []

    def get_template_response(
        self, request: Request, template_name: str, context: dict[str, Any]
    ) -> HTMLResponse:
        self.calls.append((request, template_name, context))

        def _sanitize(obj: Any) -> Any:
            if isinstance(obj, dict):
                out = {}
                for k, v in obj.items():
                    if k == "request":
                        out[k] = "<REQUEST>"
                    else:
                        out[k] = _sanitize(v)
                return out
            if isinstance(obj, (list, tuple)):
                return [_sanitize(x) for x in obj]
            return obj

        payload = {
            "template": template_name,
            "has_request": "request" in context,
            "context": _sanitize(context),
        }
        return HTMLResponse(json.dumps(payload), media_type="application/json")


def _make_app(controller_cls: type[FormController]) -> Lilya:
    return Lilya(routes=[RoutePath("/form", controller_cls, methods=["GET", "POST"], name="form")])


async def _json(client: AsyncClient, method: str, url: str, **kwargs) -> dict:
    resp = await client.request(method, url, **kwargs)
    # Try JSON body; if not JSON (e.g., redirect), fall back.
    try:
        return resp.json()
    except Exception:  # noqa
        return {"status_code": resp.status_code, "headers": dict(resp.headers)}


class SimpleForm:
    """A tiny 'schema' with no validation, just stores kwargs."""

    def __init__(self, **data: Any) -> None:
        for k, v in data.items():
            setattr(self, k, v)

    def dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


class ValidFormController(FormController):
    template_name = "forms/simple.html"
    success_url = "/ok"
    form_class = SimpleForm
    templates = _FakeTemplates()

    async def form_valid(self, request: Request, form: SimpleForm, **kwargs: Any) -> HTMLResponse:
        # Return a non-redirect to assert on the validated payload easily.
        return HTMLResponse(
            json.dumps({"ok": True, "data": form.dict()}), media_type="application/json"
        )


class RedirectFormController(FormController):
    template_name = "forms/redirect.html"
    success_url = "/done"
    form_class = SimpleForm
    templates = _FakeTemplates()
    # uses default form_valid → RedirectResponse(303)


class InvalidFormController(FormController):
    template_name = "forms/invalid.html"
    success_url = "/never"
    form_class = SimpleForm
    templates = _FakeTemplates()

    # Force a validation failure via overridden validator
    async def validate_form(self, form_class: type[Any], data: dict[str, Any]) -> Any:
        raise ValueError("boom!")


class InitialDataFormController(FormController):
    template_name = "forms/with_initial.html"
    success_url = "/ok"
    form_class = SimpleForm
    templates = _FakeTemplates()

    def get_initial(self) -> dict[str, Any]:
        return {"preset": "value", "count": 3}


class MissingFormClassController(FormController):
    template_name = "forms/missing.html"
    templates = _FakeTemplates()
    # form_class not set; POST should raise ImproperlyConfigured


class ValidatorCallableController(FormController):
    template_name = "forms/validator_callable.html"
    success_url = "/ok"
    form_class = SimpleForm
    templates = _FakeTemplates()

    # Provide a validator that uppercases a field to prove it ran
    def __init__(self) -> None:
        super().__init__()

        def _validator(cls: type[Any], data: dict[str, Any]) -> Any:
            data = dict(data)
            if "name" in data and isinstance(data["name"], str):
                data["name"] = data["name"].upper()
            return cls(**data)

        self.validator = _validator  # type: ignore[assignment]

    async def form_valid(self, request: Request, form: SimpleForm, **kwargs: Any) -> HTMLResponse:
        return HTMLResponse(
            json.dumps({"name": getattr(form, "name", None)}), media_type="application/json"
        )


class ValidateFormOverrideController(FormController):
    template_name = "forms/override_validate.html"
    success_url = "/ok"
    form_class = SimpleForm
    templates = _FakeTemplates()

    async def validate_form(self, form_class: type[Any], data: dict[str, Any]) -> Any:
        # Replace payload entirely
        return form_class(validated=True)

    async def form_valid(self, request: Request, form: SimpleForm, **kwargs: Any) -> HTMLResponse:
        return HTMLResponse(json.dumps(form.dict()), media_type="application/json")


async def test_get_renders_initial_context_and_injects_request(test_client_factory) -> None:
    app = _make_app(InitialDataFormController)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        data = await _json(client, "GET", "/form")

        assert data["template"] == "forms/with_initial.html"
        assert data["has_request"] is True

        # initial data present
        assert data["context"]["form"] == {"preset": "value", "count": 3}

        # errors initialized
        assert data["context"]["errors"] == {}


async def test_post_valid_calls_form_valid_and_returns_payload(test_client_factory) -> None:
    app = _make_app(ValidFormController)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        data = await _json(client, "POST", "/form", data={"a": "1", "b": "2"})

        assert data["ok"] is True
        assert data["data"] == {"a": "1", "b": "2"}


async def test_post_valid_default_redirect_303_and_location_header(test_client_factory) -> None:
    app = _make_app(RedirectFormController)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/form", data={"x": "y"})

        assert resp.status_code == 303
        assert resp.headers.get("location") == "/done"


async def test_post_invalid_rerenders_template_with_errors_and_echoed_data(
    test_client_factory,
) -> None:
    app = _make_app(InvalidFormController)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        data = await _json(client, "POST", "/form", data={"foo": "bar"})

        assert data["template"] == "forms/invalid.html"
        assert data["has_request"] is True

        # Submitted data should be echoed so user doesn't lose input
        assert data["context"]["form"] == {"foo": "bar"}

        # Errors propagated (stringified by controller)
        assert "boom" in str(data["context"]["errors"])


def test_missing_form_class_raises_improperly_configured(test_client_factory) -> None:
    # Call the method directly to assert the error (POST path would be 500)
    ctrl = MissingFormClassController()

    with pytest.raises(ImproperlyConfigured):
        ctrl.get_form_class()


async def test_validator_callable_is_used(test_client_factory) -> None:
    app = _make_app(ValidatorCallableController)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        data = await _json(client, "POST", "/form", data={"name": "alice"})

        # Uppercased by validator callable
        assert data["name"] == "ALICE"


async def test_validate_form_override_is_used(test_client_factory) -> None:
    app = _make_app(ValidateFormOverrideController)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        data = await _json(client, "POST", "/form", data={"ignored": "yes"})
        assert data == {"validated": True}


async def test_with_pydantic_if_available(test_client_factory) -> None:
    class ContactForm(BaseModel):  # type: ignore[misc]
        name: str
        email: str

    class PydanticFormController(FormController):
        template_name = "forms/pydantic.html"
        success_url = "/ok"
        form_class = ContactForm
        templates = _FakeTemplates()

        async def form_valid(
            self, request: Request, form: ContactForm, **kwargs: Any
        ) -> HTMLResponse:
            return HTMLResponse(json.dumps(form.model_dump()), media_type="application/json")

        async def form_invalid(
            self, request: Request, errors: Any, data: dict[str, Any], **kwargs: Any
        ) -> HTMLResponse:
            return HTMLResponse(
                json.dumps({"errors": errors, "data": data}), media_type="application/json"
            )

    app = _make_app(PydanticFormController)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Valid
        ok = await _json(client, "POST", "/form", data={"name": "Tiago", "email": "t@example.com"})
        assert ok == {"name": "Tiago", "email": "t@example.com"}

        # Invalid (missing email)
        bad = await _json(client, "POST", "/form", data={"name": "Tiago"})
        assert "errors" in bad
        assert bad["data"] == {"name": "Tiago"}


async def test_with_msgspec_if_available(test_client_factory) -> None:
    class Contact(msgspec.Struct):
        name: str
        email: str

    class MsgspecFormController(FormController):
        template_name = "forms/msgspec.html"
        success_url = "/ok"
        form_class = Contact
        templates = _FakeTemplates()

        async def validate_form(self, form_class: type[Any], data: dict[str, Any]) -> Any:
            return msgspec.convert(data, form_class)

        async def form_valid(self, request: Request, form: Contact, **kwargs: Any) -> HTMLResponse:
            return HTMLResponse(
                json.dumps({"name": form.name, "email": form.email}), media_type="application/json"
            )

        async def form_invalid(
            self, request: Request, errors: Any, data: dict[str, Any], **kwargs: Any
        ) -> HTMLResponse:
            return HTMLResponse(
                json.dumps({"errors": str(errors), "data": data}), media_type="application/json"
            )

    app = _make_app(MsgspecFormController)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        ok = await _json(client, "POST", "/form", data={"name": "A", "email": "a@b.c"})

        assert ok == {"name": "A", "email": "a@b.c"}

        bad = await _json(client, "POST", "/form", data={"name": "A"})

        assert "errors" in bad
        assert bad["data"] == {"name": "A"}
