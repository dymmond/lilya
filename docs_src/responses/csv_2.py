from lilya.apps import Lilya
from lilya.routing import Path
from lilya.responses import CSVResponse


async def download():
    users = [
        {"username": "admin", "email": "admin@example.com"},
        {"username": "guest", "email": "guest@example.com"},
    ]
    headers = {
        "Content-Disposition": 'attachment; filename="users.csv"'
    }
    return CSVResponse(content=users, headers=headers)

app = Lilya(
    routes=[Path("/download", download)]
)
