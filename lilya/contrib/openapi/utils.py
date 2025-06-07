import re
from collections.abc import Callable, Iterator, Sequence
from typing import Any, get_args, get_origin

from pydantic.json_schema import GenerateJsonSchema

from lilya import __version__
from lilya.contrib.openapi.constants import REF_TEMPLATE, WRITING_METHODS, WRITING_STATUS_MAPPING
from lilya.contrib.openapi.helpers import get_definitions
from lilya.contrib.openapi.params import Query, ResponseParam


def get_openapi(
    *,
    app: Any,
    title: str,
    version: str,
    openapi_version: str,
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
    """
    Build an OpenAPI 3.x document for all routes, including nested Includes and child Lilya apps.
    """

    info: dict[str, Any] = {
        "title": title or "",
        "version": version or __version__,
    }
    if summary:
        info["summary"] = summary
    if description:
        info["description"] = description
    if terms_of_service:
        info["termsOfService"] = terms_of_service
    if contact:
        info["contact"] = contact
    if license:
        info["license"] = license

    spec: dict[str, Any] = {
        "openapi": openapi_version or "3.0.0",
        "info": info,
        "paths": {},
        "components": {"schemas": {}},
    }
    if servers:
        spec["servers"] = list(servers)
    if tags:
        spec["tags"] = list(tags)
    if webhooks:
        spec["webhooks"] = list(webhooks)

    def _gather_routes(routes_list: Sequence[Any], prefix: str) -> Iterator[tuple[str, Any]]:
        """
        Yield (full_path, route) for each leaf route:
        - For any Include or child-app, strip off the first "/{...}" segment if present, combine prefix+cleaned, recurse.
        - Otherwise, yield (prefix + raw, route).
        """
        for route in routes_list:
            raw = getattr(route, "path_format", None) or getattr(route, "path", None)
            if raw is None:
                continue

            if not raw.startswith("/"):
                raw = "/" + raw

            # Strip any typed placeholder e.g. "{path:path}" from the raw prefix
            if "/{" in raw:
                cleaned = raw.split("/{", 1)[0]
            else:
                cleaned = raw

            # If this is an Include (has .routes), recurse into its routes using cleaned
            if hasattr(route, "routes") and getattr(route, "routes", None) is not None:
                combined = prefix + cleaned
                yield from _gather_routes(route.routes, combined)
                continue

            # If this is a child-app mount (has .app.routes), recurse into child-app routes using cleaned
            if hasattr(route, "app") and hasattr(route.app, "routes"):
                combined = prefix + cleaned
                yield from _gather_routes(route.app.routes, combined)
                continue

            # Leaf path: combine prefix and raw exactly (no stripping)
            combined = prefix + raw
            yield combined, route

    for full_path, route in _gather_routes(routes, prefix=""):
        if not getattr(route, "include_in_schema", False):
            continue

        raw_path = full_path
        if not raw_path:
            continue

        methods = getattr(route, "methods", ["GET"])
        for method in methods:
            if method.upper() == "HEAD":
                continue

            m_lower = method.lower()
            handler: Callable[..., Any] = getattr(route, "handler", None)
            meta: dict[str, Any] = getattr(handler, "openapi_meta", {}) or {}

            # Path parameters
            path_param_names = re.findall(r"\{([^}]+)\}", raw_path)
            path_parameters: list[dict[str, Any]] = []
            for name in path_param_names:
                path_parameters.append(
                    {
                        "name": name,
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                )

            # Query parameters
            user_query_params: list[dict[str, Any]] = []
            for name, query_param in (meta.get("query", {}) or {}).items():
                if isinstance(query_param, Query):
                    user_query_params.append(query_param.as_openapi_dict(name))
                else:
                    user_query_params.append(query_param)

            # Deduplicate query params that match path names
            declared_path_names = set(path_param_names)
            merged_query: list[dict[str, Any]] = []
            for p in user_query_params:
                if p.get("name") in declared_path_names:
                    continue
                merged_query.append(p)

            combined_params = path_parameters + merged_query

            operation: dict[str, Any] = {
                "operationId": meta.get("operation_id", handler.__name__ if handler else ""),
            }
            if meta.get("summary") is not None:
                operation["summary"] = meta["summary"]
            if meta.get("description") is not None:
                operation["description"] = meta["description"]
            if meta.get("tags") is not None:
                operation["tags"] = meta["tags"]
            if meta.get("deprecated"):
                operation["deprecated"] = True
            if meta.get("security") is not None:
                operation["security"] = meta["security"]

            if combined_params:
                operation["parameters"] = combined_params

            if m_lower in WRITING_METHODS:
                operation["requestBody"] = {"content": {"application/json": {"schema": {}}}}

            # Responses and schemas
            responses_obj: dict[str, Any] = {}
            seen_responses = meta.get("responses", None)
            if isinstance(seen_responses, dict) and seen_responses:
                # Create a new generator to avoid reuse errors
                schema_generator = GenerateJsonSchema(ref_template=REF_TEMPLATE)

                # Prepare list of ResponseParam, unwrapping any list[...] annotations
                to_generate: list[ResponseParam] = []
                for response in seen_responses.values():
                    ann = getattr(response, "annotation", None)
                    if ann is None:
                        continue

                    origin = get_origin(ann)
                    if origin is list or origin is Sequence:
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

                # Generate definitions for each model
                _, definitions = get_definitions(
                    fields=to_generate,  # type: ignore
                    schema_generator=schema_generator,
                )
                for name, schema_def in definitions.items():
                    spec["components"]["schemas"][name] = schema_def

                request_body = meta.get("request_body", {})
                # Build response entries
                for status_code_int, response in seen_responses.items():
                    if m_lower in WRITING_STATUS_MAPPING and status_code_int in request_body:
                        operation["requestBody"] = {
                            "content": {
                                getattr(response, "media_type", "application/json"): {
                                    "schema": request_body[status_code_int]
                                }
                            }
                        }

                    status_code = str(status_code_int)
                    desc = getattr(response, "description", "") or ""
                    content_obj: dict[str, Any] = {}

                    ann = getattr(response, "annotation", None)
                    if ann is not None:
                        media = getattr(response, "media_type", "application/json")
                        origin = get_origin(ann)
                        if origin is list or origin is Sequence:
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
            else:
                # Default 200 without schemas
                responses_obj["200"] = {
                    "description": meta.get("response_description") or "Successful response"
                }

            operation["responses"] = responses_obj
            spec["paths"].setdefault(raw_path, {})[m_lower] = operation

    return spec
