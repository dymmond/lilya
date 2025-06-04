import re
from collections.abc import Callable, Iterator, Sequence
from typing import Any

from lilya import __version__
from lilya.contrib.openapi.params import Query


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
    }
    if servers:
        spec["servers"] = list(servers)
    if tags:
        spec["tags"] = list(tags)
    if webhooks:
        spec["webhooks"] = list(webhooks)

    def _gather_routes(routes_list: Sequence[Any], prefix: str) -> Iterator[tuple[str, Any]]:
        """
        Yield (full_path, route) for each leaf route, stripping out any `{...}` catch-all:
        - If route has .routes (Include), split raw at '/{' to remove '{path}', then recurse.
        - If route has .app with .routes (nested Lilya), split raw at '/{' and recurse into app.routes.
        - Otherwise, yield (prefix + raw, route).
        """
        for route in routes_list:
            raw = getattr(route, "path_format", None) or getattr(route, "path", None)
            if raw is None:
                continue

            if not raw.startswith("/"):
                raw = "/" + raw

            # If this is an Include (has .routes)
            if hasattr(route, "routes") and getattr(route, "routes", None) is not None:
                # Strip off any '{...}' part: split at the first '/{'
                if "/{" in raw:
                    mount_prefix = raw.split("/{", 1)[0]
                else:
                    mount_prefix = raw
                combined = prefix + mount_prefix
                yield from _gather_routes(route.routes, combined)
                continue

            # If this is a mounted child-app (has .app.routes)
            if hasattr(route, "app") and hasattr(route.app, "routes"):
                if "/{" in raw:
                    mount_prefix = raw.split("/{", 1)[0]
                else:
                    mount_prefix = raw
                combined = prefix + mount_prefix
                yield from _gather_routes(route.app.routes, combined)
                continue

            # Leaf path: combine prefix and raw exactly
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

            # Extract path parameters from {param}
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

            # Build query parameters
            user_query_params: list[dict[str, Any]] = []
            for name, query_param in (meta.get("query", {}) or {}).items():
                if isinstance(query_param, Query):
                    user_query_params.append(query_param.as_openapi_dict(name))
                else:
                    user_query_params.append(query_param)

            # Remove any query-declared path params
            declared_path_names = {p["name"] for p in path_parameters}
            merged_query: list[dict[str, Any]] = []
            for p in user_query_params:
                if p.get("in") == "path" and p.get("name") in declared_path_names:
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

            # Build responses
            responses_obj: dict[str, Any] = {}
            seen_responses = meta.get("responses", None)
            if isinstance(seen_responses, dict) and seen_responses:
                for status_code_int, resp in seen_responses.items():
                    status_code = str(status_code_int)
                    desc = getattr(resp, "response_description", "") or ""
                    content_obj: dict[str, Any] = {}
                    if getattr(resp, "model", None):
                        media = getattr(resp, "media_type", "application/json")
                        content_obj[media] = {
                            "schema": {"$ref": f"#/components/schemas/{resp.model.__name__}"}
                        }
                    responses_obj[status_code] = {"description": desc or "Successful response"}
                    if content_obj:
                        responses_obj[status_code]["content"] = content_obj
            else:
                responses_obj["200"] = {
                    "description": meta.get("response_description") or "Successful response"
                }

            operation["responses"] = responses_obj
            spec["paths"].setdefault(raw_path, {})[m_lower] = operation

    return spec
