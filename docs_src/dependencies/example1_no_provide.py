import os

from lilya.apps import Lilya

# A simple config value
def load_config_value():
    return os.getenv("PAYMENT_API_KEY")

app = Lilya(
    dependencies={
        "api_key": load_config_value
    }
)
