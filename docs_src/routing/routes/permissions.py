from esmerald import APIView, Lilya, Path, Request, get
from esmerald.permissions import AllowAny, BasePermission, DenyAll


class IsAdmin(BasePermission):
    def has_permission(
        self,
        request: "Request",
        apiview: "APIView",
    ) -> bool:
        return bool(request.path_params["admin"] is True)


@get(path="/home", permissions=[AllowAny])
async def homepage() -> dict:
    return {"page": "ok"}


@get(path="/admin", permissions=[IsAdmin])
async def admin() -> dict:
    return {"page": "ok"}


@get(path="/deny")
async def deny() -> dict:
    return {"page": "tis payload will never be reached"}


app = Lilya(
    routes=[
        Path(handler=homepage),
        Path(handler=admin),
        Path(handler=deny, permissions=[DenyAll]),
    ],
    permissions=[AllowAny],
)
