from httpx import AsyncClient
from lilya.apps import Lilya
from lilya.dependencies import Provide, Provides
from lilya.enums import Scope


async def make_client():
    return AsyncClient(base_url="https://api.github.com")

app = Lilya(
    dependencies={
        "client": Provide(make_client, scope=Scope.APP, use_cache=True)
    }
)

@app.get("/repos")
async def list_repos(client=Provides()):
    response = await client.get("/orgs/dymmond/repos")
    return response.json()
