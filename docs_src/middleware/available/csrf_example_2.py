from lilya.apps import Lilya
from lilya.middleware import DefineMiddleware
from lilya.middleware.csrf import CSRFMiddleware
from lilya.responses import Ok
from lilya.routing import Path

async def login():
    return Ok({"status": "ok"})

app = Lilya(
    routes=[Path("/login", login, methods=["GET", "POST"])],
    middleware=[
        DefineMiddleware(
            CSRFMiddleware,
            secret="change-me-long-random",
            # Using header path; HttpOnly can stay True if you never read the cookie in templates
            httponly=True,
            samesite="lax",
            secure=False,  # True in production
        )
    ],
)
