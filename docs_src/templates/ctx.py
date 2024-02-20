import typing

from lilya.requests import Request


def application_context(request: Request):
    return {"app": request.app}
