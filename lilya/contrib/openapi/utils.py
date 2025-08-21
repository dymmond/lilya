import re
from collections.abc import Sequence
from typing import Any, cast, get_args, get_origin

from pydantic.json_schema import GenerateJsonSchema

from lilya._internal._encoders import json_encode
from lilya._utils import is_class_and_subclass
from lilya.contrib.openapi.constants import REF_TEMPLATE, WRITING_METHODS
from lilya.contrib.openapi.helpers import get_definitions
from lilya.contrib.openapi.params import Query, ResponseParam
from lilya.controllers import Controller
from lilya.enums import HTTPMethod


def extract_http_methods_from_endpoint(cls: type) -> list[str]:
    return [
        method.upper()
        for method in HTTPMethod.to_list()
        if callable(getattr(cls, method.lower(), None))
    ]


def get_openapi(
    *,
    app: Any,
    title: str,
    version: str,
    openapi_version: str = "3.0.0",
    routes: Sequence[Any],
    summary: str | None = None,
    description: str | None = None,
    tags: Sequence[Any] | None = None,
    servers: Sequence[Any] | None = None,
    terms_of_service: str | None = None,
    contact: dict[str, Any] | None = None,
    license: dict[str, Any] | None = None,
    webhooks: Sequence[Any] | None = None,
) -> dict[str, Any]:
    info = {
        "title": title,
        "version": version,
    }
    if summary:
        info["summary"] = summary
    if description:
        info["description"] = description
    if terms_of_service:
        info["termsOfService"] = terms_of_service
    if contact:
        info["contact"] = contact  # type: ignore
    if license:
        info["license"] = license  # type: ignore

    spec = {
        "openapi": openapi_version,
        "info": info,
        "paths": {},
        "components": {"schemas": {}, "securitySchemes": {}},
    }
    if servers:
        spec["servers"] = list(servers)
    if tags:
        spec["tags"] = list(tags)
    if webhooks:
        spec["webhooks"] = list(webhooks)

    used_security_schemes = set()
    securitySchemes: dict[str, Any] = {}

    def _gather_routes(routes_list: Sequence[Any], prefix: str) -> list[tuple[str, Any]]:
        gathered = []
        for route in routes_list:
            raw = getattr(route, "path_format", None) or getattr(route, "path", None)
            if not raw:
                continue
            if not raw.startswith("/"):
                raw = "/" + raw
            cleaned = raw.split("/{", 1)[0] if "/{" in raw else raw
            if hasattr(route, "routes") and route.routes:
                gathered.extend(_gather_routes(route.routes, prefix + cleaned))
            elif hasattr(route, "app") and hasattr(route.app, "routes"):
                gathered.extend(_gather_routes(route.app.routes, prefix + cleaned))
            else:
                gathered.append((prefix + raw, route))
        return gathered

    for full_path, route in _gather_routes(routes, prefix=""):
        if not getattr(route, "include_in_schema", False):
            continue
        raw_path = full_path
        if not raw_path:
            continue

        methods = (
            extract_http_methods_from_endpoint(route.handler)
            if is_class_and_subclass(route.handler, Controller)
            else getattr(route, "methods", ["GET"])
        )
        for method in methods:
            if method.upper() == "HEAD":
                continue
            m_lower = method.lower()
            handler = (
                getattr(route.handler, m_lower, None)
                if is_class_and_subclass(route.handler, Controller)
                else getattr(route, "handler", None)
            )
            meta = getattr(handler, "openapi_meta", {}) or {}

            if hasattr(handler, "func"):
                handler = handler.func

            operation = {
                "operationId": meta.get("operation_id", handler.__name__ if handler else ""),
                "summary": meta.get("summary"),
                "description": meta.get("description"),
                "tags": meta.get("tags"),
                "deprecated": meta.get("deprecated", False),
                "security": meta.get("security"),
                "parameters": [],
                "responses": {},
            }

            if meta.get("security"):
                for sec in meta["security"]:
                    for name in sec:
                        if name not in used_security_schemes:
                            used_security_schemes.add(name)
                            securitySchemes[name] = sec[name]

            path_param_names = re.findall(r"\{([^}]+)\}", raw_path)
            for name in path_param_names:
                operation["parameters"].append(
                    {
                        "name": name,
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                )

            for name, query_param in (meta.get("query", {}) or {}).items():
                if isinstance(query_param, Query):
                    operation["parameters"].append(query_param.as_openapi_dict(name))
                else:
                    operation["parameters"].append(query_param)

            responses_obj = {}
            seen_responses = meta.get("responses", {})
            schema_generator = GenerateJsonSchema(ref_template=REF_TEMPLATE)
            to_generate = []

            if isinstance(seen_responses, dict) and seen_responses:
                for response in seen_responses.values():
                    ann = getattr(response, "annotation", None)
                    if ann:
                        origin = get_origin(ann)
                        if origin in [list, Sequence]:
                            inner = get_args(ann)[0]
                            to_generate.append(
                                ResponseParam(
                                    annotation=inner,
                                    alias=inner.__name__,
                                    description=response.description,
                                )
                            )
                        else:
                            to_generate.append(
                                ResponseParam(
                                    annotation=ann,
                                    alias=ann.__name__,
                                    description=response.description,
                                )
                            )

                _, definitions = get_definitions(
                    fields=to_generate, schema_generator=schema_generator
                )
                for name, schema_def in definitions.items():
                    spec["components"]["schemas"][name] = schema_def  # type: ignore

                request_body = meta.get("request_body", {})
                for status_code_int, response in seen_responses.items():
                    status_code = str(status_code_int)
                    desc = getattr(response, "description", "") or ""
                    content_obj = {}
                    ann = getattr(response, "annotation", None)
                    if ann:
                        media = getattr(response, "media_type", "application/json")
                        origin = get_origin(ann)
                        if origin in [list, Sequence]:
                            inner = get_args(ann)[0]
                            ref_name = inner.__name__
                            content_obj[media] = {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": f"#/components/schemas/{ref_name}"},
                                }
                            }
                        else:
                            ref_name = ann.__name__
                            content_obj[media] = {
                                "schema": {"$ref": f"#/components/schemas/{ref_name}"}
                            }
                    responses_obj[status_code] = {"description": desc or "Successful response"}
                    if content_obj:
                        responses_obj[status_code]["content"] = content_obj

                    if m_lower in WRITING_METHODS and status_code_int in request_body:
                        operation["requestBody"] = {
                            "content": {
                                getattr(response, "media_type", "application/json"): {
                                    "schema": request_body[status_code_int]
                                }
                            }
                        }

            else:
                # If no responses are defined, we assume a 200 OK response with an empty schema
                responses_obj["200"] = {
                    "description": meta.get("response_description") or "Successful response",
                }

            operation["responses"] = responses_obj
            spec["paths"].setdefault(raw_path, {})[m_lower] = operation

    if securitySchemes:
        spec["components"]["securitySchemes"] = securitySchemes  # type: ignore
    return cast(dict[str, Any], json_encode(spec, exclude_none=True))
