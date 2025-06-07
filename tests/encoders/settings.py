from dataclasses import dataclass

from tests.settings import TestSettings


@dataclass
class EncoderSettings(TestSettings):
    infer_body: bool = True
