from lilya.responses import Response


def test_text_response(test_client_factory):
    async def app(scope, receive, send):
        response = Response("hello, world", media_type="text/plain")
        await response(scope, receive, send)

    client = test_client_factory(app)
    response = client.get("/")
    assert response.text == "hello, world"
