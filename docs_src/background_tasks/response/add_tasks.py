from datetime import datetime

from lilya.app import Lilya
from lilya.background import Tasks
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


async def create_user(request: Request):
    background_tasks = Tasks(as_group=True)
    background_tasks.add_task(
        send_email_notification,
        email="example@lilya.dev",
        message="Thank you for registering.",
    )
    background_tasks.add_task(write_in_file, email=request.user.email)

    return Response({"message": "Email sent"}, background=background_tasks)


app = Lilya(
    routes=[
        Path(
            "/register",
            create_user,
            methods=["POST"],
        )
    ]
)
