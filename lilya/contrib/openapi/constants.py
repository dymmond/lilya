METHODS_WITH_BODY = {"GET", "HEAD", "QUERY", "POST", "PUT", "DELETE", "PATCH"}
REF_PREFIX = "#/components/schemas/"
REF_TEMPLATE = "#/components/schemas/{model}"
REQUEST_BODY_METHODS = {"query", "post", "put", "patch"}
WRITING_METHODS = {"post", "put", "patch"}
WRITING_STATUS_MAPPING = {
    "post": 201,
    "put": 200,
    "patch": 200,
}
