from __future__ import annotations

import pytest

from lilya.context import application_context
from lilya.responses import Response
from lilya.routing import Path
from lilya.testclient import create_client


def test_context(test_client_factory):
    def get_data() -> bytes:
        assert application_context.get()
        return Response()

    with create_client(routes=[Path(path="/", handler=get_data)]) as client:
        response = client.get("/")

        assert response.text == ""


def test_no_context():
    with pytest.raises(LookupError):
        application_context.get()
