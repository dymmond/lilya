from lilya.apps import Lilya
from lilya.controllers import Controller
from lilya.responses import PlainText
from lilya.routing import Path

class GreetingController(Controller):
    def __init__(self, greeting: str):
        self.greeting = greeting

    async def get(self) -> PlainText:
        return PlainText(f"{self.greeting}, world!")

app = Lilya(
    routes=[Path("/", handler=GreetingController.with_init(greeting="Hello"))]
)
