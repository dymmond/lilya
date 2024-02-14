from typing import Any

import saffier
from saffier import Database, Registry

from lilya.app import Lilya

database = Database("postgres://postgres:password@localhost:5432/my_db")
registry = Registry(database=database)


class User(saffier.Model):
    """
    Base model used for a custom user of any application.
    """

    first_name = saffier.CharField(max_length=150)
    last_name = saffier.CharField(max_length=150)
    username = saffier.CharField(max_length=150, unique=True)
    email = saffier.EmailField(max_length=120, unique=True)
    password = saffier.CharField(max_length=128)
    last_login = saffier.DateTimeField(null=True)
    is_active = saffier.BooleanField(default=True)
    is_staff = saffier.BooleanField(default=False)
    is_superuser = saffier.BooleanField(default=False)

    class Meta:
        registry = registry

    @classmethod
    async def create_superuser(
        cls,
        username: str,
        email: str,
        password: str,
        **extra_fields: Any,
    ):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return await cls._create_user(username, email, password, **extra_fields)

    @classmethod
    async def _create_user(cls, username: str, email: str, password: str, **extra_fields: Any):
        """
        Create and save a user with the given username, email, and password.
        """
        if not username:
            raise ValueError("The given username must be set")
        user = await cls.query.create(
            username=username, email=email, password=password, **extra_fields
        )
        return user


def get_application():
    """
    This is optional. The function is only used for organisation purposes.
    """

    app = Lilya(
        routes=[],
        on_startup=[database.connect],
        on_shutdown=[database.disconnect],
    )

    return app


app = get_application()
