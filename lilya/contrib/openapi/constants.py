METHODS_WITH_BODY = {"GET", "HEAD", "POST", "PUT", "DELETE", "PATCH"}
REF_PREFIX = "#/components/schemas/"
REF_TEMPLATE = "#/components/schemas/{model}"
WRITING_METHODS = {"post", "put", "patch"}
WRITING_STATUS_MAPPING = {
    "post": 201,
    "put": 200,
    "patch": 200,
}
