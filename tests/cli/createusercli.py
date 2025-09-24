from __future__ import annotations

import random
import string
from typing import Annotated

from sayer import Option, command, success

from lilya.cli.decorator import directive


def get_random_string(length=10):
    letters = string.ascii_lowercase
    result_str = "".join(random.choice(letters) for i in range(length))
    return result_str


@directive(display_in_cli=True)
@command
async def create_user(
    name: Annotated[str, Option(None, "-n", required=True)],
):
    """
    Test directive for creating a user
    """

    success(f"Superuser {name} created successfully.")
