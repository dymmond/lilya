import os

from lilya.apps import Lilya
from lilya.dependencies import Provide

# A simple config value
def load_config_value():
    return os.getenv("PAYMENT_API_KEY")

app = Lilya(
    dependencies={
        "api_key": Provide(load_config_value)
    }
)
