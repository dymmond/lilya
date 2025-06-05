from lilya.contrib.openapi.decorator import openapi

description = """
Returns a list of all registered users.

You can filter by roles and active status.
"""

@openapi(
    summary="Fetch all users",
    description=description,
    tags=["users", "public"],
)
async def list_users(request):
    ...
