from lilya.apps import Lilya
from lilya.routing import Path
from lilya.responses import CSVResponse


async def export_data():
    data = [
        {"name": "Lilya", "age": 35},
        {"name": "Maria", "age": 28},
    ]
    return CSVResponse(content=data)

app = Lilya(
    routes=[Path("/export", export_data)]
)
