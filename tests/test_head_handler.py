from __future__ import annotations

import re

from capitalia.app.handlers import AbstractHandler, HeadHandler
from capitalia.app.http import HttpRequest, HttpResponse, RequestContext, Route


class DummyHandler(AbstractHandler):
    """Minimal handler used to assert delegation from ``HeadHandler``."""

    def __init__(self) -> None:  # pragma: no cover - trivial
        super().__init__()
        self.calls = 0

    def handle(self, ctx: RequestContext) -> HttpResponse:  # pragma: no cover - trivial
        self.calls += 1
        response = HttpResponse(200, {"Content-Length": "4"}, b"test")
        ctx.response = response
        return response


def make_context(method: str) -> RequestContext:
    request = HttpRequest(
        method=method,
        target="/health",
        path="/health",
        query="",
        headers={},
        body=b"",
    )
    ctx = RequestContext(request=request)
    ctx.route = Route("health", re.compile(r"^/health$"), {"GET"}, lambda c: HttpResponse(200))
    return ctx


def test_head_handler_runs_get_pipeline_for_head_requests() -> None:
    ctx = make_context("HEAD")
    head_handler = HeadHandler()
    dummy = DummyHandler()
    head_handler.set_next(dummy)

    response = head_handler.handle(ctx)

    assert dummy.calls == 1
    assert response.status == 200
    # Body is preserved so Content-Length reflects GET response size, but will
    # not be transmitted because the HTTP layer checks the original method.
    assert response.body == b"test"
    assert response.headers["Content-Length"] == "4"
    assert ctx.request.method == "HEAD"


def test_head_handler_passes_through_non_head_requests() -> None:
    ctx = make_context("GET")
    head_handler = HeadHandler()
    dummy = DummyHandler()
    head_handler.set_next(dummy)

    response = head_handler.handle(ctx)

    assert dummy.calls == 1
    assert response.status == 200
