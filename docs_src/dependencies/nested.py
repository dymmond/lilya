from lilya.apps import Lilya
from lilya.dependencies import Provide, Provides
from httpx import AsyncClient

# 1) client factory
async def get_http_client():
    return AsyncClient()

# 2) token factory uses client
async def get_access_token(client: AsyncClient=Provides()):
    resp = await client.post("https://auth/", json={...})
    return resp.json()["token"]

app = Lilya(
    dependencies={
        "client": Provide(get_http_client, use_cache=True),
        "token": Provide(get_access_token)
    }
)

@app.get("/secure-data")
async def secure_data(token=Provides()):
    return await fetch_secure(token)
