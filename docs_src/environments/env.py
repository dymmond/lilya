from dataclasses import dataclass

from lilya.conf.global_settings import Settings
from lilya.environments import EnvironLoader

loader = EnvironLoader()


@dataclass
class DatabaseSettings(Settings):
    database_name: str = loader.env("DATABASE_NAME", cast=str, default="mydb")
    database_user: str = loader.env("DATABASE_USER", cast=str, default="postgres")
    database_password: str = loader.env("DATABASE_PASSWD", cast=str, default="postgres")
    database_host: str = loader.env("DATABASE_HOST", cast=str, default="localhost")
    database_port: int = loader.env("DATABASE_PORT", cast=int, default=5432)
    api_key: str = loader.env("API_KEY", cast=str, default="")
