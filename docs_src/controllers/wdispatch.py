from typing import Any

from lilya.apps import Lilya
from lilya.controllers import Controller, WebSocketController
from lilya.responses import HTMLResponse
from lilya.routing import Path, WebSocketPath
from lilya.websockets import WebSocket

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Submit</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws = new WebSocket("ws://localhost:8000/websocket");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""


class HomepageController(Controller):
    async def get(self):
        return HTMLResponse(html)


class EchoController(WebSocketController):
    encoding = "text"

    async def on_receive(self, websocket: WebSocket, data: Any):
        await websocket.send_text(f"Message text was: {data}")


app = Lilya(
    routes=[
        Path("/", HomepageController),
        WebSocketPath()("/websocket", EchoController),
    ]
)
