import re
from collections.abc import Callable, Sequence
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

    for route in routes:
        # Only include in schema if flagged
        if not getattr(route, "include_in_schema", False):
            continue

        raw_path = getattr(route, "path_format", None) or getattr(route, "path", None)
        if not raw_path:
            continue

        # Ensure it starts with “/”
        if not raw_path.startswith("/"):
            raw_path = "/" + raw_path

        methods = getattr(route, "methods", ["GET"])
        for method in methods:
            m_lower = method.lower()
            handler: Callable[..., Any] = getattr(route, "handler", None)
            meta: dict[str, Any] = getattr(handler, "openapi_meta", {}) or {}

            # Build “path”‐params from `{foo}` in the route
            path_param_names = re.findall(r"\{([^}]+)\}", raw_path)
            path_parameters = []
            for name in path_param_names:
                path_parameters.append(
                    {
                        "name": name,
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                )

            # Build “query”‐params from any Query(...) instances
            user_query_params = []
            for name, query_param in (meta.get("query", {}) or {}).items():
                # query_param is a Query(...) instance → call its helper
                if isinstance(query_param, Query):
                    user_query_params.append(query_param.as_openapi_dict(name))
                else:
                    # If someone passed a raw dict by mistake, just trust it if it has "in": "query"
                    user_query_params.append(query_param)

            # If any user defined a path-param with Query( in_="path" ), skip duplication
            declared_path_names = {p["name"] for p in path_parameters}
            merged_query = []
            for p in user_query_params:
                if p.get("in") == "path" and p.get("name") in declared_path_names:
                    continue
                merged_query.append(p)

            # Combine path + query
            combined_params = path_parameters + merged_query

            # Build the “operation” block
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

            # Attach “parameters” if we have any
            if combined_params:
                operation["parameters"] = combined_params

            # Build “responses” exactly as before ───
            responses_obj: dict[str, Any] = {}
            seen_responses = meta.get("responses", None)
            if isinstance(seen_responses, Sequence) and len(seen_responses) > 0:
                for resp in seen_responses:
                    status_code = str(getattr(resp, "status_code", 200))
                    desc = getattr(resp, "response_description", "") or ""
                    content_obj = {}
                    if resp.model:
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

            # Insert under paths
            spec["paths"].setdefault(raw_path, {})[m_lower] = operation

    return spec
