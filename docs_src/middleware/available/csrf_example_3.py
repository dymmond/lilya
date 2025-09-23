from lilya.apps import Lilya
from lilya.middleware import DefineMiddleware
from lilya.middleware.csrf import CSRFMiddleware
from lilya.responses import HTMLResponse, Ok
from lilya.routing import Path
from lilya.requests import Request

# Simple template function; in real apps you might use Jinja.
def login_page(request: Request) -> str:
    token = request.cookies.get("csrftoken", "")  # needs httponly=False
    return f"""
    /login
      <input type="text" name="username" />
      <input type="password" name="password" />
      <input type="hidden" name="csrf_token" value="{token}" />
      <button type="submit">Login</button>
    </form>
    """

async def get_login(request: Request):
    return HTMLResponse(login_page(request))

async def post_login(request: Request):
    form = await request.form()
    return Ok({"username": form.get("username")})

app = Lilya(
    routes=[
        Path("/login", get_login, methods=["GET"]),
        Path("/login", post_login, methods=["POST"]),
    ],
    middleware=[
        DefineMiddleware(
            CSRFMiddleware,
            secret="change-me-long-random",
            httponly=False,   # template reads the cookie
            samesite="lax",
            secure=False,     # True in production
        )
    ],
)