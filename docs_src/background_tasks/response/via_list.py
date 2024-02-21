from datetime import datetime
from typing import Dict

from lilya.apps import Lilya
from lilya.background import Task, Tasks
from lilya.requests import Request
from lilya.responses import Response
from lilya.routing import Path


async def send_email_notification(email: str, message: str):
    """Sends an email notification"""
    send_notification(email, message)


def write_in_file(email: str):
    with open("log.txt", mode="w") as log:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = f"Notification sent @ {now} to: {email}"
        log.write(content)


async def create_user(request: Request) -> Response(Dict[str, str]):
    return Response(
        {"message": "Email sent"},
        background=Tasks(
            tasks=[
                Task(
                    send_email_notification,
                    email="example@lilya.dev",
                    message="Thank you for registering.",
                ),
                Task(write_in_file, email="example@lilya.dev"),
            ]
        ),
    )


app = Lilya(
    routes=[
        Path(
            "/register",
            create_user,
            methods=["POST"],
        )
    ]
)
