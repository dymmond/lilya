import sys
from typing import Annotated

from asyncpg.exceptions import UniqueViolationError
from lilya.cli.decorator import directive
from sayer import command, success, error, Option

from ..main import User


@directive
@command
def create(
    first_name: Annotated[str, Option(required=True)],
    last_name: Annotated[str, Option(required=True)],
    username: Annotated[str, Option(required=True)],
    email: Annotated[str, Option(required=True)],
    password: Annotated[str, Option(required=True)],
):
    """
    Creates a superuser with the given first name and last name.
    """
    try:
        user = await User.query.create_superuser(
            first_name=first_name,
            last_name=last_name,
            username=username,
            email=email,
            password=password,
        )
    except UniqueViolationError:
        error(f"User with email {email} already exists.")
        sys.exit(0)

    success(f"Superuser {user.email} created successfully.")
