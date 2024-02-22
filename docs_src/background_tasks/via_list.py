from datetime import datetime

from lilya.apps import Lilya
from lilya.background import Task, Tasks
from lilya.responses import JSONResponse
from lilya.routing import Path


async def send_email_notification(message: str):
    """Sends an email notification"""
    send_notification(message)


def write_in_file():
    with open("log.txt", mode="w") as log:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = f"Notification sent @ {now}"
        log.write(content)


async def create_user() -> JSONResponse:
    background = (
        Tasks(
            tasks=[
                Task(send_email_notification, message="Account created"),
                Task(write_in_file),
            ]
        ),
    )
    JSONResponse({"message": "Created"}, background=background)


app = Lilya(
    routes=[
        Path(
            "/register",
            create_user,
            methods=["POST"],
        )
    ]
)
