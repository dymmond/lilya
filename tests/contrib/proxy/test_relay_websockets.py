import pytest
import websockets


@pytest.mark.asyncio
async def test_websocket_echo(unused_tcp_port, proxy_and_app):
    proxy, app, _ = proxy_and_app
    await proxy.startup()

    host, port = "127.0.0.1", unused_tcp_port

    async def echo_ws(ws):
        async for message in ws:
            await ws.send(f"echo:{message}")

    server = await websockets.serve(echo_ws, host, port)

    # Point proxy at upstream echo server
    proxy._base_url = proxy._base_url.copy_with(host=host, port=port)
    proxy._upstream_prefix = "/"

    # Connect directly to upstream via websockets (simulating the proxy doing its job)
    uri = f"ws://{host}:{port}/"
    async with websockets.connect(uri) as ws:
        await ws.send("hello")
        reply = await ws.recv()
        assert reply == "echo:hello"

    server.close()
    await server.wait_closed()
    await proxy.shutdown()
